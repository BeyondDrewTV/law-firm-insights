"""
routes/internal_benchmark.py

Internal-only Flask Blueprint for the Clarion benchmark harness.

Mounted at: /internal/benchmark/
Protected by: INTERNAL_BENCHMARK_SECRET env var (Bearer token in Authorization header)
              Falls back to DEBUG-mode-only if env var is not set.

These routes are COMPLETELY ISOLATED from the production API surface.
No existing routes, DB schemas, or frontend contracts are touched.

ROUTES
------
  POST /internal/benchmark/single
    Run benchmark on one review (deterministic + optional AI).
    Body: { review_text, rating, date, enable_ai? }
    Returns: BenchmarkResult + disagreements

  POST /internal/benchmark/batch
    Run benchmark on a list of reviews.
    Body: { reviews: [{review_text, rating, date}], enable_ai?, fixtures? }
    If fixtures=true, runs on built-in seed dataset instead of provided reviews.
    Returns: { results, calibration_report }

  GET  /internal/benchmark/themes
    Returns the BENCHMARK_THEMES list and THEME_PHRASES keys for inspection.
    No auth required (read-only, non-sensitive).

ENV VARS
--------
  INTERNAL_BENCHMARK_SECRET  — required Bearer token for POST routes in prod
  OPENROUTER_API_KEY          — enables the AI benchmark pass
  OPENROUTER_MODEL            — model to use (default: openai/gpt-4o-mini)
  OPENROUTER_TIMEOUT          — HTTP timeout in seconds (default: 20)
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, List

from flask import Blueprint, current_app, jsonify, request

from services.benchmark_engine import (
    BENCHMARK_THEMES,
    THEME_PHRASES,
    run_benchmark,
)
from services.benchmark_comparator import classify_disagreements
from services.benchmark_report import generate_calibration_report
from data.benchmark_fixtures import BENCHMARK_FIXTURES

logger = logging.getLogger("internal_benchmark")

benchmark_bp = Blueprint("internal_benchmark", __name__, url_prefix="/internal/benchmark")

# ---------------------------------------------------------------------------
# Auth helper
# ---------------------------------------------------------------------------

def _is_authorised() -> bool:
    """
    Check request is allowed to hit internal benchmark routes.

    Strategy:
    1. If INTERNAL_BENCHMARK_SECRET is set, require Authorization: Bearer <secret>.
    2. If not set: allow only when app.config['DEBUG'] is True (local dev).
    3. Never allow in production without a secret.
    """
    secret = (os.environ.get("INTERNAL_BENCHMARK_SECRET") or "").strip()
    if secret:
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            return auth_header[7:].strip() == secret
        return False

    # No secret configured — only allow in DEBUG mode
    return bool(current_app.config.get("DEBUG"))


def _auth_error():
    return (
        jsonify({"success": False, "error": "Unauthorized. Set Authorization: Bearer <INTERNAL_BENCHMARK_SECRET>."}),
        401,
    )


# ---------------------------------------------------------------------------
# Request validation helpers
# ---------------------------------------------------------------------------

def _validate_review_fields(obj: Any) -> tuple[bool, str]:
    """Return (ok, error_message)."""
    if not isinstance(obj, dict):
        return False, "Each review must be a JSON object."
    review_text = str(obj.get("review_text") or "").strip()
    if not review_text:
        return False, "review_text is required and must not be empty."
    try:
        rating = int(obj.get("rating") or 0)
    except (TypeError, ValueError):
        return False, "rating must be an integer."
    if not (1 <= rating <= 5):
        return False, f"rating must be 1–5, got {rating}."
    return True, ""


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@benchmark_bp.route("/themes", methods=["GET"])
def get_themes():
    """
    Return the benchmark theme vocabulary and phrase families.
    Read-only, no auth required.
    """
    theme_summary = {
        theme: {
            polarity: len(phrases)
            for polarity, phrases in buckets.items()
        }
        for theme, buckets in THEME_PHRASES.items()
    }
    return jsonify({
        "success": True,
        "benchmark_themes": BENCHMARK_THEMES,
        "phrase_counts_by_theme_and_polarity": theme_summary,
        "total_phrases": sum(
            len(phrases)
            for buckets in THEME_PHRASES.values()
            for phrases in buckets.values()
        ),
    })


@benchmark_bp.route("/single", methods=["POST"])
def run_single():
    """
    Run benchmark on one review.

    Request body (JSON):
    {
      "review_text": "...",
      "rating":      4,
      "date":        "2025-02-01",   // optional, defaults to today
      "enable_ai":   true            // optional, defaults to true
    }

    Response:
    {
      "success": true,
      "benchmark_result": { ... },
      "disagreements": [ ... ]
    }
    """
    if not _is_authorised():
        return _auth_error()

    body = request.get_json(silent=True) or {}

    ok, err = _validate_review_fields(body)
    if not ok:
        return jsonify({"success": False, "error": err}), 400

    review_text = str(body["review_text"]).strip()
    rating = int(body["rating"])
    date = str(body.get("date") or "2025-01-01").strip()
    enable_ai = bool(body.get("enable_ai", True))

    try:
        result = run_benchmark(
            review_text=review_text,
            rating=rating,
            review_date=date,
            enable_ai=enable_ai,
        )
    except Exception as exc:
        logger.exception("benchmark /single error")
        return jsonify({"success": False, "error": str(exc)}), 500

    try:
        disagreements = classify_disagreements(result)
    except Exception as exc:
        logger.exception("benchmark /single comparator error")
        disagreements = []

    return jsonify({
        "success": True,
        "benchmark_result": result,
        "disagreements": disagreements,
    })


@benchmark_bp.route("/batch", methods=["POST"])
def run_batch():
    """
    Run benchmark on a list of reviews and return a calibration report.

    Request body (JSON):
    {
      "reviews": [
        { "review_text": "...", "rating": 4, "date": "2025-02-01" },
        ...
      ],
      "enable_ai":   true,    // optional, defaults to true
      "fixtures":    false    // optional; if true, ignores 'reviews' and uses seed dataset
    }

    Response:
    {
      "success": true,
      "total_reviews": N,
      "results": [ { benchmark_result, disagreements }, ... ],
      "calibration_report": { ... }
    }
    """
    if not _is_authorised():
        return _auth_error()

    body = request.get_json(silent=True) or {}
    enable_ai = bool(body.get("enable_ai", True))
    use_fixtures = bool(body.get("fixtures", False))

    if use_fixtures:
        reviews_raw = [
            {
                "review_text": f["review_text"],
                "rating": f["rating"],
                "date": f["date"],
                "_id": f.get("id", ""),
                "_notes": f.get("notes", ""),
            }
            for f in BENCHMARK_FIXTURES
        ]
    else:
        reviews_raw = body.get("reviews") or []
        if not isinstance(reviews_raw, list) or len(reviews_raw) == 0:
            return jsonify({"success": False, "error": "reviews must be a non-empty list, or set fixtures=true."}), 400

        # Validate all reviews up front before running any
        for idx, rev in enumerate(reviews_raw):
            ok, err = _validate_review_fields(rev)
            if not ok:
                return jsonify({
                    "success": False,
                    "error": f"reviews[{idx}]: {err}",
                }), 400

        # Cap batch size to prevent runaway AI spend
        cap = int(os.environ.get("BENCHMARK_BATCH_CAP") or 100)
        if len(reviews_raw) > cap:
            return jsonify({
                "success": False,
                "error": f"Batch too large: {len(reviews_raw)} reviews. Cap is {cap}. Set BENCHMARK_BATCH_CAP env var to raise.",
            }), 400

    benchmark_results: List[Dict[str, Any]] = []
    disagreement_batches: List[List[Dict[str, Any]]] = []
    output_rows: List[Dict[str, Any]] = []

    for rev in reviews_raw:
        review_text = str(rev.get("review_text") or "").strip()
        rating = int(rev.get("rating") or 3)
        date = str(rev.get("date") or "2025-01-01").strip()

        try:
            result = run_benchmark(
                review_text=review_text,
                rating=rating,
                review_date=date,
                enable_ai=enable_ai,
            )
        except Exception as exc:
            logger.exception("benchmark /batch error for review: %s", review_text[:80])
            result = {
                "review_text": review_text,
                "rating": rating,
                "review_date": date,
                "deterministic": {"themes": [], "rating_prior": "neutral"},
                "ai_benchmark": {"themes": [], "error": str(exc), "skipped": False},
                "ai_enabled": enable_ai,
            }

        try:
            disagreements = classify_disagreements(result)
        except Exception as exc:
            logger.exception("benchmark /batch comparator error")
            disagreements = []

        benchmark_results.append(result)
        disagreement_batches.append(disagreements)

        row: Dict[str, Any] = {
            "benchmark_result": result,
            "disagreements": disagreements,
        }
        # Carry fixture metadata through if present
        if rev.get("_id"):
            row["fixture_id"] = rev["_id"]
        if rev.get("_notes"):
            row["fixture_notes"] = rev["_notes"]
        output_rows.append(row)

    try:
        calibration_report = generate_calibration_report(benchmark_results, disagreement_batches)
    except Exception as exc:
        logger.exception("benchmark /batch report generation error")
        calibration_report = {"error": str(exc)}

    return jsonify({
        "success": True,
        "total_reviews": len(benchmark_results),
        "results": output_rows,
        "calibration_report": calibration_report,
    })
