# automation/calibration

Calibration workflow scripts for the Clarion benchmark engine.

## One-command workflow (from repo root)

```
# Windows — double-click or run:
run_calibration_workflow.bat

# Or directly:
python automation/calibration/run_calibration_workflow.py --csv data/calibration/inputs/real_reviews.csv
```

## Scripts

| Script | Purpose |
|--------|---------|
| `run_calibration_workflow.py` | **Entry point.** Full pipeline: validate CSV → gap report → generate synthetics → batch API → final summary |
| `run_calibration_batch.py` | Raw batch runner (used by workflow; also usable standalone) |
| `calibration_gap_report.py` | Standalone gap report against a CSV |
| `generate_synthetic_topup.py` | Generate synthetic reviews for thin rating buckets |
| `merge_calibration_data.py` | Merge real + synthetic for audit (not fed back to batch) |

## Data layout

```
data/calibration/
  inputs/          ← real_reviews.csv (your source CSV)
  synthetic/       ← synthetic_topup.json (auto-generated)
  calibration_merged.json  ← audit artifact only (not fed to batch)
  runs/
    YYYYMMDD_HHMMSS/
      real_reviews.csv
      gap_report.txt
      chunks/
      results/
      final_summary.json
      final_summary.md
```
