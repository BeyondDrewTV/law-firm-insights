# comms_protocol.md
# Clarion — Agent Communication Protocol
# Version: 1.0 | All agents must follow this protocol without exception.

---

## Principle

Agents do not communicate with each other. Every agent writes to a report file. The Chief of Staff reads all reports. Nothing else crosses agent boundaries.

---

## 1. Standard Report Structure

Every agent report must follow this exact structure. No additional sections permitted.

```
AGENT:        [Agent name]
DATE:         [YYYY-MM-DD]
CADENCE:      [Daily | Weekly | Monthly | Event-Driven]
STATUS:       [NORMAL | WATCH | ESCALATE]

SUMMARY
One to three sentences. What happened this period. No padding.

FINDINGS
- Finding one
- Finding two
- Finding three (maximum five findings)

RECOMMENDATIONS
- Recommendation one (proposed action, human decides)
- Recommendation two (maximum three recommendations)

ESCALATIONS
None. | [Issue — Reason — Urgency: High / Critical]

INPUTS USED
[List data sources or files the agent analyzed]

TOKENS USED
[Approximate token count for this run]
```

All fields are mandatory. If a field has nothing to report, write "None."

The LEARNING PROPOSAL block is optional. Include it only when you have a specific, evidence-backed proposal to improve a memory file or operating rule. Omit it entirely if you have nothing to propose.

```
LEARNING PROPOSAL          (omit this block if nothing to propose)
Target file: [memory/filename.md | comms_protocol.md | agent_prompt_template.md]
Proposal: [One paragraph. What should change, and exactly what the new text should say.]
Evidence: [The specific finding, data point, or repeated pattern from this run that supports the proposal.]
Urgency: [Low | Medium] — Learning proposals are never urgent. If something is urgent, it is an escalation.
```

A single report may include at most one LEARNING PROPOSAL block. If you have multiple proposals, pick the highest-value one. The rest are discarded.

---

## 2. Escalation Conditions

An agent sets STATUS to **WATCH** when:
- A metric is trending in the wrong direction but has not crossed a threshold.
- An anomaly is detected that needs monitoring but not immediate action.

An agent sets STATUS to **ESCALATE** when:
- A finding could affect a client, a partner, or a production system.
- A compliance or reputational risk is identified.
- A recommendation requires a decision within 48 hours.
- The agent lacks sufficient information to assess a situation safely.

**Escalations are flagged in the report only.** Agents do not trigger alerts, send messages, or contact anyone directly.

---

## 3. Learning Proposal Rules

Agents may observe patterns over time that suggest improvements to how the office operates. The LEARNING PROPOSAL mechanism gives agents a sanctioned path to surface those observations without acting on them.

**An agent may propose a change to:**
- `memory/product_truth.md` — factual corrections or additions about what Clarion does
- `memory/brand_canon.md` — tone or positioning adjustments
- `memory/customer_insights.md` — ICP refinements based on repeated findings
- `memory/office_policies.md` — operating rule changes
- `comms_protocol.md` — report format or communication rule changes
- `agent_prompt_template.md` — template improvements

**An agent may never propose a change to:**
- `memory/calibration_log.md` — this is owned by the Dictionary Calibration Analyst only
- `memory/office_learning_log.md` — this is the CEO's ledger; agents do not write to it
- Any production codebase, scoring logic, or database
- Another agent's prompt file directly

**Quality bar for proposals:**
- Grounded in a specific finding from the current run, not general opinion.
- States the exact proposed change — not just "this could be better."
- Urgency is always Low or Medium. A proposal that feels urgent is probably an escalation instead.

---

## 4. Weekly Reporting Pipeline

```
Monday - Friday
  Each agent runs on its assigned cadence.
  Each agent writes its report to: /reports/[agent_name]/[YYYY-MM-DD].md

Saturday
  Chief of Staff reads all reports filed in the past 7 days.
  Chief of Staff produces: /reports/ceo_brief/[YYYY-MM-DD].md

Sunday
  CEO brief is reviewed by a human operator before any action is taken.
  No agent acts on the brief. Humans action it.
```

Report retention: Keep the last 90 days. Archive older files. Do not delete.

---

## 5. Cost Control Rules

- Every agent prompt includes only: its system role, relevant grounding files, and current input data.
- Do not pass prior report history into a prompt unless the task explicitly requires trend analysis.
- Grounding files are injected by summary, not full text, unless the agent produces external content.

| Agent Type | Target Input Tokens | Max Output Tokens |
|---|---|---|
| Department agent | <= 1,500 | <= 600 |
| Chief of Staff | <= 4,000 | <= 1,000 |

- Use the cheapest model that can reliably complete the task.
- Reserve frontier models for Chief of Staff synthesis and escalation review only.
- If an agent run exceeds its token budget by more than 20%, log it. Do not auto-retry.
