# handoff_contracts.md
# Clarion Agent Office — Inter-Division Handoff Contracts
# Version: 1.0 | 2026-03-12
# Agents may read. Agents may never modify.

---

## PURPOSE
Defines exactly when work passes from one agent or division to another.
A handoff that is not defined here does not happen automatically — it must be escalated.
Prevents dropped work, duplicate effort, and ambiguous ownership.

---

## HANDOFF 1: Lead Discovery -> Outbound Sales

trigger: Customer Discovery documents a named firm or contact with a qualifying signal (role match, pain signal, or engagement signal)
sender: Customer Discovery
receiver: Sales Development
payload_required:
  - Firm name and public URL
  - Signal type (pain, engagement, role match)
  - Source URL (must be public)
  - Suggested outreach angle (1-2 sentences)
  - Confidence: low | medium | high
escalation_threshold: Escalate to Chief of Staff if signal indicates an inbound inquiry or a prospect has already reached out to Clarion
when_NOT_to_hand_off:
  - Firm is already in leads_pipeline.csv with status active or contacted
  - Firm appears in memory/do_not_chase.md
  - Signal is anecdotal with no verifiable source URL
  - Lead was previously ghosted and no new signal exists

---

## HANDOFF 2: Outbound Sales -> Founder

trigger: A prospect requests a call, meeting, pricing information, or a pilot analysis
sender: Sales Development
receiver: CEO (founder) — routed via founder_escalation.md format
payload_required:
  - Firm name and contact identifier
  - Trigger type (call request | pricing | pilot request)
  - How the signal was identified (source)
  - Recommended next action (one sentence)
  - Urgency: High | Critical
escalation_threshold: Always escalate immediately — no threshold. This is a mandatory founder escalation per founder_escalation.md.
when_NOT_to_hand_off:
  - Do not escalate on general lead research completions with no inbound signal
  - Do not escalate on outreach drafts that are awaiting Level 2 approval only

---

## HANDOFF 3: Outbound Sales -> Pilot Workflow

trigger: A prospect has agreed to a pilot (CEO has confirmed in approved_actions.md or decision_log.md)
sender: Sales Development (or CEO decision)
receiver: Customer Health & Onboarding
payload_required:
  - Firm name and contact
  - Pilot terms agreed (scope, timeline)
  - Any ICP notes or context from the sales process
  - Link to conversation or lead record
escalation_threshold: If pilot terms were agreed verbally and not yet documented, stop and surface to Chief of Staff before proceeding
when_NOT_to_hand_off:
  - Pilot has not been explicitly confirmed by CEO
  - Prospect is still in evaluation phase

---

## HANDOFF 4: Pilot Workflow -> Proof Asset Extraction

trigger: A pilot analysis is complete and the firm has given positive feedback or a usable outcome signal
sender: Customer Health & Onboarding
receiver: Voice of Customer & Product Demand
payload_required:
  - Firm identifier (anonymized if not yet approved for named use)
  - Outcome summary (what the pilot found)
  - Positive signal type (testimonial, outcome stat, use case confirmation)
  - Permission status: named | anonymized | not yet asked
escalation_threshold: Escalate to CEO if firm wants to be named in case study or marketing material — do not proceed without approval
when_NOT_to_hand_off:
  - Pilot ended without clear outcome or was abandoned
  - Firm gave negative or neutral feedback only
  - No usable signal exists for proof asset creation

---

## HANDOFF 5: Conversion Friction -> Chief of Staff

trigger: Funnel Conversion identifies a friction pattern appearing 3+ times or blocking a conversion-ready prospect
sender: Funnel Conversion
receiver: Chief of Staff
payload_required:
  - Friction pattern description
  - Number of occurrences or affected leads
  - Estimated impact on conversion (qualitative)
  - Proposed fix (if agent has one)
  - Priority: Low | Medium | High
escalation_threshold: If friction is blocking an active inbound prospect, escalate immediately (High priority, same cycle)
when_NOT_to_hand_off:
  - Friction is a one-off edge case with no pattern
  - Pattern has already been documented and a fix is in progress

---

## HANDOFF 6: Product Feedback -> Product Insight

trigger: Voice of Customer surfaces a recurring product theme (3+ mentions) or a feature demand signal
sender: Voice of Customer & Product Demand
receiver: Product Usage Analyst
payload_required:
  - Feedback theme or demand signal
  - Number of mentions and source types
  - Anonymized customer quotes or paraphrases
  - Suggested product implication (optional)
escalation_threshold: Escalate to Chief of Staff if feedback touches scoring logic or phrase dictionary (SO-004)
when_NOT_to_hand_off:
  - Theme is a duplicate of a previously documented signal with no new evidence
  - Feedback is a single-instance outlier with no pattern

---

## HANDOFF 7: Site Health -> Chief of Staff

trigger: Internal process monitoring detects a customer-facing process failure or SLA compliance below 70%
sender: Internal Process Analyst
receiver: Chief of Staff
payload_required:
  - Issue description
  - Customer-facing impact (yes | no | unknown)
  - SLA metric affected
  - Estimated severity: Low | Medium | High
escalation_threshold: Any confirmed customer-facing failure escalates to Chief of Staff immediately, same cycle
when_NOT_to_hand_off:
  - Issue is internal-only and resolved within the same cycle
  - SLA compliance is above 70% with no trend worsening

---

## HANDOFF 8: Competitor Tracking -> Market Intelligence -> Chief of Staff

trigger: Competitive Intelligence detects a competitor move that (a) directly threatens an active pipeline deal, or (b) creates a positioning gap Clarion cannot currently address
sender: Competitive Intelligence
receiver: Chief of Staff (for routing to CEO if needed)
payload_required:
  - Competitor name
  - Move type (pricing | feature | messaging | partnership | press)
  - Threat level: Watch | Active | Critical
  - Clarion's current counter-position (if any)
  - Recommended response (propose only — do not act)
escalation_threshold: Critical threat level = immediate CEO brief inclusion. Active = include in next weekly brief. Watch = log only.
when_NOT_to_hand_off:
  - Competitor move is a minor content update or routine activity with no strategic impact
  - Signal has already been logged in competitor_tracking.md with no change in status

---

## HANDOFF 9: Product Experience / UX Findings -> Founder Review -> Implementation

trigger: Product Usage Analyst or Funnel Conversion identifies a UX friction point with a clear, bounded fix
sender: Product Usage Analyst or Funnel Conversion
receiver: Chief of Staff (for packaging) -> CEO (for review) -> Claude implementation prompt (if approved)
payload_required:
  - UX issue description (specific, not vague)
  - Affected user journey step
  - Proposed fix (concise)
  - Estimated effort: trivial | small | medium | large
  - Risk to existing behavior: none | low | medium | high
escalation_threshold: Any fix rated medium effort or higher, or touching backend scoring/auth/billing routes, must be CEO-approved before a Claude implementation prompt is drafted
when_NOT_to_hand_off:
  - Fix requires backend security control changes (frozen per AGENTS.md)
  - Proposed change alters scoring logic or phrase dictionary (SO-004)
  - Issue is already in active_projects.md

---

## HANDOFF FAILURE PROTOCOL
If a handoff payload is incomplete:
1. Receiving agent documents the gap in its report under HANDOFF FAILURES
2. Chief of Staff surfaces all handoff failures in the CEO brief
3. The work item is held — not dropped, not advanced with incomplete data
4. Sender agent must complete the payload on the next cycle
