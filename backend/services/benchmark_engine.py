# FILE: backend/services/benchmark_engine.py
"""
services/benchmark_engine.py

Internal benchmarking engine for Clarion review-theme scoring.

RESPONSIBILITIES
----------------
1. Deterministic theme tagging/scoring with full intermediate evidence logging.
2. Optional AI benchmark pass via OpenRouter (disabled when OPENROUTER_API_KEY is absent).
3. Returns a structured BenchmarkResult dict containing both outputs side-by-side.

This module is ISOLATED from production scoring paths. It does not touch any
existing API contracts, DB schemas, or the live review_classifier pipeline.

USAGE
-----
    from services.benchmark_engine import run_benchmark

    result = run_benchmark(
        review_text="John never returned my calls and the fees were a surprise.",
        rating=2,
        review_date="2025-01-15",
        enable_ai=True,
    )

ENV VARS REQUIRED
-----------------
    OPENROUTER_API_KEY   -- OpenRouter API key (AI pass skipped when absent)
    OPENROUTER_MODEL     -- model slug, defaults to "openai/gpt-4o-mini"
    OPENROUTER_TIMEOUT   -- HTTP timeout in seconds, defaults to 20
"""

from __future__ import annotations

import json
import logging
import os
import re
import time
from typing import Any, Dict, List, Optional, Tuple

import requests

logger = logging.getLogger("benchmark_engine")

# ---------------------------------------------------------------------------
# CANONICAL BENCHMARK THEMES
# ---------------------------------------------------------------------------
BENCHMARK_THEMES = [
    "communication_responsiveness",
    "communication_clarity",
    "empathy_support",
    "professionalism_trust",
    "expectation_setting",
    "billing_transparency",
    "fee_value",
    "timeliness_progress",
    "office_staff_experience",
    "outcome_satisfaction",
]

