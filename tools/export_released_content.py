"""
export_released_content.py
Clarion — Export released content items as a publish-ready list.

Usage:
    python export_released_content.py
    python export_released_content.py --format md   (markdown, default)
    python export_released_content.py --format json

Output:
    Clarion-Agency/data/growth/content_publish_<YYYYMMDD_HHMM>.[md|json]
"""
import argparse
import json
from datetime import datetime
from pathlib import Path

BASE   = Path(__file__).resolve().parent / "Clarion-Agency" / "data"
SOURCE = BASE / "growth" / "released_content_queue.json"
OUT_DIR = BASE / "growth"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--format", choices=["md", "json"], default="md")
    args = parser.parse_args()

    if not SOURCE.exists():
        print(f"No released content queue found at {SOURCE}")
        return

    items = json.loads(SOURCE.read_text(encoding="utf-8"))
    if not items:
        print("No released content items to export.")
        return

    stamp = datetime.now().strftime("%Y%m%d_%H%M")

    if args.format == "json":
        out = OUT_DIR / f"content_publish_{stamp}.json"
        out.write_text(json.dumps(items, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"Exported {len(items)} items → {out}")
        return

    # Markdown — one post per section, easy to paste directly
    out = OUT_DIR / f"content_publish_{stamp}.md"
    lines = [f"# Clarion Content Publish Queue — {stamp}\n"]
    for item in items:
        p = item.get("payload", {})
        lines += [
            f"## {item.get('title', 'Untitled')}",
            f"**Channel:** {p.get('channel', '—')}  ",
            f"**Type:** {p.get('content_type', '—')}  ",
            f"**Released:** {item.get('released_at', '—')}  ",
            "",
            "### Hook",
            p.get("hook", "—"),
            "",
            "### Draft",
            p.get("draft", "—"),
            "",
            f"**CTA:** {p.get('cta', '—')}",
            "",
            "---",
            "",
        ]
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"Exported {len(items)} items → {out}")


if __name__ == "__main__":
    main()
