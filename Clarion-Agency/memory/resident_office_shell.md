# resident_office_shell.md
# Clarion Agent Office — Resident Shell Target Definition
# Version: 1.0 | 2026-03-12
#
# PURPOSE
# Defines the long-term architectural target for the Clarion Agent Office:
# a lightweight resident shell that stays up, watches state cheaply,
# and wakes agents only when conditions are met.
#
# STATUS
# This is a design target. The current implementation uses a batch runner
# (run_clarion_agent_office.py / run_daily.py) invoked manually or via Task Scheduler.
# This file documents the intended next evolution — not the current state.
# Nothing in this file requires immediate implementation.

---

## Target Architecture: Resident Office Shell

### What it is

A long-running Python process that:
1. Starts up and loads the office state (run_policy, event_triggers, active_projects)
2. Enters a sleep loop — the default state is doing nothing
3. Wakes at defined intervals to check trigger conditions (file stats only — no LLM)
4. When a wake condition is met: invokes the appropriate agent(s), waits for completion
5. Returns to sleep

### What it is NOT

- It is NOT an always-on LLM conversation loop
- It is NOT a polling daemon that calls APIs constantly
- It is NOT a replacement for human review and approval
- It is NOT a system that makes autonomous external actions

The shell watches state. Only agents (when woken) think. The shell itself never calls an LLM.

---

## Shell Behavior Specification

### Startup

```
1. Load memory/run_policy.md          — read quiet hours, cooldowns, cadences
2. Load memory/event_triggers.md      — build trigger map (file path → agent list)
3. Load memory/active_projects.md     — build project wake schedule
4. Read memory/office_health_log.md   — get last_trigger_check timestamp
5. Enter main loop
```

### Main Loop (target: check every 5–15 minutes)

```
while True:
    now = datetime.now()

    # 1. Quiet hours check
    if is_quiet_hours(now):
        sleep(until end of quiet window)
        continue

    # 2. Check event triggers (file stat only — NO LLM)
    for trigger in event_triggers:
        if file_modified_since(trigger.watch_file, last_trigger_check):
            if not in_cooldown(trigger.division):
                queue_wake(trigger.division, reason=trigger.id)

    # 3. Check scheduled cadences
    for agent in scheduled_agents:
        if schedule_due(agent, last_run[agent]):
            if not in_cooldown(agent.division):
                queue_wake(agent.division, reason="scheduled")

    # 4. Check active project windows
    for project in active_projects:
        if project.status == "Active" and project.wake_frequency:
            if wake_interval_elapsed(project, now):
                if not in_cooldown(project.owner_division):
                    queue_wake(project.owner_division, reason=f"project:{project.name}")

    # 5. Execute queued wakeups (bounded — max N agents per loop iteration)
    for wakeup in wake_queue:
        run_agent(wakeup.division, wakeup.reason)
        record_run(wakeup.division, now)

    # 6. Update last_trigger_check
    update_health_log(last_trigger_check=now)

    # 7. Sleep until next check
    sleep(CHECK_INTERVAL_MINUTES * 60)
```

### Check Interval

Default: 15 minutes
During active pilot window: 5 minutes (high-priority project monitoring)
During quiet hours: shell sleeps until quiet hours end

At 15-minute intervals with no wake conditions met: zero LLM calls, zero token spend.
The shell is nearly free to run in its default sleeping state.

---

## Cost Model

### Current state (batch runner, manually invoked weekly)

- LLM calls per run: 3–6 (depending on which agents pass real-input gate)
- Frequency: 1x per week (Friday)
- Token cost: bounded by the weekly run only

### Target state (resident shell — estimated)

- LLM calls from trigger-only wakeups: 0–2 per day (only when real signals exist)
- LLM calls from scheduled runs: same as current batch runner (1x weekly)
- File stat checks per day: ~100 (15-minute intervals × 16 business hours)
- Token cost per file stat check: 0 (no LLM involved)
- **Net cost increase vs. current: minimal** — only adds LLM calls when real events fire

### Cost guardrails (must be implemented in shell)

- Hard cap: max 10 LLM agent invocations per 24-hour period
- Hard cap: max 3 LLM agent invocations between midnight and 8 AM Central
- Hard cap: never invoke Chief of Staff more than once per 24 hours
- Soft cap: if daily LLM spend exceeds $5 USD equivalent tokens, pause non-critical wakeups
  and notify operator via `memory/office_health_log.md`

---

## Implementation Phases

### Phase 0 (current) — Manual batch runner
- run_clarion_agent_office.py invoked manually (Friday)
- run_daily.py invoked manually or via Task Scheduler
- No resident process
- No automatic trigger detection

### Phase 1 — Lightweight scheduler (near-term target)
- Add a simple scheduler wrapper that calls the existing batch runner on cadence
- Windows Task Scheduler or a cron job (Linux/Mac)
- No new architecture — just automated invocation of existing scripts
- Implement: `scheduler.py` that reads run_policy.md and calls the appropriate runner

### Phase 2 — Trigger detection layer (medium-term)
- Add file stat monitoring for the top-priority triggers (TRIGGER-001, -002, -004, -007)
- When trigger fires, invoke only the mapped division — not the full office
- Implement as a loop in `scheduler.py` — no external infrastructure

### Phase 3 — Resident shell (long-term)
- Full resident shell as specified above
- Active project window monitoring
- Randomization-aware scheduling for proposed action timing
- Health log updates and cost cap enforcement

---

## What Must Never Change

Regardless of how the resident shell evolves, these constraints are permanent:

1. **The shell never makes external calls autonomously.**
   Agents may propose. Humans approve. The shell executes approved actions only.
   No LLM may take external action without an entry in approved_actions.md or
   division_lead_approvals.md with STATUS: approved.

2. **The shell never bypasses the real-input gate.**
   If a wake condition fires but the target agent has no real inputs,
   the shell writes a skip-report and does not call the LLM.

3. **The shell never disables quiet hours automatically.**
   A human operator must explicitly override quiet hours. The shell cannot
   self-authorize running during quiet hours even for high-priority triggers.
   Exception: TRIGGER-007 (security incident) may surface a notification but
   still does not invoke LLM during quiet hours — it defers to the next
   business-hours window.

4. **The shell is auditable.**
   Every wake decision, every skip, every cooldown enforcement must be logged
   in `memory/office_health_log.md`. A human must be able to reconstruct
   exactly what the shell did and why, from the log alone.
