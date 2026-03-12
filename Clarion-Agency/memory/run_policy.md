# run_policy.md
# Clarion Agent Office — Run Policy
# Version: 1.0 | 2026-03-12
# All runners and orchestration logic must consult this file before invoking agents.

---

## Core Principle

The office does not run constantly. It sleeps by default.
Agents wake only when meaningful work exists, perform bounded work, log state, and return to sleep.

Every agent invocation costs tokens and time. The default answer is: skip this agent this cycle.
The exception is: a wake condition is met, real inputs exist, and bounded work is possible.

---

## The Three Run Modes

---

### MODE 1 — Scheduled Runs

Agents that run on a calendar schedule regardless of external events.

**Weekly Scheduled Agents (run every Friday unless quiet hours apply):**
- Chief of Staff
- Competitive Intelligence
- Content & SEO (Foundation Mode — only when comms inputs exist)
- Sales Development Analyst (once live pipeline data exists)
- Customer Health & Onboarding (once account roster is populated)
- Funnel Conversion Analyst (once funnel data exists)
- Head of Growth (once real pipeline reporting begins)

**Monthly Scheduled Agents (run first Friday of the month):**
- Revenue Strategist
- Market Trends Analyst
- Retention Intelligence Analyst
- People & Ops Intelligence Agent (only when team signals exist)

**Quarterly Scheduled Agents (run first Friday of the quarter):**
- ICP Analyst (only when real win/loss/churn data exists)

**Pre-Launch Cadence Override (active until post-launch directive issued):**
See SECTION 6 — CURRENT PRE-LAUNCH CADENCE below.
The pre-launch cadence is lighter and more targeted than the full schedule above.

---

### MODE 2 — Event-Driven Wakeups

Certain agents wake outside the normal schedule when a specific trigger event occurs.
See `memory/event_triggers.md` for the full trigger-to-agent mapping.

**How an event wakeup works:**
1. The runner or a human operator detects a trigger condition (file change, new input, etc.)
2. The runner checks `memory/event_triggers.md` to identify the waking division(s)
3. The runner invokes only the mapped agent(s) — no full office run
4. The agent performs bounded work scoped to the triggering event
5. The agent logs its output and returns to sleep

**Event wakeups are NOT full office runs.**
Only the triggered division runs. Chief of Staff does NOT synthesize unless explicitly scheduled
or unless the trigger's severity requires immediate escalation (see agent authority levels).

---

### MODE 3 — Active Project Windows

Projects listed as "active" in `memory/active_projects.md` may schedule their own
wake frequency independent of the standard weekly cadence.

**How active project windows work:**
1. Each active project entry defines a `wake_frequency` and `stop_condition`
2. The runner checks the project's last-run date before invoking
3. If elapsed time meets or exceeds wake_frequency, the owning agent runs
4. The agent performs work scoped to that project only
5. When stop_condition is met, wake_frequency is set to null (project goes dormant)

**Example:** A pilot project with `wake_frequency: every 2 hours` during a live pilot
window. The owning agent wakes every 2 hours, checks pilot status, and logs.
Outside the pilot window, wake_frequency reverts to `daily` or `weekly`.

---

## Sleep / Wake Rules

**Default state: SLEEP**
No agent runs unless a wake condition is explicitly met.

**Wake conditions (any one of the following):**
1. The agent's scheduled run day has arrived (MODE 1)
2. A mapped trigger event has fired for this agent (MODE 2)
3. The agent owns an active project whose wake interval has elapsed (MODE 3)
4. A human operator has manually invoked the office or a specific division

**After waking, an agent must:**
1. Check whether real inputs exist before calling the LLM (use `_has_real_input()` gate)
2. Perform bounded, scoped work — not an open-ended analysis session
3. Write its output to the reports directory
4. Update the relevant project entry in `active_projects.md` if applicable
5. Log completion state
6. Return to sleep (do not loop or reschedule itself)

---

## Quiet Hours

The office does not run between 10:00 PM and 6:00 AM Central Time.
No agent may be invoked during quiet hours, regardless of mode.

