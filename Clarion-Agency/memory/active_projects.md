# active_projects.md
# Clarion Agent Office — Active Project Tracker (Orchestration Layer)
# Version: 2.0 | 2026-03-12
#
# PURPOSE
# This file is the orchestration-aware version of the project tracker.
# It extends projects.md with wake scheduling fields needed by the runner.
# Chief of Staff reads this file. The runner reads this file to determine
# MODE 3 (Active Project Window) wake schedules.
#
# FIELDS
#   project          — human-readable project name (must match projects.md entry)
#   owner_division   — which division agent owns this project
#   status           — Active | Dormant | Stale | Completed | Archived
#   wake_frequency   — how often the runner wakes the owning agent for this project
#                      values: "every 2 hours" | "every 4 hours" | "daily" |
#                              "weekly" | "engagement_window_only" | null (dormant)
#   stop_condition   — what causes this project's active window to close
#   priority         — P1 (critical path) | P2 (important) | P3 (background)
#   last_run         — ISO date of last agent invocation for this project
#   next_eligible    — ISO date/time after which runner may next invoke
#
# RULES
# - The runner compares `next_eligible` against current datetime before invoking.
# - If `wake_frequency` is null or status is Dormant/Stale/Completed, runner skips.
# - Stale flag is set automatically by runner when project has no update in 30 days.
# - Human must clear Stale flag to re-activate.
# - Do not delete entries. Change status to Completed or Archived instead.
# - Maximum 7 Active entries (enforced per projects.md capacity safeguard).

---

## ACTIVE PROJECTS

---

project:         Pre-Launch Marketing Foundation
owner_division:  Comms & Content Agent
status:          Active
wake_frequency:  weekly
stop_condition:  CEO issues post-launch directive and marks marketing foundation complete
priority:        P1
last_run:        null
next_eligible:   2026-03-13
notes:           Covers LinkedIn presence, content calendar, ICP messaging.
                 Weekly cadence sufficient — no intra-week state changes expected.
                 Wake on Friday with full comms run.
                 Upgrade to "daily" if CEO approves a live publishing schedule.

---

project:         Early Adopter Outreach Preparation
owner_division:  Customer Discovery Agent + Sales Development Analyst
status:          Active
wake_frequency:  weekly
stop_condition:  10 qualified discovery leads are documented in discovery_interviews.md
                 OR CEO approves live outreach execution (triggers MODE 2 at higher frequency)
priority:        P1
last_run:        null
next_eligible:   2026-03-13
notes:           Research and drafting authorized without CEO approval.
                 Execution (sending messages) requires approved_actions.md entry.
                 Upgrade wake_frequency to "daily" immediately when first outreach
                 is approved and sent — reply detection must be timely (TRIGGER-004).

---

project:         Launch Content Calendar
owner_division:  Content & SEO Agent
status:          Active
wake_frequency:  weekly
stop_condition:  8-week content calendar is approved by CEO and first 3 articles are outlined
priority:        P2
last_run:        null
next_eligible:   2026-03-13
notes:           All drafts internal only until CEO approval.
                 No external publishing trigger until approved_actions.md entry exists.
                 Rolls into Pre-Launch Marketing Foundation on completion.

---

project:         Onboarding Readiness
owner_division:  Customer Health & Onboarding Agent
status:          Dormant
wake_frequency:  null
stop_condition:  First paying customer onboards (triggers activation)
priority:        P3
last_run:        null
next_eligible:   null
notes:           Dormant until account_roster.csv contains at least one real account.
                 Activation trigger: account_roster.csv gains a non-placeholder row (TRIGGER-010).
                 On activation: set status to Active and wake_frequency to "daily".

---

project:         Funnel Conversion Improvement
owner_division:  Funnel Conversion Analyst + Head of Growth
status:          Dormant
wake_frequency:  null
stop_condition:  Top 2 funnel friction points identified and proposals submitted to CEO
priority:        P2
last_run:        null
next_eligible:   null
notes:           Dormant until conversion_friction.md contains real data.
                 Activation trigger: TRIGGER-011 fires.
                 On activation: set status to Active and wake_frequency to "weekly".

---

project:         Competitive Positioning Intelligence
owner_division:  Competitive Intelligence Analyst
status:          Active
wake_frequency:  weekly
stop_condition:  No stop condition — ongoing intelligence project. Rolls to Archived
                 only if Clarion pivots away from competitive monitoring.
priority:        P2
last_run:        null
next_eligible:   2026-03-13
notes:           Full competitor matrix on monthly cadence.
                 Incremental updates on TRIGGER-012 (new competitor data added).
                 Weekly run scoped to checking for new signals — not a full reanalysis.

---

project:         Pricing & Positioning Review
owner_division:  Revenue Strategist + Head of Growth
status:          Dormant
wake_frequency:  null
stop_condition:  Pricing decision made by CEO and documented in decision_log.md
priority:        P3
last_run:        null
next_eligible:   null
notes:           Dormant until monthly revenue cycle begins (first paying customers).
                 Activation: first Friday of the month once pipeline_snapshot.csv
                 contains real revenue data.
                 Pricing changes require CEO approval per projects.md escalation flag.

---

## PILOT PROJECTS — TEMPLATE

When a pilot engagement begins, create an entry using this template:

  project:         Pilot — [Firm Name Anonymized]
  owner_division:  Customer Health & Onboarding Agent + Chief of Staff
  status:          Active
  wake_frequency:  every 2 hours  (during pilot window)
                   daily          (outside active engagement hours)
  stop_condition:  Pilot marked complete in this file OR 30 days elapsed without contact
  priority:        P1
  last_run:        [ISO date of first run]
  next_eligible:   [ISO datetime — 2 hours after last_run during business hours]
  notes:           Live pilot. High-frequency monitoring during engagement window only.
                   wake_frequency reverts to "daily" outside 9am–6pm Central.
                   TRIGGER-005 fires on start. TRIGGER-006 fires on completion.
                   Do not let this project go Stale — check in daily minimum.

---

## COMPLETED PROJECTS

_(none yet)_

---

## ARCHIVED PROJECTS

_(none yet)_

---

## Wake Frequency Reference

| Value | Meaning |
|---|---|
| every 2 hours | Invoked up to 12 times per day (business hours only, quiet hours excluded) |
| every 4 hours | Invoked up to 4 times per day (business hours only) |
| daily | Invoked once per calendar day |
| weekly | Invoked once per week (standard Friday cadence) |
| engagement_window_only | Invoked only when a human-defined engagement window is active |
| null | Not invoked — project is dormant or completed |
