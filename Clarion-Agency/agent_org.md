# agent_org.md
# Clarion — Internal AI Agent Organization Structure
# Version: 2.3

---

## Organizational Principle

Each agent represents a function a healthy SaaS company needs staffed.
Agents operate within their lane only. No agent has authority over another.
All agents report upward through the Chief of Staff.

---

## DIVISION 1 — EXECUTIVE

### Chief of Staff
**Cadence:** Weekly
**File:** `agents/executive/chief_of_staff.md`
**Mission:** Synthesize all agent reports into a weekly CEO brief that surfaces the signal, filters the noise, and flags what requires a human decision.

---

## DIVISION 2 — REVENUE

### Head of Growth
**Cadence:** Weekly
**File:** `agents/revenue/head_of_growth.md`
**Mission:** Maintain the widest view across all growth inputs and surface the most important revenue signal of the week.

### Sales Development Analyst
**Cadence:** Weekly
**File:** `agents/revenue/sales_development.md`
**Mission:** Monitor top-of-funnel lead volume, quality, and source mix.

### Funnel Conversion Analyst
**Cadence:** Weekly
**File:** `agents/revenue/funnel_conversion.md`
**Mission:** Identify exactly where the sales funnel is leaking and surface the highest-leverage fix.

### Revenue Strategist
**Cadence:** Monthly
**File:** `agents/revenue/revenue_strategy.md`
**Mission:** Assess the structural health of Clarion's revenue model: pricing, packaging, expansion, and long-term customer base shape.

---

## DIVISION 3 — MARKET INTELLIGENCE

### Customer Discovery Agent
**Cadence:** Weekly
**File:** `agents/market/customer_discovery.md`
**Mission:** Scout public channels for real people experiencing the problems Clarion solves. Produce structured discovery signals for Sales, Content, and Product.

### Competitive Intelligence Analyst
**Cadence:** Weekly
**File:** `agents/market/competitive_intelligence.md`
**Mission:** Track competitor product, pricing, and messaging moves before they affect Clarion's pipeline or retention.

### Market Trends Analyst
**Cadence:** Monthly
**File:** `agents/market/market_trends.md`
**Mission:** Surface macro trends in legal technology and law firm management that are shaping the market before they arrive at the pipeline.

### ICP Analyst
**Cadence:** Quarterly
**File:** `agents/market/icp_analyst.md`
**Mission:** Keep Clarion's Ideal Customer Profile precise and grounded in real win/loss/churn data.

---

## DIVISION 4 — CUSTOMER INTELLIGENCE

### Customer Health & Onboarding Agent
**Cadence:** Weekly
**File:** `agents/customer/customer_health_onboarding.md`
**Mission:** Track every customer from first login through long-term retention. Catch churn risk early across the full lifecycle.

### Voice of Customer & Product Demand Agent
**Cadence:** Weekly
**File:** `agents/customer/voc_product_demand.md`
**Mission:** Translate raw customer language into structured intelligence for product, marketing, and operations.

### Retention Intelligence Analyst
**Cadence:** Monthly
**File:** `agents/customer/retention_intelligence.md`
**Mission:** Turn churn and contraction events into structural learning. Find patterns so the business can prevent the same loss twice.

---

## DIVISION 5 — PRODUCT INSIGHT

### Product Usage Analyst
**Cadence:** Weekly
**File:** `agents/product_insight/usage_analyst.md`
**Mission:** Monitor how customers are using Clarion, which features are adopted, which are ignored, and where usage patterns predict expansion or churn.

### Release Impact Analyst
**Cadence:** Event-driven (triggered after each product release)
**File:** `agents/product_insight/release_impact.md`
**Mission:** Assess the impact of each product release on adoption, support volume, and customer behavior.

### Product Insights Agent
**Cadence:** Weekly
**File:** `agents/product_insight/product_insights.md`
**Mission:** Read pre-launch prospect feedback from `memory/product_feedback.md`, identify recurring capability gaps and feature requests, surface Tier 1 patterns to the CEO, and recommend prioritization before launch.

### Product Experience Agent
**Cadence:** Weekly
**File:** `agents/product/prelaunch_conversion.md`
**Mission:** Audit the website and in-app experience for clarity, conversion quality, proof visibility, and modern credibility. This is a commercial function — not an aesthetics role. Proposes changes only; never implements. All implementation requires founder review and a Claude prompt.
**Logs to:** `memory/product_experience_log.md`
**Authority:** LEVEL 1 — audit, log, recommend only

---

## DIVISION 6 — PRODUCT INTEGRITY

### Phrase Dictionary Calibration Analyst
**Cadence:** Monthly
**File:** `agents/product_integrity/dictionary_calibration.md` *(to be written)*
**Mission:** Stress-test the phrase dictionary against real review language and propose calibration improvements for human review. Never modifies the dictionary directly.

### Scoring Quality Analyst
**Cadence:** Weekly
**File:** `agents/product_integrity/scoring_quality.md` *(to be written)*
**Mission:** Monitor the consistency and accuracy of Clarion's deterministic scoring output. Flag edge cases and drift.

### Data Quality Analyst
**Cadence:** Weekly
**File:** `agents/product_integrity/data_quality.md` *(to be written)*
**Mission:** Monitor the integrity of data inputs to Clarion — review ingestion quality, format consistency, and submission anomalies.

---

## DIVISION 7 — OPERATIONS

### Internal Process Analyst
**Cadence:** Weekly
**File:** `agents/operations/process_analyst.md` *(to be written)*
**Mission:** Monitor internal operational health: SLAs, team workflows, tooling friction, and process bottlenecks.

### Cost & Resource Analyst
**Cadence:** Weekly
**File:** `agents/operations/cost_resource.md` *(to be written)*
**Mission:** Track AI agent token costs, infrastructure spend, and resource utilization against budgets.

---

## DIVISION 8 — COMMS & CONTENT

### Content & SEO Agent
**Cadence:** Weekly
**File:** `agents/comms/content_seo.md` *(to be written)*
**Mission:** Identify content opportunities, monitor SEO signals, and propose content and distribution ideas grounded in customer discovery and market intelligence. Never publishes directly.

---

## DIVISION 9 — PEOPLE & CULTURE

### People & Ops Intelligence Agent
**Cadence:** Monthly
**File:** `agents/people/people_ops_intelligence.md` *(to be written)*
**Mission:** Monitor team health signals and hiring demand patterns. Surface resourcing risks before they become blockers.

---

## DIVISION 10 — STRATEGY

### Launch Readiness Analyst
**Cadence:** Monthly
**File:** `agents/strategy/launch_readiness.md`
**Mission:** Evaluate whether Clarion is ready for a public launch or broader outreach push across 11 dimensions. Produces a scored readiness report with blockers, priorities, and a recommended timing position. Prevents both premature launch and polishing drift.
**Authority:** LEVEL 1 — analysis only
**Escalates:** Score >= 8 → TOP STRATEGIC OPPORTUNITIES. Score <= 3 → TOP COMPANY RISKS.

---

## Agent Count Summary

| Division | Agents | Status |
|---|---|---|
| Executive | 1 | Complete |
| Revenue | 4 | Complete |
| Market Intelligence | 4 | Complete |
| Customer Intelligence | 3 | Complete |
| Product Insight | 4 | Complete (includes Product Experience) |
| Product Integrity | 3 | Stubs — to be written |
| Operations | 2 | Stubs — to be written |
| Comms & Content | 1 | Stub — to be written |
| People & Culture | 1 | Stub — to be written |
| Strategy | 1 | Complete |
| **Total** | **24** | **17 complete, 7 pending** |
