# Clarion AI Working Rules

_Single reference for all working rules, pass discipline, scope boundaries, and protected systems. Read this at the start of every session alongside `NORTH_STAR.md` and `PROJECT_STATE.md`._

---

## Startup Context
Load these three docs at the top of every session:
1. `NORTH_STAR.md` — what the product is, what it should feel like, canonical brief spine
2. `PROJECT_STATE.md` — where things stand right now, architecture map, active pass
3. `AI_WORKING_RULES.md` (this file) — how to work, what's protected, pass format

Load only the additional files needed for the active task. Read them fully before editing anything.

---

## Docs System Contract

Roles are stable; content is living.

- `NORTH_STAR.md` = product identity, narrative spine, design lane, canonical brief truth
- `PROJECT_STATE.md` = live implementation truth and current phase
- `AI_WORKING_RULES.md` = execution discipline, protected-system handling, verification rules
- `CHANGELOG_AI.md` = append-only history of completed passes

Protected docs are not frozen docs. If reality changes, update the relevant doc in the same pass that proves the change.

---

## Pass Discipline

**One goal per pass — not one file per pass.**

A pass can touch multiple related files when they serve a single coherent outcome. Examples of appropriate scope:
- Landing pacing changes across 4–5 section components → one pass
- Brief output vocabulary alignment across 3 frontend files + 1 backend template → one pass
- Authenticated continuity audit + targeted fixes across 2–3 pages → one pass

**Not appropriate in a single pass:**
- Backend logic change + unrelated frontend redesign
- Calibration work + UX polish
- Auth changes + anything else

Scope creep means adding *unrelated* changes — not touching multiple files for one clear purpose.

Required pass behavior:
- Confirm exact file ownership before edits.
- Keep diffs minimal and scoped to the single pass goal.
- No opportunistic cleanup, renames, or style churn.

---

## Inspect Before Change

- Read the actual files before forming opinions. Never assume from filenames or memory.
- Label uncertain claims: FACT / INFERENCE / UNKNOWN.
- Do not write code that references components, routes, or data shapes without confirming they exist.
- When a pass spans 5+ files, read them all upfront in one batch before writing anything.
- Diagnose before risky implementation; do not patch first and investigate later.

---

## Implementation Discipline

- Precise, minimal diffs. No "while I'm in here" changes.
- Prefer additive changes over rewrites when both achieve the same outcome.
- Never change TypeScript types, API shapes, or Flask route signatures unless directly in scope.
- Refactor only when the active pass explicitly requires it.
- **Build verification:** `npm run build` in `frontend/` after every frontend-touching pass. `python -m py_compile` for touched Python files.
- **Runtime verification:** Required when behavior changes (auth, routing, data fetch, workflow transitions, render paths).
- Do not invent product states, metrics, or deployment claims.
- If root cause is not confirmed, stop and report findings instead of shipping speculative fixes.

---

## Protected Systems

These require deliberate justification before touching. "Protected" means inspect carefully — not never touch.

### Always High-Caution (require explicit scope + review)

**`backend/app.py` — Security/Auth/Session boundary**
- Login/session checks, role guards, CSRF handlers, rate-limit decorators, security headers
- Safe pattern: additive route-local changes only; never modify global middleware defaults

**`backend/services/governance_insights.py` — Governance Signal Engine**
- Severity thresholds, ratio normalization, signal/action generation rules, output shapes
- Safe pattern: keep outputs backward compatible; add tests for any rule change

**`backend/services/benchmark_*.py` + `automation/calibration/*.py` — Calibration Pipeline**
- Batch runner behavior, chunking, synthetic top-up assumptions, audit artifact handling
- Safe pattern: preserve audit artifact separation; validate with dry-run before merge

**`backend/pdf_generator.py` — Governance Brief Rendering**
- Core document layout, data binding, watermark/plan-limit dependencies
- Safe pattern: narrowly scoped section edits only; verify PDF renders after any change

### Smoke-Tested — Accessible for UI/Narrative Changes

`Dashboard.tsx`, `ExecutionPage.tsx`, `Upload.tsx`, `ReportsPage.tsx`, `ReportDetail.tsx`

These are operator-verified. UI and narrative changes are fine with inspection + build verification. Behavior rewrites, fetch logic changes, and API contract changes still require explicit scope and smoke validation.

---

## Pass Report Format

Every meaningful pass includes:
1. Goal
2. Files inspected
3. Files changed
4. Exact changes + why
5. Verification (build pass or equivalent)
6. Commit hash
7. Remaining risks or known gaps

Minor passes (doc updates, small copy fixes): abbreviated is fine.

---

## Doc Evolution

These docs should evolve when they're stale or wrong — fix it as part of the pass that reveals the problem.

- `NORTH_STAR.md` — update only when product identity, design direction, or canonical brief spine genuinely changes
- `PROJECT_STATE.md` — keep current; trim historical detail to `CHANGELOG_AI.md` when it stops being actionable
- `AI_WORKING_RULES.md` (this file) — update when a rule is wrong, a protection level changes, or scope guidance needs adjustment
- `CHANGELOG_AI.md` — append-only historical log; never rewrite or trim

Doc update policy:
- Update docs only when a pass materially changes live truth, operating rules, or current priorities.
- For narrow passes, make narrow doc edits.
- Do not duplicate the same architecture/current-state narrative across multiple docs.

**Anti-scope-creep guard:** If a request implies broad reimagining while a pass is scoped to something specific — stop, document the out-of-scope items, complete only the scoped work, surface the larger question.

---

## Architecture Reference (Critical — Do Not Lose)

**Calibration engines are separate:**
- `backend/services/benchmark_engine.py` — live calibration path (`/internal/benchmark/batch`); all phrase/guard changes go here
- `backend/services/bench/deterministic_tagger.py` — standalone harness only, not called by Flask

**Phrase dictionary:** `THEME_PHRASES` in `benchmark_engine.py`. Add/tweak only — never remove existing phrases without explicit instruction.

**Frontend contracts:** TypeScript types and `/api/*` response shapes are not changed without a matching backend change in the same scoped pass.

---

## Tool/Connector Recommendation Lane (Recommendation-Only)

Use this lane only when a pass exposes concrete delivery friction. This lane is not roadmap authority.

Recommendation format (required):
- Observed friction
- Suggested tool / connector / workflow improvement
- Why it helps in this repository specifically
- Expected payoff
- Downside / risk
- Priority: now / later / ignore
- Approval required before adoption: yes

No recommendation in this lane should be implemented without explicit user approval in a later scoped pass.