**Exception:** A human operator may override quiet hours by explicitly running the office manually.
The runner does not auto-override quiet hours. Scheduled jobs must respect this window.

---

## Max Wake Frequency Per Division

No division may be invoked more frequently than these caps, regardless of trigger volume.

| Division | Max Frequency |
|---|---|
| Executive (Chief of Staff) | Once per 24 hours |
| Revenue (any agent) | Once per 12 hours |
| Market Intelligence (any agent) | Once per 6 hours |
| Customer Intelligence (any agent) | Once per 6 hours |
| Product Insight (any agent) | Once per 12 hours |
| Product Integrity (any agent) | Once per 24 hours |
| Comms & Content (any agent) | Once per 12 hours |
| Operations (any agent) | Once per 24 hours |
| People & Culture | Once per 24 hours |

If a trigger fires within the cooldown window, the runner logs it as "skipped — cooldown active"
and defers until the cooldown expires.

---

## Stale Project Shutdown

A project is considered stale if ALL of the following are true:
- Status is "In Progress" or "Not Started"
- Last Update is more than 30 days ago
- No trigger event has fired for the owning division in 14 days
- stop_condition has not been documented

When a project is stale, the runner:
1. Flags it as STALE in `active_projects.md`
2. Sets its wake_frequency to null (dormant)
3. Surfaces the stale flag in the next Chief of Staff report

A human must actively re-activate the project by updating its entry and removing the STALE flag.
The office does not auto-restart stale projects.

---

## Skip Low-Signal Wakeups

Before invoking an LLM, the runner must confirm at least one of the following is true:

- The agent's real-input gate returns True (data files contain non-placeholder content)
- An approved action exists in `approved_actions.md` with STATUS: approved that maps to this agent
- A Level 2 action exists in `division_lead_approvals.md` with STATUS: approved for this division
- An event trigger has fired and the trigger's source file contains new content since last run

If none of these are true: skip the agent this cycle. Write a skip-report. Do not call the LLM.

The office must not burn tokens on agents that have nothing real to work with.

---

## SECTION 6 — CURRENT PRE-LAUNCH CADENCE

Active until: CEO issues a post-launch directive and updates `memory/prelaunch_context.md`

### Morning Run (Fridays, first run of the day)

Run in this order. Skip any agent whose real-input gate fails.

1. **Chief of Staff** — synthesizes all available division reports
2. **Competitive Intelligence** — market scan, competitor tracking
3. **Content & SEO Agent** — content calendar, social drafts (Foundation Mode)
4. **Sales Development Analyst** — lead pipeline review (skip if no pipeline data)
5. **Conversation Discovery** — public channel monitoring for ICP signals

### Midday Run (Fridays, second run — lighter)

Run only if active project entries have elapsed wake intervals.

- Sales (if outreach is in active project window)
- Content & SEO (if a specific deliverable is in active project window)
- Any agent whose active project `wake_frequency` is "daily" or shorter

### Weekly Deeper Run (First Friday of the month)

- Revenue Strategist (structural revenue review)
- Competitive Intelligence (full competitor matrix refresh)
- Chief of Staff (full executive synthesis including monthly-cycle agents)

### Off Unless Needed

These agents do NOT run unless real inputs exist or a specific event trigger fires:

- Customer Discovery — off unless `discovery_interviews.md`, `voc_signals.csv`, and `icp_snapshot.md` contain real data
- People & Ops Intelligence — off until team headcount signals exist
- Product Integrity agents — off until production scoring data is available
- Customer Health & Onboarding — off until account roster is populated
- Retention Intelligence — off until real churn events are logged
- ICP Analyst — off until quarterly review date and real win/loss data exist
- Release Impact Analyst — off until a product release event fires

---

## Enforcement

The runner (`run_clarion_agent_office.py`) is responsible for enforcing this policy.
If a new runner or scheduler is introduced, it must read and implement all rules in this file
before invoking any agent.

Agents are not responsible for enforcing run policy. Agents trust the runner to invoke them only
when appropriate. Agents are responsible only for checking real-input gates and writing skip-reports
when inputs are absent.