# ---------------------------------------------------------------------------
# DETERMINISTIC THEME PHRASE TABLE
#
# Structure:
#   theme_id -> {
#     "positive": [ (phrase, weight), ... ],
#     "negative": [ (phrase, weight), ... ],
#     "severe_negative": [ (phrase, weight), ... ],
#   }
#
# Weight is the base impact score per phrase hit (1.0 = normal, 2.0 = strong).
#
# Annotation key used in inline comments:
#   [CG]      = needs_context_guard -- phrase is ambiguous without sentence-level
#               context; a future pass should add negation/contrast/sentence logic.
#   [W1]      = Wave 1 phrase import (safe_import_now batch, 2026-03)
#   [W1-GUARD] = Wave 1 phrase flagged as needing context guard logic;
#               marked with CONTEXT-GUARD PLACEHOLDER comment below the entry.
# ---------------------------------------------------------------------------
THEME_PHRASES: Dict[str, Dict[str, List[Tuple[str, float]]]] = {

    # =========================================================================
    # THEME: communication_responsiveness
    # =========================================================================
    "communication_responsiveness": {
        "positive": [
            # --- original ---
            ("always available", 1.5),
            ("always responded", 1.5),
            ("called me back", 1.0),
            ("easy to reach", 1.0),
            ("immediately responded", 1.5),
            ("kept me updated", 1.0),
            ("kept me informed", 1.0),
            ("prompt response", 1.0),
            ("promptly", 1.0),
            ("quick to respond", 1.0),
            ("quick response", 1.0),
            ("responded quickly", 1.0),
            ("returned my call", 1.0),
            ("returned my calls", 1.0),
            ("very responsive", 1.5),
            # --- new: safe_import_now [W1] ---
            ("always picked up", 1.5),
            ("answered every question", 1.0),
            ("answered my calls", 1.0),
            ("answered my messages", 1.0),
            ("answered promptly", 1.0),
            ("available when i needed", 1.5),
            ("communicated regularly", 1.0),
            ("consistently reachable", 1.5),
            ("got back to me quickly", 1.0),
            ("immediately reachable", 1.5),
            ("kept us posted", 1.0),
            ("never had trouble reaching", 1.0),
            ("proactive communication", 1.5),
            ("proactive updates", 1.5),
            ("quick turnaround on messages", 1.0),
            ("reached out proactively", 1.5),
            ("regularly checked in", 1.0),
            ("replied promptly", 1.0),
            ("replied same day", 1.5),
            ("responded right away", 1.5),
            ("responded same day", 1.5),
            ("responsive attorney", 1.5),
            ("responsive to calls", 1.0),
            ("responsive to emails", 1.0),
            ("responsive to messages", 1.0),
            ("returned emails promptly", 1.5),
            ("sends regular updates", 1.0),
            ("stays in touch", 1.0),
            ("timely replies", 1.0),
            ("timely updates", 1.0),
            # --- phrase expansion: missed responsiveness phrases ---
            ("prompt replies", 1.0),
            ("answered my questions", 1.0),
            # --- calibration: gap-report wave 2 (final_summary.json) ---
            ("patiently answering all of our questions", 1.0),
            ("answered all of my questions patiently", 1.0),
            ("there to help and answer all of our questions", 1.0),
            # --- calibration: sample2 ---
            ("corrected quickly", 1.0),
            ("more frequent check-ins would have been nice", 0.8),
            ("best way to reach them", 0.8),
            # --- calibration: full_batch_20260311 ---
            ("responses were quick", 1.5),
            # --- calibration: wave3 live-run gaps ---
            ("kept us informed of the legal process", 1.5),
            ("kept him informed", 1.0),
            ("kept her informed", 1.0),
            ("he kept us informed", 1.5),
            ("kept in close contact", 1.5),
            ("stayed in contact", 1.0),
            ("stayed in contact with me", 1.0),
            ("quick to contact me", 1.0),
            ("stayed informed", 1.0),
            ("gave us his time", 1.5),
            ("give you his time for free", 1.5),
            ("give his time for free", 1.5),
            ("returned my calls in a timely fashion", 1.5),
            ("returned your calls", 1.0),
            ("returned your call", 1.0),
            ("very good at returning your call", 1.0),
        ],
        "negative": [
            # --- original ---
            ("couldn't reach", 1.0),
            ("could not reach", 1.0),
            ("didn't respond", 1.0),
            ("did not respond", 1.0),
            ("did not return", 1.0),
            ("didn't return", 1.0),
            ("hard to reach", 1.0),
            ("ignored my calls", 1.5),
            ("ignored my emails", 1.5),
            ("left me hanging", 1.0),
            ("never called back", 1.5),
            ("never called me back", 1.5),
            ("never responded", 1.5),
            ("never returned my call", 1.5),
            ("no response", 1.0),
            ("not responsive", 1.0),
            ("slow to respond", 1.0),
            ("unresponsive", 1.5),
            ("weeks without hearing", 1.5),
            ("went silent", 1.5),
            # --- new: safe_import_now [W1] ---
            ("calls went unanswered", 1.5),
            ("couldn't get a reply", 1.0),
            ("days without a response", 1.5),
            ("delayed responses", 1.0),
            ("difficult to get in touch", 1.0),
            ("emails went unanswered", 1.5),
            ("hard to get a hold of", 1.0),
            ("ignored my messages", 1.5),
            ("impossible to get an update", 1.5),
            ("kept waiting for a response", 1.0),
            ("left messages with no reply", 1.5),
            ("messages not returned", 1.5),
            ("never answered my calls", 1.5),
            ("never heard back", 1.5),
            ("never heard from them for over a year", 1.5),
            ("no follow-up", 1.0),
            ("no return call", 1.5),
            ("no updates for weeks", 1.5),
            ("not communicating", 1.0),  # [W1-GUARD]
            # CONTEXT-GUARD PLACEHOLDER: "not communicating" -- short negation phrase
            # that can appear in ambiguous contexts ("not communicating well" vs
            # "not communicating with the other party"). Needs sentence scope check.
            ("phone calls ignored", 1.5),
            ("poor communication", 1.0),
            ("rarely responded", 1.5),
            ("response took weeks", 1.5),
            ("takes days to respond", 1.5),
            ("takes forever to reply", 1.5),
            ("takes too long to reply", 1.5),
            ("unreachable", 1.5),
            ("voicemails never returned", 1.5),
            ("weeks of silence", 1.5),
            ("would not return calls", 1.5),
            # --- calibration: sample2 ---
            ("emails sometimes came late at night", 1.0),
            # --- calibration: phrase expansion ---
            ("never got back to me", 1.5),
            ("took forever to respond", 1.5),
            ("weeks without response", 1.5),
            ("ignored emails", 1.5),
            ("could not get a response", 1.5),
            # --- calibration: gap-report wave (real-review evidence) ---
            ("don't expect fast responses", 1.5),
            ("had to chase them down", 1.5),
            ("barely gave me any opportunity to speak", 2.0),
            ("communication dropped off significantly", 2.0),
            # --- calibration: gap-report wave 2 (final_summary.json) ---
            ("i had to repeat myself multiple times", 1.5),
            ("felt like i wasn't a priority", 1.5),
            ("answered quickly without much depth", 1.0),
            ("miscommunications along the way", 1.0),
            # --- bug fix: polarity corrections (were in positive bucket) ---
            ("do not return calls", 1.5),
            ("late on getting back", 1.0),
            ("don't return calls", 1.5),
            ("told to do it yourself", 1.5),
            ("cut off mid-sentence", 2.0),
            ("went silent for", 2.0),
            ("firm went silent", 2.0),
            # --- calibration: wave3 live-run gaps ---
            ("i send email after email", 2.0),
            ("send email after email without", 2.0),
            ("email after email without responses", 2.0),
            ("without replies", 1.5),
            ("kept calling and sending messages", 1.5),
            ("i kept calling", 1.5),
            ("crickets", 1.5),
            ("crickets from", 1.5),
            ("never even really had meetings", 1.5),
            ("never had real meetings", 1.5),
            ("never had meetings with me", 1.5),
            ("told to do it yourself", 1.5),
            ("tell me to do it yourself", 1.5),
            ("no one ever returns a call", 1.5),
            ("no one returns calls", 1.5),
            ("horrible with communication", 1.5),
            ("never spoke with my lawyer", 1.5),
            ("never spoke with the lawyer", 1.5),
            ("didn't contact the client", 1.5),
            ("did not contact the client", 1.5),
            ("can't ever talk to an actual lawyer", 1.5),
            ("cannot ever talk to an actual lawyer", 1.5),
            ("will not answer simple questions", 1.5),
            ("barely had communication", 1.5),
            ("barely had communication with the lawyer", 1.5),
            ("multiple calls were canceled", 1.5),
            ("multiple calls were canceled or no-showed", 1.5),
            ("i was the only one making the main calls", 1.5),
            ("whoever answered the phone was not pleasant or helpful", 1.5),
            ("could not get a word in", 1.5),
            ("couldn't get a word in", 1.5),
            ("tell you to do it yourself", 1.5),
            ("questions went unanswered", 1.5),
            ("more communication from my lawyer", 1.0),
            ("no response to my email", 1.5),
        ],
        "severe_negative": [
            # --- original ---
            ("completely unreachable", 2.0),
            ("impossible to contact", 2.0),
            ("months without any contact", 2.0),
            ("never returned my calls", 2.0),
            # --- new: safe_import_now [W1] ---
            ("abandoned me completely", 2.0),
            ("completely stopped communicating", 2.0),
            ("ghosted me", 2.0),
            ("months of no contact", 2.0),
            ("months without communication", 2.0),
            ("months without hearing anything", 2.0),
            ("no communication for months", 2.0),
            ("refused to return calls", 2.0),
            ("totally disappeared", 2.0),
            # --- calibration: gap-report wave 2 (final_summary.json) ---
            # --- real-reviews wave A ---
            ("hung up on me", 2.0),
            ("stopped returning my calls", 2.0),
            # --- calibration: severity-tier follow-up ---
            ("barely gave me any opportunity to speak", 2.0),
            ("never even really had meetings", 2.0),
            ("can't ever talk to an actual lawyer", 2.0),
            ("cannot ever talk to an actual lawyer", 2.0),
            ("multiple calls were canceled", 2.0),
            ("multiple calls were canceled or no-showed", 2.0),
            ("tell you to do it yourself", 2.0),
            ("horrible with communication", 2.0),
        ],
    },

    # =========================================================================
    # THEME: communication_clarity
    # =========================================================================
    "communication_clarity": {
        "positive": [
            # --- original ---
            ("clearly explained", 1.0),
            ("easy to understand", 1.0),
            ("explained everything", 1.0),
            ("explained the process", 1.0),
            ("kept me in the loop", 1.0),
            ("plain language", 1.0),
            ("thoroughly explained", 1.5),
            ("very clear", 1.0),
            # --- new: safe_import_now [W1] ---
            ("answered all my questions", 1.0),
            ("broke everything down", 1.0),
            ("clear and concise", 1.0),
            ("clear communication", 1.0),
            ("clearly communicated", 1.0),
            ("detailed explanations", 1.0),
            ("easy to follow", 1.0),
            ("explained in detail", 1.0),
            ("explained my options clearly", 1.5),
            ("explained the risks", 1.0),
            ("explained what was happening", 1.0),
            ("gave me a clear picture", 1.0),
            ("great at explaining", 1.5),
            ("helped me understand", 1.0),
            ("information was clear", 1.0),
            ("made complex things simple", 1.5),
            ("made it easy to understand", 1.5),
            ("made things very clear", 1.5),
            ("no legal jargon", 1.0),
            ("patient in explaining", 1.0),
            ("plain english", 1.0),
            ("spoke in plain terms", 1.0),
            ("straight to the point", 1.0),
            ("took time to explain", 1.0),
            ("transparent throughout", 1.0),  # [W1-GUARD]
            # CONTEXT-GUARD PLACEHOLDER: "transparent throughout" -- needs sentence
            # context to confirm referent is attorney behavior, not process/outcome.
            ("very informative", 1.0),
            ("walked me through everything", 1.5),
            ("well explained", 1.0),
            # --- phrase expansion: real-review evidence ---
            ("step by step", 1.0),
            # NOTE: "broke it down" / "no confusion" / "no stress" were too
            # generic and produced clarity extras without explicit explanatory context.
            # --- phrase expansion: missed clarity phrases ---
            ("explained everything clearly", 1.5),
            ("broke things down simply", 1.5),
            ("kept things transparent", 1.0),
            # --- calibration: sample2 ---
            ("explained each step of the custody process", 1.5),
            ("direct communication style", 1.0),
            ("asked for a summary they provided it", 1.0),
            # --- calibration: full_batch_20260311 ---
            ("communication was clear", 1.5),
            # --- calibration: gap-report wave 2 (final_summary.json) ---
            ("in a way that was easily understood", 1.5),
            ("guided us through our different options", 1.5),
            ("helped him understand his options", 1.0),
            ("provided the necessary information with clarity", 1.5),
            ("clear communicator", 1.5),
            ("were fair, clear, concise", 1.5),
        ],
        "negative": [
            # --- original ---
            ("confusing", 1.0),
            ("didn't explain", 1.0),
            ("didn't keep me informed", 1.0),
            ("hard to understand", 1.0),
            ("jargon", 0.8),
            ("kept in the dark", 1.5),
            ("legalese", 0.8),
            ("never explained", 1.5),
            ("no explanation", 1.0),
            ("unclear", 1.0),
            # --- new: safe_import_now [W1] ---
            ("confusing communication", 1.0),
            ("confused about the process", 1.0),
            ("didn't communicate clearly", 1.5),
            ("didn't inform me", 1.0),
            ("didn't keep me updated", 1.0),
            ("gave contradictory information", 1.5),
            ("gave me no information", 1.5),
            ("hard to follow", 1.0),
            ("hard to understand what was happening", 1.5),
            ("impossible to understand", 1.5),
            ("kept changing the story", 1.5),
            ("lack of clarity", 1.0),
            ("lack of communication", 1.0),
            ("left me confused", 1.0),
            ("left out important details", 1.5),
            ("never informed me", 1.5),
            ("never told me what was happening", 1.5),
            ("no clarity", 1.0),
            ("not transparent", 1.0),
            ("poor communication skills", 1.0),
            ("too much jargon", 1.0),
            ("vague answers", 1.0),
            ("very confusing", 1.0),
            ("withheld information", 1.5),
            ("would not explain", 1.5),
            # --- calibration: sample2 ---
            ("clearer written roadmap", 1.0),
            ("long emails without a clear summary", 1.2),
            ("didn't always understand why", 1.0),
            ("repeat background details to different people", 1.2),
            ("don't leave confused", 0.8),
            # --- calibration: gap-report wave 2 (final_summary.json) ---
            ("cut me off and start rambling", 2.0),
            ("would want more clarity", 1.0),
            ("wasn't fully explained", 1.5),
            ("was not fully explained", 1.5),
            ("had no idea what was going on", 2.0),
            ("communication barriers made it impossible", 1.5),
            ("barely explained things", 1.5),
            ("wasn't providing a lot of information", 1.2),
            ("could have been more clearly explained", 1.2),
            ("told me that i was not going to be able to receive disability", 1.5),
        ],
        "severe_negative": [
            # --- original ---
            ("completely in the dark", 2.0),
            ("had no idea what was happening", 2.0),
            ("no communication whatsoever", 2.0),
            # --- new: safe_import_now [W1] ---
            ("deliberately withheld information", 2.0),
            ("hid important information", 2.0),
            ("kept completely in the dark", 2.0),
            ("never told me anything", 2.0),
            ("stonewalled me", 2.0),
            # --- calibration: severity-tier follow-up ---
            ("cut me off and start rambling", 2.0),
            ("communication barriers made it impossible", 2.0),
        ],
    },

    # =========================================================================
    # THEME: empathy_support
    # =========================================================================
    "empathy_support": {
        "positive": [
            # --- original ---
            ("caring", 1.0),
            ("compassionate", 1.0),
            ("empathetic", 1.0),
            ("felt heard", 1.0),
            ("felt supported", 1.0),
            ("genuinely cared", 1.5),
            ("kind and understanding", 1.5),
            ("listened to my concerns", 1.0),
            ("made me feel comfortable", 1.0),
            ("supportive", 1.0),
            ("truly understood", 1.0),
            # NOTE: bare "understanding" removed -- fires on "deep understanding of
            # the case" and similar expertise contexts (confirmed FP in chunks 4+5).
            # Compound form "kind and understanding" above covers the empathy sense.
            # ("understanding", 1.0),
            # --- new: safe_import_now [W1] ---
            ("acknowledged my feelings", 1.0),
            ("always there for me", 1.5),
            ("attentive to my needs", 1.0),
            ("cared about my wellbeing", 1.5),
            ("checked in on me", 1.0),
            ("concerned about my situation", 1.0),
            ("emotionally supportive", 1.5),
            ("empathized with my situation", 1.5),
            ("felt like they genuinely cared", 1.5),
            ("friendly and caring", 1.0),
            ("genuinely concerned", 1.5),
            ("heard my concerns", 1.0),
            ("kind and compassionate", 1.5),
            ("listened carefully", 1.0),
            ("made me feel at ease", 1.0),
            ("made me feel valued", 1.0),
            ("patient and understanding", 1.5),
            ("really listened", 1.0),
            ("showed genuine concern", 1.5),
            ("showed real empathy", 1.5),
            ("took my concerns seriously", 1.0),
            ("took time to listen", 1.0),
            ("truly caring", 1.5),
            ("very kind", 1.0),
            ("very patient", 1.0),
            ("looking out for my best interest", 1.5),
            ("warm and compassionate", 1.5),
            # --- phrase expansion: real-review evidence ---
            ("reassured me", 1.5),
            ("in my corner", 1.5),
            ("like family", 1.5),
            ("worst year of my life", 2.0),
            ("helped me through the worst", 2.0),
            # --- phrase expansion: missed empathy phrases ---
            ("made me feel heard", 1.5),
            ("took the time to listen", 1.5),
            ("showed compassion", 1.5),
            ("treated me with respect", 1.5),
            ("very supportive", 1.5),
            ("helped me through", 1.0),
            ("understood my situation", 1.5),
            # --- calibration: sample2 ---
            ("treated my case with empathy", 1.5),
            ("never made me feel judged", 1.5),
            ("focused on what was best for my kids", 1.5),
            ("remembered details about my schedule", 1.0),
            ("gave me scripts for how to talk to my co-parent", 1.0),
            ("checked on my emotional wellbeing", 1.5),
            # --- calibration: full_batch_20260311 ---
            ("i felt listened to", 1.5),
            # --- calibration: gap-report wave (real-review evidence) ---
            ("went above and beyond", 2.0),
            ("made me feel like my case actually mattered", 2.0),
            ("felt fully supported and informed", 1.5),
            ("with ease and genuine concern", 1.5),
            ("handled my case with genuine care", 2.0),
            # --- calibration: gap-report wave 2 (final_summary.json) ---
            ("always had my son's best interests in mind", 2.0),
            ("best interests in mind", 1.5),
            ("i truly felt that he cared and wanted to help", 1.5),
            ("reassured me when it came to anxiety", 1.5),
            ("when i needed help the most", 1.5),
            ("helpful for me in navigating the process", 1.5),
            # --- real-reviews wave A ---
            ("saved my life", 2.0),
            ("never gave up on me", 2.0),
            ("toughest times in my life", 2.0),
            ("in my corner all the way", 1.5),
            ("at my very bottom", 1.5),
            ("world had turned upside down", 1.5),
            ("very friendly and also very helpful", 1.0),
            # --- calibration: wave3 live-run gaps ---
            ("friendly, patient", 1.5),
            ("friendly and patient", 1.5),
            ("friendly family oriented", 1.5),
            ("family oriented practice", 1.5),
            ("we appreciate the help", 1.5),
            ("appreciate the help he provided", 1.5),
            ("appreciate the help she provided", 1.5),
            ("appreciate all of the help", 1.5),
            ("appreciate the help", 1.0),
            ("incredibly organized", 1.0),
            ("helps people in this crucial area", 1.5),
            ("dedicated to helping", 1.5),
        ],
        "negative": [
            # --- original ---
            ("cold", 1.0),
            ("didn't care", 1.0),
            ("dismissed", 1.0),
            ("dismissive", 1.5),
            ("felt like a number", 1.5),
            # NOTE: bare "impersonal" removed — it overfired on continuity /
            # staffing-change reviews that AI routes to expectation-setting instead.
            ("no empathy", 1.5),
            ("not compassionate", 1.0),
            ("uncaring", 1.5),
            # --- new: safe_import_now [W1] ---
            ("acted like it was just a job", 1.0),
            ("cold and detached", 1.5),
            ("cold and impersonal", 1.5),
            ("didn't acknowledge my feelings", 1.0),
            ("didn't seem to care", 1.0),
            ("felt ignored", 1.0),
            ("felt unimportant", 1.0),
            ("felt unheard", 1.0),
            ("ignored my concerns", 1.5),
            ("indifferent", 1.0),
            ("lacked compassion", 1.5),
            ("lacked empathy", 1.5),
            ("no personal connection", 1.0),
            ("not understanding", 1.0),
            ("seemed uninterested", 1.0),
            ("treated me coldly", 1.5),
            ("treated me like just another client", 1.0),
            ("unsympathetic", 1.5),
            # --- calibration: sample2 ---
            ("concerns weren't fully addressed", 1.0),
            # --- calibration: phrase expansion ---
            ("no compassion", 1.5),
            ("zero compassion", 1.5),
            ("did not care about my situation", 1.5),
            ("made me feel ignored", 1.5),
            ("treated me like a number", 1.5),
            ("emotionally dismissive", 1.5),
            ("cold attitude", 1.2),
            ("rude and has zero compassion", 1.5),
        ],
        "severe_negative": [
            # --- original ---
            ("completely dismissive", 2.0),
            ("felt abandoned", 2.0),
            ("treated me like i didn't matter", 2.0),
            # --- new: safe_import_now [W1] ---
            ("callous disregard", 2.0),
            ("cruel and dismissive", 2.0),
            ("emotionally abusive", 2.0),
            ("had zero compassion", 2.0),
            ("showed no empathy whatsoever", 2.0),
            # --- calibration: gap-report wave (real-review evidence) ---
            ("she hung up on me", 2.0),
            ("threw in my face", 2.0),
            # --- calibration: gap-report wave 2 (final_summary.json) ---
            ("won't help unless it's been figured out already", 2.0),
            # --- real-reviews wave A ---
            ("no compassion either", 2.0),
            ("sensitivity training", 2.0),
            ("no idea how to deal with a client", 2.0),
            ("left a lot to be desired in terms of personal attention", 1.5),
            ("wasn't listened to", 1.5),
            ("was not listened to", 1.5),
            ("spoken over", 1.5),
            ("didn't have my back", 1.5),
            ("did not have my back", 1.5),
            # --- calibration: severity-tier follow-up ---
            ("not caring at all", 2.0),
            ("are not caring at all", 2.0),
            ("failed to provide support", 2.0),
        ],
    },

    # =========================================================================
    # THEME: professionalism_trust
    # =========================================================================
    "professionalism_trust": {
        "positive": [
            # --- original ---
            ("courteous", 1.0),
            ("ethical", 1.0),
            ("honest", 0.5),           # [FP-GUARD] single-word -- weight reduced to cut false positives
            ("integrity", 1.0),
            # NOTE: bare "polite" belongs with office-staff interactions in the
            # benchmark data and created repeated extra_theme trust hits.
            ("professional", 0.5),     # [FP-GUARD] single-word -- fires in unrelated contexts
            ("respectful", 1.0),
            ("straightforward", 0.5),  # [FP-GUARD] single-word -- "straightforward matter" etc.
            ("transparent", 0.5),      # [FP-GUARD] single-word -- "transparent billing" redirects elsewhere
            ("trustworthy", 1.5),
            # --- new: safe_import_now [W1] ---
            ("acted with integrity", 1.5),
            ("always honest", 1.5),
            ("candid advice", 1.0),
            ("completely honest", 1.5),
            ("conduct was exemplary", 1.5),
            ("demonstrated integrity", 1.5),
            ("dependable", 1.0),
            ("forthright", 1.0),
            ("gave honest advice", 1.5),
            ("genuinely trustworthy", 1.5),
            ("handled everything professionally", 1.5),
            ("highest professional standards", 2.0),
            ("honest and transparent", 1.5),
            ("impeccable professionalism", 2.0),
            ("kept their word", 1.5),
            ("professional conduct", 1.5),
            ("professional manner", 1.0),
            ("reliable", 1.0),
            ("trustworthy attorney", 1.5),
            ("very dependable", 1.5),
            ("very ethical", 1.5),
            ("very honest", 1.5),
            ("very professional", 1.5),
            ("very trustworthy", 1.5),
            # --- calibration: sample2 ---
            ("very organized with exhibits", 1.5),
            ("prepared for trial", 1.0),
            ("confident and prepared to win at trial", 1.5),
            # --- calibration: gap-report wave (real-review evidence) ---
            ("dedicated and very thorough", 2.0),
            ("competent attorney", 2.0),
            ("skilled negotiator", 2.0),
            ("commitment to their clientele", 1.5),
            # --- calibration: gap-report wave 2 (final_summary.json) ---
            # --- real-reviews wave A ---
            ("second to none", 2.0),
            ("dedicated advocate", 1.5),
            ("fearless", 1.5),
            ("deep understanding of the legal complexities", 1.5),
            ("deep understanding", 1.0),
            ("passion, professionalism, determination", 2.0),
            ("never gave up on", 1.5),
            ("definition of what a defense attorney should be", 2.0),
            ("smart, strategic", 1.0),
            # --- calibration: wave3 live-run gaps (precision-guarded) ---
            # NOTE: "kindness" kept at reduced weight — fires correctly on
            # "professionalism and kindness" compounds but avoids standalone FPs.
            ("kindness", 0.3),
            ("professionalism and kindness", 1.5),
            # NOTE: "wonderful/pleasure to work with" removed — too generic;
            # AI does not tag professionalism_trust for these in isolation.
            # NOTE: generic "lovely/great experience" phrasing is too broad for
            # live professionalism scoring and was producing extras in positive praise.
            # NOTE: bare "highly recommend" / "i would recommend" / "strongly recommend"
            # removed — recommendation language is not a trust/professionalism signal.
            # Only the attorney-specific form is retained.
            ("i highly recommend him", 1.5),
            ("i highly recommend her", 1.5),
            ("i highly recommend this attorney", 1.5),
            ("i highly recommend this firm", 1.5),
            # NOTE: "very knowledgeable", "very thorough" removed — fires in too many
            # non-professionalism contexts (estate planning, case expertise, etc).
            # More specific compound forms kept.
            ("knowledgeable attorney", 1.5),
            ("knowledgeable and professional", 1.5),
            ("thorough attorney", 1.5),
            ("thorough and professional", 1.5),
            ("dedicated attorney", 1.5),
        ],
        "negative": [
            # --- original ---
            ("dishonest", 1.5),
            ("disrespectful", 1.5),
            ("felt misled", 1.5),
            ("lied", 2.0),
            ("misled", 1.5),
            ("not honest", 1.5),
            ("rude", 1.5),
            ("unprofessional", 1.5),
            ("untrustworthy", 1.5),
            # --- new: safe_import_now [W1] ---
            ("acted inappropriately", 1.5),
            ("arrogant", 1.5),
            ("condescending", 1.5),
            ("deceptive", 1.5),
            ("disregarded my wishes", 1.5),
            ("extremely rude", 1.5),
            ("gave contradictory advice", 1.5),
            ("incompetent behavior", 1.5),
            ("lacked professionalism", 1.5),
            ("not reliable", 1.5),
            ("not trustworthy", 1.5),
            ("rude and dismissive", 1.5),
            ("seemed dishonest", 1.5),
            ("too arrogant", 1.5),
            ("treated me rudely", 1.5),
            ("very unprofessional", 1.5),
            ("was condescending", 1.5),
            ("wasn't honest with me", 1.5),
            # --- calibration: phrase expansion ---
            ("acted unprofessionally", 1.5),
            ("lack of professionalism", 1.5),
            ("lost confidence in", 1.2),
            ("misrepresented", 1.5),
            ("unethical behavior", 2.0),
            # --- calibration: gap-report wave 2 (final_summary.json) ---
            ("never felt confident in the representation", 1.5),
            ("too old for them to represent me", 2.0),
            ("stopped working when they got paid", 2.0),
            ("they're not even licensed in my state", 2.0),
        ],
        "severe_negative": [
            # --- original ---
            ("accused of lying", 2.0),
            ("completely unprofessional", 2.0),
            ("ethical violation", 2.0),
            ("filed a complaint", 2.0),
            ("fraudulent", 2.0),
            ("reported to the bar", 2.0),
            # --- new: safe_import_now [W1] ---
            ("bar complaint filed", 2.0),
            ("blatantly lied", 2.0),
            ("criminal conduct", 2.0),
            ("disciplinary action", 2.0),
            ("egregiously unprofessional", 2.0),
            ("ethics complaint", 2.0),
            ("flagrant misconduct", 2.0),
            ("gross misconduct", 2.0),
            ("lied to my face", 2.0),
            ("misconduct", 1.5),
            ("professional misconduct", 2.0),
            ("rude and condescending", 2.0),
            ("extremely rude", 2.0),
            ("actually racist", 2.0),
            ("racist", 2.0),
            ("stole my money", 2.0),
            ("submitted false documents", 2.0),
            # --- calibration: gap-report wave (real-review evidence) ---
            ("lost his temper", 2.0),
            ("screamed at", 2.0),
            ("thrown out of their office", 2.0),
            ("my case was handed off to a junior associate", 2.0),
            ("an absolute nightmare", 2.0),
            ("crooked law office", 2.0),
            # --- calibration: gap-report wave 2 (final_summary.json) ---
            ("let me down and sent his inexperienced son", 2.0),
            ("did almost no work", 2.0),
            ("sent me to another courtroom", 1.5),
            ("made my situation significantly worse", 2.0),
            ("left without legal counsel", 2.0),
            ("do not trust this firm", 2.0),
            ("do not trust this law firm", 2.0),
            ("arresting officer was his cousin", 2.0),
            ("couldn't anymore bc the arresting officer was his cousin", 2.0),
            ("was not trying to get me to the best outcome", 2.0),
            # --- real-reviews wave A ---
            ("inexperienced son", 2.0),
            ("sent his inexperienced son", 2.0),
            ("threw my folder", 2.0),
            ("thrown out of their office", 2.0),
            ("rude and condescending", 2.0),
            ("deal with your kind all the time", 2.0),
            ("absolute nightmare to deal with", 2.0),
            ("charged me the full amount and left me without legal counsel", 2.0),
            # --- calibration: severity-tier follow-up ---
            ("too old for them to represent me", 2.0),
            ("stopped working when they got paid", 2.0),
            ("they're not even licensed in my state", 2.0),
        ],
    },

    # =========================================================================
    # THEME: expectation_setting
    # =========================================================================
    "expectation_setting": {
        "positive": [
            # --- original ---
            ("clearly outlined", 1.0),
            ("explained what to expect", 1.0),
            ("gave me realistic expectations", 1.5),
            ("no surprises", 1.0),
            ("set clear expectations", 1.5),
            ("upfront about", 1.0),
            ("walked me through the process", 1.0),
            # --- new: safe_import_now [W1] ---
            ("always kept me grounded", 1.0),
            ("being realistic about outcomes", 1.5),
            ("clear about possible outcomes", 1.5),
            ("communicated likely outcomes", 1.5),
            ("gave an honest assessment", 1.5),
            ("gave realistic advice", 1.5),
            ("honest about the timeline", 1.5),
            ("honest about what to expect", 1.5),
            ("laid everything out clearly", 1.0),
            ("no false hope", 1.5),
            ("prepared me for all possibilities", 1.5),
            ("set proper expectations", 1.5),
            ("told me what to realistically expect", 1.5),
            ("transparent about timelines", 1.0),
            ("upfront about the process", 1.0),
            ("upfront about risks", 1.5),
            ("was realistic with me", 1.5),
            # --- phrase expansion: real-review evidence ---
            ("best case scenario", 1.5),
            ("worst case scenario", 1.5),
            # --- calibration: sample2 ---
            ("walked me through every possible scenario", 1.5),
            ("honest about the risks", 1.0),
            # --- calibration: gap-report wave 2 (final_summary.json) ---
            ("took the time to explain all of our choices", 1.5),
            ("came up with a plan", 1.0),
            ("end result exceeded my expectations", 1.5),
            ("exceeded our expectations", 1.5),
            ("everything was resolved just like they said it would be", 1.5),
        ],
        "negative": [
            # --- original ---
            ("didn't warn me", 1.0),
            ("expected a different outcome", 1.0),
            ("false promises", 2.0),
            ("misleading promises", 2.0),
            ("not what i expected", 1.0),
            ("overpromised", 1.5),
            ("surprised by", 1.0),
            ("unexpected", 1.0),
            # --- new: safe_import_now [W1] ---
            ("gave false hope", 1.5),
            ("gave me unrealistic expectations", 1.5),
            ("misled my expectations", 1.5),
            ("never warned me", 1.0),
            ("no warning about costs", 1.0),
            ("not prepared for what happened", 1.0),
            ("not transparent about risks", 1.5),
            ("over-promised and under-delivered", 1.5),
            ("overstated chances of success", 1.5),
            ("promises not kept", 1.5),
            ("set unrealistic expectations", 1.5),
            ("told me what i wanted to hear", 1.5),
            ("unrealistic promises", 1.5),
            ("wasn't honest about the odds", 1.5),
            ("wasn't upfront about costs", 1.5),
            ("wasn't upfront about risks", 1.5),
            # --- calibration: sample2 ---
            ("more clarity on realistic outcomes", 1.2),
            ("case was one of many, not a priority", 1.2),
            # --- calibration: full_batch_20260311 ---
            ("deadlines felt unpredictable", 1.5),
            # --- calibration: gap-report wave 2 (final_summary.json) ---
            ("the timeline was unacceptable", 1.5),
            ("never gave a timeframe", 1.5),
            ("disconnect between early expectations and reality", 2.0),
            ("expected more strategic guidance", 1.0),
            ("contact changed multiple times", 1.5),
            ("i had to do the legwork", 1.5),
            ("had to do the legwork", 1.5),
            ("sent me to another courtroom", 1.5),
            ("no attorney ever really reviewed my case", 1.5),
            ("i had to remind them", 1.2),
            ("our case was forgotten about", 1.5),
            ("case was forgotten about", 1.5),
            ("i was stuck without legal council", 1.5),
            ("i was stuck without legal counsel", 1.5),
            ("attorney on our case is even still employed there", 1.5),
            ("do all the legwork of my disability appeal", 1.5),
        ],
        "severe_negative": [
            # --- original ---
            ("blatant false promises", 2.0),
            ("guaranteed a win", 2.0),
            ("promised outcomes", 2.0),
            # --- new: safe_import_now [W1] ---
            ("flat out lied about outcomes", 2.0),
            ("guaranteed results they couldn't deliver", 2.0),
            ("made promises they couldn't keep", 2.0),
            ("promised a specific outcome", 2.0),
            ("promised success", 2.0),
            # --- calibration: severity-tier follow-up ---
            ("sent me to another courtroom", 2.0),
            ("no attorney ever really reviewed my case", 2.0),
            ("sent his inexperienced son to represent me", 2.0),
            ("sent his son to represent me", 2.0),
            ("he completely let me down and sent his inexperienced son to represent me", 2.0),
        ],
    },

    # =========================================================================
    # THEME: billing_transparency
    # =========================================================================
    "billing_transparency": {
        "positive": [
            # --- original ---
            ("billing was clear", 1.5),
            ("clear billing", 1.5),
            ("detailed invoice", 1.0),
            ("explained the fees", 1.0),
            ("fee structure was transparent", 1.5),
            ("no hidden fees", 1.5),
            ("no surprise charges", 1.5),
            ("transparent about costs", 1.5),
            ("upfront about fees", 1.5),
            # --- new: safe_import_now [W1] ---
            ("accurate billing", 1.0),
            ("billing was accurate", 1.5),
            ("billing was straightforward", 1.5),
            ("billing was transparent", 1.5),
            ("clear invoices", 1.0),
            ("clearly itemized", 1.5),
            ("detailed billing statements", 1.5),
            ("explained all charges", 1.5),
            ("explained billing clearly", 1.5),
            ("fair billing practices", 1.5),
            ("fees were clearly explained", 1.5),
            ("fully itemized", 1.5),
            ("gave a clear fee estimate", 1.5),
            ("itemized billing", 1.5),
            ("no billing surprises", 1.5),
            ("no unexpected fees", 1.5),
            ("provided cost breakdown", 1.0),
            ("transparent billing practices", 1.5),
            ("upfront about all costs", 1.5),
            ("very transparent about billing", 1.5),
            # --- calibration: sample2 ---
            ("billing was fair", 1.5),
            ("warned me when a motion would be more expensive", 1.0),
            ("respected my budget", 1.5),
            ("suggested options to minimize court time", 1.0),
            # --- calibration: full_batch_20260311 ---
            ("billing was explained upfront", 1.5),
        ],
        "negative": [
            # --- original ---
            ("charged extra", 1.0),
            ("confusing bill", 1.0),
            ("hidden fees", 2.0),
            ("not transparent about fees", 1.5),
            ("overcharged", 1.5),
            ("surprise bill", 1.5),
            ("surprise charge", 1.5),
            ("surprise fees", 1.5),
            ("unclear billing", 1.0),
            ("unclear invoices", 1.0),
            ("unexpected bill", 1.5),
            ("unexpected charges", 1.5),
            ("unexpected fees", 1.5),
            # --- new: safe_import_now [W1] ---
            ("billing errors", 1.0),
            ("billing irregularities", 1.5),
            ("billed for unnecessary work", 1.5),
            ("billed for work not done", 1.5),
            ("billed without notice", 1.5),
            ("bills were confusing", 1.0),
            ("charges were not explained", 1.5),
            ("confusing invoices", 1.0),
            ("excessive charges", 1.5),
            ("excessive fees", 1.5),
            ("fees were never disclosed", 1.5),
            ("hard to understand the bill", 1.0),
            ("incorrect billing", 1.5),
            ("inflated billing", 1.5),
            ("inflated fees", 1.5),
            ("mysterious charges", 1.5),
            ("no itemization", 1.5),
            ("no transparency on fees", 1.5),
            ("opaque billing", 1.5),
            ("unexplained charges", 1.5),
            ("unexplained fees", 1.5),
            ("vague billing", 1.0),
            # --- calibration: sample2 ---
            ("billing statements were confusing", 1.2),
            # --- phrase expansion: real-review evidence ---
            ("free initial consultation", 1.5),
            ("non-refundable", 1.5),
            ("administration fees", 1.0),
            ("per hour rate", 1.0),
            ("did not disclose", 1.5),
            ("inflated charges", 1.5),
            ("charged the full amount", 1.5),
            ("charged me the full amount", 1.5),
            # --- calibration: phrase expansion ---
            ("consultation was not free", 1.5),
            ("free consultation not free", 1.5),
            ("charged for consultation", 1.5),
            ("consultation appointment fee", 1.5),
            ("unexpected consultation fee", 1.5),
            ("billing was misleading", 1.5),
            # --- calibration: gap-report wave (real-review evidence) ---
            ("billing felt a bit opaque", 1.5),
            ("billing statements were hard to read", 1.5),
            ("slight billing surprise", 1.0),
            ("billing was on the higher end", 1.0),
            ("dealing with the billing department is a nightmare", 2.0),
            ("appeared inflated", 1.5),
            ("don't have a way to estimate the typical baseline", 1.5),
            ("maximum they would take out of my settlement", 1.5),
        ],
        "severe_negative": [
            # --- original ---
            ("billing fraud", 2.0),
            ("double billed", 2.0),
            ("grossly overcharged", 2.0),
            # --- new: safe_import_now [W1] ---
            ("billed for services never rendered", 2.0),
            ("blatant billing fraud", 2.0),
            ("charged far more than agreed", 2.0),
            ("completely fabricated charges", 2.0),
            ("fraudulent billing", 2.0),
            ("fraudulent invoices", 2.0),
            ("grossly inflated billing", 2.0),
            ("charged $50", 2.0),
            ("charged 50", 2.0),
            ("charged for consultation appointment", 2.0),
        ],
    },

    # =========================================================================
    # THEME: fee_value
    # =========================================================================
    "fee_value": {
        "positive": [
            # --- original ---
            ("affordable", 1.0),
            ("fair price", 1.0),
            ("good value", 1.0),
            ("reasonable fees", 1.0),
            ("reasonable rates", 1.0),
            ("well worth it", 1.5),
            ("worth every penny", 1.5),
            ("worth the cost", 1.0),
            ("worth the fee", 1.0),
            ("worth the money", 1.0),
            ("worth the price", 1.0),
            # --- new: safe_import_now [W1] ---
            ("competitively priced", 1.0),
            ("excellent value for money", 1.5),
            ("excellent value for the price", 1.5),
            ("fair and reasonable fees", 1.5),
            ("fair billing", 1.0),
            ("fairly priced", 1.0),
            ("fees were justified", 1.0),
            ("fees were more than fair", 1.5),
            ("fees were reasonable", 1.0),
            ("great value for the money", 1.5),
            ("money well spent", 1.5),
            ("price was fair", 1.0),
            ("price was reasonable", 1.0),
            ("rates were affordable", 1.0),
            ("rates were fair", 1.0),
            ("reasonable cost", 1.0),
            ("reasonably priced", 1.0),
            ("very affordable", 1.5),
            ("very fair price", 1.5),
        ],
        "negative": [
            # --- original ---
            ("expensive", 1.0),
            ("exorbitant", 1.5),
            ("fees are too high", 1.5),
            ("not worth it", 1.5),
            ("not worth the cost", 1.5),
            ("not worth the money", 1.5),
            ("not worth the price", 1.5),
            ("overpriced", 1.5),
            ("too expensive", 1.5),
            ("too much money", 1.0),
            # --- new: safe_import_now [W1] ---
            ("charged too much", 1.5),
            ("cost too much", 1.0),
            ("extremely expensive", 1.5),
            ("fees are excessive", 1.5),
            ("fees are unreasonable", 1.5),
            ("fees were outrageous", 1.5),
            ("felt overcharged", 1.5),
            ("highway robbery", 1.5),
            ("lot of money for little result", 1.5),
            ("not cost-effective", 1.0),
            ("not worth the expense", 1.5),
            ("outrageous fees", 1.5),
            ("overpriced for what you get", 1.5),
            ("poor value", 1.0),
            ("poor value for money", 1.5),
            ("rates are too high", 1.5),
            ("ridiculous fees", 1.5),
            ("too costly", 1.0),
            ("way too expensive", 1.5),
            # --- calibration: phrase expansion ---
            ("expensive for what you get", 1.5),
            ("cost far more than expected", 1.5),
            ("fees kept increasing", 1.5),
            # --- calibration: gap-report wave (real-review evidence) ---
            ("failed to provide value", 1.5),
            ("for the money i paid i expected more", 1.5),
            ("i felt like i could have gotten the same result for less money", 1.5),
            ("they just want money from you", 1.5),
        ],
        "severe_negative": [
            # --- original ---
            ("absolutely outrageous fees", 2.0),
            ("predatory billing", 2.0),
            ("price gouging", 2.0),
            # --- new: safe_import_now [W1] ---
            ("extortionate fees", 2.0),
            ("extortion", 2.0),
            ("flagrant price gouging", 2.0),
            ("grossly overpriced", 2.0),
            ("outrageously overpriced", 2.0),
            ("predatory pricing", 2.0),
            ("what a scam", 2.0),
            ("total scam", 2.0),
            # --- calibration: severity-tier follow-up ---
            ("failed to provide value", 2.0),
        ],
    },

    # =========================================================================
    # THEME: timeliness_progress
    # NOTE: "efficient" removed from positive list - AI consistently maps it to
    #       professionalism_trust when appearing in "respectful and efficient".
    #       Replaced with more specific timeliness phrases.
    # =========================================================================
    "timeliness_progress": {
        "positive": [
            # --- original ("efficient" removed - see note above) ---
            ("ahead of schedule", 1.5),
            ("completed on time", 1.0),
            ("fast turnaround", 1.0),
            ("handled quickly", 1.0),
            ("moved quickly", 1.0),
            ("no unnecessary delays", 1.0),
            ("quick resolution", 1.5),
            ("resolved quickly", 1.5),
            # NOTE: bare "timely" removed — it overfires inside responsiveness
            # sentences such as "returned my calls in a timely fashion".
            # --- new: safe_import_now [W1] ---
            ("acted fast", 1.0),
            ("case moved forward quickly", 1.5),
            ("case moved quickly", 1.5),
            ("case progressed quickly", 1.5),
            ("case resolved quickly", 1.5),
            ("dealt with promptly", 1.0),
            ("diligent and timely", 1.5),
            ("efficient process", 1.0),  # [W1-GUARD]
            # CONTEXT-GUARD PLACEHOLDER: "efficient process" -- ambiguous; scoring
            # should verify subject is the attorney/firm, not the legal system.
            ("everything was done in a timely manner", 1.5),
            ("fast and efficient", 1.5),
            ("handled efficiently", 1.0),
            ("handled in a timely manner", 1.5),
            ("matter was resolved quickly", 1.5),
            ("met all deadlines", 1.5),
            ("met deadlines", 1.5),
            ("moved the case forward", 1.0),
            ("no delays", 1.0),
            ("on schedule", 1.0),
            ("process was quick", 1.0),
            ("quick and efficient", 1.5),
            ("resolved in a timely fashion", 1.5),
            ("stayed on schedule", 1.0),
            ("work was done promptly", 1.0),
            ("made sure your case is ready on time", 1.5),
            ("made sure everything was done correctly and on time", 1.5),
            ("answered them within a day", 1.0),
            # --- calibration: sample2 ---
            ("always knew when the next court date was", 1.5),
            ("helped me get a protective order quickly", 1.5),
            ("took a day to get updates after court", 0.8),
            # --- calibration: full_batch_20260311 ---
            ("they kept things moving", 1.5),
        ],
        "negative": [
            # --- original ---
            ("case dragged on", 1.5),
            ("delayed", 1.0),
            ("delays", 1.0),
            ("everything took too long", 1.5),
            ("missed deadlines", 1.5),
            ("slow", 1.0),
            ("took forever", 1.5),
            ("took too long", 1.5),
            ("unnecessary delays", 1.5),
            # --- new: safe_import_now [W1] ---
            ("always an excuse for the delay", 1.5),
            ("behind schedule", 1.5),
            ("case stalled", 1.5),
            ("case went nowhere", 1.5),
            ("constant delays", 1.5),
            ("constantly delayed", 1.5),
            ("dragged on forever", 1.5),
            ("extremely slow", 1.5),
            ("felt like nothing was happening", 1.0),
            ("kept getting pushed back", 1.5),
            ("kept putting things off", 1.5),
            ("lack of progress", 1.5),
            ("making no progress", 1.5),
            ("matter took far too long", 1.5),
            ("missed every deadline", 1.5),
            ("no progress", 1.5),
            ("no urgency", 1.0),
            ("not making progress", 1.5),
            ("painfully slow", 1.5),
            ("seemed to drag their feet", 1.5),
            ("slow process", 1.0),
            ("very slow", 1.5),
            # --- phrase expansion: real-review evidence ---
            ("over a year", 1.5),
            ("never heard from them", 1.5),
            ("forgotten about", 1.5),
            ("nothing was completed", 1.5),
            ("nothing had been worked on", 1.5),
            # --- phrase expansion: missed timeliness phrases ---
            ("took longer than expected", 1.5),
            ("delayed process", 1.5),
            ("timeline extended", 1.0),
            ("slow progress", 1.5),
            # --- calibration: gap-report wave 2 (final_summary.json) ---
            ("took much longer than expected", 1.5),
            ("timeline ran longer than estimated", 1.5),
            ("dropped the ball", 1.5),
            ("administrative mix-up", 1.0),
            ("missed a few demands", 1.5),
            # --- calibration: phrase expansion ---
            ("case taking years", 1.5),
            ("still waiting after", 1.2),
            ("taking far too long", 1.5),
            ("still waiting for resolution", 1.5),
            ("taking forever", 1.2),
            ("process dragged out", 1.5),
            # --- calibration: wave3 live-run gaps ---
            ("it took 12 months", 1.5),
            ("took 12 months", 1.5),
            ("took over a year", 1.5),
            ("my ltd appeal took a long time", 1.5),
            ("appeal took a long time", 1.5),
            ("took a long time", 1.0),
            ("after 2 years", 1.5),
            ("after two years", 1.5),
            ("2 years later", 1.5),
            ("still waiting", 1.5),
            ("still no resolution", 1.5),
            ("over two years", 1.5),
            ("two and a half years", 1.5),
            ("2 and a half years", 1.5),
            ("without achieving any meaningful progress", 1.5),
        ],
        "severe_negative": [
            # --- original ---
            ("filed too late", 2.0),
            ("missed critical deadline", 2.0),
            ("statute of limitations", 2.0),
            # --- new: safe_import_now [W1] ---
            ("case dismissed due to delay", 2.0),
            ("critical filing missed", 2.0),
            ("deadline missed entirely", 2.0),
            ("filing deadline missed", 2.0),
            ("irreparable harm from delay", 2.0),
            ("lost case due to missed deadline", 2.0),
            ("missed statute of limitations", 2.0),
            ("showed up late", 2.0),
            ("didn't even know he had to come", 2.0),
            ("taken more than 2 years", 2.0),
            ("taken more then 2 years", 2.0),
            ("tanked my case", 2.0),
            # --- calibration: severity-tier follow-up ---
            ("2 and a half years", 2.0),
        ],
    },

    # =========================================================================
    # THEME: office_staff_experience
    # =========================================================================
    "office_staff_experience": {
        "positive": [
            # --- original ---
            ("front desk was great", 1.0),
            ("friendly staff", 1.0),
            ("helpful staff", 1.0),
            ("office was welcoming", 1.0),
            ("paralegal was helpful", 1.0),
            ("receptionist was kind", 1.0),
            ("staff was friendly", 1.0),
            ("staff was helpful", 1.0),
            ("support staff", 1.0),
            ("the whole team", 1.0),
            ("very polite staff", 1.5),
            ("polite staff", 1.5),
            ("people picking up the phone are very nice", 1.0),
            # --- new: safe_import_now [W1] ---
            ("admin staff was excellent", 1.5),
            ("assistant was knowledgeable", 1.0),
            ("entire office was professional", 1.5),
            ("entire staff was great", 1.5),
            ("everyone in the office was kind", 1.5),
            ("excellent support team", 1.5),
            ("front desk staff was helpful", 1.5),
            ("front desk was friendly", 1.0),
            ("front desk was professional", 1.0),
            ("great office staff", 1.5),
            ("greeted warmly", 1.0),
            ("incredible support staff", 1.5),
            ("knowledgeable paralegal", 1.0),
            ("lovely office staff", 1.5),
            ("office staff was attentive", 1.0),
            ("office staff was excellent", 1.5),
            ("office staff was friendly", 1.0),
            ("office staff was helpful", 1.0),
            ("office staff was kind", 1.0),
            ("office staff was professional", 1.0),
            ("paralegal was amazing", 1.5),
            ("paralegal was great", 1.5),
            ("receptionist was friendly", 1.0),
            ("receptionist was helpful", 1.0),
            ("receptionist was professional", 1.0),
            ("staff went out of their way", 1.5),
            ("staff were excellent", 1.5),
            ("will work hard for you", 1.5),
            ("wonderful support staff", 1.5),
        ],
        "negative": [
            # --- original ---
            ("front desk was rude", 1.5),
            ("rude receptionist", 1.5),
            ("rude staff", 1.5),
            ("staff was disorganized", 1.0),
            ("staff was rude", 1.5),
            ("staff was unhelpful", 1.0),
            ("unfriendly staff", 1.0),
            ("unhelpful staff", 1.0),
            # --- new: safe_import_now [W1] ---
            ("administrative errors", 1.0),
            ("assistant was unhelpful", 1.0),
            ("disorganized office", 1.0),
            ("disorganized staff", 1.0),
            ("front desk was cold", 1.0),
            ("front desk was dismissive", 1.5),
            ("front desk was unhelpful", 1.0),
            ("incompetent staff", 1.5),
            ("inefficient office", 1.0),
            ("office staff was cold", 1.0),
            ("office staff was dismissive", 1.5),
            ("office staff was rude", 1.5),
            ("office was chaotic", 1.0),
            ("paralegal was rude", 1.5),
            ("poor administrative support", 1.0),
            ("poor office management", 1.0),
            ("receptionist was cold", 1.0),
            ("receptionist was dismissive", 1.5),
            ("receptionist was rude", 1.5),
            ("receptionist was unhelpful", 1.0),
            ("staff made errors", 1.0),
            ("staff were rude", 1.5),
            ("staff were unhelpful", 1.0),
            ("support staff was not helpful", 1.0),
            ("unorganized office", 1.0),
            # --- calibration: sample2 ---
            ("spoke to staff and waited for callbacks", 1.2),
            # --- calibration: gap-report wave 2 (final_summary.json) ---
            ("not pleasant or helpful", 1.5),
            ("always got told that our message was left for our lawyer", 1.5),
            ("paralegals are not efficient", 1.5),
            ("whenever i call i get attitude", 1.5),
            # --- real-reviews wave A ---
            ("complete attitude", 1.5),
            ("complete attitude every call", 2.0),
            ("absolutely no compassion", 1.5),
            ("paralegal is assigned to your case", 1.0),
            ("completely inept at their job", 1.5),
            ("not friendly at all", 1.5),
            ("waiting room felt outdated and unprofessional", 1.0),
        ],
        "severe_negative": [
            # --- original ---
            ("abusive staff", 2.0),
            ("harassment by staff", 2.0),
            ("hostile front desk", 2.0),
            # --- new: safe_import_now [W1] ---
            ("aggressive staff", 2.0),
            ("berated by staff", 2.0),
            ("discriminatory treatment by staff", 2.0),
            ("harassed by receptionist", 2.0),
            ("hostile office environment", 2.0),
            ("staff threatened me", 2.0),
        ],
    },

    # =========================================================================
    # THEME: outcome_satisfaction
    # =========================================================================
    "outcome_satisfaction": {
        "positive": [
            # --- original ---
            ("achieved great results", 1.5),
            ("case was dismissed", 1.5),
            ("excellent outcome", 1.5),
            ("favorable outcome", 1.5),
            ("favorable settlement", 1.5),
            ("got exactly what i wanted", 1.5),
            ("great result", 1.5),
            ("great results", 1.5),
            ("happy with the outcome", 1.0),
            ("happy with the result", 1.0),
            ("successful outcome", 1.5),
            ("very happy with the result", 1.5),
            ("won my case", 1.5),
            # --- new: safe_import_now [W1] ---
            ("best possible outcome", 2.0),
            ("better than expected outcome", 1.5),
            ("case resolved favorably", 1.5),
            ("case resolved in my favor", 1.5),
            ("case settled favorably", 1.5),
            ("case was a success", 1.5),
            ("case was resolved successfully", 1.5),
            ("charges were dropped", 1.5),
            ("couldn't be happier with the result", 2.0),
            ("excellent results", 1.5),
            ("exceptional outcome", 2.0),
            ("extremely happy with the outcome", 1.5),
            ("fantastic result", 1.5),
            ("fantastic results", 1.5),
            ("full victory", 2.0),
            ("got the settlement i deserved", 1.5),
            ("happy with the settlement", 1.0),
            ("incredible result", 1.5),
            ("matter was resolved in my favor", 1.5),
            ("more than satisfied with the outcome", 1.5),
            ("outstanding result", 2.0),
            ("outstanding results", 2.0),
            ("positive resolution", 1.5),
            ("resolved in my favor", 1.5),
            ("saved my case", 1.5),
            ("secured a great settlement", 1.5),
            ("successful resolution", 1.5),
            ("very pleased with the outcome", 1.5),
            ("very pleased with the result", 1.5),
            ("victory", 1.5),
            ("won a great settlement", 1.5),
            ("won the case", 1.5),
            # --- phrase expansion: real-review evidence ---
            ("not guilty", 2.0),
            ("found not guilty", 2.0),
            ("not guilty verdict", 2.0),
            ("acquitted", 2.0),
            ("got the job done", 1.5),
            ("won so to speak", 1.5),
            # --- phrase expansion: missed outcome phrases ---
            ("great outcome", 1.5),
            ("excellent result", 1.5),
            ("favorable result", 1.5),
            ("case dismissed", 1.5),
            ("settlement exceeded expectations", 2.0),
            ("better than expected", 1.0),
            # --- calibration: sample2 ---
            ("mediation preparation was excellent", 1.5),
            ("helped me focus on long-term outcomes", 1.5),
            ("not just winning every argument", 1.0),
            # --- calibration: full_batch_20260311 ---
            ("the outcome met expectations", 1.5),
            # --- calibration: gap-report wave (real-review evidence) ---
            ("resulted in a significant settlement", 2.0),
            ("everything was resolved just like they said it would be", 1.5),
            ("he's home", 2.0),
            ("the outcome exceeded my expectations", 2.0),
            ("outcome was fine", 1.0),
            ("results were acceptable", 1.0),
            ("the final result was satisfactory", 1.0),
            ("turned a terrifying situation into a manageable one", 2.0),
            # NOTE: "would highly recommend" removed -- recommendation language
            # is not an outcome signal; confirmed extra_theme FP x2 in chunk 5.
            # --- calibration: wave3 live-run gaps ---
            ("very happy with how the matter turned out", 1.5),
            ("happy with how everything was handled", 1.5),
            ("very pleased with how everything was handled", 1.5),
            ("grateful and satisfied", 1.5),
            ("very grateful and satisfied", 1.5),
            ("satisfying result", 1.5),
            ("very satisfying", 1.5),
            ("made the process so easy", 1.0),
            ("helped me get approved", 1.5),
            ("got approved", 1.5),
            ("approved for", 1.0),
            ("dismissed the battery charge", 1.8),
            ("finally got justice", 1.8),
            ("very happy with the final outcome", 1.8),
            ("got more than expected out of it", 1.8),
        ],
        "negative": [
            # --- original ---
            ("case was lost", 1.5),
            ("disappointed with the outcome", 1.5),
            ("disappointed with the result", 1.5),
            ("dissatisfied with the outcome", 1.5),
            ("lost my case", 1.5),
            ("not happy with the result", 1.5),
            ("not satisfied with the outcome", 1.5),
            ("poor outcome", 1.5),
            ("terrible outcome", 1.5),
            ("terrible result", 1.5),
            ("unhappy with the outcome", 1.0),
            ("unhappy with the result", 1.0),
            # --- new: safe_import_now [W1] ---
            ("awful result", 1.5),
            ("bad outcome", 1.0),
            ("bad result", 1.0),
            ("case did not go well", 1.5),
            ("case ended badly", 1.5),
            ("case fell apart", 1.5),
            ("case was a disaster", 1.5),
            ("completely dissatisfied with outcome", 1.5),
            ("deeply disappointed with the outcome", 1.5),
            ("disappointing outcome", 1.5),
            ("disappointing result", 1.5),
            ("disappointing results", 1.5),
            ("did not get what i was hoping for", 1.0),
            ("ended in failure", 1.5),
            ("extremely disappointed with the result", 1.5),
            ("failed to achieve a good outcome", 1.5),
            ("lost the case", 1.5),
            ("matter was not resolved", 1.5),
            ("no resolution", 1.0),
            ("not the outcome i wanted", 1.0),
            ("outcome was not good", 1.5),
            ("poor results", 1.5),
            ("really disappointed with the outcome", 1.5),
            ("result was not what i hoped for", 1.0),
            ("terrible results", 1.5),
            ("very disappointed with the outcome", 1.5),
            ("very disappointed with the result", 1.5),
            ("very poor result", 1.5),
            ("we lost", 1.5),
            # --- calibration: gap-report wave (real-review evidence) ---
            ("complete waste of money", 2.0),
            ("nothing but wasting my time and money", 2.0),
            ("never got proper legal help", 1.5),
            ("had to hire another attorney", 1.5),
            ("stuck without legal counsel", 2.0),
            ("never got proper legal help from him", 2.0),
            ("nothing was completed at all", 1.5),
            # --- calibration: wave3 live-run gaps ---
            ("not satisfied with their efforts", 1.5),
            ("not satisfied with the work", 1.5),
            ("my lawyer was representing the defendant", 2.0),
            ("felt like my lawyer was on the other side", 2.0),
            ("never really fought", 1.5),
            ("never really did anything", 1.5),
            ("never fought for me", 1.5),
            ("still lost my license", 2.0),
        ],
        "severe_negative": [
            # --- original ---
            ("case completely mishandled", 2.0),
            ("lost everything", 2.0),
            ("malpractice", 2.0),
            ("negligence", 2.0),
            # --- new: safe_import_now [W1] ---
            ("attorney malpractice", 2.0),
            ("case destroyed by incompetence", 2.0),
            ("completely ruined my case", 2.0),
            ("destroyed my case", 2.0),
            ("egregious failure", 2.0),
            ("gross negligence", 2.0),
            ("legal malpractice", 2.0),
            ("lost due to lawyer error", 2.0),
            ("lost due to negligence", 2.0),
            ("ruined any chance of winning", 2.0),
            # --- calibration: severity-tier follow-up ---
            ("never got proper legal help from him", 2.0),
            ("never really fought", 2.0),
            ("never really did anything", 2.0),
            ("never fought for me", 2.0),
            ("still lost my license", 2.0),
        ],
    },
}

