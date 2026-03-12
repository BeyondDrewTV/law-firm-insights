# randomization_policy.md
# Clarion Agent Office — Randomization Policy
# Version: 1.0 | 2026-03-12
#
# PURPOSE
# Define bounded randomness rules for agent-proposed timing and scheduling.
# Randomness must feel human, remain strategic, and never produce constant activity.
#
# SCOPE
# This file governs how agents propose timing for actions that, if executed on
# exact schedules, would appear automated. It does NOT govern when agents themselves
# run (that is governed by run_policy.md). It governs the timing embedded in
# PROPOSED ACTIONS that agents write into their reports and approved_actions.md.
#
# ENFORCEMENT
# Agents self-enforce these rules when producing proposed action timing.
# Chief of Staff enforces by flagging robotic timing patterns in the CEO brief.
# See also: memory/social_posting_cadence.md for social-specific rules.

---

## Core Randomness Principles

1. **Bounded, not free.** Randomness must operate within a defined window.
   An action proposed for "Tuesday morning" should land anywhere in a 2-hour window —
   not at 9:00:00 AM on the dot every single Tuesday.

2. **Strategic, not random.** Timing must still make sense for the audience.
   A follow-up email to a law firm principal is not randomly scheduled at 11 PM.
   Randomness operates within the appropriate engagement window.

3. **Variability over consistency.** Patterns that emerge (same day, same time,
   same frequency) are the signal that something has gone robotic.
   Deliberately vary days, times, and intervals — even when this means skipping.

4. **Skip days are features, not failures.** An outreach sequence that skips
   Wednesday occasionally is more credible than one that fires every Wednesday
   like clockwork. Build skip probability into every cadence.

5. **Agents propose timing. Humans approve and execute.**
   Agents do not execute time-sensitive actions autonomously.
   Timing randomization applies to the proposed schedule an agent includes
   in its report — not to autonomous execution.

---

## Randomization Rules by Activity Type

---

### SOCIAL ENGAGEMENT TIMING

**Context:** LinkedIn posts, Twitter/X posts, community participation

**Base rule from social_posting_cadence.md:**
- LinkedIn: 2–4 posts per week. Do not post same time every day. Skip days intentionally.
- Twitter/X: 3–6 posts per week. Vary days and times. Replies and retweets count.

**Randomization layer (agent applies when proposing a content schedule):**

When proposing a weekly social content batch, agents must:
- Distribute proposed times across a ±90-minute window from the target time
  (e.g., target 9:00 AM → propose anywhere from 8:00–10:30 AM)
- Vary proposed days — do not repeat the same day pattern two weeks in a row
- Build in at least one skip day per platform per week (a day with no proposed content)
- Vary post length: batch must not be uniformly short or uniformly long
- Vary post format: no two consecutive posts in a batch should share the same structure

**Skip probability:**
- LinkedIn: 20% chance of skipping any given proposed posting day (1 in 5 days)
- Twitter/X: 15% chance of skipping any given proposed posting day
- Community: 30% chance of skipping any given participation opportunity

**Implementation note:**
Agents do not use a random number generator. Agents apply these skip rules
by reviewing the proposed batch and manually removing or deprioritizing lower-quality
content until the batch feels natural and varied. The skip probability is a
behavioral guideline, not a computed value.

---

### OUTREACH FOLLOW-UP TIMING

**Context:** Follow-up sequences for discovery leads, pilot prospects, and inbound replies

**Base rule:** Follow-ups must not land on exact-day intervals.
A "3-day follow-up" should be proposed as day 2–4, not day 3 precisely.

**Timing windows by sequence step:**

| Sequence Step | Target Window | Acceptable Variation |
|---|---|---|
| Initial outreach | Based on engagement signal | None — timing is based on signal, not schedule |
| First follow-up | 3–5 business days after initial | ±1 day from midpoint |
| Second follow-up | 7–10 business days after first | ±2 days from midpoint |
| Final follow-up | 14–21 business days after second | ±3 days from midpoint |
| Post-pilot check-in | 5–7 business days after pilot close | ±1 day from midpoint |

**Day-of-week rules:**
- Never propose a follow-up for Monday (lands in crowded inbox after weekend)
- Prefer Tuesday–Thursday for initial outreach
- Friday follow-ups are acceptable for second or third step — not initial contact
- Do not propose follow-ups on federal holidays

**Time-of-day rules (all Central Time):**
- Target window: 7:30 AM – 10:30 AM or 1:00 PM – 3:30 PM
- Do not propose exact on-the-hour times (9:00 AM, 10:00 AM)
- Vary minutes: 8:17 AM, 9:43 AM, 2:08 PM — not 9:00 AM, 10:00 AM, 2:00 PM

---

### MARKET SCAN TIMING

**Context:** Competitive Intelligence, Market Trends, and Customer Discovery scans

**Base rule:** Market scans run on the weekly cadence. Agents do not run market scans
more frequently unless a specific event trigger fires (see event_triggers.md).

**Randomization for trigger-based scans:**
When TRIGGER-012 (competitor data change) fires, the Competitive Intelligence agent
wakes and runs a bounded incremental scan. The timing of that scan is:
- Within 2–4 hours of trigger detection during business hours
- Not at exact trigger-detection time (add 15–90 minute buffer)
- Never during quiet hours even if trigger fires then

**Monthly deep scan timing:**
The monthly competitor matrix refresh is proposed for the first Friday of the month
but may be shifted to the second Friday if:
- A pilot is in active engagement window (bandwidth conflict)
- Multiple high-priority event triggers fired in the same week
- The first Friday falls within 3 days of a major legal industry event or deadline

---

### PILOT FOLLOW-UP TIMING

**Context:** Check-ins, status reviews, and post-pilot conversion attempts with live pilot clients

**Base rule:** High-frequency during active engagement window (every 2 hours per active_projects.md).
But each check-in should not feel like a polling loop.

**What "every 2 hours" means in practice:**
- The runner checks whether new data has arrived (new pilot notes, status change, inbound reply)
- If new data: agent wakes and produces a bounded response or next-step recommendation
- If no new data: runner logs "no change" and skips. Agent does NOT run.
- "Every 2 hours" is a ceiling on check frequency, not a floor on agent invocations.

**Post-pilot follow-up sequence:**
Use the same follow-up timing windows as outreach follow-up (table above).
Do not follow up more than once per business day after pilot completion.
Apply a minimum 2-business-day gap before the first post-pilot follow-up.

---

## Patterns That Constitute "Robotic" Behavior

The following patterns indicate randomization has failed. Chief of Staff must flag these.

| Pattern | Definition | Action |
|---|---|---|
| Clock-exact scheduling | Proposed times cluster at :00 or :30 minute marks | Revise — vary minutes |
| Same-day repetition | Same day of week proposed 3+ consecutive weeks | Vary the day |
| Same-interval follow-up | Follow-up steps land exactly N days apart | Add ±1–3 day variation |
| Missing skip days | Every social slot is filled every week | Remove lowest-quality content |
| Burst posting | 3+ posts proposed for same calendar day | Redistribute or remove |
| Weekend-heavy | More than 25% of proposed social posts on Sat/Sun | Shift to weekdays |
| Uniform format | All posts in a batch are same format or length | Vary before approving |

---

## Relationship to Social Posting Cadence

This file governs the randomization mechanism.
`memory/social_posting_cadence.md` governs the voice, format, and authenticity standards.
Both must be read together when producing proposed content schedules.

If a conflict exists between this file and social_posting_cadence.md, the stricter rule applies.
