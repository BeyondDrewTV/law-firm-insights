# event_triggers.md
# Clarion Agent Office — Event Trigger Registry
# Version: 1.0 | 2026-03-12
#
# PURPOSE
# Maps specific file changes and operational events to the agent division(s)
# that should wake in response. The runner reads this file to determine
# which agents to invoke outside of the normal weekly schedule.
#
# RULES
# - Triggers do NOT fire a full office run. Only the mapped division(s) wake.
# - Chief of Staff does NOT run unless the trigger is marked ESCALATE or it is a scheduled run day.
# - Triggers must be detected by the runner through file modification timestamps or
#   explicit signal files — not by polling LLM agents continuously.
# - If multiple triggers fire simultaneously, group the invocations: run mapped agents once
#   with all trigger context, not once per trigger.

---

## Trigger Detection Method

The runner checks event triggers by comparing file modification timestamps against a
last-run timestamp stored in `memory/office_health_log.md` (field: `last_trigger_check`).

If a trigger file's mtime is newer than `last_trigger_check`, the trigger is considered fired.

No LLM is called to detect triggers. File stat checks only.

---

## TRIGGER REGISTRY

---

### TRIGGER-001
**Event:** `memory/approved_actions.md` has been modified since last run
**Meaning:** CEO has approved one or more new actions for execution
**Wake:** Chief of Staff + owning division agent for each approved action
**Mode:** Event-driven wakeup (MODE 2)
**Notes:** Runner reads the file, identifies newly-approved entries (STATUS: approved),
routes each to the owning division. Does not run Chief of Staff if trigger fires
outside a scheduled run — unless ESCALATE flag is present.

---

### TRIGGER-002
**Event:** `memory/division_lead_approvals.md` has been modified since last run
**Meaning:** A division lead has approved a Level 2 action for execution
**Wake:** Owning division agent for each approved entry
**Mode:** Event-driven wakeup (MODE 2)
**Notes:** Same routing logic as TRIGGER-001. Chief of Staff does not run unless
the approved action touches brand, external communication, or budget.

---

### TRIGGER-003
**Event:** A new lead entry has been appended to a leads or discovery file
(e.g., `data/market/discovery_interviews.md` or `data/revenue/pipeline_snapshot.csv`
has a new non-placeholder row since last run)
**Meaning:** A real discovery or sales lead has been added to the system
**Wake:** Customer Discovery Agent + Sales Development Analyst
**Mode:** Event-driven wakeup (MODE 2)
**Notes:** Only fires if the new entry is not a placeholder row. Agent performs
bounded analysis of the new lead only — does not re-process the full file.

---

### TRIGGER-004
**Event:** An outreach reply signal is logged
(e.g., `memory/email_log.md` has a new entry with type: INBOUND since last run)
**Meaning:** A prospect or contact has replied to Clarion outreach
**Wake:** Sales Development Analyst + Head of Growth
**Mode:** Event-driven wakeup (MODE 2)
**Priority:** HIGH — reply detection should surface within the same business day
**Notes:** Do not defer to weekly run. This is a high-signal event. Runner should
check this trigger at least once per business day. Chief of Staff is notified
via next scheduled run.

---

### TRIGGER-005
**Event:** A pilot project is marked as started in `memory/active_projects.md`
(status changes from Not Started or Staged → In Progress, with project type: pilot)
**Meaning:** A live pilot is underway with a real law firm
**Wake:** Chief of Staff + Customer Health & Onboarding Agent + Sales Development Analyst
**Mode:** Event-driven wakeup (MODE 2) + Active Project Window (MODE 3)
**Priority:** HIGH
**Notes:** When a pilot starts, the project's `wake_frequency` in `active_projects.md`
should be set to "every 2 hours" or "daily" per the project definition. The runner
begins MODE 3 active project monitoring immediately on this trigger.

---

