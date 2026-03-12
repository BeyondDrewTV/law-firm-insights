# founder_inbox_contract.md
# Clarion — Founder Inbox Contract
# Version: 1.0 | 2026-03-12
# Agents may read. Agents may never modify.

---

## PURPOSE
Protect founder attention. Every item that reaches the CEO brief must earn its place.
Raw research never reaches the founder. Unstructured status updates do not reach the founder.
Every item sent requires synthesis, a recommendation, and a clear decision ask.

---

## THE FOUR BUCKETS

### BUCKET 1: URGENT_NOW
Items that require a founder response within 24 hours.
Routed via EXCEPTIONS REQUIRING CEO ATTENTION at the top of the CEO brief.

Qualifies as URGENT_NOW:
- A prospect requests a call, meeting, pricing, or pilot
- A completed pilot brief is ready for founder review
- A legal, security, or compliance signal has been detected
- A determinism violation or data integrity failure is confirmed
- A journalist, investor, or strategic partner has reached out
- A high-value account (top 20% ARR) has moved to red-flag status

### BUCKET 2: REVIEW_WITHIN_24H
Items that require founder attention this week but not immediately.
Surfaced in the CEO brief under DECISIONS REQUIRED.

Qualifies as REVIEW_WITHIN_24H:
- A proposed action is staged and awaiting CEO approval
- A cross-department conflict has been detected and cannot be resolved without strategic direction
- A competitor move at threat level Active or Critical
- A pricing, positioning, or ICP boundary question has been raised
- An experiment proposal requires CEO sign-off before execution

### BUCKET 3: WEEKLY_DIGEST_ONLY
Items the founder should be aware of but do not require a decision.
Surfaced in the CEO brief body under standard division summaries.

Qualifies as WEEKLY_DIGEST_ONLY:
- Pipeline status updates with no inbound signal
- Content drafts ready for review (not requiring immediate decision)
- Product usage trends (no crisis)
- Lead research completions
- Competitor signals at threat level Watch
- Office health summary (normal range)
- Proof asset additions
- Onboarding milestone updates

### BUCKET 4: NEVER_SEND_DIRECTLY
Items that are never surfaced to the founder as raw output.
These must be synthesized, archived, or dropped before reaching the CEO brief.

Never send:
- Raw research dumps without a synthesis layer
- Unformatted competitor tracking logs
- Individual agent tool call outputs or raw data files
- Duplicate escalations for the same open item (carry forward the original, do not re-escalate)
- Internal agent-to-agent status messages
- Items with no decision ask and no recommended action

---

## REQUIRED FORMAT FOR EVERY ITEM SENT TO FOUNDER

Every item surfaced to the founder — in any bucket — must include:

WHY IT MATTERS: [One sentence. Impact on Clarion's goals.]
RECOMMENDED ACTION: [One sentence. What the office recommends doing.]
URGENCY: [URGENT_NOW | REVIEW_WITHIN_24H | WEEKLY_DIGEST_ONLY]
DECISION NEEDED: [Specific yes/no or choice question the CEO must answer. If no decision needed, state "Awareness only."]
OFFICE RECOMMENDATION: [What the office will do next pending CEO input, or what it has already done.]

---

## HARD RULES

1. Never send raw research to the founder. Always synthesize first.
2. Never escalate the same open item twice in the same cycle. Carry it forward from the prior brief.
3. Never route a BUCKET 4 item to the founder brief under any framing.
4. Never suppress a BUCKET 1 item. If it qualifies, it appears — regardless of how clean the brief looks.
5. Chief of Staff is the final gatekeeper on bucket classification. If uncertain, escalate to BUCKET 2 rather than BUCKET 3.

---

## MAINTENANCE
This contract is reviewed by CEO quarterly or when escalation patterns suggest it needs updating.
Chief of Staff flags misrouted items in the office health log.
