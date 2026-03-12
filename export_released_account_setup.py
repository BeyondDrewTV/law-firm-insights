"""
export_released_account_setup.py
Clarion — Export released account-setup tasks as a clean checklist.

Usage:
    python export_released_account_setup.py
    python export_released_account_setup.py --format json

Output:
    Clarion-Agency/data/accounts/account_setup_checklist_<YYYYMMDD_HHMM>.[md|json]
"""
import argparse
import json
from datetime import datetime
from pathlib import Path

BASE   = Path(__file__).resolve().parent / "Clarion-Agency" / "data"
SOURCE = BASE / "accounts" / "released_account_setup_queue.json"
OUT_DIR = BASE / "accounts"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--format", choices=["md", "json"], default="md")
    args = parser.parse_args()

    if not SOURCE.exists():
        print(f"No released account-setup queue at {SOURCE}")
        return

    items = json.loads(SOURCE.read_text(encoding="utf-8"))
    if not items:
        print("No released account-setup items to export.")
        return

    stamp = datetime.now().strftime("%Y%m%d_%H%M")

    if args.format == "json":
        out = OUT_DIR / f"account_setup_checklist_{stamp}.json"
        out.write_text(json.dumps(items, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"Exported {len(items)} items → {out}")
        return

    out = OUT_DIR / f"account_setup_checklist_{stamp}.md"
    lines = [f"# Clarion Account Setup Checklist — {stamp}\n",
             "Complete each item manually, then mark done.\n"]
    for i, item in enumerate(items, 1):
        p = item.get("payload", {})
        lines += [
            f"## {i}. {item.get('title', 'Untitled')}",
            f"- **Platform:** {p.get('platform', '—')}",
            f"- **Action:**   {p.get('action', item.get('recommended_action', '—'))}",
            f"- **Released:** {item.get('released_at', '—')}",
            "",
            "**Details:**",
        ]
        for k, v in p.items():
            if k not in ("platform", "action"):
                lines.append(f"- {k}: {v}")
        lines += ["", "- [ ] **Done**", "", "---", ""]
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"Exported {len(items)} items → {out}")


if __name__ == "__main__":
    main()
