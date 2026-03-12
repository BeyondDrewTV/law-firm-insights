# office_review_loop.md
# Clarion Agent Office — Monthly Self-Review Loop
# Version: 1.0 | 2026-03-12
# Cadence: Monthly (first run of each calendar month)
# Performed by: Chief of Staff
# Reviewed by: CEO

---

## PURPOSE
Evaluate whether the office is producing useful work — not just activity.
The review covers agent behavior, output quality, handoff integrity, escalation hygiene,
and whether the office's work is actually moving revenue, product, or operations.
Output is a short memo to the CEO with concrete process change proposals.

---

## REVIEW DIMENSIONS AND QUESTIONS

### 1. AGENT WAKE DISCIPLINE
Did agents run when they should and skip when they should?

Questions:
- Did all weekly-cadence agents file reports every cycle this month?
- Did any agent fire on a surface or topic outside its defined scope (office_blueprint.md)?
- Did any agent produce a report with no grounded input (NO REAL INPUT AVAILABLE or equivalent)?
- Did monthly-cadence agents run only once this month?

Failure indicators:
- An agent filed more reports than its defined cadence
- An agent's report covered work assigned to a different agent
- More than one agent filed a report with zero real input in the same cycle


### 2. DUPLICATE WORK PREVENTION
Did agents avoid re-doing work already done?

Questions:
- Were any leads added to leads_pipeline.csv that already existed?
- Were any competitor signals logged in competitor_tracking.md that were duplicates of prior entries?
- Did any agent propose an action already tracked in execution_history.md or projects.md?
- Were any proof assets duplicated in proof_assets.md?

Failure indicators:
- Chief of Staff flagged a deduplication failure in any cycle this month
- The same proposed action appeared in 3+ consecutive weekly reports without decision
- The same competitor signal was logged twice within a 60-day window

---

### 3. AUTHORITY COMPLIANCE
Did agents stay within their defined authority?

Questions:
- Did any agent describe real-world execution without a matching approved_actions.md entry?
- Did any agent propose a Level 3 action (send, post, publish, commit, deploy) and attempt to execute it autonomously?
- Did any agent modify a static policy file (standing_orders.md, agent_authority.md, etc.)?
- Did any agent contact an external party or submit a form?

Failure indicators:
- A STANDING ORDER CONFLICT was filed in any weekly CEO brief this month for an authority violation
- An agent claimed to have executed an external action without an approved entry
- Any entry added to a read-only file by an agent

---

### 4. CONCRETE ARTIFACT PRODUCTION
Did agents produce real deliverables, not just summaries of nothing?

Questions:
- Did Sales Development produce at least one new qualified lead or outreach angle this month?
- Did Customer Discovery produce at least one new documented discovery signal with a source URL?
- Did Competitive Intelligence produce at least one updated competitor entry?
- Did Content & SEO produce at least one content draft or topic outline?
- Did Product Experience produce at least one logged finding in product_experience_log.md?
- Did any agent file 3+ consecutive reports with no concrete artifact produced?

Failure indicators:
- An agent filed reports all month but added nothing to any memory file or data file
- Report content was narrative-only with no structured output produced
- Proposed actions count exceeded executed or advanced work by 5:1 ratio


### 5. HANDOFF INTEGRITY
Did work move between divisions correctly per handoff_contracts.md?

Questions:
- Were any handoff payloads incomplete this month? (check Chief of Staff HANDOFF FAILURES sections)
- Did Customer Discovery hand qualified leads to Sales Development with source URLs?
- Did pilots that completed route to Voice of Customer for proof extraction?
- Did HIGH-severity conversion friction reach Chief of Staff within the same cycle it was logged?
- Did Product Experience HIGH findings reach the CEO brief when conversion-blocking?

Failure indicators:
- A handoff payload was incomplete in 2+ consecutive cycles
- A pilot completed but no proof extraction handoff was initiated
- A HIGH friction finding sat in conversion_friction.md for 2+ cycles without surfacing

---

### 6. FOUNDER ESCALATION QUALITY
Did the CEO brief stay clean and useful?

Questions:
- Did any BUCKET 4 item (raw research, unformatted log, zero decision ask) appear in the CEO brief?
- Did any escalation appear without the required format: why it matters / recommended action / urgency / decision needed / office recommendation?
- Did any real BUCKET 1 escalation get suppressed or buried in a summary section?
- Were duplicate escalations filed for the same open item in the same cycle?
- Did the CEO brief average more than 5 EXCEPTIONS REQUIRING CEO ATTENTION per cycle this month? (signal of over-escalation)

Failure indicators:
- A raw research dump reached the CEO brief
- A prospect call request or pilot inquiry was not escalated as URGENT_NOW
- Escalation count in CEO brief trended upward without a matching increase in real events

