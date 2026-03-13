# Clarion — Pricing Structure
**Status: Launch configuration. Last updated: 2026-03-08.**

---

## Plans

### Free — $0/month
Solo trial. No credit card required.

| Limit | Value |
|-------|-------|
| Users | 1 (solo only) |
| Reviews per upload | 50 |
| Reports per month | 1 |
| History window | 90 days |
| PDF brief | Watermarked |
| Scheduled briefs | No |
| Team invites | No |

---

### Team — $179/month or $1,790/year *(save ~$358)*
Small to mid-size firms. Unlimited seats.

| Limit | Value |
|-------|-------|
| Users | Unlimited |
| Reviews per upload | 250 |
| Reports per month | 10 |
| History window | 365 days (1 year) |
| PDF brief | Clean (no watermark) |
| Scheduled briefs | Yes |
| Team invites | Yes |

---

### Firm — $449/month or $4,490/year *(save ~$898)*
Large or high-volume firms. No limits on reports or history.

| Limit | Value |
|-------|-------|
| Users | Unlimited |
| Reviews per upload | 1,000 |
| Reports per month | Unlimited |
| History window | Unlimited |
| PDF brief | Clean (no watermark) |
| Scheduled briefs | Yes |
| Team invites | Yes |
| Report restore | Yes |

---

## Rationale

**Why flat-rate?**
Variable costs are effectively $0 per report. Classification is keyword-based (no LLM API
calls in production). PDF generation is server CPU. Storage is negligible text data.
Fixed infrastructure costs run $20–75/month total regardless of usage.

Flat-rate pricing eliminates friction at the purchase decision and matches how law firms
budget software (annual line items, not consumption billing).

**Margin profile:**
- Fixed cost per firm: ~$5–15/month (infrastructure allocation)
- Variable cost per report: ~$0.00
- Gross margin at Team ($179): **~95%+**
- Gross margin at Firm ($449): **~95%+**

**Why unlimited seats on paid plans?**
Law firms make decisions by committee. Seat limits create a negotiation obstacle before
the sale is closed. Unlimited seats on Team and Firm removes that friction — the
differentiator between tiers is review volume and report cadence, not headcount.

**Why 250/1,000 review caps (not 5,000)?**
These caps match real firm data volumes at each market segment. The previous 5,000 cap
on both paid plans created no meaningful tier differentiation. 250 reviews covers a small
firm's quarterly feedback. 1,000 covers a large firm's full review history.
The 5,000-row processing cap in `app.py` (MAX_CSV_ROWS) remains as an absolute server
safety limit — it is not a plan feature.

---

## Enforcement Map

All limits are enforced server-side. Frontend display is informational only.

| Limit | Enforced in | Behavior when exceeded |
|-------|-------------|----------------------|
| `max_users` | `plan_service.enforce_seat_limit()` | Returns error, blocks invite |
| `max_reviews_per_upload` | `plan_service.enforce_upload_limit()` | Returns 400, rejects upload |
| `max_reports_per_month` | `plan_service.enforce_monthly_report_limit()` | Returns 403, blocks report save |
| `history_days` | `plan_service.enforce_history_access()` | Returns 403 on report fetch |
| `pdf_watermark` | `pdf_generator.py` reads flag from plan limits | Watermark rendered in PDF |

`None` in any limit field = unlimited (enforcement function returns `None` = allow).

---

## One-Time Report (Legacy / Entry Point)
**$49 per report**

Single analysis with no subscription. Counts against Free plan report quota.
Kept as a low-friction entry point for firms evaluating before subscribing.
