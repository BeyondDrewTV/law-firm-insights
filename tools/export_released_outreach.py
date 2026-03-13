"""
export_released_outreach.py
Clarion — Export released outreach items as send-ready CSV and JSON.

Usage:
    python export_released_outreach.py
    python export_released_outreach.py --format csv   (default)
    python export_released_outreach.py --format json

Output:
    Clarion-Agency/data/outreach/send_queue_export_<YYYYMMDD>.csv
    Clarion-Agency/data/outreach/send_queue_export_<YYYYMMDD>.json  (with --format json)
"""
import argparse
import csv
import json
from datetime import datetime
from pathlib import Path

BASE = Path(__file__).resolve().parent / "Clarion-Agency" / "data"
SOURCE = BASE / "outreach" / "released_outreach_queue.json"
OUT_DIR = BASE / "outreach"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--format", choices=["csv", "json"], default="csv")
    args = parser.parse_args()

    if not SOURCE.exists():
        print(f"No released outreach queue found at {SOURCE}")
        return

    items = json.loads(SOURCE.read_text(encoding="utf-8"))
    if not items:
        print("No released outreach items to export.")
        return

    stamp = datetime.now().strftime("%Y%m%d_%H%M")
    if args.format == "json":
        out = OUT_DIR / f"send_queue_export_{stamp}.json"
        out.write_text(json.dumps(items, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"Exported {len(items)} items → {out}")
        return

    # CSV — flatten payload for easy copy-paste / mail merge
    out = OUT_DIR / f"send_queue_export_{stamp}.csv"
    fieldnames = ["id", "title", "released_at", "released_by",
                  "channel", "prospect_id", "draft", "cta"]
    with out.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for item in items:
            row = {
                "id":          item.get("id"),
                "title":       item.get("title"),
                "released_at": item.get("released_at"),
                "released_by": item.get("released_by"),
                **{k: item.get("payload", {}).get(k, "") for k in
                   ("channel", "prospect_id", "draft", "cta")},
            }
            writer.writerow(row)
    print(f"Exported {len(items)} items → {out}")


if __name__ == "__main__":
    main()
