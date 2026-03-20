# AI Development Standards (Clarion)

## 1) Pass Discipline
- Define a clear goal before editing. One goal per pass — not one file per pass.
- Passes can span multiple related files when they serve a single coherent outcome (e.g., fixing landing pacing across 5 section components is one pass, not five).
- Scope creep means adding *unrelated* changes, not touching multiple files for one purpose.
- Do not mix frontend UX work with backend logic changes in the same pass unless they are tightly coupled and both explicitly in scope.

## 2) Inspect Before Change
- Read the actual files before forming opinions. Do not assume from filenames or prior memory.
- If a claim about architecture can't be verified from an inspected file, label it INFERENCE or UNKNOWN.
- Do not write code that references components, routes, or data shapes without confirming they exist.

## 3) Additive Architecture Preference
- Prefer additive changes over rewrites where both options achieve the same outcome.
- Refactor only when the active pass explicitly requires it.
- Never change TypeScript types, API shapes, or Flask route signatures unless directly in scope.

## 4) No Drift / No Speculation
- Do not invent product states, metrics, or deployment claims.
- Do not describe future features as if they exist.
- State uncertainty explicitly — FACT / INFERENCE / UNKNOWN separation is the standard in architecture passes.

## 5) Protected Systems Respect
- Backend security/auth, governance signal engine, calibration pipeline, and pdf_generator remain high-caution. Check `docs/PROTECTED_SYSTEMS.md`.
- Core workspace frontend flows are now smoke-tested and accessible for UI/narrative changes. Behavior and API contract changes still require explicit scope.

## 6) Pass Report Requirement
Every meaningful pass should include:
- Goal
- Files inspected
- Files changed
- Exact changes (what and why)
- Verification run (build pass or equivalent)
- Commit hash

Minor passes (1–2 file doc updates, trivial copy fixes) can use abbreviated reports.

## 7) Update Memory Files After Every Meaningful Pass
When a pass changes repo behavior or scope understanding, update:
- `docs/PROJECT_STATE.md`
- `docs/CURRENT_BUILD.md`
- `docs/CHANGELOG_AI.md` (for significant changes)

Keep doc updates tight. The goal is accurate handoff state, not exhaustive prose.

## 8) Context Loading
- Load the 4 startup docs at the top of each session.
- Load only the files needed for the active task — but load them fully before editing.
- When a pass spans 5+ files, it is fine to read them all upfront in one batch before writing anything.
