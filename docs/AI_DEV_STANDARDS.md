# AI Development Standards (Clarion)

## 1) Pass Discipline
- Work in small, explicit passes.
- Define scope before editing.
- Avoid mixed-purpose passes.

## 2) Inspect Before Change
- Read real files first.
- Do not infer architecture from naming alone.
- Do not claim a subsystem exists without verification.

## 3) Additive Architecture Preference
- Prefer additive changes over broad rewrites.
- Refactor only when required by the active pass.
- Keep existing contracts stable unless explicitly in scope.

## 4) No Drift / No Speculation
- Avoid aspirational roadmap language in implementation docs.
- State uncertainty explicitly.
- Do not invent metrics, customers, or deployment states.

## 5) Protected Systems Respect
- Check `docs/PROTECTED_SYSTEMS.md` before touching critical surfaces.
- Security/auth/rate-limit/CSRF and governance-core logic require extra caution.

## 6) Pass Report Requirement
Every pass should include:
- Goal
- Files inspected
- Files changed/created
- Exact changes
- Safety rationale
- Verification run
- Commit status/hash
- Remaining risks

## 7) Update Memory Files After Every Pass
When a pass changes repo behavior or scope understanding, update as needed:
- `AI_CONTROL_PANEL.md`
- `docs/PROJECT_STATE.md`
- `docs/CURRENT_BUILD.md`
- `docs/CHANGELOG_AI.md`

## 8) Minimal Context Loading
- Start with the 4 startup files.
- Load only files needed for the active task.
- Avoid full-repo scans unless necessary.
