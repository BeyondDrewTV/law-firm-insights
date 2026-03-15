#!/usr/bin/env python3
"""
automation/calibration/analyze_disagreements.py
================================================
Reads a calibration run's final_summary.json (which embeds per-chunk batch
results) and outputs a structured disagreement analysis:

  - disagreement_report.md   Human-readable summary with phrase suggestions
  - phrase_candidates.json   Machine-readable list of potential new phrases

Usage:
    python automation/calibration/analyze_disagreements.py
    python automation/calibration/analyze_disagreements.py --run 20260315_141200

If --run is omitted, the most recent run folder is used.

Output written to: data/calibration/runs/<run>/disagreement_report.md
"""

import argparse
import json
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT     = Path(__file__).resolve().parent.parent.parent
RUNS_DIR      = REPO_ROOT / "data" / "calibration" / "runs"
MIN_FREQUENCY = 2   # min times a missing_theme must appear before suggesting a phrase


def latest_run() -> Path:
    runs = sorted([r for r in RUNS_DIR.iterdir() if r.is_dir()], reverse=True)
    if not runs:
        sys.exit("No calibration runs found in data/calibration/runs/")
    return runs[0]


def load_all_results(run_dir: Path) -> list[dict]:
    """Collect all benchmark result dicts from result_*.json files."""
    results_dir = run_dir / "results"
    all_results = []
    if not results_dir.exists():
        # Try extracting from final_summary.json chunk_results
        summary_path = run_dir / "final_summary.json"
        if summary_path.exists():
            summary = json.loads(summary_path.read_text(encoding="utf-8"))
            for chunk in summary.get("chunk_results", []):
                r = chunk.get("result") or {}
                all_results.extend(r.get("results", []))
        return all_results

    for f in sorted(results_dir.glob("result_*.json")):
        data = json.loads(f.read_text(encoding="utf-8"))
        all_results.extend(data.get("results", []))
    return all_results


def extract_disagreements(all_results: list[dict]) -> list[dict]:
    """Flatten disagreements from all benchmark results."""
    out = []
    for item in all_results:
        br = item.get("benchmark_result") or item  # handle both wrapped and flat
        for d in item.get("disagreements", []):
            d["_review_text"] = br.get("review_text", "")[:200]
            d["_rating"]      = br.get("rating", 0)
            out.append(d)
    return out


def analyze(disagreements: list[dict]) -> dict:
    by_type:  dict[str, list] = defaultdict(list)
    by_theme: dict[str, list] = defaultdict(list)
    priority4: list = []

    for d in disagreements:
        t = d.get("disagreement_type", "unknown")
        theme = d.get("theme", "unknown")
        by_type[t].append(d)
        by_theme[theme].append(d)
        if d.get("disagreement_priority", 0) >= 4:
            priority4.append(d)

    return {"by_type": by_type, "by_theme": by_theme, "priority4": priority4}


def suggest_phrases(by_type: dict) -> list[dict]:
    """
    For missing_theme disagreements: cluster by (theme, ai_polarity, evidence_span)
    and suggest candidate phrases when a pattern appears >= MIN_FREQUENCY times.
    """
    candidates = []
    missing = by_type.get("missing_theme", [])

    # Group by (theme, polarity)
    groups: dict[tuple, list[str]] = defaultdict(list)
    for d in missing:
        key = (d.get("theme", ""), d.get("ai_polarity", ""))
        ev = (d.get("ai_evidence_span") or "").strip().lower()
        if ev:
            groups[key].append(ev)

    for (theme, polarity), spans in groups.items():
        if len(spans) < MIN_FREQUENCY:
            continue
        # Find common short sub-phrases (3+ word n-grams appearing multiple times)
        ngram_counts: Counter = Counter()
        for span in spans:
            words = span.split()
            for n in range(2, min(7, len(words)+1)):
                for i in range(len(words) - n + 1):
                    ngram_counts[" ".join(words[i:i+n])] += 1
        top = [(ng, c) for ng, c in ngram_counts.most_common(10) if c >= MIN_FREQUENCY]
        if top:
            candidates.append({
                "theme":           theme,
                "polarity":        polarity,
                "frequency":       len(spans),
                "suggested_phrases": [{"phrase": ng, "occurrences": c} for ng, c in top],
                "sample_evidence": spans[:3],
            })

    return sorted(candidates, key=lambda x: -x["frequency"])


