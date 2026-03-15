#!/usr/bin/env python3
"""
Clarion Engine — One-Click Calibration Workflow
================================================
Runs the full calibration pipeline in a single command:
  1. Validate & copy CSV to run folder
  2. Gap report
  3. Generate synthetic top-ups for thin star ratings
  4. Merge (for human reference only — NOT fed back into batch to avoid double-counting)
  5. Batch calibration in chunks of CHUNK_SIZE to avoid client timeout
  6. Aggregate chunk results
  7. Write final_summary.json + final_summary.md

Usage (from repo root):
    python automation/calibration/run_calibration_workflow.py --csv "path/to/reviews.csv"

Optional flags:
    --server  http://localhost:5000   Flask server URL
    --token   Themepark12             Bearer token
    --chunk   20                      Reviews per API batch (keep <=25 to avoid timeouts)
    --dry-run                         Validate + generate data, skip API calls
    --no-ai                           Skip benchmark API entirely, just produce data artifacts

Design note — avoiding double-counting:
    merge_calibration_data.py produces calibration_merged.json as a human-readable
    audit artifact. The batch runner receives ONLY the original CSV (real reviews)
    PLUS the synthetic_topup.json (synthetic reviews) via separate --csv / --json args.
    This matches run_calibration_batch.py's own load_csv + load_json path, which tags
    sources correctly and never double-loads merged output.
"""

import argparse
import csv
import json
import shutil
import subprocess
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

try:
    import requests
except ImportError:
    sys.exit("❌ Missing dependency: pip install requests")

# ── Repo-root-safe paths ──────────────────────────────────────────────────────
# Script lives at automation/calibration/ — two levels below repo root
CALIBRATION_DIR = Path(__file__).resolve().parent          # automation/calibration/
REPO_ROOT       = CALIBRATION_DIR.parent.parent            # repo root
DATA_DIR        = REPO_ROOT / "data" / "calibration"
RUNS_DIR        = DATA_DIR / "runs"
DEFAULT_CSV     = DATA_DIR / "inputs" / "real_reviews.csv"  # canonical input location

# ── Constants ─────────────────────────────────────────────────────────────────
DEFAULT_SERVER   = "http://localhost:5000"
DEFAULT_TOKEN    = "Themepark12"
BATCH_ENDPOINT   = "/internal/benchmark/batch"
DEFAULT_DATE     = "2025-01-01"
CHUNK_SIZE       = 20     # reviews per API call — keeps well inside timeout window
CHUNK_TIMEOUT    = 300    # seconds per chunk request
MIN_REAL         = 75     # warn if below this

# ── Helpers ───────────────────────────────────────────────────────────────────

def banner(msg: str):
    print(f"\n{'='*60}")
    print(f"  {msg}")
    print(f"{'='*60}")


def step(msg: str):
    print(f"\n▶  {msg}")


def ok(msg: str):
    print(f"   ✅ {msg}")


def warn(msg: str):
    print(f"   ⚠️  {msg}")


def die(msg: str):
    print(f"\n❌ {msg}")
    sys.exit(1)


# ── CSV loading (mirrors run_calibration_batch.py) ───────────────────────────

def load_csv(path: Path) -> list[dict]:
    reviews = []
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            text = row.get("review_text", "").strip()
            rating_raw = row.get("rating", "")
            if not text:
                continue
            try:
                rating = int(float(rating_raw))
            except (ValueError, TypeError):
                continue
            if rating not in range(1, 6):
                continue
            reviews.append({
                "review_text": text,
                "rating": rating,
                "owner_response": row.get("owner_response", "").strip(),
                "date": DEFAULT_DATE,
                "source": "real",
            })
    return reviews


def load_json_reviews(path: Path) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    for item in data:
        item.setdefault("date", DEFAULT_DATE)
        item.setdefault("source", "synthetic")
        item.setdefault("owner_response", "")
    return data


# ── Gap analysis (inline — avoids subprocess path issues) ────────────────────

IDEAL_DIST = {1: 0.15, 2: 0.15, 3: 0.20, 4: 0.20, 5: 0.30}
IDEAL_TOTAL = 100

def compute_gaps(real_reviews: list[dict]) -> dict[int, int]:
    counts = Counter(r["rating"] for r in real_reviews)
    gaps = {}
    for star in range(1, 6):
        ideal = int(IDEAL_TOTAL * IDEAL_DIST[star])
        gaps[star] = max(0, ideal - counts.get(star, 0))
    return gaps