### TRIGGER-006
**Event:** A pilot project is marked as completed in `memory/active_projects.md`
(status changes to Completed for a project with type: pilot)
**Meaning:** A pilot engagement has concluded
**Wake:** Chief of Staff + Customer Health & Onboarding Agent + Head of Growth + Revenue Strategist
**Mode:** Event-driven wakeup (MODE 2)
**Priority:** HIGH — this is a conversion signal
**Notes:** Runner triggers a full synthesis pass scoped to the pilot outcome.
Revenue Strategist assesses conversion opportunity. Chief of Staff surfaces in
next CEO brief regardless of schedule.

---

### TRIGGER-007
**Event:** A new incident entry is appended to `memory/security_incident_log.md`
or `memory/moderation_log.md` since last run
**Meaning:** A security or moderation incident has been logged
**Wake:** Chief of Staff (immediate) + Internal Process Analyst
**Mode:** Event-driven wakeup (MODE 2)
**Priority:** CRITICAL — must surface within 2 hours during business hours
**Notes:** Chief of Staff runs an abbreviated synthesis focused on the incident.
The full weekly brief is NOT triggered — only an incident-scoped brief is produced.
Human escalation per `memory/standing_orders.md` SO-005 is mandatory.

---

### TRIGGER-008
**Event:** A new post or content asset is marked as published or staged-for-review
in `data/comms/content_log.csv` or `memory/execution_log.md`
**Meaning:** Content has gone live or is awaiting CEO review for publication
**Wake:** Content & SEO Agent (review pass) + Chief of Staff (if published)
**Mode:** Event-driven wakeup (MODE 2)
**Notes:** If STATUS is staged-for-review: Content & SEO Agent performs a self-review pass.
If STATUS is published (CEO executed): Chief of Staff notes it in next brief.

---

### TRIGGER-009
**Event:** A reply or comment is detected on a Clarion-owned social post
(flagged in `data/comms/discovered_conversations.md` with source: owned-reply)
**Meaning:** Someone has responded to Clarion content on a social platform
**Wake:** Content & SEO Agent + Customer Discovery Agent (if reply contains discovery signal)
**Mode:** Event-driven wakeup (MODE 2)
**Notes:** Agent produces a bounded response-recommendation only.
No agent may draft or send a reply without CEO approval per SO-006.

---

### TRIGGER-010
**Event:** A product artifact file in `data/product/` has been modified since last run
(any of: `feature_usage.csv`, `session_log.csv`, `adoption_baseline.csv`)
**Meaning:** Fresh product usage data has been loaded
**Wake:** Product Usage Analyst + Voice of Customer & Product Demand Agent
**Mode:** Event-driven wakeup (MODE 2)
**Notes:** Only fires if the file change adds real data rows (not placeholder lines).
Runner uses the same `_has_real_input()` gate as the scheduled runner.

---

### TRIGGER-011
**Event:** `data/market/conversion_friction.md` has been modified since last run
**Meaning:** Funnel friction data has been updated (new friction signals identified)
**Wake:** Funnel Conversion Analyst + Head of Growth
**Mode:** Event-driven wakeup (MODE 2)
**Notes:** Agents run a bounded analysis of the new friction signal only.
Do not re-run the full funnel analysis unless scheduled run day has also arrived.

---

### TRIGGER-012
**Event:** A new competitor entry or pricing update is added to
`data/market/competitors.md` or `data/market/competitor_pricing.md`
**Meaning:** New competitive intelligence data is available
**Wake:** Competitive Intelligence Analyst
**Mode:** Event-driven wakeup (MODE 2)
**Notes:** Agent produces an incremental competitive brief scoped to the new entry.
Full competitor matrix refresh runs on the monthly scheduled cadence.

---

## Trigger Cooldowns

Even for event-driven triggers, per-division max wake frequency from `run_policy.md` applies.

If a trigger fires for Market Intelligence but Market Intelligence ran 2 hours ago,
the trigger is logged but execution is deferred until the cooldown expires.

Deferred triggers are not lost. Runner logs them in `memory/office_health_log.md`
under `deferred_triggers` and processes them on the next eligible window.

---

## Manual Override

A human operator may invoke any agent directly at any time, bypassing trigger logic.
Manual invocations are not subject to cooldowns.
Manual invocations must be logged in `memory/execution_log.md` with:
- Operator: [name/role]
- Reason: [why manual override was used]
- Agents invoked: [list]
