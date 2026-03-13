# office_health_log.md
# Clarion — Office Health Log
# Append-only. Do not overwrite or delete entries.
# Chief of Staff appends one entry per weekly run after the CEO brief is generated.
#
# ORCHESTRATION FIELDS (added v2.0 — 2026-03-12)
# The resident shell and trigger detection layer also write to this file.
# Fields used by the orchestration layer:
#   last_trigger_check  — ISO datetime of last event trigger scan
#   deferred_triggers   — list of trigger IDs deferred due to cooldown
#   daily_llm_count     — running count of LLM invocations today (resets at midnight)
#   cost_cap_hit        — true/false — whether the daily soft cap was reached

---

# ORCHESTRATION STATE (updated by runner each cycle)
last_trigger_check:  2026-03-12T17:02:12
deferred_triggers:   []
daily_llm_count:     3
cost_cap_hit:        false

---

## OFFICE HEALTH HISTORY

---
RUN DATE:                    [System initialized — first live entry will appear after first weekly run]
AGENTS SUCCESSFUL:           [Pending first run]
AGENTS FAILED / MISSING:     [Pending first run]
STALLED AGENTS:              [Pending first run]
STALLED PROJECTS:            [Pending first run]
BLOCKED PROJECTS:            [Pending first run]
CONFLICTING SIGNALS:         [Pending first run]
DEPARTMENT ACTIVITY:
  Revenue:                   [Pending first run]
  Market Intelligence:       [Pending first run]
  Customer:                  [Pending first run]
  Product Insight:           [Pending first run]
  Product Integrity:         [Pending first run]
  Operations:                [Pending first run]
  Comms & Content:           [Pending first run]
  People & Culture:          [Pending first run]
OPERATIONAL RISK LEVEL:      [Pending first run]
CEO BRIEF GENERATED:         [Pending first run]
---
