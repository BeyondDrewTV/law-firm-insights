#!/usr/bin/env python3
"""
Clarion Engine — Calibration Batch Runner

Usage:
    python scripts/run_calibration_batch.py \
        --csv path/to/real_reviews.csv \
        --json path/to/synthetic_reviews.json \
        --output calibration_results.json

Expected CSV columns:  review_text, rating, owner_response
Expected JSON format:  list of objects with same keys

Defaults:
    --server  http://localhost:5000
    --token   Themepark12
    --min     75   (warns if real review count is below this)
"""

import argparse
import csv
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

try:
    import requests
except ImportError:
    sys.exit("Missing dependency: pip install requests")

DEFAULT_SERVER = "http://localhost:5000"
DEFAULT_TOKEN = "Themepark12"
BATCH_ENDPOINT = "/internal/benchmark/batch"
DEFAULT_DATE = "2025-01-01"
MIN_REAL_REVIEWS = 75


def load_csv(path: str) -> list[dict]:
    reviews = []
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            reviews.append({
                "review_text": row.get("review_text", "").strip(),
                "rating": int(row.get("rating", 0)),
                "owner_response": row.get("owner_response", "").strip(),
                "date": DEFAULT_DATE,
                "source": "real"
            })
    return reviews


def load_json(path: str) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    for item in data:
        item.setdefault("date", DEFAULT_DATE)
        item.setdefault("source", "synthetic")
        item.setdefault("owner_response", "")
    return data


def print_distribution(reviews: list[dict], label: str):
    from collections import Counter
    counts = Counter(r["rating"] for r in reviews)
    print(f"\n{label} ({len(reviews)} total):")
    for star in range(1, 6):
        bar = "█" * counts.get(star, 0)
        print(f"  {star}★  {counts.get(star, 0):>4}  {bar}")


def run_batch(reviews: list[dict], server: str, token: str) -> dict:
    url = server.rstrip("/") + BATCH_ENDPOINT
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    payload = {"reviews": reviews}
    print(f"\nPOSTing {len(reviews)} reviews to {url} ...")
    start = time.time()
    resp = requests.post(url, headers=headers, json=payload, timeout=120)
    elapsed = time.time() - start
    resp.raise_for_status()
    print(f"Response: {resp.status_code} in {elapsed:.1f}s")
    return resp.json()


def save_results(results: dict, output_path: str, reviews: list[dict]):
    out = {
        "run_timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "total_reviews": len(reviews),
        "real_count": sum(1 for r in reviews if r.get("source") == "real"),
        "synthetic_count": sum(1 for r in reviews if r.get("source") == "synthetic"),
        "results": results
    }
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)
    print(f"\nResults saved → {output_path}")


def main():
    parser = argparse.ArgumentParser(description="Clarion Engine Calibration Batch Runner")
    parser.add_argument("--csv", required=True, help="Path to real reviews CSV")
    parser.add_argument("--json", required=False, help="Path to synthetic reviews JSON (optional)")
    parser.add_argument("--output", default="calibration_results.json", help="Output file path")
    parser.add_argument("--server", default=DEFAULT_SERVER, help=f"Flask server URL (default: {DEFAULT_SERVER})")
    parser.add_argument("--token", default=DEFAULT_TOKEN, help="Bearer token")
    parser.add_argument("--dry-run", action="store_true", help="Load + validate data without sending to server")
    args = parser.parse_args()

    # Load real reviews
    print(f"Loading real reviews from: {args.csv}")
    real_reviews = load_csv(args.csv)
    print(f"  → {len(real_reviews)} real reviews loaded")

    if len(real_reviews) < MIN_REAL_REVIEWS:
        print(f"\n⚠️  WARNING: Only {len(real_reviews)} real reviews loaded. "
              f"Target is {MIN_REAL_REVIEWS}+ before calibration pass.")
        print("   Thin spots to fill: 2-star, 4-star, and 3-star reviews.")
        proceed = input("   Continue anyway? [y/N]: ").strip().lower()
        if proceed != "y":
            print("Aborting. Collect more reviews and re-run.")
            sys.exit(0)

    # Load synthetic reviews
    synthetic_reviews = []
    if args.json:
        print(f"Loading synthetic reviews from: {args.json}")
        synthetic_reviews = load_json(args.json)
        print(f"  → {len(synthetic_reviews)} synthetic reviews loaded")

    all_reviews = real_reviews + synthetic_reviews

    # Print distributions
    print_distribution(real_reviews, "Real reviews (star distribution)")
    if synthetic_reviews:
        print_distribution(synthetic_reviews, "Synthetic reviews (star distribution)")
    print_distribution(all_reviews, "COMBINED (star distribution)")

    if args.dry_run:
        print("\n✅ Dry run complete. Data looks good — remove --dry-run to send to server.")
        sys.exit(0)

    # Run batch
    results = run_batch(all_reviews, args.server, args.token)
    save_results(results, args.output, all_reviews)
    print("\n✅ Calibration batch complete!")


if __name__ == "__main__":
    main()
