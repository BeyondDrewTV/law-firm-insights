#!/usr/bin/env python3
"""
Clarion Engine — Calibration Gap Report

Analyzes your current real review CSV and reports exactly how many
reviews you still need by star rating to hit calibration thresholds.

Usage:
    python automation/calibration/calibration_gap_report.py --csv path/to/real_reviews.csv

Optional:
    --target 75       (minimum real reviews before first calibration pass, default 75)
    --ideal  100      (ideal target, default 100)
"""

import argparse
import csv
import sys
from collections import Counter
from pathlib import Path

# Ideal distribution targets as percentages of total
# Based on what gives the Clarion Engine good signal across all scoring bands
IDEAL_DISTRIBUTION = {
    1: 0.15,  # 15% — severe negatives
    2: 0.15,  # 15% — moderate negatives (hardest to find, most valuable)
    3: 0.20,  # 20% — ambiguous/mixed (critical for threshold tuning)
    4: 0.20,  # 20% — soft positives with caveats
    5: 0.30,  # 30% — strong positives
}

PRIORITY_LABELS = {
    1: "severe negative",
    2: "moderate negative ⚠️  PRIORITY",
    3: "mixed/ambiguous ⚠️  PRIORITY",
    4: "soft positive   ⚠️  PRIORITY",
    5: "strong positive",
}


def load_csv(path: str) -> list[dict]:
    reviews = []
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader, 1):
            text = row.get("review_text", "").strip()
            rating_raw = row.get("rating", "").strip()
            if not text:
                print(f"  ⚠️  Row {i}: empty review_text — skipping")
                continue
            try:
                rating = int(float(rating_raw))
            except (ValueError, TypeError):
                print(f"  ⚠️  Row {i}: invalid rating '{rating_raw}' — skipping")
                continue
            if rating not in range(1, 6):
                print(f"  ⚠️  Row {i}: rating {rating} out of range — skipping")
                continue
            reviews.append({"review_text": text, "rating": rating})
    return reviews


def bar(count: int, max_count: int, width: int = 30) -> str:
    filled = int((count / max_count) * width) if max_count > 0 else 0
    return "█" * filled + "░" * (width - filled)


def main():
    parser = argparse.ArgumentParser(description="Clarion Calibration Gap Report")
    parser.add_argument("--csv", required=True, help="Path to real reviews CSV")
    parser.add_argument("--target", type=int, default=75, help="Minimum real reviews target (default: 75)")
    parser.add_argument("--ideal", type=int, default=100, help="Ideal total real reviews (default: 100)")
    args = parser.parse_args()

    if not Path(args.csv).exists():
        sys.exit(f"❌ File not found: {args.csv}")

    print(f"\n{'='*60}")
    print(" CLARION ENGINE — CALIBRATION GAP REPORT")
    print(f"{'='*60}")
    print(f"  CSV: {args.csv}")
    print(f"  Minimum target: {args.target} real reviews")
    print(f"  Ideal target:   {args.ideal} real reviews")
    print(f"{'='*60}\n")

    reviews = load_csv(args.csv)
    total = len(reviews)
    counts = Counter(r["rating"] for r in reviews)
    has_owner_response = sum(1 for r in reviews if r.get("owner_response", ""))

    print(f"  Total valid real reviews loaded: {total}")
    print(f"  Reviews with owner responses:    {has_owner_response}\n")

    # Progress to target
    needed_for_target = max(0, args.target - total)
    needed_for_ideal = max(0, args.ideal - total)
    pct = min(100, int((total / args.target) * 100))
    progress_bar = "█" * (pct // 5) + "░" * (20 - pct // 5)

    print(f"  Progress to minimum ({args.target}): [{progress_bar}] {pct}%")
    if needed_for_target > 0:
        print(f"  → Still need {needed_for_target} more real reviews to hit minimum target")
    else:
        print(f"  ✅ Minimum target reached! ({needed_for_ideal} more for ideal target of {args.ideal})")

    print(f"\n  {'Star':<6} {'Have':>6} {'Ideal@'+str(args.ideal):>12} {'Gap':>8}   {'Priority':>10}   Distribution")
    print(f"  {'-'*80}")

    max_count = max(counts.values()) if counts else 1
    total_gap = 0
    gaps = {}
    for star in range(1, 6):
        have = counts.get(star, 0)
        ideal_count = int(args.ideal * IDEAL_DISTRIBUTION[star])
        gap = max(0, ideal_count - have)
        gaps[star] = gap
        total_gap += gap
        label = PRIORITY_LABELS[star]
        b = bar(have, max(max_count, ideal_count))
        print(f"  {star}★     {have:>6}  {ideal_count:>12}  {'+'+str(gap) if gap > 0 else '✅ ok':>8}   {label:<28} {b}")

    print(f"\n  Total additional reviews needed (for ideal distribution): {total_gap}")

    # Prioritized shopping list
    print(f"\n{'='*60}")
    print(" COLLECTION PRIORITY LIST")
    print(f"{'='*60}")
    priority_order = sorted([s for s in gaps if gaps[s] > 0], key=lambda s: IDEAL_DISTRIBUTION[s] - (counts.get(s, 0) / max(total, 1)), reverse=True)
    if not priority_order:
        print("  ✅ All star ratings are at or above ideal distribution!")
    else:
        for rank, star in enumerate(priority_order, 1):
            print(f"  {rank}. {star}★ — collect {gaps[star]} more   ({PRIORITY_LABELS[star]})")

    print(f"\n  Suggested sources for 2-4 star law firm reviews:")
    print("    • Avvo.com       — filter attorneys by rating 2-4, sort by Most Recent")
    print("    • Yelp           — law firms, sort by Rating (Low to High)")
    print("    • Google Maps    — open firm profile → Sort by 'Lowest'")
    print("    • Martindale.com — detailed reviews, good mid-range signal")
    print("    • Facebook Pages — less filtered, good for 2-3 star frustration reviews")
    print(f"\n{'='*60}\n")


if __name__ == "__main__":
    main()
