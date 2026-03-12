# memory_lifecycle.md
# Clarion Agent Office — Memory Lifecycle Rules
# Version: 1.0 | 2026-03-12
# Agents may read. Agents may never modify.

---

## PURPOSE
Prevent uncontrolled growth of memory files, context bloat, and loss of critical history.
Every file has a defined lifecycle. When in doubt, archive rather than delete.

---

## FILE CATEGORIES

### CATEGORY 1: APPEND-ONLY LOGS
These files grow over time and are never overwritten. Entries are never deleted directly.
Compression is applied on a defined schedule (see below).

Files in this category:
- memory/execution_log.md
- memory/decision_log.md
- memory/office_health_log.md
- memory/office_learning_log.md
- memory/calibration_log.md
- memory/market_refresh_log.md
- memory/security_incident_log.md
- memory/moderation_log.md
- memory/email_log.md
- memory/office_upgrade_log.md
- memory/office_optimization_log.md
- memory/operational_office_upgrade_log.md
- memory/history_summaries.md
- memory/office_scorecard.md (log section only)

Rules:
- Append entries with date prefix: [YYYY-MM-DD]
- Never delete entries from these files directly
- Compress entries older than 90 days into rolling summaries (see Monthly Compression below)

---

### CATEGORY 2: ROLLING STATE FILES
These files represent current state. They are updated in place.
Old entries may be superseded but are not deleted — they are marked superseded or archived inline.

Files in this category:
- memory/active_projects.md
- memory/projects.md
- memory/approved_actions.md (completed actions move to Archived section)
- memory/competitor_tracking.md
- memory/conversion_friction.md
- memory/product_feedback.md
- memory/proof_assets.md
- memory/do_not_chase.md
- memory/experiments.md
- memory/leads_pipeline.csv (via Sales Development)

Rules:
- When an entry is resolved or superseded, mark it with [ARCHIVED: YYYY-MM-DD] rather than deleting
- Keep the last 60 days of active state visible at top of file
- Entries older than 60 days with no active reference move to an ARCHIVED section at the bottom

---

### CATEGORY 3: STATIC POLICY FILES
These files are stable and change infrequently. They are maintained by CEO only.
They do not grow through agent activity.

Files in this category:
- memory/standing_orders.md
- memory/agent_authority.md
- memory/agent_security_policy.md
- memory/icp_definition.md
- memory/brand_canon.md
- memory/brand_voice.md
- memory/north_star.md
- memory/company_north_star.md
- memory/company_stage.md
- memory/office_blueprint.md
- memory/handoff_contracts.md
- memory/work_state_rules.md
- memory/founder_inbox_contract.md
- memory/tool_permissions.md
- memory/memory_lifecycle.md (this file)

Rules:
- No agent may append or modify these files
- CEO increments version number on each update
- Prior versions are not preserved inline — use git history

---

### CATEGORY 4: EPHEMERAL / WORKING FILES
These files are working documents that are replaced or purged at defined intervals.

Files in this category:
- All files in reports/ subdirectories (weekly reports)
- memory/execution_states.md (current cycle state — not a log)

Rules for reports/:
- Keep the most recent 4 weekly reports per agent
- Reports older than 28 days are deleted or moved to an archive folder
- CEO brief reports (reports/ceo_brief/) are kept for 90 days then summarized

---

## MONTHLY COMPRESSION PROCESS

Trigger: First run of each calendar month
Performed by: Chief of Staff (propose compression summary — do not auto-delete)

Steps:
1. For each CATEGORY 1 append-only log:
   a. Identify all entries older than 90 days
   b. Write a 3-5 sentence summary of those entries
   c. Append the summary as: [COMPRESSED: YYYY-MM-DD through YYYY-MM-DD] [summary]
   d. Mark original entries as eligible for archiving (do not delete in same cycle)
   e. CEO reviews and confirms before entries are removed

2. For each CATEGORY 2 rolling state file:
   a. Move all entries marked [ARCHIVED: ...] older than 90 days to the end of the file under an ARCHIVE section
   b. Do not delete

3. Propose (do not execute) deletion of ephemeral reports older than 28 days
4. Include compression summary in the monthly CEO brief

---

## WHAT MUST NEVER BE DELETED

The following must never be deleted, even during compression:
- Any entry in memory/security_incident_log.md
- Any entry in memory/decision_log.md relating to a CEO decision
- Any escalation entry that was responded to by the CEO
- Any proof asset entry in memory/proof_assets.md (archive only, never delete)
- Any entry relating to a pilot (pilot agreements, outcomes, customer IDs)
- The most recent 2 versions of any static policy file (via git, not inline)

---

## ACTIVE vs ARCHIVE MEMORY

Active memory: Files in memory/ that agents read during normal runs.
Archive memory: The ARCHIVED sections within rolling state files, plus compressed log sections.
Agents read active memory only. Archive sections are for reference and audit.

---

## CONTEXT BLOAT PREVENTION

If a memory file exceeds 500 lines:
- Chief of Staff flags it in the CEO brief: "MEMORY FILE APPROACHING LIMIT: [filename]"
- Compression or archiving is proposed for CEO review
- No agent may continue appending to a file over 500 lines without explicit authorization

---

## MEMORY FILE CREATION

New memory files may only be created by:
- CEO (directly)
- Chief of Staff (with a CEO-approved proposed action entry)

Agents may not create new memory files autonomously.
