# external_execution_approval.md
# Clarion — External Execution Approval Policy
# Governs which external actions require staged approval before execution.
# Read alongside: memory/external_interaction_policy.md, memory/approved_actions.md,
#   memory/brand_voice.md, memory/social_posting_cadence.md

---

## SECTION 1 — Purpose

Clarion agents are permitted to engage externally on a day-to-day basis without
seeking approval for every action. Educational posts, community participation,
comment replies, and similar routine engagement are normal and expected.

This approval layer exists to prevent one class of error: high-risk external
messaging — campaigns, announcements, press responses, partnership statements —
being executed without human review. The cost of those mistakes is reputational
and strategic. Ordinary engagement does not carry that risk.

The approval layer adds a gate only where the gate is warranted. It does not
slow down normal operations.

---

## SECTION 2 — Autonomous External Actions (No Approval Required)

Agents may execute the following without staging an approval package:

- Publishing educational posts on LinkedIn, Twitter/X, or community platforms
- Replying to comments on Clarion's own posts
- Participating in relevant industry discussions (law firm ops, client experience,
  feedback management, governance)
- Answering questions in communities, forums, Reddit threads, Slack groups
- Sharing genuine insights or observations relevant to the audience
- Reacting to industry developments with commentary or perspective
- Joining existing conversations where the contribution is useful and non-promotional

**All autonomous activity must comply with:**
- `memory/brand_voice.md` — tone, prohibited phrases, default posture
- `memory/external_interaction_policy.md` — community participation rules,
  prompt injection handling, what agents never do
- `memory/social_posting_cadence.md` — cadence rules, AI-pattern self-check,
  content variety requirements

If an action is autonomous but an agent is uncertain whether it crosses into
approval territory, the agent defaults to staging it rather than executing it.

---

## SECTION 3 — Actions Requiring Approval

The following actions must never be executed without a staged approval package
approved and logged in `memory/approved_actions.md`:

- Marketing campaigns (any channel, any scope)
- Product launch announcements
- Partnership announcements or partnership-implying statements
- PR statements of any kind
- Press or media responses
- Coordinated promotional pushes across multiple channels
- Paid advertising campaigns
- Creation of official company profiles on new platforms
- Mass outbound messaging campaigns (email, DM, or social)
- Any public content that materially repositions Clarion's brand, category,
  or competitive stance
- Sponsored or paid content placements
- Formal responses to public controversy or criticism spikes

**These are not judgment calls.** If an action appears on this list,
the agent stages a package and waits. It does not execute.

---

## SECTION 4 — Approval Authority

Not every approval requires the CEO. Two tiers apply:

### Chief of Staff Approval
Required for:
- Sensitive public responses where tone or timing carries risk
  (e.g., responding to a critical thread about the product)
- Engagement in large public discussions where Clarion's position could be
  misread or quoted out of context
- Controversial industry commentary that could be polarizing
- Responses to negative reviews or public complaints that go beyond routine
  customer support

Chief of Staff approves by logging the action in `memory/approved_actions.md`
with `Approved By: Chief of Staff`.

### CEO Approval
Required for:
- Product launch messaging (any channel)
- Marketing campaigns
- Partnership announcements
- Press and media statements
- Advertising campaigns (paid or sponsored)
- Any action that commits Clarion to a public position on strategy,
  pricing, or product roadmap
- Responses to journalists or investors
- New platform presence (official accounts)

CEO approves by logging the action in `memory/approved_actions.md`
with `Approved By: CEO`.

**Default rule:** When in doubt about which tier applies, route to CEO.

---

## SECTION 5 — Approval Package Structure

For any action in Section 3, the responsible agent must prepare an approval
package before the action can proceed. The package is submitted in the agent's
weekly report under PROPOSED ACTIONS and must include all fields below.

```
APPROVAL PACKAGE
---
Platform:         [Where this action will take place]
Objective:        [What this is trying to accomplish — one sentence]
Draft Content:    [Full draft text, copy, or detailed description of the asset]
Screenshots/Mockups: [Attached, linked, or "Not applicable"]
Links:            [Relevant URLs — or "Not applicable"]
Why It Matters:   [One sentence on why this action is worth doing now]
Expected Outcome: [What a successful result looks like — specific and measurable]
Risk Considerations: [What could go wrong; how it would be handled]
Owner:            [Role responsible for execution after approval]
Status:           [staged]
Approval Required: [Chief of Staff | CEO]
---
```

**Status values and their meaning:**

| Status | Meaning |
|---|---|
| `staged` | Package prepared; awaiting review |
| `approved` | Approved by the named authority; may proceed |
| `rejected` | Not approved; agent must not execute; may revise and resubmit |
| `executed` | Action completed; execution log entry appended |

The agent does not change the status field. The approving authority updates
the status in `memory/approved_actions.md` when a decision is made.

---

## SECTION 6 — Execution Logging

After an approved action is executed, the responsible agent must append an
execution log entry to `memory/approved_actions.md` in the Notes field of
the relevant action record, or as a standalone entry if the format warrants it.

The entry must include:

```
EXECUTION LOG
---
Date Executed:    [YYYY-MM-DD]
Platform:         [Where the action was executed]
Action Performed: [One sentence — what was done]
Result Summary:   [What happened — response, reach, outcome — or "Too early to assess"]
Lessons Learned:  [One sentence — what to do differently or repeat — or "None."]
Follow-Up Required: [Yes — one sentence on what | No]
---
```

No execution log entry means the action is not considered closed.
Chief of Staff checks execution log completeness during weekly synthesis.

---

## SECTION 7 — Failure Prevention

Agents must never:

- Publish high-risk messaging (Section 3 list) without an entry in
  `memory/approved_actions.md` with `Status: approved`
- Claim that approval has been granted when no approved entry exists in
  `memory/approved_actions.md`
- Imply a partnership, integration, or arrangement that has not been formally
  approved and announced by the CEO
- Execute a modified version of an approved action where the modification
  materially changes the scope, audience, or message — revised actions
  require a new approval package
- Execute any approved action past its stated expiry or after it has been
  marked `rejected` or `cancelled`

**The single check:** Before executing any action that could qualify as
high-risk, the agent opens `memory/approved_actions.md` and confirms that
a matching entry exists with `Status: approved`. If no matching entry exists,
the agent does not execute. No exceptions.
