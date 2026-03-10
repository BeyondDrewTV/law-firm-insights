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
        enable_ai=True,          # False to skip OpenRouter call
    )

ENV VARS REQUIRED
-----------------
    OPENROUTER_API_KEY   — OpenRouter API key (AI pass skipped when absent)
    OPENROUTER_MODEL     — model slug, defaults to "openai/gpt-4o-mini"
    OPENROUTER_TIMEOUT   — HTTP timeout in seconds, defaults to 20
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
# These are the 10 governance themes Clarion tracks for law firms.
# Separate from ALLOWED_THEMES in classification_schema.py — those are the
# older internal LLM classification vocabulary; these are the governance-level
# themes used in the benchmark harness.
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
# ---------------------------------------------------------------------------
THEME_PHRASES: Dict[str, Dict[str, List[Tuple[str, float]]]] = {
    "communication_responsiveness": {
        "positive": [
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
        ],
        "negative": [
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
        ],
        "severe_negative": [
            ("completely unreachable", 2.0),
            ("impossible to contact", 2.0),
            ("months without any contact", 2.0),
            ("never returned my calls", 2.0),
        ],
    },
    "communication_clarity": {
        "positive": [
            ("clearly explained", 1.0),
            ("easy to understand", 1.0),
            ("explained everything", 1.0),
            ("explained the process", 1.0),
            ("kept me in the loop", 1.0),
            ("plain language", 1.0),
            ("thoroughly explained", 1.5),
            ("very clear", 1.0),
            ("walked me through", 1.0),
        ],
        "negative": [
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
        ],
        "severe_negative": [
            ("completely in the dark", 2.0),
            ("had no idea what was happening", 2.0),
            ("no communication whatsoever", 2.0),
        ],
    },
    "empathy_support": {
        "positive": [
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
        ],
        "negative": [
            ("cold", 1.0),
            ("didn't care", 1.0),
            ("dismissed", 1.0),
            ("dismissive", 1.5),
            ("felt like a number", 1.5),
            ("impersonal", 1.0),
            ("no empathy", 1.5),
            ("not compassionate", 1.0),
            ("uncaring", 1.5),
        ],
        "severe_negative": [
            ("completely dismissive", 2.0),
            ("treated me like i didn't matter", 2.0),
            ("felt abandoned", 2.0),
        ],
    },
    "professionalism_trust": {
        "positive": [
            ("courteous", 1.0),
            ("ethical", 1.0),
            ("honest", 1.0),
            ("integrity", 1.0),
            ("polite", 1.0),
            ("professional", 1.0),
            ("respectful", 1.0),
            ("straightforward", 1.0),
            ("trustworthy", 1.5),
            ("transparent", 1.0),
        ],
        "negative": [
            ("dishonest", 1.5),
            ("disrespectful", 1.5),
            ("felt misled", 1.5),
            ("lied", 2.0),
            ("misled", 1.5),
            ("not honest", 1.5),
            ("rude", 1.5),
            ("unprofessional", 1.5),
            ("untrustworthy", 1.5),
        ],
        "severe_negative": [
            ("accused of lying", 2.0),
            ("completely unprofessional", 2.0),
            ("ethical violation", 2.0),
            ("filed a complaint", 2.0),
            ("fraudulent", 2.0),
            ("reported to the bar", 2.0),
        ],
    },
    "expectation_setting": {
        "positive": [
            ("clearly outlined", 1.0),
            ("explained what to expect", 1.0),
            ("gave me realistic expectations", 1.5),
            ("no surprises", 1.0),
            ("set clear expectations", 1.5),
            ("upfront about", 1.0),
            ("walked me through the process", 1.0),
        ],
        "negative": [
            ("didn't warn me", 1.0),
            ("expected a different outcome", 1.0),
            ("false promises", 2.0),
            ("misleading promises", 2.0),
            ("not what i expected", 1.0),
            ("overpromised", 1.5),
            ("surprised by", 1.0),
            ("unexpected", 1.0),
        ],
        "severe_negative": [
            ("blatant false promises", 2.0),
            ("guaranteed a win", 2.0),
            ("promised outcomes", 2.0),
        ],
    },
    "billing_transparency": {
        "positive": [
            ("billing was clear", 1.5),
            ("clear billing", 1.5),
            ("detailed invoice", 1.0),
            ("explained the fees", 1.0),
            ("fee structure was transparent", 1.5),
            ("no hidden fees", 1.5),
            ("no surprise charges", 1.5),
            ("transparent about costs", 1.5),
            ("upfront about fees", 1.5),
        ],
        "negative": [
            ("charged extra", 1.0),
            ("confusing bill", 1.0),
            ("hidden fees", 2.0),
            ("not transparent about fees", 1.5),
            ("overcharged", 1.5),
            ("surprise bill", 1.5),
            ("surprise charge", 1.5),
            ("surprise fees", 1.5),
            ("unexpected bill", 1.5),
            ("unexpected charges", 1.5),
            ("unexpected fees", 1.5),
            ("unclear billing", 1.0),
            ("unclear invoices", 1.0),
        ],
        "severe_negative": [
            ("billing fraud", 2.0),
            ("double billed", 2.0),
            ("grossly overcharged", 2.0),
        ],
    },
    "fee_value": {
        "positive": [
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
        ],
        "negative": [
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
        ],
        "severe_negative": [
            ("absolutely outrageous fees", 2.0),
            ("price gouging", 2.0),
            ("predatory billing", 2.0),
        ],
    },
    "timeliness_progress": {
        "positive": [
            ("ahead of schedule", 1.5),
            ("completed on time", 1.0),
            ("efficient", 1.0),
            ("fast turnaround", 1.0),
            ("handled quickly", 1.0),
            ("moved quickly", 1.0),
            ("no unnecessary delays", 1.0),
            ("quick resolution", 1.5),
            ("resolved quickly", 1.5),
            ("timely", 1.0),
        ],
        "negative": [
            ("case dragged on", 1.5),
            ("delayed", 1.0),
            ("delays", 1.0),
            ("everything took too long", 1.5),
            ("missed deadlines", 1.5),
            ("slow", 1.0),
            ("took forever", 1.5),
            ("took too long", 1.5),
            ("unnecessary delays", 1.5),
        ],
        "severe_negative": [
            ("missed critical deadline", 2.0),
            ("statute of limitations", 2.0),
            ("filed too late", 2.0),
        ],
    },
    "office_staff_experience": {
        "positive": [
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
        ],
        "negative": [
            ("front desk was rude", 1.5),
            ("rude receptionist", 1.5),
            ("rude staff", 1.5),
            ("staff was disorganized", 1.0),
            ("staff was rude", 1.5),
            ("staff was unhelpful", 1.0),
            ("unfriendly staff", 1.0),
            ("unhelpful staff", 1.0),
        ],
        "severe_negative": [
            ("abusive staff", 2.0),
            ("harassment by staff", 2.0),
            ("hostile front desk", 2.0),
        ],
    },
    "outcome_satisfaction": {
        "positive": [
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
        ],
        "negative": [
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
        ],
        "severe_negative": [
            ("case completely mishandled", 2.0),
            ("lost everything", 2.0),
            ("negligence", 2.0),
            ("malpractice", 2.0),
        ],
    },
}

