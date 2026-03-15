# Clarion AI Control Panel

## Active Pass
- **Pass:** Internal Tools Launcher UX Pass
- **Focus:** Add one-click dashboard/account access to internal calibration and benchmark routes.

## Build Focus (Now)
1. Keep core product execution stable (upload → analysis → governance outputs).
2. Keep deterministic benchmark alignment improvements intact.
3. Reduce operator friction for internal calibration/hardening access.

## Last Completed Pass (from git history)
- `b9a8a97` — calibration wave 2 phrase additions + bug fixes.

## Next Pass (Suggested)
- Continue targeted deterministic calibration tuning on remaining high-priority disagreement clusters.

## Protected Systems (Do Not Casually Modify)
- `backend/app.py` auth/session/CSRF/rate-limit/security-header surfaces.
- `backend/services/benchmark_engine.py` + related benchmark pipeline services.
- `backend/services/governance_insights.py` deterministic signal/action generation.
- `backend/pdf_generator.py` governance brief generation.
- `automation/calibration/*.py` and `data/calibration/` workflow artifacts.

See: `docs/PROTECTED_SYSTEMS.md`.

## Product Truths (Anchor)
- Clarion is a governance operating layer for law-firm leadership, not a generic analytics dashboard.
- Primary loop is **issue → action → owner → follow-through over time**.
- Reports, signals, actions, and briefs are decision-support artifacts for partner/operator meetings.
- Marketing should reflect existing depth; dashboard internals should not be casually reinvented during landing-page work.

## Repo Quick Map
- `backend/` — Flask API, auth, ingestion, governance, PDF/email, scheduling.
- `frontend/` — React workspace + marketing pages.
- `automation/calibration/` + `data/calibration/` — calibration pipeline + run artifacts.
- `docs/active/` + `docs/reference/` — operational and reference docs.
- `Clarion-Agency/` — autonomous agent office layer and company north star memory.

## Startup Files (Read First)
1. `AI_START_HERE.md`
2. `AI_CONTROL_PANEL.md`
3. `docs/PROJECT_STATE.md`
4. `docs/CURRENT_BUILD.md`
