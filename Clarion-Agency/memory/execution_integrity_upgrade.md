# execution_integrity_upgrade.md
# Clarion Agency — Execution Integrity Upgrade

**Date:** 2026-03-12
**Author:** Agency Config Session
**Status:** Complete

---

## Rule Added

**Rule name:** `## Execution Integrity Rule`

**Summary:**
Agents must only report concrete, completed work in WORK COMPLETED THIS RUN. Prohibited entries include vague planning statements, generic brainstorming, and speculative ideas. If no meaningful work was done, the agent must write exactly: "No significant progress this run."

**Consecutive stall rule:**
If an agent reports "No significant progress this run." for 2 consecutive runs on the same active project, the agent must update that project in `memory/projects.md`: set `Blocked? = Yes` and `Escalate? = Yes`, and include a one-sentence blocker description.

---

## Files Modified

All 13 weekly-cadence agent prompt files received exactly one `## Execution Integrity Rule` section, inserted immediately before `## Guardrails` (or `## Hard Rules` for `customer_discovery.md`):

| File | Anchor |
|------|--------|
| agents/market/competitive_intelligence.md | ## Guardrails |
| agents/market/customer_discovery.md | ## Hard Rules |
| agents/revenue/head_of_growth.md | ## Guardrails |
| agents/comms/content_seo.md | ## Guardrails |
| agents/operations/cost_resource.md | ## Guardrails |
| agents/operations/process_analyst.md | ## Guardrails |
| agents/customer/customer_health_onboarding.md | ## Guardrails |
| agents/customer/voc_product_demand.md | ## Guardrails |
| agents/product_insight/usage_analyst.md | ## Guardrails |
| agents/product_integrity/data_quality.md | ## Guardrails |
| agents/product_integrity/scoring_quality.md | ## Guardrails |
| agents/revenue/funnel_conversion.md | ## Guardrails |
| agents/revenue/sales_development.md | ## Guardrails |

---

## Files Not Modified

- `agents/executive/chief_of_staff.md` — monthly cadence, not weekly
- `memory/projects.md` — no structural changes; agents update it at runtime per the stall rule
- All backend, frontend, and production scoring files — untouched

---

## Blocked Items

None. All 13 files verified: 1 instance each of `## Execution Integrity Rule`, no duplicates.

Note: Two previous interrupted sessions had left duplicate blocks in `competitive_intelligence.md`, `customer_discovery.md`, and `head_of_growth.md`. These were cleaned and resolved during this session via idempotent PowerShell script (`fix_execution_integrity.ps1`).
