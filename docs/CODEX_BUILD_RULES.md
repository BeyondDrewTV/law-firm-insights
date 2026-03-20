# Codex Build Rules — Clarion

## Core Rules
1. **Inspect first, then edit.** Read the actual files. No assumptions.
2. **List exact files changed** in every pass report.
3. **Do not refactor by default.** Changes serve the active goal, nothing else.
4. **State uncertainty explicitly** — FACT / INFERENCE / UNKNOWN, not confident guesses.
5. **Keep protected systems stable** unless directly requested and justified.
6. **Update AI memory docs after each meaningful pass.**

## Pass Scope
A pass has one goal. That goal can touch multiple files if they're tightly related.

**Appropriate multi-file passes:**
- Landing pacing changes across 4–5 section components (one visual outcome)
- Brief output vocabulary alignment across 3 frontend files and 1 backend template
- Authenticated continuity audit + targeted fixes across 2–3 pages

**Not appropriate in a single pass:**
- Backend logic change + unrelated frontend redesign
- Calibration work + UX polish
- Auth changes + anything else

## Implementation Discipline
- Precise, minimal diffs. No "while I'm in here" changes.
- Preserve API contracts and TypeScript types unless scope explicitly includes changing them.
- Build must pass (`npm run build` in `frontend/`) after every frontend-touching pass.
- Python files touched: run `python -m py_compile` as minimum check.
- Do not rewrite working product behavior during passes scoped to visual/narrative changes.

## Required Pass Report Format
1. Goal
2. Files Inspected
3. Files Changed
4. Exact Changes + Why
5. Verification
6. Commit hash
7. Remaining risks or known gaps

Minor passes (doc updates, small copy fixes): abbreviated report is fine.

## Standard for Claims
- Every architectural or product state claim must map to an inspected file.
- If a claim can't be quickly verified, label it unknown and don't act on it.

## Anti-Scope-Creep Guard
If a request implies broad reimagining while the pass is scoped to something specific:
- Stop
- Document the out-of-scope items
- Complete only the scoped work
- Surface the larger question to the user

This guard is about *unrelated* scope expansion, not about touching multiple related files for one clear outcome.