---

### 7. COMMERCIAL USEFULNESS
Did the office's work actually help revenue, product, or operations?

Questions:
- Did any Sales Development output lead to an approved outreach attempt or a pilot conversation?
- Did any Customer Discovery output produce a lead that entered the pipeline?
- Did any Product Experience finding produce an approved_for_claude implementation?
- Did any Product Insight output influence a product or positioning decision?
- Did any Competitive Intelligence finding change how Clarion positioned against a competitor?
- Did any Funnel Conversion finding produce a resolved friction pattern?

Failure indicators:
- All Sales output stayed internal for the full month with no downstream usage
- Product feedback themes recurred in 3+ cycles with no product routing or decision
- Office produced 20+ proposed actions this month with 0 CEO approvals (proposal backlog is growing, not clearing)


---

## ACTION RULES (what to do when repeated issues appear)

These rules are deterministic. When a failure indicator is confirmed, the action applies automatically.

| Failure pattern | Threshold | Action |
|---|---|---|
| Agent files report with no real input | 3 consecutive cycles | Chief of Staff flags agent as LOW ACTIVITY in office health log; propose deactivating that agent's run until real input is available |
| Duplicate lead or signal added | 2 occurrences in a month | Chief of Staff proposes a targeted rule addition to work_state_rules.md |
| Authority violation (agent exceeded scope) | 1 occurrence | Appear in STANDING ORDER CONFLICTS; CEO decides whether agent_authority.md needs tightening |
| Handoff payload incomplete | 2 consecutive cycles for same handoff | Chief of Staff proposes a fix to handoff_contracts.md; surface to CEO as process risk |
| Proposed action loops (3+ cycles, no decision) | 3 cycles | Agent stops re-proposing; Chief of Staff flags as PENDING DECISION — BLOCKED in CEO brief |
| CEO brief over-escalation | 5+ EXCEPTIONS in 3+ cycles | Chief of Staff reviews escalation classification; proposes tightening founder_inbox_contract.md |
| Agent produces no artifact for full month | 1 full month | Chief of Staff proposes scope review for that agent; surface in monthly memo |
| Commercial usefulness failure | Office-wide, 0 CEO approvals in 30 days | Chief of Staff surfaces in monthly memo as PROPOSAL BACKLOG GROWING — escalate to CEO |

---

## MONTHLY REVIEW MEMO FORMAT

Chief of Staff writes this memo at the start of each month and includes it in the first CEO brief of the month.

```
MONTHLY OFFICE SELF-REVIEW
Period: [YYYY-MM-DD] through [YYYY-MM-DD]
Filed by: Chief of Staff
---

OVERALL ASSESSMENT: [Healthy | Watch | Needs Attention]

DIMENSION RESULTS
  1. Agent Wake Discipline:       [Pass | Watch | Fail] — [one sentence]
  2. Duplicate Work Prevention:   [Pass | Watch | Fail] — [one sentence]
  3. Authority Compliance:        [Pass | Watch | Fail] — [one sentence]
  4. Artifact Production:         [Pass | Watch | Fail] — [one sentence]
  5. Handoff Integrity:           [Pass | Watch | Fail] — [one sentence]
  6. Escalation Quality:          [Pass | Watch | Fail] — [one sentence]
  7. Commercial Usefulness:       [Pass | Watch | Fail] — [one sentence]

ISSUES FOUND (any Fail or Watch)
  [None. | For each issue:
    Dimension: [N]
    Issue: [One sentence — specific, factual]
    Failure indicator met: [Quote the indicator from this file]
    Action rule applied: [Quote the action from the table above, or "No rule — proposing one"]
    Proposed change: [Specific file and rule to update, or process change to make]
    ---]

PATTERNS ACROSS MULTIPLE DIMENSIONS
  [None. | One paragraph if 2+ dimensions show the same underlying cause]

PROPOSED PROCESS CHANGES
  [None. | Verbatim change proposals for CEO approval, one per block:
    File: [memory/filename.md]
    Change: [Specific addition, deletion, or update — non-ambiguous]
    Reason: [One sentence]
    ---]

CEO DECISIONS NEEDED
  [None. | For each proposed change requiring CEO approval:
    Decision: [Yes/no question]
    Recommendation: [What the office recommends]
    ---]
```

---

## REVIEW LOG
# Append one line per monthly review completed.
# Format: [YYYY-MM-DD] | OVERALL: [Healthy | Watch | Needs Attention] | ISSUES: [N] | CHANGES PROPOSED: [N]

[2026-03-12] | REVIEW LOOP INITIALIZED | No review data yet. First review due start of April 2026.
