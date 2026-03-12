# postmortem_template.md
# Clarion Agent Office — Postmortem Template
# Version: 1.0 | 2026-03-12
# Agents may read. Agents may never modify.

---

## PURPOSE
Lightweight, consistent review process for misses and failures.
A postmortem is not blame. It is a process update.
The output of every postmortem is a concrete rule change or decision, not a reflection.

---

## WHEN TO FILE A POSTMORTEM

File when any of the following occur:
- A pilot was lost or abandoned
- An opportunity (inbound or pipeline lead) was missed or allowed to go cold
- An outreach pattern produced no engagement after 3+ attempts
- A site or process incident caused a confirmed customer-facing impact
- A product confusion event is detected (customer misunderstood core functionality)
- An agent looped, duplicated work, or violated a work state rule
- A founder escalation was missed or mis-routed

Do NOT file a postmortem for:
- Routine ghosted leads (handled by work_state_rules.md)
- Normal competitor signals with no action required
- Standard office health fluctuations within WATCH range

---

## WHO FILES

- The division closest to the event is responsible for filing
- Chief of Staff files if the failure is cross-division or systemic
- CEO files if a strategic miss requires direct documentation

---

## POSTMORTEM FORMAT

Copy this template for each postmortem. File in memory/decision_log.md under a POSTMORTEM entry,
or as a named file in reports/ if the postmortem is extensive.

---

## POSTMORTEM: [TITLE]

DATE FILED: [YYYY-MM-DD]
FILED BY: [Agent name or CEO]
RELATED DIVISION(S): [Division(s) involved]

---

### WHAT HAPPENED
[2-4 sentences. Factual description of the event. No interpretation yet.]

---

### IMPACT
[What was the consequence? Lost revenue opportunity, customer trust damage, wasted cycles, data gap?
Be specific. If unmeasurable, say so.]

---

### ROOT CAUSE
[One primary root cause. If multiple, list in order of significance. Be honest.
Common root causes: missing rule, agent exceeded authority, handoff payload incomplete,
work state rule not enforced, signal was detected but not routed, duplicate action executed.]

---

### WHAT SIGNAL WAS MISSED
[What was visible that should have triggered a different action?
Where did the office have the information but not act on it?]

---

### PROCESS CHANGES NOW APPLY
[Specific, concrete changes. Reference the file and rule being updated.
If a new rule is being added, state the rule exactly.
If an existing rule is being tightened, state the before and after.
Do not write vague improvements. Write rules.]

Example format:
- CHANGE: memory/work_state_rules.md RULE 3 — Added: "...and has not responded to a follow-up within 7 days"
- CHANGE: handoff_contracts.md HANDOFF 2 — Added escalation condition: "If lead was identified via inbound community post"
- NEW RULE: Sales Development must confirm do_not_chase status before drafting any outreach for a lead older than 60 days

---

### OWNER
[Who is responsible for implementing the process change?]
[CEO | Chief of Staff | Division Lead]

---

### FOLLOW-UP DATE
[YYYY-MM-DD — When does Chief of Staff verify the process change has been applied?]

---

## POSTMORTEM LOG
# Append completed postmortem summaries below as they are filed.
# Format: [YYYY-MM-DD] | [TITLE] | [ROOT CAUSE — one phrase] | [PROCESS CHANGE — one phrase]

[2026-03-12] | POSTMORTEM TEMPLATE INITIALIZED | n/a | n/a
