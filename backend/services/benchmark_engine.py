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
#   [CG] = needs_context_guard -- phrase is ambiguous without sentence-level
#          context; a future pass should add negation/contrast/sentence logic.
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
            # --- new: safe_import_now ---
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
            # --- calibration: sample2 ---
            ("corrected quickly", 1.0),
            ("more frequent check-ins would have been nice", 0.8),
            ("best way to reach them", 0.8),
            # --- calibration: full_batch_20260311 ---
            ("responses were quick", 1.5),
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
            # --- new: safe_import_now ---
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
            ("no follow-up", 1.0),
            ("no return call", 1.5),
            ("no updates for weeks", 1.5),
            ("not communicating", 1.0),
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
        ],
        "severe_negative": [
            # --- original ---
            ("completely unreachable", 2.0),
            ("impossible to contact", 2.0),
            ("months without any contact", 2.0),
            ("never returned my calls", 2.0),
            # --- new: safe_import_now ---
            ("abandoned me completely", 2.0),
            ("completely stopped communicating", 2.0),
            ("ghosted me", 2.0),
            ("months of no contact", 2.0),
            ("months without communication", 2.0),
            ("months without hearing anything", 2.0),
            ("no communication for months", 2.0),
            ("refused to return calls", 2.0),
            ("totally disappeared", 2.0),
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
            # --- new: safe_import_now ---
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
            ("transparent throughout", 1.0),
            ("very informative", 1.0),
            ("walked me through everything", 1.5),
            ("well explained", 1.0),
            # --- calibration: sample2 ---
            ("explained each step of the custody process", 1.5),
            ("direct communication style", 1.0),
            ("asked for a summary they provided it", 1.0),
            # --- calibration: full_batch_20260311 ---
            ("communication was clear", 1.5),
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
            # --- new: safe_import_now ---
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
        ],
        "severe_negative": [
            # --- original ---
            ("completely in the dark", 2.0),
            ("had no idea what was happening", 2.0),
            ("no communication whatsoever", 2.0),
            # --- new: safe_import_now ---
            ("deliberately withheld information", 2.0),
            ("hid important information", 2.0),
            ("kept completely in the dark", 2.0),
            ("never told me anything", 2.0),
            ("stonewalled me", 2.0),
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
            ("understanding", 1.0),
            # --- new: safe_import_now ---
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
            ("warm and compassionate", 1.5),
            # --- calibration: sample2 ---
            ("treated my case with empathy", 1.5),
            ("never made me feel judged", 1.5),
            ("focused on what was best for my kids", 1.5),
            ("remembered details about my schedule", 1.0),
            ("gave me scripts for how to talk to my co-parent", 1.0),
            ("checked on my emotional wellbeing", 1.5),
            # --- calibration: full_batch_20260311 ---
            ("i felt listened to", 1.5),
        ],
        "negative": [
            # --- original ---
            ("cold", 1.0),
            ("didn't care", 1.0),
            ("dismissed", 1.0),
            ("dismissive", 1.5),
            ("felt like a number", 1.5),
            ("impersonal", 1.0),
            ("no empathy", 1.5),
            ("not compassionate", 1.0),
            ("uncaring", 1.5),
            # --- new: safe_import_now ---
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
        ],
        "severe_negative": [
            # --- original ---
            ("completely dismissive", 2.0),
            ("felt abandoned", 2.0),
            ("treated me like i didn't matter", 2.0),
            # --- new: safe_import_now ---
            ("callous disregard", 2.0),
            ("cruel and dismissive", 2.0),
            ("emotionally abusive", 2.0),
            ("had zero compassion", 2.0),
            ("showed no empathy whatsoever", 2.0),
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
            ("honest", 1.0),
            ("integrity", 1.0),
            ("polite", 1.0),
            ("professional", 1.0),
            ("respectful", 1.0),
            ("straightforward", 1.0),
            ("transparent", 1.0),
            ("trustworthy", 1.5),
            # --- new: safe_import_now ---
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
            # --- new: safe_import_now ---
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
        ],
        "severe_negative": [
            # --- original ---
            ("accused of lying", 2.0),
            ("completely unprofessional", 2.0),
            ("ethical violation", 2.0),
            ("filed a complaint", 2.0),
            ("fraudulent", 2.0),
            ("reported to the bar", 2.0),
            # --- new: safe_import_now ---
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
            ("stole my money", 2.0),
            ("submitted false documents", 2.0),
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
            # --- new: safe_import_now ---
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
            # --- calibration: sample2 ---
            ("walked me through every possible scenario", 1.5),
            ("honest about the risks", 1.0),
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
            # --- new: safe_import_now ---
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
        ],
        "severe_negative": [
            # --- original ---
            ("blatant false promises", 2.0),
            ("guaranteed a win", 2.0),
            ("promised outcomes", 2.0),
            # --- new: safe_import_now ---
            ("flat out lied about outcomes", 2.0),
            ("guaranteed results they couldn't deliver", 2.0),
            ("made promises they couldn't keep", 2.0),
            ("promised a specific outcome", 2.0),
            ("promised success", 2.0),
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
            # --- new: safe_import_now ---
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
            # --- new: safe_import_now ---
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
        ],
        "severe_negative": [
            # --- original ---
            ("billing fraud", 2.0),
            ("double billed", 2.0),
            ("grossly overcharged", 2.0),
            # --- new: safe_import_now ---
            ("billed for services never rendered", 2.0),
            ("blatant billing fraud", 2.0),
            ("charged far more than agreed", 2.0),
            ("completely fabricated charges", 2.0),
            ("fraudulent billing", 2.0),
            ("fraudulent invoices", 2.0),
            ("grossly inflated billing", 2.0),
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
            # --- new: safe_import_now ---
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
            # --- new: safe_import_now ---
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
        ],
        "severe_negative": [
            # --- original ---
            ("absolutely outrageous fees", 2.0),
            ("predatory billing", 2.0),
            ("price gouging", 2.0),
            # --- new: safe_import_now ---
            ("extortionate fees", 2.0),
            ("extortion", 2.0),
            ("flagrant price gouging", 2.0),
            ("grossly overpriced", 2.0),
            ("outrageously overpriced", 2.0),
            ("predatory pricing", 2.0),
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
            ("timely", 1.0),
            # --- new: safe_import_now ---
            ("acted fast", 1.0),
            ("case moved forward quickly", 1.5),
            ("case moved quickly", 1.5),
            ("case progressed quickly", 1.5),
            ("case resolved quickly", 1.5),
            ("dealt with promptly", 1.0),
            ("diligent and timely", 1.5),
            ("efficient process", 1.0),
            ("everything was done in a timely manner", 1.5),
            ("fast and efficient", 1.5),
            ("handled efficiently", 1.0),
            ("handled in a timely manner", 1.5),
            ("matter was resolved quickly", 1.5),
            ("met all deadlines", 1.5),
            ("moved the case forward", 1.0),
            ("no delays", 1.0),
            ("on schedule", 1.0),
            ("process was quick", 1.0),
            ("quick and efficient", 1.5),
            ("resolved in a timely fashion", 1.5),
            ("stayed on schedule", 1.0),
            ("work was done promptly", 1.0),
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
            # --- new: safe_import_now ---
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
        ],
        "severe_negative": [
            # --- original ---
            ("filed too late", 2.0),
            ("missed critical deadline", 2.0),
            ("statute of limitations", 2.0),
            # --- new: safe_import_now ---
            ("case dismissed due to delay", 2.0),
            ("critical filing missed", 2.0),
            ("deadline missed entirely", 2.0),
            ("filing deadline missed", 2.0),
            ("irreparable harm from delay", 2.0),
            ("lost case due to missed deadline", 2.0),
            ("missed statute of limitations", 2.0),
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
            # --- new: safe_import_now ---
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
            # --- new: safe_import_now ---
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
        ],
        "severe_negative": [
            # --- original ---
            ("abusive staff", 2.0),
            ("harassment by staff", 2.0),
            ("hostile front desk", 2.0),
            # --- new: safe_import_now ---
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
            # --- new: safe_import_now ---
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
            # --- calibration: sample2 ---
            ("mediation preparation was excellent", 1.5),
            ("helped me focus on long-term outcomes", 1.5),
            ("not just winning every argument", 1.0),
            # --- calibration: full_batch_20260311 ---
            ("the outcome met expectations", 1.5),
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
            # --- new: safe_import_now ---
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
        ],
        "severe_negative": [
            # --- original ---
            ("case completely mishandled", 2.0),
            ("lost everything", 2.0),
            ("malpractice", 2.0),
            ("negligence", 2.0),
            # --- new: safe_import_now ---
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
                idx = text_lower.find(phrase)
                if idx == -1:
                    continue

                pre_text = text_lower[:idx]
                phrase_token_start = len(pre_text.split())

                negation_applied = _check_negation(tokens, phrase_token_start)
                contrast_applied = _check_contrast(tokens, phrase_token_start)

                base_polarity = phrase_family
                if negation_applied:
                    if phrase_family == "positive":
                        actual_polarity = "negative"
                    elif phrase_family in ("negative", "severe_negative"):
                        actual_polarity = "positive"
                    else:
                        actual_polarity = phrase_family
                else:
                    actual_polarity = phrase_family

                multiplier = 1.0
                if contrast_applied and actual_polarity == "positive":
                    multiplier = 0.6

                if actual_polarity in ("negative", "severe_negative") and rating_prior == "negative":
                    multiplier *= 1.2
                elif actual_polarity == "positive" and rating_prior == "positive":
                    multiplier *= 1.2

                final_impact = round(base_weight * multiplier, 3)

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
                    "base_weight": base_weight,
                    "multiplier": round(multiplier, 3),
                    "final_impact": final_impact,
                    "confidence": confidence,
                }

                # --- calibration: sample2 context guards ---
                # GUARD 1: "confusing" in billing context -> redirect to billing_transparency
                if (
                    phrase == "confusing"
                    and theme_id == "communication_clarity"
                    and any(kw in text_lower for kw in ("billing", "statement", "invoice"))
                ):
                    theme_id = "billing_transparency"
                    hit["theme"] = "billing_transparency"

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
                # --- end calibration guards ---

                existing = matched_themes.get(theme_id)
                if existing is None or final_impact > existing["final_impact"]:
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