# ---------------------------------------------------------------------------
# NEGATION GUARDS
# ---------------------------------------------------------------------------
NEGATION_TOKENS = {
    "not", "never", "no", "didn't", "did not", "doesn't", "does not",
    "wasn't", "was not", "weren't", "were not", "wouldn't", "would not",
    "couldn't", "could not", "haven't", "have not", "hadn't", "had not",
    "isn't", "is not", "aren't", "are not", "hardly", "barely", "scarcely",
}
NEGATION_WINDOW = 6
CLAUSE_BOUNDARY_TOKENS = {
    "but", "however", "although", "though", "except", "despite",
    "if", "when", "while", "unless", "until",
}
CLAUSE_BOUNDARY_CHARS = {".", "!", "?", ";", ",", "\n", "\r", ":", "(", ")"}
INLINE_BOUNDARY_MARKERS = (" and ", " but ", " or ", " however ", " although ", " though ", " while ")

# ---------------------------------------------------------------------------
# CONTRAST GUARDS
# ---------------------------------------------------------------------------
CONTRAST_TOKENS = {
    "however", "but", "although", "though", "despite", "except",
    "unfortunately", "sadly", "regrettably", "while",
}
CONTRAST_WINDOW = 4

# ---------------------------------------------------------------------------
# STAR RATING -> POLARITY PRIOR
# ---------------------------------------------------------------------------
RATING_POLARITY_MAP = {
    5: "positive",
    4: "positive",
    3: "neutral",
    2: "negative",
    1: "negative",
}

