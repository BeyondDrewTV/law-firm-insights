# approved_actions.md
# Clarion — CEO Approved Actions Register
# Version: 1.0

---

## Purpose

This file is the single source of truth for actions agents are authorized to execute.

Agents may propose actions in their reports. Agents may NEVER execute any real-world
action — including outreach, publishing, website edits, marketing campaigns, account
creation, or any external communication — unless that specific action appears in this
file with Status: Approved.

The CEO approves all entries. No agent, workflow, or automated process may add,
modify, or remove entries from this file.

---

## How to Add an Approved Action

1. CEO reviews the PROPOSED ACTIONS section of the CEO brief.
2. CEO decides which actions to approve.
3. CEO (or authorized operator) adds the entry to this file using the format below.
4. Agents check this file at the start of each run. If their proposed action is listed
   here as Approved, they may execute it. Otherwise, they propose only.

---

## Approved Actions

_No actions approved yet. This register is empty at system initialization._

_When the CEO approves an action from the weekly brief, add it here using the format below._

---

## Format

Each action block is delimited by `---` on its own line.
The runner reads Status: approved and executes automatically on next run.

```
---
Action ID:   ACT-[NNN]
Action:      [What is approved — one sentence, specific and unambiguous]
Approved By: [CEO | Chief of Staff]
Date:        [YYYY-MM-DD]
Owner:       [Content & SEO Agent | Competitive Intelligence | Usage Analyst | Chief of Staff | Customer Discovery]
Status:      [staged | approved | in_progress | completed | blocked]
Notes:       [Optional — constraints, context, or execution output path]
---
```

Status definitions:
- `staged`      — package prepared by agent; awaiting CEO review
- `approved`    — approved; runner will execute next cycle
- `in_progress` — execution underway this run
- `completed`   — executed; execution_log.md entry appended
- `blocked`     — execution failed or action type not permitted autonomously

Owner must match exactly one of the routed values above.
Blocked execution types (never auto-executed): post, publish, send, create account, sign up, register, email, tweet, submit.

Approval authority:
- Chief of Staff may approve: sensitive public responses, large product discussion
  engagement, controversial industry commentary
- CEO must approve: product launch messaging, marketing campaigns, partnerships,
  press/media statements, advertising campaigns, new platform profiles
- See `memory/external_execution_approval.md` for the full approval tier definition

---

## Completed and Archived Actions

_Actions moved here once Status = Completed or Cancelled._

_(none)_
