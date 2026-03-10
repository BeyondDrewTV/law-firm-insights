"""
services/benchmark_report.py

Calibration report generator for the Clarion benchmark harness.

Aggregates DisagreementRecord lists across a batch of benchmark runs
into a structured CalibrationReport dict suitable for JSON output or
human review.

REPORT SECTIONS
---------------
  summary                 — total reviews, AI-enabled count, total disagreements
  disagreement_by_type    — counts per disagreement_type
  disagreement_by_theme   — counts per theme
  false_positive_themes   — most common likely_false_positive theme hits
  missed_phrases          — AI found themes deterministic missed (sorted by freq)
  severe_mismatches       — all records with severity_flag=True
  context_guard_failures  — all likely_context_guard_failure records
  candidate_phrase_additions — AI-only themes (missing_theme records),
                            grouped by theme with evidence snippets
  candidate_negation_guards  — extra_theme + likely_false_positive records
                            where a contrast/negation guard may be needed
  reviews_needing_inspection — reviews with ≥2 severity_flag disagreements
                            or ≥1 severe_mismatch + rating contradiction

USAGE
-----
    from services.benchmark_report import generate_calibration_report

    results = [run_benchmark(...) for review in reviews]
    disagreement_batches = [classify_disagreements(r) for r in results]
    report = generate_calibration_report(results, disagreement_batches)
"""

from __future__ import annotations

import logging
from collections import Counter, defaultdict
from typing import Any, Dict, List

from services.benchmark_phrase_miner import mine_phrase_candidates

logger = logging.getLogger("benchmark_report")


