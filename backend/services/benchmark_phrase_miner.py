"""
services/benchmark_phrase_miner.py

Candidate phrase mining from benchmark disagreements.

Extracts AI-identified evidence spans from disagreement records where the
deterministic scorer missed or under-classified a theme. Groups candidates
by theme + polarity + normalised span, counts occurrences, and returns a
deduplicated, sorted suggestion list for manual review.

IMPORTANT: This module NEVER writes to THEME_PHRASES. It produces
suggestion output only. A human must review and manually add any
candidates to benchmark_engine.THEME_PHRASES.

Usage:
    from services.benchmark_phrase_miner import mine_phrase_candidates

    candidates = mine_phrase_candidates(
        benchmark_results,     # List[BenchmarkResult]
        disagreement_batches,  # List[List[DisagreementRecord]]
    )
    # Returns List[PhraseCandidateGroup]
"""

from __future__ import annotations

import re
import logging
from collections import defaultdict
from typing import Any, Dict, List, Optional

logger = logging.getLogger("benchmark_phrase_miner")

# Disagreement types that indicate AI found something deterministic missed
_MINING_TYPES = {"missing_theme", "wrong_polarity", "wrong_severity", "missed_severe_phrase"}

# Max chars for a normalised candidate span
_MAX_SPAN_LEN = 80


def _normalise_span(span: str) -> str:
    """
    Lowercase, strip, collapse whitespace, and truncate to _MAX_SPAN_LEN.
    Used as a deduplication key.
    """
    span = span.lower().strip()
    span = re.sub(r'\s+', ' ', span)
    return span[:_MAX_SPAN_LEN]


def mine_phrase_candidates(
    benchmark_results: List[Dict[str, Any]],
    disagreement_batches: List[List[Dict[str, Any]]],
) -> List[Dict[str, Any]]:
    """
    Extract candidate phrase additions from disagreement data.

    Scans all disagreement records in _MINING_TYPES and extracts the
    AI-provided evidence_span, grouping by (theme, ai_polarity, normalised_span).

    Returns a list of PhraseCandidateGroup dicts, sorted by occurrence_count
    descending:

    [
      {
        "theme":              str,
        "polarity":           str,   # the AI-assigned polarity
        "evidence_span":      str,   # canonical (first seen) form
        "normalised_span":    str,   # dedup key
        "occurrence_count":   int,
        "source_types":       List[str],  # unique disagreement_type values that contributed
        "sample_review_snippets": List[str],  # up to 3 review snippets for context
      },
      ...
    ]
    """
    # key -> {count, evidence_span (first seen), source_types, snippets}
    grouped: Dict[tuple, Dict[str, Any]] = defaultdict(lambda: {
        "count": 0,
        "evidence_span": "",
        "source_types": set(),
        "snippets": [],
    })

    for i, batch in enumerate(disagreement_batches):
        review_text = ""
        if i < len(benchmark_results):
            review_text = (benchmark_results[i].get("review_text") or "")[:200]

        for rec in batch:
            if rec.get("disagreement_type") not in _MINING_TYPES:
                continue

            ai_evidence = (rec.get("ai_evidence_span") or "").strip()
            if not ai_evidence:
                continue

            theme = rec.get("theme") or ""
            polarity = rec.get("ai_polarity") or ""
            if not theme or not polarity:
                continue

            norm = _normalise_span(ai_evidence)
            key = (theme, polarity, norm)

            entry = grouped[key]
            entry["count"] += 1
            if not entry["evidence_span"]:
                entry["evidence_span"] = ai_evidence[:_MAX_SPAN_LEN]
            entry["source_types"].add(rec["disagreement_type"])
            if len(entry["snippets"]) < 3 and review_text:
                entry["snippets"].append(review_text)

    result = []
    for (theme, polarity, norm), entry in grouped.items():
        result.append({
            "theme": theme,
            "polarity": polarity,
            "evidence_span": entry["evidence_span"],
            "normalised_span": norm,
            "occurrence_count": entry["count"],
            "source_types": sorted(entry["source_types"]),
            "sample_review_snippets": entry["snippets"],
        })

    result.sort(key=lambda x: -x["occurrence_count"])
    logger.debug("benchmark_phrase_miner: %d candidate groups extracted", len(result))
    return result