# ---------------------------------------------------------------------------
# NEGATION GUARDS
# If any of these tokens appear in a sliding window of NEGATION_WINDOW words
# *before* a matched phrase, the polarity is flipped.
# ---------------------------------------------------------------------------
NEGATION_TOKENS = {
    "not", "never", "no", "didn't", "did not", "doesn't", "does not",
    "wasn't", "was not", "weren't", "were not", "wouldn't", "would not",
    "couldn't", "could not", "haven't", "have not", "hadn't", "had not",
    "isn't", "is not", "aren't", "are not", "hardly", "barely", "scarcely",
}
NEGATION_WINDOW = 6  # words before the phrase start to scan

# ---------------------------------------------------------------------------
# CONTRAST GUARDS
# Phrases that signal the reviewer is about to contrast with something
# positive — downweight the positive hit that follows.
# ---------------------------------------------------------------------------
CONTRAST_TOKENS = {
    "however", "but", "although", "though", "despite", "except",
    "unfortunately", "sadly", "regrettably", "while",
}
CONTRAST_WINDOW = 4  # words before the matched phrase

# ---------------------------------------------------------------------------
# STAR RATING → POLARITY PRIOR
# When star rating strongly disagrees with matched phrase polarity,
# apply a confidence penalty but do not suppress the hit.
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
  theme         — exact string from the allowed list
  polarity      — exactly one of: positive, negative, severe_negative
  evidence_span — verbatim excerpt from the review (max 120 chars)
  confidence    — exactly one of: high, medium, low

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
    # Check single-token negations
    for tok in window:
        if tok in NEGATION_TOKENS:
            return True
    # Check two-word negations ("did not", "was not", etc.)
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
        snippet = "…" + snippet
    if end < len(text):
        snippet = snippet + "…"
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
          "base_polarity":      str,   # polarity before negation/contrast flip
          "matched_phrase":     str,
          "phrase_family":      str,   # polarity bucket: positive/negative/severe_negative
          "sentence_snippet":   str,
          "negation_applied":   bool,
          "contrast_applied":   bool,
          "base_weight":        float,
          "multiplier":         float,
          "final_impact":       float,
          "confidence":         str,   # high/medium/low
        },
        ...
      ],
      "rating_prior":           str,   # star-rating polarity prior
      "review_text_length":     int,
    }
    """
    text_lower = review_text.lower()
    tokens = _tokenize(review_text)
    rating_prior = RATING_POLARITY_MAP.get(int(rating or 3), "neutral")
    matched_themes: Dict[str, Any] = {}  # theme_id -> best hit dict

    for theme_id, polarity_buckets in THEME_PHRASES.items():
        for phrase_family, phrase_list in polarity_buckets.items():
            for phrase, base_weight in phrase_list:
                # Find phrase in lowercased text
                idx = text_lower.find(phrase)
                if idx == -1:
                    continue

                # Find approximate token position for negation/contrast window
                pre_text = text_lower[:idx]
                phrase_token_start = len(pre_text.split())

                negation_applied = _check_negation(tokens, phrase_token_start)
                contrast_applied = _check_contrast(tokens, phrase_token_start)

                # Determine actual polarity after guards
                base_polarity = phrase_family
                if negation_applied:
                    # Flip positive ↔ negative; severe_negative becomes negative
                    if phrase_family == "positive":
                        actual_polarity = "negative"
                    elif phrase_family in ("negative", "severe_negative"):
                        actual_polarity = "positive"
                    else:
                        actual_polarity = phrase_family
                else:
                    actual_polarity = phrase_family

                # Multiplier: contrast on a positive match downgrades it
                multiplier = 1.0
                if contrast_applied and actual_polarity == "positive":
                    multiplier = 0.6

                # Rating-prior agreement boosts confidence
                if actual_polarity in ("negative", "severe_negative") and rating_prior == "negative":
                    multiplier *= 1.2
                elif actual_polarity == "positive" and rating_prior == "positive":
                    multiplier *= 1.2

                final_impact = round(base_weight * multiplier, 3)

                # Confidence: driven by severity + rating alignment
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

                # Keep best hit per theme (highest final_impact)
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
    """
    Call OpenRouter with the review. Returns (themes_list, error_str).
    themes_list is None on failure.
    """
    api_key = _get_openrouter_key()
    if not api_key:
        return None, "OPENROUTER_API_KEY not set"

    user_content = OPENROUTER_USER_TEMPLATE.format(
        rating=rating,
        date=review_date,
        text=review_text[:1200],  # cap to keep prompt tight
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

    # Strip any accidental markdown fences
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

    # Validate and normalise each theme entry
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
            logger.debug("benchmark_engine: AI returned unknown theme %r — skipped", theme)
            continue
        if polarity not in allowed_polarities:
            logger.debug("benchmark_engine: AI returned unknown polarity %r — skipped", polarity)
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
      "skipped": bool,   # True when AI pass was not attempted (no key or disabled)
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
        raise ValueError("rating must be an integer 1–5")

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
