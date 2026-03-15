# Codex Build Rules — Clarion

## Core Rules
1. **Inspect first, then edit.**
2. **List exact files changed** in every pass report.
3. **Do not refactor by default.** Keep changes scoped.
4. **State uncertainty explicitly** instead of guessing.
5. **Keep protected systems stable** unless directly requested.
6. **Update AI memory docs after each meaningful pass.**

## Implementation Discipline
- Prefer precise, minimal diffs.
- Keep API and data-shape compatibility unless scope requires change.
- Do not rewrite working product surfaces during documentation-only passes.
- Validate touched behavior with the lightest reliable checks.

## Required Pass Report Format
Use this structure:
1. Goal
2. Files Inspected
3. Files Created
4. Files Changed
5. Exact Changes
6. Why It Is Safe
7. Verification
8. Commit
9. Remaining Risks

## Standard for Claims
- Every architectural/product claim must map to an inspected file.
- If a claim cannot be verified quickly, mark as unknown and defer.

## Anti-Scope-Creep Guard
If a change request suggests broad product reimagining while the pass is scoped to docs/handoff:
- stop,
- document out-of-scope items,
- complete only the scoped work.
