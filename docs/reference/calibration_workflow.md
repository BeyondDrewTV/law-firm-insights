# Clarion Calibration Workflow

## One-command usage (recommended)

```bash
# From repo root:
python scripts/run_calibration_workflow.py --csv "path/to/your_reviews.csv"
```

Or double-click **`run_calibration_workflow.bat`** at the repo root (Windows). It will prompt you to paste/drag your CSV path.

---

## What it does (automatically)

| Step | Action |
|------|--------|
| 1 | Validates CSV path; copies it into a timestamped run folder |
| 2 | Runs gap analysis against ideal distribution (1★=15% 2★=15% 3★=20% 4★=20% 5★=30%) |
| 3 | Generates synthetic top-ups for any thin star ratings |
| 4 | Produces `calibration_merged.json` as an **audit artifact only** |
| 5 | POSTs reviews to the benchmark API in chunks of 20 (300s timeout per chunk) |
| 6 | Writes `final_summary.json` + `final_summary.md` |

---

## Output structure

```
scripts/data/calibration_runs/<YYYYMMDD_HHMMSS>/
  real_reviews.csv         ← copy of your input
  gap_report.txt           ← star distribution gaps
  synthetic_topup.json     ← generated fill reviews
  calibration_merged.json  ← audit artifact (not fed to API)
  chunks/                  ← per-chunk input payloads
  results/                 ← per-chunk API responses
  final_summary.json
  final_summary.md         ← human-readable run report
```

---

## Double-counting prevention

`calibration_merged.json` is written for human reference **only**.  
The batch runner receives:
- `--csv` → real reviews (tagged `source=real`)
- `--json` → synthetic top-up (tagged `source=synthetic`)

It does **not** receive the merged file. This prevents the real reviews from being counted twice.

---

## Timeout prevention

Requests are chunked into batches of 20 reviews each with a 300-second per-chunk timeout (vs the old 120s whole-run timeout). If a chunk fails, the others continue and the summary flags it.

Tune chunk size with `--chunk N` if needed.

---

## Optional flags

| Flag | Default | Effect |
|------|---------|--------|
| `--server` | `http://localhost:5000` | Flask server URL |
| `--token` | `Themepark12` | Bearer token |
| `--chunk` | `20` | Reviews per API call |
| `--dry-run` | off | Build data artifacts, skip API |
| `--no-ai` | off | Skip API entirely |

---

## Individual scripts (still available)

These still work standalone if you need them:

```bash
python scripts/calibration_gap_report.py --csv real_reviews.csv
python scripts/generate_synthetic_topup.py --batch "2:15,3:20,4:15" --output data/synthetic_topup.json
python scripts/merge_calibration_data.py --csv real_reviews.csv --json synthetic_topup.json
python scripts/run_calibration_batch.py --csv real_reviews.csv --json synthetic_topup.json
```

> **Note:** Do not pass `calibration_merged.json` into `run_calibration_batch.py` — it will double-count real reviews. Always pass the original CSV + synthetic JSON separately.
