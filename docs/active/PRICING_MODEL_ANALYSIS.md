# Clarion — Pricing Model Analysis
**Based on direct codebase audit. No assumptions.**

---

## Part 1: Technical Findings

### Analysis Flow Status

```
Anthropic integration:  EXISTS IN CODEBASE — never imported or called in app.py
Classification method:  100% rules-based keyword matching (no LLM in production)
Feature flag location:  N/A — the classifier is simply not wired up, not gated
Fallback behavior:      Keyword matching IS the production behavior, not a fallback
```

**What actually runs when a firm uploads a CSV:**

1. `api_upload()` → parses CSV, enforces plan row cap, calls `_ingest_rows_into_report()`
2. `_ingest_rows_into_report()` → calls `_save_report_snapshot_tx()`
3. `_save_report_snapshot_tx()` → calls `_analyze_reviews_tx()` — this is the classifier
4. `_analyze_reviews_tx()` runs a **hardcoded dictionary of 8 themes with keyword lists**:
   - Communication, Professionalism, Legal Expertise, Case Outcome,
     Cost/Value, Responsiveness, Compassion, Staff Support
5. Each review text is lowercased and checked against keyword lists using `any(keyword in text)`
6. Results → `generate_governance_insights()` (deterministic, no LLM) → signals + actions saved

**`review_classifier.py` and `llm_client.py` are never imported anywhere in `app.py`.**
They are fully implemented and ready but completely disconnected from the product.

The Anthropic API key in `.env` is currently unused at runtime.

---

### Cost Structure: Current Reality

**Variable costs per report (today):**

| Cost Item | Amount | Notes |
|-----------|--------|-------|
| LLM classification | $0.00 | Not called |
| Email delivery (Resend) | ~$0.001/email | Per brief sent |
| PDF generation | ~$0.00 | Server CPU, negligible |
| Storage | ~$0.00 | Text data in SQLite/PG |
| **Total variable cost per report** | **~$0.00** | |

**Variable costs per report (if LLM enabled):**

| Reviews | Model | Input tokens | Output tokens | Est. cost |
|---------|-------|-------------|--------------|-----------|
| 50 reviews | claude-sonnet-4-5 | ~50 × 250 = 12,500 | ~50 × 150 = 7,500 | ~$0.09 |
| 250 reviews | claude-sonnet-4-5 | ~62,500 in | ~37,500 out | ~$0.45 |
| 1,000 reviews | claude-sonnet-4-5 | ~250,000 in | ~150,000 out | ~$1.80 |
| 5,000 reviews | claude-sonnet-4-5 | ~1.25M in | ~750K out | ~$9.00 |

*(Sonnet 4 pricing: $3/M input, $15/M output — one call per review)*

**Fixed monthly costs (estimated):**

| Item | Estimated Cost |
|------|---------------|
| Hosting (Fly.io/Railway/Render single instance) | $15–30/mo |
| PostgreSQL managed (Neon/Supabase free tier or small) | $0–25/mo |
| Sentry (free tier) | $0 |
| Resend email (free tier = 3,000/mo) | $0–20/mo |
| Domain + SSL | ~$2/mo amortized |
| **Total fixed** | **~$20–75/mo** |

**Break-even with current (keyword) classifier:** 1–2 paying customers at any price point.

**Break-even if LLM enabled at Team plan (250 reviews):** $0.45/report in variable cost.
At 10 reports/month per firm, that's $4.50/firm/month in variable costs — easily absorbed.

---

## Part 2: Pricing Recommendations

### Recommended Model: Flat-Rate SaaS (3 tiers)

**Rationale:** Variable costs are effectively zero with the current classifier, and even
with LLM enabled at any realistic volume they stay under $10/firm/month. The cost structure
strongly favors flat-rate pricing. Usage-based pricing would add billing complexity with
no economic justification at current scale.

Law firm buyers also prefer predictable invoices. Usage-based pricing introduces friction
at the purchase decision point.

---

### Tier Structure

#### Free (Keep as conversion funnel)
**$0/month**

- 1 report per month
- 50 reviews per upload
- 90-day history
- PDF with Clarion watermark
- 1 user
- No scheduled briefs

*Purpose: Let a managing partner validate the product with real data before committing.*

---

#### Team — $149/month or $1,490/year (save ~$300)
**Target: Solo practitioners, small firms (1–5 attorneys)**

- 10 reports per month
- 250 reviews per upload
- 365-day history
- PDF without watermark
- Up to 5 users (seat limit enforced in `plan_limits.py`)
- Weekly scheduled brief emails

*Margin analysis:*
- Variable cost (keyword): ~$0/mo
- Variable cost (if LLM enabled): ~$4.50/mo (10 reports × 250 reviews × $0.0018/review)
- Fixed cost allocation: ~$25/mo
- Net margin at $149: **~$120–149/mo per firm (80–100%)**

---

#### Firm — $349/month or $3,490/year (save ~$700)
**Target: Mid-size firms (5–20+ attorneys), office managers, marketing partners**