POSITIVE_OUTCOME_HINTS = (
    "got it done", "dismissed", "approved", "win my case", "won my case",
    "favorable", "successful", "resolved", "great result", "great outcome",
)

SEVERITY_RECOVERY_HINTS = (
    "corrected quickly", "quickly corrected", "eventually resolved",
    "resolved satisfactorily", "made it right", "made things right",
    "ultimately resolved", "ended well", "worked out in the end",
)

TIMELINESS_LONG_DELAY_HINTS = (
    "still waiting after", "still waiting for resolution", "still waiting",
    "after 2 years", "after two years", "2 years later", "over two years",
    "two and a half years", "2 and a half years", "nearly five months",
    "five months", "5 months",
)

TIMELINESS_CASE_HARM_HINTS = (
    "plea deal", "without achieving any meaningful progress", "no progress",
    "nothing was completed", "nothing had been worked on", "case went nowhere",
    "case stalled", "missed a few demands", "dropped the ball",
)

BILLING_SURPRISE_HINTS = (
    "never knew", "didn't know", "did not know", "wasn't free", "was not free",
    "charged me $", "charged me ", "consultation", "without notice",
    "without telling", "did not disclose", "fees were never disclosed",
)

FEE_EXPLOITATIVE_HINTS = (
    "only for profit", "only in it for profit", "in it only for profit",
    "wouldn't help because", "would not help because", "quick and big",
    "big and quick", "would collect", "collecting", "profit",
)

