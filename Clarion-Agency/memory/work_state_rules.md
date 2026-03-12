# work_state_rules.md
# Clarion Agent Office — Work State Rules
# Version: 1.0 | 2026-03-12
# Agents may read. Agents may never modify.

---

## PURPOSE
Deterministic rules to prevent duplicate work, stale work, re-opened closed work, and infinite loops.
When in doubt, do not proceed. Surface the ambiguity to Chief of Staff.

---

## RULE 1: LEAD DEDUPE

Before adding any lead to leads_pipeline.csv or lead_research_queue.csv:
1. Check if firm name or domain already exists in leads_pipeline.csv (any status)
2. Check if firm appears in memory/do_not_chase.md
3. If either match exists → DO NOT add. Log "duplicate suppressed" in your report.
4. If no match → proceed with add.

Tie-breaking rule: The most recent entry wins. Do not create a second row for an existing firm.
Agent responsible for enforcement: Sales Development (on write), Customer Discovery (on research queue)

---

## RULE 2: OUTREACH COOLDOWNS

A lead may not receive a new outreach angle draft within 14 days of the previous one.
Check the leads_pipeline.csv last_contacted field before drafting.
If last_contacted is within 14 days → hold. Log "cooldown active" in report.
Cooldown resets only when a new inbound signal is detected from that firm.

Exception: CEO-approved urgent escalation overrides cooldown. Requires approved_actions entry.

---

## RULE 3: GHOSTED LEAD SHUTDOWN

A lead is classified as GHOSTED when:
- Outreach angle was drafted and approved
- No response or signal for 30 days after last outreach draft

On GHOSTED classification:
- Update status to ghosted in leads_pipeline.csv
- Move to do_not_chase.md if 2+ outreach cycles with no response
- Do not draft new outreach for this lead without a new inbound signal
- New signal requirement: documented public engagement, inbound inquiry, or referral mention

---

## RULE 4: STALE ACTIVE PROJECT SHUTDOWN

A project in memory/active_projects.md or memory/projects.md is STALE when:
- Status is "active" or "in_progress"
- No update has been written to it in 21 days
- No agent has referenced it in 2 consecutive weekly runs

On STALE detection:
- Agent detecting the stale state flags it in report under STALE PROJECTS
- Chief of Staff surfaces it in the CEO brief
- CEO must explicitly reactivate or close it
- Agents do NOT auto-close active projects

---

## RULE 5: DUPLICATE INCIDENT PREVENTION

Before logging a new entry to memory/incidents_log.md or data/incidents/:
1. Check the last 30 days of incidents for the same system/symptom
2. If a matching open incident exists → append to existing, do not create new
3. If the matching incident is closed → create new with reference to prior incident ID
4. Never log duplicate incidents for the same event in the same cycle

---

## RULE 6: PROOF ASSET DEDUPE

Before adding a new entry to memory/proof_assets.md:
1. Check existing entries for same firm and same outcome type
2. If duplicate exists → update the existing entry, do not add a new row
3. If the new signal adds meaningfully new information → append as "Additional signal [date]" under the existing entry
4. Named vs. anonymized entries are distinct — a named entry does not replace an anonymized one without CEO approval

---

## RULE 7: REPEATED COMPETITOR SIGNAL HANDLING

Before logging a competitor signal to memory/competitor_tracking.md:
1. Check the last 60 days of entries for the same competitor and same move type
2. If the same signal has already been logged → do not log again
3. If the signal represents a meaningful development (e.g., price change confirmed, new feature launched) → update existing entry with date and new detail
4. Threat level may be escalated (Watch -> Active -> Critical) but never downgraded autonomously

---

## RULE 8: DO NOT REOPEN WITHOUT NEW SIGNAL

This rule applies to: ghosted leads, closed incidents, archived projects, resolved friction patterns, and completed pilots.

A closed item may only be reopened when:
- A new, documented, external signal exists (not an agent inference)
- The signal is different in kind from those that existed when the item was closed
- The reopening is logged with the new signal and date

Agents may propose reopening. Only Chief of Staff or CEO may authorize it.
Autonomous reopening is prohibited.

---

## RULE 9: AGENT LOOP PREVENTION

If the same proposed action has appeared in 3 consecutive weekly reports without CEO decision:
- Agent stops re-proposing it
- Chief of Staff flags it in the CEO brief as "Pending Decision — Action Blocked Pending Review"
- Item is not dropped — it is held pending explicit CEO resolution

Agents do not infer that silence equals approval. Silence equals hold.

---

## ENFORCEMENT
Chief of Staff reviews the weekly run for work state violations.
Violations are surfaced in the CEO brief under OFFICE DISCIPLINE FLAGS.
Repeat violations by the same agent trigger a process review note.