- Unlimited reports per month
- 1,000 reviews per upload (5,000 cap exists in constants, consider exposing this)
- Unlimited history
- PDF without watermark
- Up to 20 users
- Weekly scheduled brief emails
- Priority support (manual, no new dev required)

*Margin analysis:*
- Variable cost (keyword): ~$0/mo
- Variable cost (if LLM enabled, heavy user): ~$36/mo (20 reports × 1,000 reviews)
- Fixed cost allocation: ~$35/mo
- Net margin at $349: **~$278–349/mo per firm (80–100%)**

---

### One-Time Report (Keep — already implemented)
**$49/report**

Already built, already sold. Keep as an entry point for firms not ready to subscribe.
Variable cost: ~$0 (keyword), ~$0.09 (LLM on 50 reviews). Margin: effectively 100%.

---

## Part 3: Tier Differentiation Matrix

| Feature | Free | Team | Firm | Implementation Status |
|---------|------|------|------|-----------------------|
| Reviews per upload | 50 | 250 | 1,000 | ✅ Enforced server-side (`plan_limits.py` + `plan_service.enforce_upload_limit`) |
| Reports per month | 1 | 10 | Unlimited | ✅ Enforced server-side (`plan_service.enforce_monthly_report_limit`) |
| History window | 90 days | 365 days | Unlimited | ✅ Enforced server-side (`plan_service.enforce_history_access`) |
| PDF watermark | Yes | No | No | ✅ Enforced server-side (`pdf_generator.py` reads `pdf_watermark` from plan limits) |
| Seats (users) | 1 | 5 | 20 | ✅ Enforced server-side (`plan_service.enforce_seat_limit`) |
| Team invite system | No | Yes | Yes | ✅ Functional — `/api/team/invite`, `/api/team/accept`, `/api/team/members` all implemented |
| Scheduled brief emails | No | Yes | Yes | ⚠️ Partially — scheduler exists and fires, but recipient list comes from `PARTNER_EMAILS` env var, not per-firm DB config. Multi-firm scheduling not yet wired to `report_pack_schedules` table (table exists, scheduler doesn't read it) |
| Governance signals | All | All | All | ✅ Generated on every report via `generate_governance_insights()` |
| Action tracking | All | All | All | ✅ Full CRUD at `/api/reports/:id/actions` |
| Report restore (soft delete) | No | No | Yes | ✅ Enforced — `can_restore` flag gated by plan check in reports API |
| Slack alerts | — | — | — | ⚠️ `slack_service.py` exists but is a stub (no real Slack API call implemented). Do not advertise. |
| Multi-user roles | — | Yes | Yes | ✅ owner/partner/member roles enforced in firm_users schema |
| Custom branding | — | — | — | ⚠️ `account_branding` table and logo upload exists, but not exposed as a paid tier differentiator. Could be a Firm-only feature with zero new dev. |
| Data export | — | — | — | ❌ Not implemented |
| API access | — | — | — | ❌ Not implemented |
| "Governance workflow" | All | All | All | ✅ This is just the actions + signals flow — it's real and available to all plans |

---

## Part 4: Key Decisions Before Launch

### Decision 1: Enable LLM or ship keyword classifier?

**Recommendation: Ship the keyword classifier now.**

The keyword classifier produces real, useful output for governance purposes. Eight well-chosen
themes cover the core of what law firm feedback contains. Governance signals and the brief are
both generated deterministically — they are coherent and defensible.

Enabling the LLM adds meaningful cost ($0.09–$9/report), requires testing the new output
format against the existing frontend, and introduces an external API dependency with latency
and failure modes.

Activate LLM classification as a v2 feature, positioned as "AI-enhanced analysis" when
you're ready to validate the quality difference and price for it.

### Decision 2: Fix the scheduled brief before advertising it

The `report_pack_schedules` table exists and has the right schema (per-firm, with
`enabled`, `cadence`, `recipients_json`). The scheduler currently reads `PARTNER_EMAILS`
from the env — a single global list. Before advertising scheduled briefs as a Team/Firm
feature, the scheduler needs to query `report_pack_schedules` per firm instead.

This is a small, contained change. Do it before launch if scheduled briefs are in marketing
copy; otherwise gate the feature flag in the UI and defer.

### Decision 3: Custom branding as a Firm differentiator

The `account_branding` table, logo upload endpoint, and theme presets are fully implemented.
Exposing this as a Firm-only feature requires only a plan check on the branding API route —
no new development. It's a meaningful visual differentiator for a $349/mo purchase decision.

---

## Summary

| | Current reality | Impact on pricing |
|--|----------------|-------------------|
| LLM integration | Built but not called | Zero variable cost today |
| Keyword classifier | Production classifier | Solid output, no API risk |
| Plan limits | All enforced server-side | Safe to sell on |
| Team/invite system | Fully functional | Team tier is real |
| Scheduled briefs | Partially wired | Fix before advertising |
| Slack | Stub only | Do not advertise |
| Variable cost per firm | ~$0/mo (keyword) | Flat-rate pricing is correct |
| Recommended price | Free / $149 / $349 | 80–100% gross margin |
