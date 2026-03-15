# AI Pass Changelog

## 2026-03-15 — Operator Startup Launcher Pass
- Added root-level Windows launcher files: `START_CLARION.bat`, `OPEN_COMMAND_CENTER.bat`, `RUN_CALIBRATION.bat`, and `OPEN_ENGINE_TOOLS.bat`.
- Reused existing backend startup convention via `backend/start.bat` and wired command center URL to `http://localhost:5000/dashboard`.
- Added README operator-launcher section for non-technical startup clarity.
- **Commit:** recorded in git for this pass (see repository log).

## 2026-03-15 — Internal Tools Route Correction Pass
- Moved the new launcher/hub route from `/internal/calibration/` to dedicated `/internal/tools/`.
- Preserved `/internal/calibration/` as the calibration-console target by removing launcher ownership of that path.
- Kept dashboard/account CTAs pointing directly to `/internal/calibration/` and `/internal/benchmark/themes`.
- **Commit:** recorded in git for this pass (see repository log).

## 2026-03-15 — Internal Tools Launcher UX Pass
- Added an authenticated admin/dev-only internal tools launcher route for calibration/benchmark access.
- Added an internal tools card in Dashboard Account → Internal Testing with one-click launch links for calibration and benchmark console access.
- Added a minimal backend template for internal benchmark endpoint launch targets used during calibration/hardening.
- **Commit:** recorded in git for this pass (see repository log).

## 2026-03-15 — Deterministic Calibration Alignment Pass
- Tightened deterministic phrase matching with word-boundary logic for single-token phrases to reduce substring false positives.
- Added calibration-targeted phrase/guard updates for launch-relevant disagreements (billing consultation-fee severity, severe professionalism cues, timeliness typo variant, office staff positive phrase).
- Fixed a dictionary-key overwrite bug in `office_staff_experience` that was dropping most positive staff phrases.
- Removed calibration workflow `datetime.utcnow()` deprecation usage in workflow/batch scripts via timezone-aware UTC timestamps.
- **Commit:** recorded in git for this pass (see repository log).

## 2026-03-15 — Clarion AI Memory System Setup
- Added a lightweight AI control/startup layer for fast orientation and handoff continuity.
- Added scoped docs for current build boundaries, project state, protected systems, overview, and AI standards.
- Normalized startup path so future sessions can begin with four files instead of long chat handoffs.
- **Commit:** recorded in git for this pass (see repository log).

## Prior Notable Passes (from git history)
- `b9a8a97` — calibration wave 2 phrase additions + bug fixes.
- `3f6aba0` — outbound email quality and content SEO improvements.
- `d2647c5` — calibration + agent office pipeline fix.
- `30cb290` — approval queue dashboard/backend integration pass.
