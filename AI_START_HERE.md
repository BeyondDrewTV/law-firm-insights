# AI Start Here — Clarion

Read these 4 files first (in order):
1. `AI_START_HERE.md`
2. `AI_CONTROL_PANEL.md`
3. `docs/PROJECT_STATE.md`
4. `docs/CURRENT_BUILD.md`

## What Clarion Is
Clarion is a law-firm client feedback governance product: it ingests feedback, detects recurring issues, produces governance signals/recommendations, and supports owner/due/status follow-through with governance brief output.

## Before You Change Anything
- Inspect real files first; do not assume subsystem names or paths.
- Do not make speculative architecture claims in docs or code.
- Treat backend security/auth/rate-limit/CSRF surfaces as protected unless explicitly in scope.
- Keep passes small and additive.

## Quick Orientation
- Backend entrypoint: `backend/app.py`
- Core deterministic governance logic: `backend/services/governance_insights.py`
- Core PDF brief generation: `backend/pdf_generator.py`
- Calibration workflow entrypoint: `automation/calibration/run_calibration_workflow.py`
- Frontend routing shell: `frontend/src/App.tsx`
- Primary workspace surfaces: `frontend/src/pages/Dashboard.tsx`, `frontend/src/pages/ExecutionPage.tsx`, `frontend/src/pages/ReportsPage.tsx`, `frontend/src/pages/Upload.tsx`
- Marketing surface: `frontend/src/pages/Index.tsx` and marketing components under `frontend/src/components/`

## Do-Not-Drift Rules
- Clarion is governance/operating intelligence, not generic analytics software.
- Partner/operator decision support comes before visual novelty.
- Preserve issue → action → owner → trend workflow focus.
- If uncertain, state uncertainty explicitly and verify in code before writing.