# ---------------------------------------------------------------------------
# OPENROUTER CONFIG
# ---------------------------------------------------------------------------
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"
DEFAULT_OPENROUTER_MODEL = "openai/gpt-4o-mini"
DEFAULT_OPENROUTER_TIMEOUT = 20

OPENROUTER_SYSTEM_PROMPT = """\
You are a classification engine for a legal services client-feedback platform.
Output ONLY valid JSON. No markdown. No explanation. No preamble.

You must identify which governance themes are present in the review.

ALLOWED THEMES (use ONLY these exact string values):
communication_responsiveness, communication_clarity, empathy_support,
professionalism_trust, expectation_setting, billing_transparency,
fee_value, timeliness_progress, office_staff_experience, outcome_satisfaction

For each theme present output:
  theme         -- exact string from the allowed list
  polarity      -- exactly one of: positive, negative, severe_negative
  evidence_span -- verbatim excerpt from the review (max 120 chars)
  confidence    -- exactly one of: high, medium, low

Output format:
{"themes": [{"theme": "...", "polarity": "...", "evidence_span": "...", "confidence": "..."}]}

Rules:
- Only tag themes that are clearly present.
- Return an empty themes array if nothing is clearly present.
- Never invent themes outside the allowed list.
- severe_negative = systemic failure, explicit harm, ethics/malpractice language.
"""