def write_gap_report(real_reviews: list[dict], run_dir: Path) -> dict[int, int]:
    counts = Counter(r["rating"] for r in real_reviews)
    total = len(real_reviews)
    gaps = compute_gaps(real_reviews)
    lines = [
        "CLARION CALIBRATION GAP REPORT",
        f"Generated: {datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')}",
        f"Total real reviews: {total}",
        "",
        f"{'Star':<6} {'Have':>6} {'Ideal':>8} {'Gap':>8}",
        "-" * 35,
    ]
    for star in range(1, 6):
        have = counts.get(star, 0)
        ideal = int(IDEAL_TOTAL * IDEAL_DIST[star])
        gap = gaps[star]
        lines.append(f"{star}★     {have:>6}  {ideal:>8}  {'+'+str(gap) if gap else 'ok':>8}")
    report_path = run_dir / "gap_report.txt"
    report_path.write_text("\n".join(lines), encoding="utf-8")
    return gaps

# ── Synthetic top-up generation (calls existing script) ──────────────────────

def generate_synthetic(gaps: dict[int, int], run_dir: Path) -> Path | None:
    """Generate synthetic reviews to fill distribution gaps. Returns path to JSON or None."""
    needed = {star: count for star, count in gaps.items() if count > 0}
    if not needed:
        ok("No gaps — skipping synthetic generation")
        return None

    batch_arg = ",".join(f"{star}:{count}" for star, count in needed.items())
    out_path = run_dir / "synthetic_topup.json"
    script = CALIBRATION_DIR / "generate_synthetic_topup.py"

    print(f"   Generating synthetic top-up: {batch_arg}")
    result = subprocess.run(
        [sys.executable, str(script), "--batch", batch_arg, "--output", str(out_path)],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        warn(f"Synthetic generation warning:\n{result.stderr}")
    ok(f"Synthetic reviews → {out_path.name}")
    return out_path


# ── Merge for audit artifact only ─────────────────────────────────────────────

def merge_for_audit(csv_path: Path, synth_path: Path | None, run_dir: Path) -> Path:
    """Produce calibration_merged.json as a human-readable audit artifact ONLY.
    This file is NOT fed into the batch runner (would cause double-counting)."""
    script = CALIBRATION_DIR / "merge_calibration_data.py"
    out_path = run_dir / "calibration_merged.json"
    cmd = [sys.executable, str(script), "--csv", str(csv_path), "--output", str(out_path)]
    if synth_path:
        cmd += ["--json", str(synth_path)]
    subprocess.run(cmd, capture_output=True, text=True)  # output is audit artifact; errors non-fatal
    return out_path


# ── Chunked batch runner ───────────────────────────────────────────────────────

def run_chunked(all_reviews: list[dict], server: str, token: str,
                run_dir: Path, dry_run: bool) -> list[dict]:
    """Split reviews into chunks and POST each. Returns list of per-chunk result dicts."""
    chunks_dir = run_dir / "chunks"
    results_dir = run_dir / "results"
    chunks_dir.mkdir(exist_ok=True)
    results_dir.mkdir(exist_ok=True)

    chunks = [all_reviews[i:i+CHUNK_SIZE] for i in range(0, len(all_reviews), CHUNK_SIZE)]
    print(f"   {len(all_reviews)} reviews → {len(chunks)} chunks of ≤{CHUNK_SIZE}")

    url = server.rstrip("/") + BATCH_ENDPOINT
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    chunk_results = []

    for idx, chunk in enumerate(chunks, 1):
        chunk_file = chunks_dir / f"chunk_{idx:03d}.json"
        chunk_file.write_text(json.dumps(chunk, indent=2), encoding="utf-8")

        if dry_run:
            print(f"   [dry-run] Chunk {idx}/{len(chunks)} — {len(chunk)} reviews (skipping API)")
            continue

        print(f"   Chunk {idx}/{len(chunks)} — {len(chunk)} reviews … ", end="", flush=True)
        t0 = time.time()
        try:
            resp = requests.post(url, headers=headers, json={"reviews": chunk}, timeout=CHUNK_TIMEOUT)
            elapsed = time.time() - t0
            resp.raise_for_status()
            result = resp.json()
            result_file = results_dir / f"result_{idx:03d}.json"
            result_file.write_text(json.dumps(result, indent=2), encoding="utf-8")
            chunk_results.append({"chunk": idx, "count": len(chunk), "elapsed": round(elapsed, 1), "result": result})
            print(f"✅ {resp.status_code} in {elapsed:.1f}s")
        except requests.exceptions.Timeout:
            elapsed = time.time() - t0
            warn(f"Chunk {idx} timed out after {elapsed:.0f}s (CHUNK_TIMEOUT={CHUNK_TIMEOUT}s). "
                 f"Check backend logs; try reducing --chunk size.")
            chunk_results.append({"chunk": idx, "count": len(chunk), "elapsed": round(elapsed, 1), "error": "timeout"})
        except requests.exceptions.RequestException as exc:
            elapsed = time.time() - t0
            warn(f"Chunk {idx} failed: {exc}")
            chunk_results.append({"chunk": idx, "count": len(chunk), "elapsed": round(elapsed, 1), "error": str(exc)})

    return chunk_results

# ── Final summary writer ───────────────────────────────────────────────────────

def write_summary(real: list[dict], synthetic: list[dict], chunk_results: list[dict],
                  gaps: dict[int, int], run_dir: Path, ai_enabled: bool):
    total = len(real) + len(synthetic)
    real_counts = Counter(r["rating"] for r in real)
    synth_counts = Counter(r["rating"] for r in synthetic)
    successes = [c for c in chunk_results if "error" not in c]
    failures  = [c for c in chunk_results if "error" in c]

    summary = {
        "run_timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "ai_benchmark_enabled": ai_enabled,
        "total_real_reviews": len(real),
        "total_synthetic_reviews": len(synthetic),
        "total_reviews_submitted": total,
        "chunks_total": len(chunk_results),
        "chunks_succeeded": len(successes),
        "chunks_failed": len(failures),
        "per_star_distribution": {
            str(s): {"real": real_counts.get(s, 0), "synthetic": synth_counts.get(s, 0)}
            for s in range(1, 6)
        },
        "gaps_at_start": {str(k): v for k, v in gaps.items()},
        "chunk_results": chunk_results,
    }

    # JSON
    (run_dir / "final_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

    # Markdown
    lines = [
        "# Clarion Calibration Run Summary",
        f"**Run:** `{summary['run_timestamp']}`",
        f"**AI Benchmark:** {'enabled' if ai_enabled else 'skipped (--no-ai)'}",
        "",
        "## Review Counts",
        f"| Source | Count |",
        f"|--------|-------|",
        f"| Real   | {len(real)} |",
        f"| Synthetic | {len(synthetic)} |",
        f"| **Total submitted** | **{total}** |",
        "",
        "## Per-Star Distribution",
        "| Star | Real | Synthetic | Total |",
        "|------|------|-----------|-------|",
    ]
    for s in range(1, 6):
        r = real_counts.get(s, 0)
        sy = synth_counts.get(s, 0)
        lines.append(f"| {s}★ | {r} | {sy} | {r+sy} |")

    lines += [
        "",
        "## Batch Execution",
        f"- Chunks run: {len(chunk_results)}",
        f"- Succeeded: {len(successes)}",
        f"- Failed/timed out: {len(failures)}",
    ]
    if failures:
        lines.append("\n### Failed Chunks")
        for f in failures:
            lines.append(f"- Chunk {f['chunk']}: {f.get('error','unknown')} ({f.get('elapsed',0)}s)")

    lines += [
        "",
        "## Next Actions",
    ]
    remaining_gaps = {s: g for s, g in gaps.items() if g > 0 and synth_counts.get(s, 0) == 0}
    if remaining_gaps:
        lines.append("- Collect more real reviews for: " +
                     ", ".join(f"{s}★ (+{g})" for s, g in remaining_gaps.items()))
    if failures:
        lines.append("- Re-run failed chunks after checking backend logs")
    if len(real) < MIN_REAL:
        lines.append(f"- ⚠️ Only {len(real)} real reviews — aim for {MIN_REAL}+ before trusting calibration results")
    if not failures and len(real) >= MIN_REAL:
        lines.append("- ✅ Calibration run complete. Review final_summary.json for per-chunk details.")

    (run_dir / "final_summary.md").write_text("\n".join(lines), encoding="utf-8")
    return summary

# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Clarion one-click calibration workflow",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--csv",    default=str(DEFAULT_CSV),
                        help=f"Path to real reviews CSV (default: data/calibration/inputs/real_reviews.csv)")
    parser.add_argument("--server", default=DEFAULT_SERVER)
    parser.add_argument("--token",  default=DEFAULT_TOKEN)
    parser.add_argument("--chunk",  type=int, default=CHUNK_SIZE, help=f"Reviews per API batch (default: {CHUNK_SIZE})")
    parser.add_argument("--dry-run", action="store_true", help="Build all data artifacts, skip API calls")
    parser.add_argument("--no-ai",  action="store_true", help="Skip API batch entirely (data artifacts only)")
    args = parser.parse_args()

    banner("CLARION CALIBRATION WORKFLOW")

    # ── 1. Validate & resolve CSV path ────────────────────────────────────────
    step("Step 1 — Validate CSV")
    csv_src = Path(args.csv).resolve()
    if not csv_src.exists():
        die(f"CSV not found: {csv_src}")
    ok(f"Found: {csv_src.name}")

    # ── 2. Create timestamped run folder ──────────────────────────────────────
    step("Step 2 — Create run folder")
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = RUNS_DIR / ts
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "chunks").mkdir(exist_ok=True)
    (run_dir / "results").mkdir(exist_ok=True)

    # Copy CSV into run folder so the run is self-contained
    csv_dest = run_dir / "real_reviews.csv"
    shutil.copy2(csv_src, csv_dest)
    ok(f"Run folder: {run_dir.relative_to(REPO_ROOT)}")

    # ── 3. Load real reviews & gap report ────────────────────────────────────
    step("Step 3 — Gap report")
    real_reviews = load_csv(csv_dest)
    if not real_reviews:
        die("No valid reviews found in CSV. Check that columns are: review_text, rating, owner_response")
    print(f"   {len(real_reviews)} real reviews loaded")
    if len(real_reviews) < MIN_REAL:
        warn(f"Only {len(real_reviews)} real reviews — recommend {MIN_REAL}+ for reliable calibration")

    gaps = write_gap_report(real_reviews, run_dir)
    real_counts = Counter(r["rating"] for r in real_reviews)
    for star in range(1, 6):
        g = gaps[star]
        flag = f"  ← need {g} more" if g else "  ✅"
        print(f"   {star}★  have {real_counts.get(star,0):>3}{flag}")

    # ── 4. Generate synthetic top-ups ─────────────────────────────────────────
    step("Step 4 — Synthetic top-up")
    synth_path = generate_synthetic(gaps, run_dir)

    # ── 5. Merge (audit artifact only — NOT fed into batch runner) ────────────
    step("Step 5 — Merge (audit artifact)")
    merge_for_audit(csv_dest, synth_path, run_dir)
    ok("calibration_merged.json written (audit reference only)")

    # ── 6. Build final review list for API ───────────────────────────────────
    synthetic_reviews = []
    if synth_path and synth_path.exists():
        synthetic_reviews = load_json_reviews(synth_path)
    all_reviews = real_reviews + synthetic_reviews
    print(f"   Total for batch: {len(all_reviews)} ({len(real_reviews)} real + {len(synthetic_reviews)} synthetic)")

    # ── 7. Run chunked calibration ────────────────────────────────────────────
    ai_enabled = not args.no_ai
    step(f"Step 6 — Calibration batch ({'dry-run' if args.dry_run else 'no-ai' if args.no_ai else 'live'})")
    if args.no_ai:
        ok("Skipped (--no-ai). Data artifacts written.")
        chunk_results = []
    else:
        chunk_results = run_chunked(all_reviews, args.server, args.token, run_dir, args.dry_run)

    # ── 8. Final summary ──────────────────────────────────────────────────────
    step("Step 7 — Final summary")
    summary = write_summary(real_reviews, synthetic_reviews, chunk_results, gaps, run_dir, ai_enabled)

    banner("DONE")
    print(f"  Run folder : {run_dir}")
    print(f"  Real       : {summary['total_real_reviews']}")
    print(f"  Synthetic  : {summary['total_synthetic_reviews']}")
    if ai_enabled and not args.dry_run:
        print(f"  Chunks     : {summary['chunks_succeeded']}/{summary['chunks_total']} succeeded")
    print(f"  Summary    : {run_dir / 'final_summary.md'}")
    print()


if __name__ == "__main__":
    main()
