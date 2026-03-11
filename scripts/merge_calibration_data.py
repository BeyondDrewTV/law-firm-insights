#!/usr/bin/env python3
"""
Clarion Engine — Calibration Data Merger & Validator

Merges real reviews (CSV) with synthetic reviews (JSON) into a single
validated JSON file ready for run_calibration_batch.py

Usage:
    python scripts/merge_calibration_data.py \
        --csv path/to/real_reviews.csv \
        --json path/to/synthetic_reviews.json \
        --output data/calibration_merged.json

Runs validation checks:
    - No empty review_text
    - Rating is integer 1-5
    - owner_response is string or empty (not null)
    - Deduplication on review_text (exact match)
    - Minimum length check (review_text >= 10 chars)
"""

import argparse
import csv
import json
import sys
from collections import Counter
from pathlib import Path

DEFAULT_DATE = "2025-01-01"


def validate_review(review: dict, source: str, index: int) -> tuple[dict | None, list[str]]:
    """Validate and normalize a single review. Returns (cleaned_review, warnings)."""
    warnings = []
    label = f"[{source} #{index}]"

    text = str(review.get("review_text", "") or "").strip()
    if not text:
        return None, [f"{label} SKIP — empty review_text"]
    if len(text) < 10:
        return None, [f"{label} SKIP — review_text too short ({len(text)} chars): '{text}'"]

    rating_raw = review.get("rating")
    try:
        rating = int(float(str(rating_raw)))
    except (ValueError, TypeError):
        return None, [f"{label} SKIP — invalid rating: '{rating_raw}'"]
    if rating not in range(1, 6):
        return None, [f"{label} SKIP — rating {rating} out of 1-5 range"]

    owner_response = review.get("owner_response")
    if owner_response is None:
        owner_response = ""
        warnings.append(f"{label} NOTE — owner_response was null, set to empty string")
    owner_response = str(owner_response).strip()

    date = str(review.get("date") or DEFAULT_DATE).strip()
    if not date:
        date = DEFAULT_DATE

    cleaned = {
        "review_text": text,
        "rating": rating,
        "owner_response": owner_response,
        "date": date,
        "source": source,
    }
    # Preserve theme/tags from synthetic reviews if present
    for field in ["theme", "tags", "practice_area", "subtype"]:
        if field in review:
            cleaned[field] = review[field]

    return cleaned, warnings


def load_csv(path: str) -> tuple[list[dict], list[str]]:
    reviews, all_warnings = [], []
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader, 1):
            review, warnings = validate_review(dict(row), "real", i)
            all_warnings.extend(warnings)
            if review:
                reviews.append(review)
    return reviews, all_warnings


def load_json(path: str) -> tuple[list[dict], list[str]]:
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        sys.exit(f"❌ JSON file must be a list of review objects, got: {type(data).__name__}")
    reviews, all_warnings = [], []
    for i, item in enumerate(data, 1):
        review, warnings = validate_review(item, "synthetic", i)
        all_warnings.extend(warnings)
        if review:
            reviews.append(review)
    return reviews, all_warnings


def deduplicate(reviews: list[dict]) -> tuple[list[dict], int]:
    seen = set()
    unique, dupes = [], 0
    for r in reviews:
        key = r["review_text"].lower().strip()
        if key in seen:
            dupes += 1
        else:
            seen.add(key)
            unique.append(r)
    return unique, dupes


def print_summary(real: list[dict], synthetic: list[dict], merged: list[dict]):
    all_reviews = merged
    real_counts = Counter(r["rating"] for r in real)
    synth_counts = Counter(r["rating"] for r in synthetic)
    total_counts = Counter(r["rating"] for r in all_reviews)

    print(f"\n{'='*65}")
    print(" MERGE SUMMARY")
    print(f"{'='*65}")
    print(f"  {'Star':<6} {'Real':>8} {'Synthetic':>12} {'Total':>8}")
    print(f"  {'-'*40}")
    for star in range(1, 6):
        r = real_counts.get(star, 0)
        s = synth_counts.get(star, 0)
        t = total_counts.get(star, 0)
        flag = "  ⚠️  thin" if r < 5 and star in [2, 3, 4] else ""
        print(f"  {star}★     {r:>8}  {s:>12}  {t:>8}{flag}")
    print(f"  {'-'*40}")
    print(f"  {'TOTAL':<6} {len(real):>8}  {len(synthetic):>12}  {len(all_reviews):>8}")
    print(f"{'='*65}\n")


def main():
    parser = argparse.ArgumentParser(description="Clarion Calibration Data Merger")
    parser.add_argument("--csv", required=True, help="Path to real reviews CSV")
    parser.add_argument("--json", required=False, help="Path to synthetic reviews JSON")
    parser.add_argument("--output", default="data/calibration_merged.json", help="Output path (default: data/calibration_merged.json)")
    parser.add_argument("--no-dedup", action="store_true", help="Skip deduplication step")
    args = parser.parse_args()

    print(f"\n{'='*65}")
    print(" CLARION ENGINE — CALIBRATION DATA MERGER")
    print(f"{'='*65}\n")

    # Load real reviews
    print(f"Loading real reviews: {args.csv}")
    if not Path(args.csv).exists():
        sys.exit(f"❌ File not found: {args.csv}")
    real_reviews, real_warnings = load_csv(args.csv)
    for w in real_warnings:
        print(f"  {w}")
    print(f"  → {len(real_reviews)} valid real reviews loaded")

    # Load synthetic reviews
    synthetic_reviews = []
    if args.json:
        print(f"\nLoading synthetic reviews: {args.json}")
        if not Path(args.json).exists():
            sys.exit(f"❌ File not found: {args.json}")
        synthetic_reviews, synth_warnings = load_json(args.json)
        for w in synth_warnings:
            print(f"  {w}")
        print(f"  → {len(synthetic_reviews)} valid synthetic reviews loaded")

    # Merge
    merged = real_reviews + synthetic_reviews

    # Deduplicate
    if not args.no_dedup:
        merged, dupes = deduplicate(merged)
        if dupes > 0:
            print(f"\n  ⚠️  Removed {dupes} duplicate review(s) (exact text match)")

    # Summary
    print_summary(real_reviews, synthetic_reviews, merged)

    # Write output
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(merged, f, indent=2, ensure_ascii=False)
    print(f"  ✅ Merged dataset written → {output_path}")
    print(f"     {len(merged)} total reviews ready for calibration batch\n")

    # Readiness check
    real_count = sum(1 for r in merged if r.get("source") == "real")
    if real_count < 75:
        print(f"  ⚠️  Only {real_count} real reviews in merged set.")
        print(f"     Recommended: collect {75 - real_count} more real reviews before running calibration.")
        print(f"     Run: python scripts/calibration_gap_report.py --csv {args.csv}")
    else:
        print(f"  ✅ {real_count} real reviews — ready to run calibration batch!")
        print(f"     Next: python scripts/run_calibration_batch.py --csv {args.csv} --json {args.output}")


if __name__ == "__main__":
    main()