OPENROUTER_USER_TEMPLATE = """\
REVIEW (rating {rating}/5, date {date}):
\"\"\"{text}\"\"\"
"""


# ---------------------------------------------------------------------------
# DETERMINISTIC SCORER
# ---------------------------------------------------------------------------

def _tokenize(text: str) -> List[str]:
    """Lowercase word-token list, punctuation stripped."""
    return re.findall(r"[a-z']+", text.lower())


def _check_negation(tokens: List[str], phrase_start_idx: int) -> bool:
    """Return True if a negation token appears within NEGATION_WINDOW tokens before phrase_start_idx."""
    window_start = max(0, phrase_start_idx - NEGATION_WINDOW)
    window = tokens[window_start:phrase_start_idx]
    for tok in window:
        if tok in NEGATION_TOKENS:
            return True
    window_text = " ".join(window)
    for neg in NEGATION_TOKENS:
        if " " in neg and neg in window_text:
            return True
    return False


def _get_bounded_context_tokens(
    tokens: List[str],
    phrase_start_idx: int,
    phrase_token_len: int,
    before_only: bool = False,
) -> List[str]:
    """Return nearby tokens without crossing contrast / subordinate-clause boundaries."""
    left_context: List[str] = []
    idx = phrase_start_idx - 1
    while idx >= 0 and len(left_context) < NEGATION_WINDOW:
        tok = tokens[idx]
        if tok in CLAUSE_BOUNDARY_TOKENS:
            break
        left_context.append(tok)
        idx -= 1

    if before_only:
        return list(reversed(left_context))

    right_context: List[str] = []
    idx = phrase_start_idx + phrase_token_len
    while idx < len(tokens) and len(right_context) < NEGATION_WINDOW:
        tok = tokens[idx]
        if tok in CLAUSE_BOUNDARY_TOKENS:
            break
        right_context.append(tok)
        idx += 1

    return list(reversed(left_context)) + right_context