def generate_calibration_report(
    benchmark_results: List[Dict[str, Any]],
    disagreement_batches: List[List[Dict[str, Any]]],
) -> Dict[str, Any]:
    """
    Build a structured calibration report from a batch of benchmark runs.

    Parameters
    ----------
    benchmark_results   : list of BenchmarkResult dicts (from benchmark_engine.run_benchmark)
    disagreement_batches: list of disagreement record lists (from benchmark_comparator.classify_disagreements)
                          must be the same length and order as benchmark_results

    Returns
    -------
    CalibrationReport dict (JSON-serialisable)
    """
    if len(benchmark_results) != len(disagreement_batches):
        raise ValueError(
            "benchmark_results and disagreement_batches must be the same length"
        )

    total_reviews = len(benchmark_results)
    ai_enabled_count = sum(1 for r in benchmark_results if r.get("ai_enabled"))
    ai_run_count = sum(
        1 for r in benchmark_results
        if r.get("ai_enabled") and
        r.get("ai_benchmark") and
        not r["ai_benchmark"].get("skipped") and
        not r["ai_benchmark"].get("error")
    )

    ai_invalid_count = sum(
        1 for r in benchmark_results
        if r.get("ai_benchmark") and (
            r["ai_benchmark"].get("invalid_schema") or
            r["ai_benchmark"].get("parse_error") or
            r["ai_benchmark"].get("provider_error")
        )
    )
    ai_item_invalid_total = sum(
        (r.get("ai_benchmark") or {}).get("ai_item_invalid_count", 0)
        for r in benchmark_results
    )

    # Flatten all disagreement records with their review index attached
    all_records: List[Dict[str, Any]] = []
    per_review_records: List[List[Dict[str, Any]]] = []
    for i, batch in enumerate(disagreement_batches):
        tagged = [{**rec, "_review_idx": i} for rec in batch]
        all_records.extend(tagged)
        per_review_records.append(tagged)

    total_disagreements = len(all_records)

    # ----------------------------------------------------------------
    # Disagreement counts
    # ----------------------------------------------------------------
    by_type: Counter = Counter()
    by_theme: Counter = Counter()
    severity_flag_by_review: Counter = Counter()

    for rec in all_records:
        by_type[rec["disagreement_type"]] += 1
        by_theme[rec["theme"]] += 1
        if rec.get("severity_flag"):
            severity_flag_by_review[rec["_review_idx"]] += 1

    # ----------------------------------------------------------------
    # False positive themes (likely_false_positive + extra_theme)
    # ----------------------------------------------------------------
    fp_theme_counter: Counter = Counter()
    for rec in all_records:
        if rec["disagreement_type"] in ("likely_false_positive", "extra_theme"):
            fp_theme_counter[rec["theme"]] += 1

    false_positive_themes = [
        {"theme": theme, "count": count}
        for theme, count in fp_theme_counter.most_common()
    ]

    # ----------------------------------------------------------------
    # Missed phrases — AI found these; deterministic missed (missing_theme)
    # ----------------------------------------------------------------
    missed_phrase_counter: Counter = Counter()
    missed_evidence: Dict[str, List[str]] = defaultdict(list)

    for rec in all_records:
        if rec["disagreement_type"] == "missing_theme":
            missed_phrase_counter[rec["theme"]] += 1
            evidence = (rec.get("ai_evidence_span") or "").strip()
            if evidence and len(missed_evidence[rec["theme"]]) < 5:
                missed_evidence[rec["theme"]].append(evidence)

    missed_phrases = [
        {
            "theme": theme,
            "count": count,
            "sample_evidence": missed_evidence.get(theme, []),
        }
        for theme, count in missed_phrase_counter.most_common()
    ]

    # ----------------------------------------------------------------
    # Severe mismatches
    # ----------------------------------------------------------------
    severe_mismatches = [
        {
            "review_idx": rec["_review_idx"],
            "review_snippet": (benchmark_results[rec["_review_idx"]].get("review_text") or "")[:120],
            "rating": benchmark_results[rec["_review_idx"]].get("rating"),
            "disagreement_type": rec["disagreement_type"],
            "theme": rec["theme"],
            "deterministic_polarity": rec.get("deterministic_polarity"),
            "ai_polarity": rec.get("ai_polarity"),
            "deterministic_phrase": rec.get("deterministic_phrase"),
            "detail": rec.get("detail"),
        }
        for rec in all_records
        if rec.get("severity_flag")
    ]

    # ----------------------------------------------------------------
    # Context guard failures
    # ----------------------------------------------------------------
    context_guard_failures = [
        {
            "review_idx": rec["_review_idx"],
            "review_snippet": (benchmark_results[rec["_review_idx"]].get("review_text") or "")[:120],
            "rating": benchmark_results[rec["_review_idx"]].get("rating"),
            "theme": rec["theme"],
            "deterministic_polarity": rec.get("deterministic_polarity"),
            "ai_polarity": rec.get("ai_polarity"),
            "deterministic_phrase": rec.get("deterministic_phrase"),
            "detail": rec.get("detail"),
        }
        for rec in all_records
        if rec["disagreement_type"] == "likely_context_guard_failure"
    ]

    # ----------------------------------------------------------------
    # Candidate phrase additions
    # AI found a theme the deterministic engine missed — these evidence
    # spans are candidates for adding to THEME_PHRASES.
    # ----------------------------------------------------------------
    phrase_additions: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for rec in all_records:
        if rec["disagreement_type"] == "missing_theme":
            phrase_additions[rec["theme"]].append({
                "ai_polarity": rec.get("ai_polarity"),
                "evidence_span": rec.get("ai_evidence_span"),
                "review_snippet": (
                    benchmark_results[rec["_review_idx"]].get("review_text") or ""
                )[:200],
                "rating": benchmark_results[rec["_review_idx"]].get("rating"),
            })

    candidate_phrase_additions = [
        {
            "theme": theme,
            "occurrence_count": len(examples),
            "examples": examples[:5],  # cap to 5 per theme
        }
        for theme, examples in sorted(
            phrase_additions.items(),
            key=lambda kv: -len(kv[1]),
        )
    ]

    # ----------------------------------------------------------------
    # Candidate negation/contrast guards
    # Extra_theme + likely_false_positive records where a guard may help.
    # ----------------------------------------------------------------
    guard_candidates: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for rec in all_records:
        if rec["disagreement_type"] in ("extra_theme", "likely_false_positive"):
            theme = rec["theme"]
            phrase = rec.get("deterministic_phrase")
            if phrase:
                guard_candidates[phrase].append({
                    "theme": theme,
                    "det_polarity": rec.get("deterministic_polarity"),
                    "review_snippet": (
                        benchmark_results[rec["_review_idx"]].get("review_text") or ""
                    )[:200],
                    "rating": benchmark_results[rec["_review_idx"]].get("rating"),
                })

    candidate_negation_guards = [
        {
            "phrase": phrase,
            "occurrence_count": len(examples),
            "themes_affected": list({e["theme"] for e in examples}),
            "examples": examples[:3],
        }
        for phrase, examples in sorted(
            guard_candidates.items(),
            key=lambda kv: -len(kv[1]),
        )
    ]

    # ----------------------------------------------------------------
    # Reviews needing manual inspection
    # Criteria: ≥2 severity-flagged records, or any severe_mismatch where
    # the review's star rating contradicts the deterministic polarity.
    # ----------------------------------------------------------------
    needs_inspection = []
    for i, records in enumerate(per_review_records):
        sev_flags = sum(1 for r in records if r.get("severity_flag"))
        has_polarity_contradiction = any(
            r["disagreement_type"] in ("wrong_polarity", "missed_severe_phrase") and
            r.get("severity_flag")
            for r in records
        )
        if sev_flags >= 2 or has_polarity_contradiction:
            result = benchmark_results[i]
            needs_inspection.append({
                "review_idx": i,
                "review_snippet": (result.get("review_text") or "")[:200],
                "rating": result.get("rating"),
                "severity_flag_count": sev_flags,
                "disagreement_types": list({r["disagreement_type"] for r in records}),
                "reasons": [r.get("detail", "") for r in records if r.get("severity_flag")],
            })

    # ----------------------------------------------------------------
    # Agreement rate (reviews with zero disagreements)
    # ----------------------------------------------------------------
    zero_disagreement_count = sum(
        1 for batch in disagreement_batches if len(batch) == 0
    )
    agreement_rate = (
        round(zero_disagreement_count / total_reviews, 4)
        if total_reviews > 0 else 0.0
    )

    # ----------------------------------------------------------------
    # Top disagreements by priority (6b)
    # ----------------------------------------------------------------
    top_disagreements_by_priority = sorted(
        [
            {
                "review_idx": rec["_review_idx"],
                "priority": rec.get("disagreement_priority", 1),
                "disagreement_type": rec["disagreement_type"],
                "theme": rec["theme"],
                "deterministic_polarity": rec.get("deterministic_polarity"),
                "ai_polarity": rec.get("ai_polarity"),
                "deterministic_phrase": rec.get("deterministic_phrase"),
                "ai_evidence_span": rec.get("ai_evidence_span"),
                "detail": rec.get("detail", ""),
                "severity_flag": rec.get("severity_flag", False),
                "review_snippet": (
                    benchmark_results[rec["_review_idx"]].get("review_text") or ""
                )[:150],
            }
            for rec in all_records
        ],
        key=lambda x: (-x["priority"], x["review_idx"]),
    )[:50]  # cap at 50 to keep payload reasonable

    # ----------------------------------------------------------------
    # Manual review queue — priority ≥ 3 (6c)
    # ----------------------------------------------------------------
    manual_review_queue = [
        rec for rec in top_disagreements_by_priority
        if rec["priority"] >= 3
    ]

    # ----------------------------------------------------------------
    # Phrase mining candidates (6d)
    # ----------------------------------------------------------------
    phrase_mining_candidates = mine_phrase_candidates(benchmark_results, disagreement_batches)

    # ----------------------------------------------------------------
    # Theme disagreement rates (6e)
    # ----------------------------------------------------------------
    theme_disagreement_rates = {
        theme: {
            "disagreement_count": count,
            "rate": round(count / ai_run_count, 4) if ai_run_count > 0 else 0.0,
        }
        for theme, count in by_theme.most_common()
    }

    return {
        "summary": {
            "total_reviews": total_reviews,
            "ai_enabled_count": ai_enabled_count,
            "ai_run_count": ai_run_count,
            "total_disagreements": total_disagreements,
            "zero_disagreement_reviews": zero_disagreement_count,
            "agreement_rate": agreement_rate,
            "ai_invalid_response_count": ai_invalid_count,
            "ai_item_invalid_total": ai_item_invalid_total,
        },
        "disagreement_by_type": dict(by_type.most_common()),
        "disagreement_by_theme": dict(by_theme.most_common()),
        "false_positive_themes": false_positive_themes,
        "missed_phrases": missed_phrases,
        "severe_mismatches": severe_mismatches,
        "context_guard_failures": context_guard_failures,
        "candidate_phrase_additions": candidate_phrase_additions,
        "candidate_negation_guards": candidate_negation_guards,
        "reviews_needing_inspection": needs_inspection,
        "top_disagreements_by_priority": top_disagreements_by_priority,
        "manual_review_queue": manual_review_queue,
        "phrase_mining_candidates": phrase_mining_candidates,
        "theme_disagreement_rates": theme_disagreement_rates,
    }
