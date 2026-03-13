# Metrics Time Logic

## Core rule
- Primary timeline uses `review_date` (`reviews.date`), not report upload/generation time.
- Dashboard trend periods and "last N days" review-volume counters are based on `review_date`.

## Report snapshot dates
- `reports.created_at` is used only for snapshot metadata:
  - when a report was generated,
  - ordering snapshots for "latest vs previous report" comparisons.
- Snapshot cards/tables may show both:
  - `review_date` coverage window (`review_date_start` to `review_date_end`),
  - generated timestamp (`created_at`).

## How snapshot review windows are derived
- For each report snapshot, we reconstruct the included review set using:
  - user ownership,
  - reviews created up to the snapshot `created_at`,
  - snapshot `total_reviews` as the row limit.
- The timeline period is the min/max `review_date` across that reconstructed set.

## Change vs previous report
- Comparison picks the immediately previous snapshot by `created_at` for the same user.
- Metric formulas stay unchanged:
  - overall satisfaction (avg rating),
  - positive share,
  - at-risk signals.
- UI labels include the previous report generated date and (when available) its review-date coverage window.

## Edge cases
- If no previous snapshot exists: show "first report" fallback messaging.
- If a snapshot review-date range cannot be reconstructed: fall back to snapshot generated date labels.
- Preview/free outputs must label only the visible period window.