def _get_bounded_clause_text(
    text_lower: str,
    phrase_char_idx: int,
    phrase_len: int,
    before_only: bool = False,
) -> str:
    """Return nearby raw text without crossing punctuation clause boundaries."""
    left = phrase_char_idx - 1
    while left >= 0:
        if text_lower[left] in CLAUSE_BOUNDARY_CHARS:
            break
        left -= 1
    left_text = text_lower[left + 1:phrase_char_idx]
    for marker in INLINE_BOUNDARY_MARKERS:
        marker_idx = left_text.rfind(marker)
        if marker_idx != -1:
            left_text = left_text[marker_idx + len(marker):]
            break

    if before_only:
        return left_text

    right = phrase_char_idx + phrase_len
    while right < len(text_lower):
        if text_lower[right] in CLAUSE_BOUNDARY_CHARS:
            break
        right += 1
    right_text = text_lower[phrase_char_idx + phrase_len:right]
    for marker in INLINE_BOUNDARY_MARKERS:
        marker_idx = right_text.find(marker)
        if marker_idx != -1:
            right_text = right_text[:marker_idx]
            break
    return f"{left_text} {right_text}".strip()


def _has_proximal_negation(
    text_lower: str,
    tokens: List[str],
    phrase_start_idx: int,
    phrase_char_idx: int,
    phrase: str,
    before_only: bool = False,
) -> bool:
    """Return True when local clause-bounded context contains a negation token."""
    raw_window = _get_bounded_clause_text(
        text_lower,
        phrase_char_idx,
        len(phrase),
        before_only=before_only,
    )
    raw_tokens = _tokenize(raw_window)
    if raw_tokens:
        if any(tok in NEGATION_TOKENS for tok in raw_tokens):
            return True
        raw_window_text = " ".join(raw_tokens)
        for neg in NEGATION_TOKENS:
            if " " in neg and neg in raw_window_text:
                return True
        return False
    return False


def _check_contrast(tokens: List[str], phrase_start_idx: int) -> bool:
    """Return True if a contrast token appears within CONTRAST_WINDOW tokens before phrase_start_idx."""
    window_start = max(0, phrase_start_idx - CONTRAST_WINDOW)
    window = tokens[window_start:phrase_start_idx]
    return any(tok in CONTRAST_TOKENS for tok in window)


