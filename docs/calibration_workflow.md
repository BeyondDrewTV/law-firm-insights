# Clarion Engine — Calibration Workflow

This document outlines the full pipeline for collecting, validating, and running the calibration dataset against the Clarion Engine.

---

## Overview

| Phase | Status | Goal |
|---|---|---|
| Real review collection | 🔄 In Progress | 75–100 real reviews |
| Synthetic review generation | ✅ Complete | 158 synthetic reviews generated |
| Data merge & validation | ⏳ Pending | Merge CSV + JSON into unified dataset |
| Calibration batch run | ⏳ Pending | POST to `/internal/benchmark/batch` |
| Threshold tuning | ⏳ Pending | Analyze results, adjust Clarion scoring |

---

## Scripts Reference

### 1. Check Your Collection Gap
```bash
python scripts/calibration_gap_report.py --csv data/real_reviews.csv
```
Shows exactly how many reviews you still need by star rating, with a prioritized collection list.

---

### 2. Generate Synthetic Top-Ups (for thin spots)
```bash
# Target the specific thin spots (2-star, 3-star, 4-star):
python scripts/generate_synthetic_topup.py \
    --batch "2:15,3:20,4:15" \
    --output data/synthetic_topup.json

# Or for a single star rating:
python scripts/generate_synthetic_topup.py --star 2 --count 20 --output data/synthetic_topup_2star.json
```

---

### 3. Merge Real + Synthetic Data
```bash
python scripts/merge_calibration_data.py \
    --csv data/real_reviews.csv \
    --json data/synthetic_reviews.json \
    --output data/calibration_merged.json
```
Runs full validation: empty text, invalid ratings, null owner_response, and deduplication.

---

### 4. Dry Run (validate without hitting server)
```bash
python scripts/run_calibration_batch.py \
    --csv data/real_reviews.csv \
    --json data/calibration_merged.json \
    --dry-run
```

---

### 5. Run Full Calibration Batch
```bash
python scripts/run_calibration_batch.py \
    --csv data/real_reviews.csv \
    --json data/calibration_merged.json \
    --output data/calibration_results.json
```
Defaults: `--server http://localhost:5000` · `--token Themepark12`

---

## CSV Format (Real Reviews)

| Column | Type | Notes |
|---|---|---|
| `review_text` | string | Full review text, required |
| `rating` | integer 1–5 | Required |
| `owner_response` | string | Attorney reply, blank if none |

Date column is optional — defaults to `2025-01-01` and does not affect scoring.

---

## Target Distribution for Calibration

| Star | Ideal % of 100 reviews | Priority |
|---|---|---|
| ⭐ 1-star | ~15 reviews | Normal |
| ⭐⭐ 2-star | ~15 reviews | **HIGH** — hardest to collect |
| ⭐⭐⭐ 3-star | ~20 reviews | **HIGH** — critical for threshold tuning |
| ⭐⭐⭐⭐ 4-star | ~20 reviews | **HIGH** — soft positive boundary |
| ⭐⭐⭐⭐⭐ 5-star | ~30 reviews | Normal — typically over-stocked |

---

## What to Look for in Calibration Results

After running the batch, focus your analysis on:

1. **2★ vs 3★ boundary** — The engine must clearly distinguish moderate failure from neutral/mixed. This is the hardest threshold to tune.
2. **4★ with caveats** — Reviews that are mostly positive but flag one issue (billing, communication) should score high overall but trigger the relevant sub-flag.
3. **Owner response signal** — A defensive/dismissive owner response on a 3-star review should nudge the risk score upward.
4. **Severe negative flags** — 1-star reviews mentioning missed deadlines, abandonment, or fee disputes should all trigger the `severe_flag` indicator.
5. **Theme coverage** — Check that all 8 major themes (communication, billing, empathy, outcome, timeliness, professionalism, practice areas, severe negatives) are represented in results.

---

## Recommended Sources for 2–4 Star Real Reviews

- **Avvo.com** — Filter by rating 2–4, sort by Most Recent
- **Yelp** — Law firms, Sort by Rating (Low to High)
- **Google Maps** — Open firm profile → Sort reviews by "Lowest"
- **Martindale-Hubbell / lawyers.com** — Detailed text reviews, good mid-range signal
- **Facebook Business Pages** — Less filtered, common source of 2–3 star frustration reviews

---

*Last updated: 2026-03-11*
