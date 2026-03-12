# office_scorecard.md
# Clarion Agent Office — Office Scorecard
# Version: 1.0 | 2026-03-12
# Updated by: Chief of Staff each cycle (append only)
# CEO reviews: weekly

---

## PURPOSE
Evaluate whether the office is functioning well using only real, measurable signals.
No vanity metrics. No synthetic KPIs. Only signals derived from actual agent outputs.

---

## SIGNAL DEFINITIONS

### HEALTHY | WATCH | UNHEALTHY
HEALTHY: Operating within expected range. No action needed.
WATCH:   Trending toward a problem. Monitor closely. May require intervention.
UNHEALTHY: Outside acceptable range. Requires CEO attention or process change.

---

## SECTION 1: PIPELINE HEALTH

Signal: Number of active leads in leads_pipeline.csv with status = active or qualifying
  HEALTHY: 3 or more leads advancing
  WATCH: 1-2 leads active, no new additions in 14 days
  UNHEALTHY: Zero active leads, or no new lead added in 21 days

Signal: Number of leads converted to pilot conversations
  HEALTHY: At least 1 pilot conversation initiated since launch
  WATCH: No pilot conversations but active leads exist
  UNHEALTHY: No pilot conversations and pipeline has been active for 30+ days

Signal: Do-not-chase list growth
  HEALTHY: Grows only when ghosted — not used as a dumping ground
  WATCH: More than 5 new entries in a single cycle
  UNHEALTHY: Entries added without documented ghost criteria being met

---

## SECTION 2: OUTREACH ACTIVITY

Signal: Outreach drafts ready for CEO/Level 2 review per cycle
  HEALTHY: At least 1 new outreach angle drafted per cycle
  WATCH: No new drafts for 2 consecutive cycles
  UNHEALTHY: No outreach activity for 3+ consecutive cycles

Signal: Cooldown compliance
  HEALTHY: No cooldown violations detected by Chief of Staff
  WATCH: 1 cooldown violation per cycle
  UNHEALTHY: 2+ cooldown violations or pattern of violations

---

## SECTION 3: PILOT THROUGHPUT

Signal: Active pilots (firms in pilot stage)
  HEALTHY: At least 1 pilot active or completed since office launch
  WATCH: No pilots initiated despite pipeline activity
  UNHEALTHY: Pipeline has active leads but no pilot has been proposed in 30+ days

Signal: Pilot completion rate
  HEALTHY: Pilots started reach completion with a documented outcome
  WATCH: A pilot has stalled with no update for 14+ days
  UNHEALTHY: A pilot has stalled with no update for 21+ days

---

## SECTION 4: PROOF ASSET GROWTH

Signal: Entries in memory/proof_assets.md
  HEALTHY: At least 1 usable proof asset exists
  WATCH: Zero proof assets despite completed pilots
  UNHEALTHY: Zero proof assets and no pilots in pipeline

Signal: Asset quality (named vs. anonymized)
  HEALTHY: At least 1 named or permissioned asset exists
  WATCH: All assets are anonymized — permission conversations not yet initiated
  UNHEALTHY: Proof assets exist but are not usable in any outreach format

---

## SECTION 5: CONVERSION FRICTION PATTERNS

Signal: Documented friction patterns in memory/conversion_friction.md
  HEALTHY: Friction patterns documented, at least 1 has a proposed fix
  WATCH: Multiple friction patterns with no proposed fix for 2+ cycles
  UNHEALTHY: Same friction pattern recurs 3+ times with no resolution path

Signal: Friction resolution rate
  HEALTHY: At least 1 friction pattern resolved or has an approved fix in last 30 days
  WATCH: No friction patterns resolved in last 30 days
  UNHEALTHY: Friction patterns growing faster than resolution

---

## SECTION 6: SITE HEALTH STABILITY

Signal: Customer-facing process failures (from Internal Process Analyst)
  HEALTHY: Zero confirmed customer-facing failures this cycle
  WATCH: 1 failure detected and being addressed
  UNHEALTHY: 2+ failures in a single cycle, or a failure unresolved for 7+ days

Signal: SLA compliance
  HEALTHY: Above 85%
  WATCH: 70-85%
  UNHEALTHY: Below 70%

---

## SECTION 7: COMPETITOR ACTIVITY VOLUME

Signal: New entries in memory/competitor_tracking.md per cycle
  HEALTHY: 1-3 new meaningful signals per cycle
  WATCH: Zero signals for 3+ consecutive cycles (monitoring gap)
  UNHEALTHY: Critical competitor move detected and not surfaced to CEO

Signal: Threat level distribution
  HEALTHY: Most signals at Watch level; Active and Critical are rare
  WATCH: 2+ Active signals open simultaneously
  UNHEALTHY: Any Critical signal unresolved for 7+ days

---

## SECTION 8: PRODUCT FEEDBACK VOLUME

Signal: New entries in memory/product_feedback.md per cycle
  HEALTHY: At least 1 new theme documented
  WATCH: No new feedback documented for 2 consecutive cycles
  UNHEALTHY: No feedback captured despite active customers or pilots

Signal: Feedback-to-product routing rate
  HEALTHY: Recurring themes are routed to Product Insight within 1 cycle
  WATCH: Recurring themes documented but not routed
  UNHEALTHY: 3+ recurring themes with no product routing for 30 days

---

## SECTION 9: ESCALATION QUALITY

Signal: Escalations surfaced to CEO brief that were correctly classified
  HEALTHY: All escalations meet the threshold in founder_escalation.md
  WATCH: 1 under-threshold escalation per cycle (noise in the brief)
  UNHEALTHY: 3+ under-threshold escalations, or a valid escalation was suppressed

Signal: Open escalation resolution time
  HEALTHY: Critical escalations resolved by CEO within 24h; High within 48h
  WATCH: A High escalation unresolved for 72h
  UNHEALTHY: A Critical escalation unresolved for 48h or an open escalation carried 3+ cycles without decision

---

## SCORECARD LOG
# Append a brief status update each weekly cycle below.
# Format: [YYYY-MM-DD] | OVERALL: HEALTHY | WATCH | UNHEALTHY | KEY FLAGS: [brief note]

[2026-03-12] | SCORECARD INITIALIZED | No data yet. Baseline to be established on first full run.
