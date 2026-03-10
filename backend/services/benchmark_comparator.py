"""
services/benchmark_comparator.py

Disagreement classifier for Clarion benchmark harness.

Takes a BenchmarkResult (output of benchmark_engine.run_benchmark) and
classifies every place where the deterministic scorer and the AI benchmark
disagree. Output is a structured list of DisagreementRecord dicts.

DISAGREEMENT TYPES
------------------
  missing_theme           — AI tagged a theme; deterministic did not
  extra_theme             — Deterministic tagged a theme; AI did not
  wrong_polarity          — Both tagged the same theme but assigned different polarity
  wrong_severity          — Same theme, same polarity category but different
                            severity signal (severe_negative vs negative)
  missed_severe_phrase    — Deterministic found a severe_negative phrase;
                            AI only returned negative for the same theme
  ambiguity_or_mixed_sentiment — AI returned low confidence on a theme that
                            the deterministic engine also tagged as uncertain
  likely_false_positive   — Deterministic tagged a theme but AI did not AND
                            rating prior contradicts the polarity
  likely_context_guard_failure — Deterministic applied negation/contrast guard
                            but AI tagged the opposite polarity for the same theme

USAGE
-----
    from services.benchmark_comparator import classify_disagreements

    disagreements = classify_disagreements(benchmark_result)
    # returns List[DisagreementRecord]

Each DisagreementRecord is a plain dict with keys:
  disagreement_type, theme, deterministic_polarity, ai_polarity,
  deterministic_phrase, ai_evidence_span, detail, severity_flag
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger("benchmark_comparator")

# Polarity ordering for severity comparison
_POLARITY_RANK = {
    "positive": 0,
    "negative": 1,
    "severe_negative": 2,
}


def _det_themes_by_id(deterministic: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    """Index deterministic theme hits by theme ID. One entry per theme (best hit)."""
    out: Dict[str, Dict[str, Any]] = {}
    for hit in deterministic.get("themes") or []:
        tid = hit.get("theme")
        if not tid:
            continue
        existing = out.get(tid)
        # Keep highest final_impact if somehow duplicated
        if existing is None or hit.get("final_impact", 0) > existing.get("final_impact", 0):
            out[tid] = hit
    return out


def _ai_themes_by_id(ai_benchmark: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    """Index AI theme hits by theme ID. One entry per theme (last one wins for simplicity)."""
    out: Dict[str, Dict[str, Any]] = {}
    for item in ai_benchmark.get("themes") or []:
        tid = item.get("theme")
        if tid:
            out[tid] = item
    return out


def _make_record(
    disagreement_type: str,
    theme: str,
    *,
    det_polarity: Optional[str] = None,
    ai_polarity: Optional[str] = None,
    det_phrase: Optional[str] = None,
    ai_evidence: Optional[str] = None,
    detail: str = "",
    severity_flag: bool = False,
) -> Dict[str, Any]:
    return {
        "disagreement_type": disagreement_type,
        "theme": theme,
        "deterministic_polarity": det_polarity,
        "ai_polarity": ai_polarity,
        "deterministic_phrase": det_phrase,
        "ai_evidence_span": ai_evidence,
        "detail": detail,
        "severity_flag": severity_flag,
    }


def classify_disagreements(benchmark_result: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Compare deterministic and AI outputs from a BenchmarkResult.
    Returns a list of DisagreementRecord dicts.

    Returns an empty list when:
      - AI pass was skipped (no API key / enable_ai=False)
      - AI pass failed (error was set)
      - Either output is missing
    """
    deterministic = benchmark_result.get("deterministic") or {}
    ai_benchmark = benchmark_result.get("ai_benchmark") or {}

    # Skip if AI was not run or failed
    if not benchmark_result.get("ai_enabled"):
        return []
    if ai_benchmark.get("skipped"):
        return []
    if ai_benchmark.get("error"):
        logger.debug("benchmark_comparator: skipping comparison — AI error: %s", ai_benchmark["error"])
        return []

    rating_prior = deterministic.get("rating_prior", "neutral")

    det_by_theme = _det_themes_by_id(deterministic)
    ai_by_theme = _ai_themes_by_id(ai_benchmark)

    all_themes = set(det_by_theme.keys()) | set(ai_by_theme.keys())
    records: List[Dict[str, Any]] = []

    for theme in sorted(all_themes):
        det_hit = det_by_theme.get(theme)
        ai_hit = ai_by_theme.get(theme)

        # ----------------------------------------------------------------
        # Case 1: AI found it, deterministic did not
        # ----------------------------------------------------------------
        if det_hit is None and ai_hit is not None:
            records.append(_make_record(
                "missing_theme",
                theme,
                det_polarity=None,
                ai_polarity=ai_hit.get("polarity"),
                ai_evidence=ai_hit.get("evidence_span"),
                detail=(
                    f"AI tagged '{theme}' with polarity '{ai_hit.get('polarity')}' "
                    f"(confidence={ai_hit.get('confidence')}); "
                    "no deterministic phrase matched."
                ),
                severity_flag=ai_hit.get("polarity") == "severe_negative",
            ))
            continue

        # ----------------------------------------------------------------
        # Case 2: Deterministic found it, AI did not
        # ----------------------------------------------------------------
        if det_hit is not None and ai_hit is None:
            det_polarity = det_hit.get("polarity", "")
            negation = det_hit.get("negation_applied", False)
            contrast = det_hit.get("contrast_applied", False)

            # Sub-classify the extra_theme
            if negation or contrast:
                rec_type = "likely_context_guard_failure"
                detail = (
                    f"Deterministic tagged '{theme}' as '{det_polarity}' via phrase "
                    f"'{det_hit.get('matched_phrase')}' with "
                    f"negation={negation}, contrast={contrast}. "
                    "AI did not tag this theme — possible guard over-triggering."
                )
            elif (
                det_polarity in ("negative", "severe_negative") and rating_prior == "positive"
            ) or (
                det_polarity == "positive" and rating_prior == "negative"
            ):
                rec_type = "likely_false_positive"
                detail = (
                    f"Deterministic tagged '{theme}' as '{det_polarity}' via phrase "
                    f"'{det_hit.get('matched_phrase')}' but star rating prior is '{rating_prior}'. "
                    "AI did not tag this theme — possible false positive."
                )
            else:
                rec_type = "extra_theme"
                detail = (
                    f"Deterministic tagged '{theme}' as '{det_polarity}' via phrase "
                    f"'{det_hit.get('matched_phrase')}'. "
                    "AI did not tag this theme."
                )

            records.append(_make_record(
                rec_type,
                theme,
                det_polarity=det_polarity,
                ai_polarity=None,
                det_phrase=det_hit.get("matched_phrase"),
                detail=detail,
                severity_flag=det_polarity == "severe_negative",
            ))
            continue

        # ----------------------------------------------------------------
        # Case 3: Both tagged the theme — compare polarity
        # ----------------------------------------------------------------
        if det_hit is not None and ai_hit is not None:
            det_polarity = det_hit.get("polarity", "")
            ai_polarity = ai_hit.get("polarity", "")

            if det_polarity == ai_polarity:
                # Full agreement — no record
                continue

            det_rank = _POLARITY_RANK.get(det_polarity, 0)
            ai_rank = _POLARITY_RANK.get(ai_polarity, 0)

            # Distinguish severity disagreement from polarity disagreement
            if (
                det_polarity in ("negative", "severe_negative") and
                ai_polarity in ("negative", "severe_negative") and
                det_polarity != ai_polarity
            ):
                # Both negative-family but different severity tier
                if det_polarity == "severe_negative" and ai_polarity == "negative":
                    rec_type = "missed_severe_phrase"
                    detail = (
                        f"Deterministic matched severe phrase '{det_hit.get('matched_phrase')}' "
                        f"for '{theme}'; AI only returned 'negative'. "
                        "Potential missed severe pattern in AI output."
                    )
                    severity_flag = True
                else:
                    rec_type = "wrong_severity"
                    detail = (
                        f"Deterministic: '{det_polarity}', AI: '{ai_polarity}' for theme '{theme}'. "
                        f"Det phrase: '{det_hit.get('matched_phrase')}', "
                        f"AI evidence: '{ai_hit.get('evidence_span')}'"
                    )
                    severity_flag = det_rank > ai_rank

                records.append(_make_record(
                    rec_type,
                    theme,
                    det_polarity=det_polarity,
                    ai_polarity=ai_polarity,
                    det_phrase=det_hit.get("matched_phrase"),
                    ai_evidence=ai_hit.get("evidence_span"),
                    detail=detail,
                    severity_flag=severity_flag,
                ))

            elif (
                (det_polarity == "positive" and ai_polarity in ("negative", "severe_negative")) or
                (det_polarity in ("negative", "severe_negative") and ai_polarity == "positive")
            ):
                # True polarity flip
                negation = det_hit.get("negation_applied", False)
                contrast = det_hit.get("contrast_applied", False)

                if negation or contrast:
                    rec_type = "likely_context_guard_failure"
                    detail = (
                        f"Deterministic flipped polarity on '{theme}' to '{det_polarity}' "
                        f"(negation={negation}, contrast={contrast}) via phrase "
                        f"'{det_hit.get('matched_phrase')}', but AI tagged it '{ai_polarity}'. "
                        "Guard may have fired incorrectly."
                    )
                elif ai_hit.get("confidence") == "low":
                    rec_type = "ambiguity_or_mixed_sentiment"
                    detail = (
                        f"Polarity conflict on '{theme}': det='{det_polarity}', ai='{ai_polarity}' "
                        f"(AI confidence=low). "
                        f"Det phrase: '{det_hit.get('matched_phrase')}', "
                        f"AI evidence: '{ai_hit.get('evidence_span')}'"
                    )
                else:
                    rec_type = "wrong_polarity"
                    detail = (
                        f"Polarity conflict on '{theme}': det='{det_polarity}', ai='{ai_polarity}'. "
                        f"Det phrase: '{det_hit.get('matched_phrase')}', "
                        f"AI evidence: '{ai_hit.get('evidence_span')}'"
                    )

                records.append(_make_record(
                    rec_type,
                    theme,
                    det_polarity=det_polarity,
                    ai_polarity=ai_polarity,
                    det_phrase=det_hit.get("matched_phrase"),
                    ai_evidence=ai_hit.get("evidence_span"),
                    detail=detail,
                    severity_flag=(
                        "severe_negative" in (det_polarity, ai_polarity)
                    ),
                ))

    return records