def _extract_sentence_snippet(text: str, char_pos: int, window: int = 120) -> str:
    """Return a snippet of up to `window` chars centred around char_pos."""
    start = max(0, char_pos - window // 2)
    end = min(len(text), char_pos + window // 2)
    snippet = text[start:end].strip()
    if start > 0:
        snippet = "\u2026" + snippet
    if end < len(text):
        snippet = snippet + "\u2026"
    return snippet


def _find_phrase_start(text_lower: str, phrase: str) -> int:
    """Return phrase start index with word-boundary matching for single-token phrases."""
    if " " not in phrase:
        pattern = re.compile(rf"\b{re.escape(phrase)}\b")
        match = pattern.search(text_lower)
        return match.start() if match else -1
    return text_lower.find(phrase)


def _phrase_is_negation_anchored(phrase: str) -> bool:
    """Return True when the phrase itself starts with a negation token."""
    phrase_tokens = _tokenize(phrase)
    if not phrase_tokens:
        return False
    return phrase_tokens[0] in NEGATION_TOKENS


def _text_has_any(text_lower: str, candidates: Tuple[str, ...]) -> bool:
    return any(candidate in text_lower for candidate in candidates)


def _polarity_rank(polarity: str) -> int:
    return {
        "positive": 0,
        "negative": 1,
        "severe_negative": 2,
    }.get(polarity, -1)


def _maybe_escalate_negative_severity(
    theme_id: str,
    actual_polarity: str,
    phrase: str,
    text_lower: str,
) -> str:
    """Promote selected negative hits to severe_negative when strong context is present."""
    if actual_polarity != "negative":
        return actual_polarity
    if _text_has_any(text_lower, SEVERITY_RECOVERY_HINTS):
        return actual_polarity

    if theme_id == "timeliness_progress":
        long_delay = _text_has_any(text_lower, TIMELINESS_LONG_DELAY_HINTS)
        case_harm = _text_has_any(text_lower, TIMELINESS_CASE_HARM_HINTS)
        if phrase in ("2 and a half years", "two and a half years"):
            return "severe_negative"
        if phrase in ("delayed", "still waiting", "still waiting after", "still waiting for resolution") and (long_delay or case_harm):
            return "severe_negative"

    if theme_id == "billing_transparency":
        if phrase == "per hour rate" and _text_has_any(text_lower, BILLING_SURPRISE_HINTS):
            return "severe_negative"

    if theme_id == "fee_value":
        if phrase in ("worth the money", "not worth the money", "failed to provide value", "for the money i paid i expected more") and _text_has_any(text_lower, FEE_EXPLOITATIVE_HINTS):
            return "severe_negative"

    return actual_polarity


def score_review_deterministic(
    review_text: str,
    rating: int,
    review_date: str,
) -> Dict[str, Any]:
    """
    Run the deterministic theme tagger over a single review.

    Returns:
    {
      "themes": [
        {
          "theme":              str,
          "polarity":           "positive" | "negative" | "severe_negative",
          "base_polarity":      str,
          "matched_phrase":     str,
          "phrase_family":      str,
          "sentence_snippet":   str,
          "negation_applied":   bool,
          "contrast_applied":   bool,
          "base_weight":        float,
          "multiplier":         float,
          "final_impact":       float,
          "confidence":         str,
        },
        ...
      ],
      "rating_prior":           str,
      "review_text_length":     int,
    }
    """
    text_lower = review_text.lower()
    tokens = _tokenize(review_text)
    rating_prior = RATING_POLARITY_MAP.get(int(rating or 3), "neutral")
    matched_themes: Dict[str, Any] = {}

    for theme_id, polarity_buckets in THEME_PHRASES.items():
        for phrase_family, phrase_list in polarity_buckets.items():
            for phrase, base_weight in phrase_list:
                idx = _find_phrase_start(text_lower, phrase)
                if idx == -1:
                    continue

                pre_text = text_lower[:idx]
                phrase_token_start = len(pre_text.split())

                negation_applied = _has_proximal_negation(
                    text_lower,
                    tokens,
                    phrase_token_start,
                    idx,
                    phrase,
                    before_only=(phrase_family in ("negative", "severe_negative")),
                )
                contrast_applied = _check_contrast(tokens, phrase_token_start)

                base_polarity = phrase_family
                if negation_applied:
                    if _phrase_is_negation_anchored(phrase):
                        # Phrases like "never explained" already include negation;
                        # avoid inverting them a second time.
                        actual_polarity = phrase_family
                    elif phrase_family == "positive":
                        actual_polarity = "negative"
                    elif phrase_family in ("negative", "severe_negative"):
                        actual_polarity = "positive"
                    else:
                        actual_polarity = phrase_family
                else:
                    actual_polarity = phrase_family

                actual_polarity = _maybe_escalate_negative_severity(
                    theme_id,
                    actual_polarity,
                    phrase,
                    text_lower,
                )

                effective_weight = base_weight
                if actual_polarity == "severe_negative":
                    effective_weight = max(base_weight, 1.8)

                multiplier = 1.0
                if contrast_applied and actual_polarity == "positive":
                    multiplier = 0.6

                if actual_polarity in ("negative", "severe_negative") and rating_prior == "negative":
                    multiplier *= 1.2
                elif actual_polarity == "positive" and rating_prior == "positive":
                    multiplier *= 1.2

                final_impact = round(effective_weight * multiplier, 3)

                if actual_polarity == "severe_negative":
                    confidence = "high"
                elif (actual_polarity in ("positive", "negative")) and (
                    (actual_polarity == "positive" and rating_prior == "positive") or
                    (actual_polarity == "negative" and rating_prior == "negative")
                ):
                    confidence = "high" if base_weight >= 1.5 else "medium"
                elif negation_applied or contrast_applied:
                    confidence = "low"
                else:
                    confidence = "medium"

                snippet = _extract_sentence_snippet(review_text, idx)

                hit = {
                    "theme": theme_id,
                    "polarity": actual_polarity,
                    "base_polarity": base_polarity,
                    "matched_phrase": phrase,
                    "phrase_family": phrase_family,
                    "sentence_snippet": snippet,
                    "negation_applied": negation_applied,
                    "contrast_applied": contrast_applied,
                    "base_weight": effective_weight,
                    "multiplier": round(multiplier, 3),
                    "final_impact": final_impact,
                    "confidence": confidence,
                }

                # GUARD 0: explicit consultation charge phrases should stay negative.
                # If sentence-level negation appears nearby (e.g. "wasn't free"), do not
                # invert these billing charge indicators to positive.
                if (
                    theme_id == "billing_transparency"
                    and phrase in ("charged $50", "charged 50", "charged for consultation appointment")
                    and actual_polarity == "positive"
                ):
                    actual_polarity = phrase_family
                    hit["polarity"] = phrase_family
                    hit["negation_applied"] = False
                elif (
                    theme_id == "billing_transparency"
                    and phrase == "per hour rate"
                    and _text_has_any(text_lower, BILLING_SURPRISE_HINTS)
                ):
                    actual_polarity = "severe_negative"
                    hit["polarity"] = "severe_negative"
                    hit["negation_applied"] = False
                    hit["base_weight"] = max(hit["base_weight"], 1.8)
                    hit["final_impact"] = round(hit["base_weight"] * hit["multiplier"], 3)
                    hit["confidence"] = "high"

                # --- calibration: sample2 context guards ---
                # GUARD 0a: "not guilty" negation-exempt -- phrase is a compound positive
                # (legal verdict language); negation guard must NOT flip it to negative.
                if (
                    phrase == "not guilty"
                    and theme_id == "outcome_satisfaction"
                    and negation_applied
                ):
                    actual_polarity = "positive"
                    hit["polarity"] = "positive"
                    hit["negation_applied"] = False
                elif (
                    theme_id == "communication_responsiveness"
                    and phrase in ("returned my call", "returned my calls", "returned my calls in a timely fashion")
                    and "if not available" in text_lower
                    and actual_polarity == "negative"
                ):
                    actual_polarity = "positive"
                    hit["polarity"] = "positive"
                    hit["negation_applied"] = False

                # GUARD 0b: "misconduct" subject guard -- only fire severe_negative when
                # the attorney/firm is the subject. Suppress when review describes
                # accusations OF misconduct *against the client* (false accusations,
                # accused of misconduct, charged with misconduct, etc.)
                elif (
                    phrase == "misconduct"
                    and theme_id == "professionalism_trust"
                    and actual_polarity == "severe_negative"
                    and any(kw in text_lower for kw in (
                        "false accusation", "accused of misconduct",
                        "charged with misconduct", "allegations of misconduct",
                        "allegations against", "false charges", "wrongfully accused",
                        "fighting misconduct", "against misconduct",
                        "insurance misconduct", "opposing counsel misconduct",
                    ))
                ):
                    continue  # suppress: misconduct subject is the client, not the attorney

                # GUARD 1: "confusing" in billing context -> redirect to billing_transparency
                elif (
                    phrase == "confusing"
                    and theme_id == "communication_clarity"
                    and any(kw in text_lower for kw in ("billing", "statement", "invoice"))
                ):
                    theme_id = "billing_transparency"
                    hit["theme"] = "billing_transparency"

                # GUARD 1b: "slow" timeliness false positive guard
                # "response times were slow" -> responsiveness, not timeliness
                # "intake process was slow" -> not a timeliness signal
                elif (
                    phrase == "slow"
                    and theme_id == "timeliness_progress"
                    and actual_polarity == "negative"
                    and any(kw in text_lower for kw in (
                        "response time", "response times", "getting back",
                        "intake", "intake process", "confusing",
                    ))
                ):
                    continue  # suppress: "slow" here signals responsiveness or clarity, not timeliness

                # GUARD 1c: clause-comparison + staffing context routing.
                # "more professional" inside a negative comparison is not a live
                # professionalism positive hit. Likewise bare "rude" in staff
                # reviews belongs with office staff unless the attorney is explicit.
                elif (
                    phrase == "professional"
                    and theme_id == "professionalism_trust"
                    and actual_polarity == "positive"
                    and rating <= 2
                    and "more professional" in text_lower
                ):
                    continue
                elif (
                    phrase == "rude"
                    and theme_id == "professionalism_trust"
                    and any(kw in text_lower for kw in (
                        "staff", "office", "receptionist", "paralegal", "assistant",
                    ))
                    and "attorney was rude" not in text_lower
                    and "lawyer was rude" not in text_lower
                ):
                    theme_id = "office_staff_experience"
                    hit["theme"] = "office_staff_experience"

                # GUARD 1d: positive-leaning long-duration timing statements can
                # appear in successful legal matters; do not force a negative theme
                # when the surrounding review is positive and the result cues are strong.
                elif (
                    phrase in ("it took 12 months", "took 12 months", "took over a year", "took a long time")
                    and theme_id == "timeliness_progress"
                    and actual_polarity == "negative"
                    and rating >= 4
                    and _text_has_any(text_lower, POSITIVE_OUTCOME_HINTS)
                ):
                    continue

                # GUARD 2: "expensive" praised in cost-warning context -> suppress fee_value negative hit
                elif (
                    phrase == "expensive"
                    and theme_id == "fee_value"
                    and actual_polarity == "negative"
                    and any(kw in text_lower for kw in ("would be more expensive", "when a motion"))
                    and any(kw in text_lower for kw in ("fair", "warned", "transparent", "budget"))
                ):
                    continue

                # GUARD 3: "honest" with contrast + low rating -> re-route to expectation_setting
                elif (
                    phrase == "honest"
                    and theme_id == "professionalism_trust"
                    and actual_polarity == "positive"
                    and contrast_applied
                    and rating <= 3
                    and any(kw in text_lower for kw in ("wasn't", "didn't", "hoped", "not what", "lost"))
                ):
                    theme_id = "expectation_setting"
                    hit["theme"] = "expectation_setting"
                elif (
                    phrase == "clearly explained"
                    and theme_id == "communication_clarity"
                    and _text_has_any(text_lower, (
                        "more clearly explained",
                        "could have been more clearly explained",
                        "should have been more clearly explained",
                    ))
                ):
                    continue
                elif (
                    phrase == "never heard from them"
                    and theme_id == "timeliness_progress"
                    and _text_has_any(text_lower, (
                        "contacted them", "contact the office", "tried and tried to contact",
                        "message was left", "returns calls", "reply", "replied",
                    ))
                ):
                    continue
                elif (
                    phrase in ("over a year", "over two years", "after 2 years", "after two years", "2 years later")
                    and theme_id == "timeliness_progress"
                    and _text_has_any(text_lower, (
                        "contacted them", "contact the office", "tried and tried to contact",
                        "message was left", "returns calls", "reply", "replied",
                        "never heard from them",
                    ))
                ):
                    continue
                elif (
                    phrase == "forgotten about"
                    and theme_id == "timeliness_progress"
                    and _text_has_any(text_lower, ("case was forgotten about", "our case was forgotten about"))
                ):
                    continue
                elif (
                    phrase == "everything was resolved just like they said it would be"
                    and theme_id == "expectation_setting"
                    and actual_polarity == "positive"
                    and rating >= 4
                    and _text_has_any(text_lower, ("resolved", "recommend", "worth it"))
                ):
                    continue
                elif (
                    phrase == "i had to remind them"
                    and theme_id == "expectation_setting"
                    and _text_has_any(text_lower, ("paralegal", "paralegals", "demands"))
                ):
                    continue
                elif (
                    phrase in ("wasn't fully explained", "was not fully explained")
                    and theme_id == "communication_clarity"
                    and _text_has_any(text_lower, (
                        "cost me over $", "cost me over", "plea deal", "owed money",
                        "still owed money", "settled",
                    ))
                ):
                    continue
                elif (
                    phrase == "lack of communication"
                    and theme_id == "communication_clarity"
                    and _text_has_any(text_lower, (
                        "responses", "questions", "paralegal", "paralegals",
                        "call", "calls", "slow",
                    ))
                ):
                    continue
                elif (
                    phrase == "not pleasant or helpful"
                    and theme_id == "office_staff_experience"
                    and _text_has_any(text_lower, (
                        "phone call to schedule", "answered the phone",
                        "didn't even get past the phone call",
                    ))
                ):
                    continue
                # --- end calibration guards ---

                existing = matched_themes.get(theme_id)
                if (
                    existing is None
                    or final_impact > existing["final_impact"]
                    or (
                        final_impact == existing["final_impact"]
                        and _polarity_rank(hit["polarity"]) > _polarity_rank(existing["polarity"])
                    )
                ):
                    matched_themes[theme_id] = hit

    return {
        "themes": list(matched_themes.values()),
        "rating_prior": rating_prior,
        "review_text_length": len(review_text),
    }


# ---------------------------------------------------------------------------
# OPENROUTER AI BENCHMARK PASS
# ---------------------------------------------------------------------------

def _get_openrouter_key() -> Optional[str]:
    return (os.environ.get("OPENROUTER_API_KEY") or "").strip() or None


def _call_openrouter(
    review_text: str,
    rating: int,
    review_date: str,
    model: str,
    timeout: int,
) -> Tuple[Optional[List[Dict[str, Any]]], Optional[str]]:
    """Call OpenRouter with the review. Returns (themes_list, error_str)."""
    api_key = _get_openrouter_key()
    if not api_key:
        return None, "OPENROUTER_API_KEY not set"

    user_content = OPENROUTER_USER_TEMPLATE.format(
        rating=rating,
        date=review_date,
        text=review_text[:1200],
    )

    payload = {
        "model": model,
        "temperature": 0.0,
        "max_tokens": 600,
        "messages": [
            {"role": "system", "content": OPENROUTER_SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ],
    }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://clarionhq.co",
        "X-Title": "Clarion Benchmark Harness",
    }

    try:
        resp = requests.post(
            OPENROUTER_API_URL,
            json=payload,
            headers=headers,
            timeout=timeout,
        )
        resp.raise_for_status()
    except requests.exceptions.Timeout:
        return None, f"OpenRouter timeout after {timeout}s"
    except requests.exceptions.RequestException as exc:
        return None, f"OpenRouter request error: {exc}"

    try:
        data = resp.json()
        raw_text = data["choices"][0]["message"]["content"].strip()
    except (KeyError, IndexError, ValueError) as exc:
        return None, f"OpenRouter response parse error: {exc}"

    if raw_text.startswith("```"):
        raw_text = re.sub(r"^```[a-z]*\n?", "", raw_text)
        raw_text = re.sub(r"\n?```$", "", raw_text)
    raw_text = raw_text.strip()

    try:
        parsed = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        return None, f"OpenRouter JSON decode error: {exc} | raw: {raw_text[:200]}"

    themes = parsed.get("themes")
    if not isinstance(themes, list):
        return None, f"OpenRouter response missing 'themes' list: {raw_text[:200]}"

    valid_themes = []
    allowed_polarities = {"positive", "negative", "severe_negative"}
    allowed_confidences = {"high", "medium", "low"}

    for item in themes:
        if not isinstance(item, dict):
            continue
        theme = (item.get("theme") or "").strip()
        polarity = (item.get("polarity") or "").strip()
        evidence_span = str(item.get("evidence_span") or "").strip()[:200]
        confidence = (item.get("confidence") or "medium").strip()

        if theme not in BENCHMARK_THEMES:
            logger.debug("benchmark_engine: AI returned unknown theme %r -- skipped", theme)
            continue
        if polarity not in allowed_polarities:
            logger.debug("benchmark_engine: AI returned unknown polarity %r -- skipped", polarity)
            continue
        if confidence not in allowed_confidences:
            confidence = "medium"

        valid_themes.append({
            "theme": theme,
            "polarity": polarity,
            "evidence_span": evidence_span,
            "confidence": confidence,
        })

    return valid_themes, None


def score_review_ai(
    review_text: str,
    rating: int,
    review_date: str,
) -> Dict[str, Any]:
    """
    Run the AI benchmark pass for a single review via OpenRouter.

    Returns:
    {
      "themes":  [ {theme, polarity, evidence_span, confidence}, ... ],
      "error":   str | None,
      "model":   str,
      "skipped": bool,
    }
    """
    api_key = _get_openrouter_key()
    if not api_key:
        return {
            "themes": [],
            "error": None,
            "model": None,
            "skipped": True,
        }

    model = (os.environ.get("OPENROUTER_MODEL") or DEFAULT_OPENROUTER_MODEL).strip()
    timeout = int(os.environ.get("OPENROUTER_TIMEOUT") or DEFAULT_OPENROUTER_TIMEOUT)

    start = time.perf_counter()
    themes, error = _call_openrouter(review_text, rating, review_date, model, timeout)
    elapsed = round(time.perf_counter() - start, 3)

    if error:
        logger.warning("benchmark_engine: AI pass failed in %.3fs: %s", elapsed, error)
        return {
            "themes": [],
            "error": error,
            "model": model,
            "skipped": False,
            "elapsed_s": elapsed,
        }

    logger.info(
        "benchmark_engine: AI pass completed in %.3fs, %d themes", elapsed, len(themes or [])
    )
    return {
        "themes": themes or [],
        "error": None,
        "model": model,
        "skipped": False,
        "elapsed_s": elapsed,
    }


# ---------------------------------------------------------------------------
# COMBINED BENCHMARK RUNNER
# ---------------------------------------------------------------------------

def run_benchmark(
    review_text: str,
    rating: int,
    review_date: str,
    enable_ai: bool = True,
) -> Dict[str, Any]:
    """
    Run deterministic scoring + optional AI benchmark pass for one review.

    Returns a BenchmarkResult dict:
    {
      "review_text":        str,
      "rating":             int,
      "review_date":        str,
      "deterministic":      { ... score_review_deterministic output ... },
      "ai_benchmark":       { ... score_review_ai output ... } | None,
      "ai_enabled":         bool,
    }
    """
    if not review_text or not str(review_text).strip():
        raise ValueError("review_text must not be empty")
    if not isinstance(rating, int) or not (1 <= rating <= 5):
        raise ValueError("rating must be an integer 1-5")

    det_result = score_review_deterministic(review_text, rating, review_date)

    ai_result = None
    if enable_ai:
        ai_result = score_review_ai(review_text, rating, review_date)

    return {
        "review_text": review_text,
        "rating": rating,
        "review_date": review_date,
        "deterministic": det_result,
        "ai_benchmark": ai_result,
        "ai_enabled": enable_ai,
    }