def write_report(run_dir: Path, disagreements: list[dict], analysis: dict, candidates: list[dict]):
    total = len(disagreements)
    by_type = analysis["by_type"]
    by_theme = analysis["by_theme"]
    p4 = analysis["priority4"]

    lines = [
        "# Clarion Calibration — Disagreement Analysis",
        f"**Run:** `{run_dir.name}`",
        f"**Generated:** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
        f"**Total disagreements:** {total}",
        "",
        "---",
        "",
        "## 1. By Disagreement Type",
        "",
        "| Type | Count | % |",
        "|------|-------|---|",
    ]
    for t, items in sorted(by_type.items(), key=lambda x: -len(x[1])):
        pct = round(len(items) / total * 100) if total else 0
        lines.append(f"| `{t}` | {len(items)} | {pct}% |")

    lines += [
        "",
        "## 2. By Theme",
        "",
        "| Theme | Count | Top Type |",
        "|-------|-------|----------|",
    ]
    for theme, items in sorted(by_theme.items(), key=lambda x: -len(x[1])):
        top_type = Counter(d.get("disagreement_type","") for d in items).most_common(1)[0][0]
        lines.append(f"| `{theme}` | {len(items)} | `{top_type}` |")

    lines += [
        "",
        "## 3. Priority-4 Issues (Production Risk)",
        f"*{len(p4)} issues requiring immediate attention*",
        "",
    ]
    for i, d in enumerate(p4[:20], 1):
        lines += [
            f"### P4-{i}: `{d.get('disagreement_type')}` on `{d.get('theme')}`",
            f"- **Det polarity:** `{d.get('deterministic_polarity', '—')}`",
            f"- **AI polarity:**  `{d.get('ai_polarity', '—')}`",
            f"- **Det phrase:**   `{d.get('deterministic_phrase', '—')}`",
            f"- **AI evidence:**  _{d.get('ai_evidence_span', '—')}_",
            f"- **Detail:** {d.get('detail', '')}",
            f"- **Review snippet:** _{d.get('_review_text', '')[:120]}_",
            "",
        ]

    lines += [
        "## 4. Phrase Candidates (missing_theme patterns)",
        f"*Patterns appearing ≥{MIN_FREQUENCY}x where AI tagged a theme the deterministic engine missed*",
        "",
    ]
    if not candidates:
        lines.append("_No phrase candidates at this frequency threshold._")
    else:
        for c in candidates[:20]:
            lines += [
                f"### `{c['theme']}` / `{c['polarity']}` (seen {c['frequency']}x)",
                "**Suggested phrases to evaluate:**",
            ]
            for sp in c["suggested_phrases"][:5]:
                lines.append(f"- `\"{sp['phrase']}\"` — {sp['occurrences']}x")
            lines += ["**Sample evidence:**"]
            for s in c["sample_evidence"]:
                lines.append(f"> _{s}_")
            lines.append("")

    lines += [
        "---",
        "## 5. Next Steps",
        "",
        "1. Review Priority-4 issues above — these have the highest production risk",
        "2. For each `missing_theme`: evaluate suggested phrases and add approved ones to `THEME_PHRASES` in `backend/services/benchmark_engine.py`",
        "3. For `likely_false_positive` / `likely_context_guard_failure`: review context guards in `score_review_deterministic()`",
        "4. Re-run calibration after phrase additions and compare disagreement counts",
        "5. Target: <15% overall disagreement rate, 0 P4 issues",
        "",
        f"Full phrase candidates: `{run_dir.name}/phrase_candidates.json`",
    ]

    report_path = run_dir / "disagreement_report.md"
    report_path.write_text("\n".join(lines), encoding="utf-8")
    return report_path


def main():
    parser = argparse.ArgumentParser(description="Analyze calibration run disagreements")
    parser.add_argument("--run", default=None, help="Run folder name (e.g. 20260315_141200). Defaults to latest.")
    args = parser.parse_args()

    run_dir = RUNS_DIR / args.run if args.run else latest_run()
    if not run_dir.exists():
        sys.exit(f"Run folder not found: {run_dir}")

    print(f"Analyzing run: {run_dir.name}")

    all_results   = load_all_results(run_dir)
    disagreements = extract_disagreements(all_results)
    analysis      = analyze(disagreements)
    candidates    = suggest_phrases(analysis["by_type"])

    # Write phrase_candidates.json
    candidates_path = run_dir / "phrase_candidates.json"
    candidates_path.write_text(json.dumps(candidates, indent=2, ensure_ascii=False), encoding="utf-8")

    # Write disagreement_report.md
    report_path = write_report(run_dir, disagreements, analysis, candidates)

    print(f"✅ {len(disagreements)} disagreements analyzed")
    print(f"   Report     : {report_path}")
    print(f"   Candidates : {candidates_path}")

    by_type = analysis["by_type"]
    p4_count = len(analysis["priority4"])
    total = len(disagreements)
    if total:
        print(f"\n   Type breakdown:")
        for t, items in sorted(by_type.items(), key=lambda x: -len(x[1])):
            print(f"     {t:<35} {len(items):>4}  ({round(len(items)/total*100)}%)")
    print(f"\n   Priority-4 issues: {p4_count}")
    if p4_count == 0:
        print("   ✅ No P4 issues — engine is in good shape")
    else:
        print("   ⚠️  Review P4 issues in the report before launch")


if __name__ == "__main__":
    main()
