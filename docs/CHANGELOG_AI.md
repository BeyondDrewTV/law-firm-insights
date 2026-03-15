# AI Pass Changelog

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
