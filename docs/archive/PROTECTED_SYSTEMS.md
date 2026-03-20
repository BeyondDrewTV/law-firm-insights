# Protected Systems — Clarion

These surfaces carry real risk and require deliberate care. "Protected" means inspect carefully and justify changes — not never touch.

## 1) Security/Auth/Session Boundary (`backend/app.py`)
**Protected because:** Central auth/session + CSRF + rate-limiting behavior affects every API/browser flow. Mistakes here break the whole product or create security holes.

**Caution areas**
- Login/session checks and role guards
- CSRF handlers and token endpoints
- Rate-limit decorators/config + security headers
- Error handlers that differentiate API vs non-API behavior

**Safe change pattern**
- Additive, route-local changes only
- Never modify global middleware/security defaults without explicit request + review
- Validate with targeted auth/security smoke after any touch

## 2) Governance Signal Engine (`backend/services/governance_insights.py`)
**Protected because:** Deterministic governance signals and recommended actions come from here. Output shape changes break dashboard, report detail, and brief generation.

**Caution areas**
- Severity thresholds and ratio normalization
- Signal/action generation rules and output shapes

**Safe change pattern**
- Keep outputs backward compatible
- Add tests/fixtures for any rule adjustment

## 3) Benchmark + Calibration Pipeline (`backend/services/benchmark_*.py`, `automation/calibration/*.py`)
**Protected because:** Calibration reliability depends on consistent inputs/outputs and audit artifacts. Silent regressions are hard to catch.

**Caution areas**
- Batch runner behavior and chunking
- Synthetic top-up generation assumptions
- Merged/audit artifact handling

**Safe change pattern**
- Preserve audit artifact separation from API ingestion
- Validate with dry-run + real-run summaries before merge

## 4) Governance Brief Rendering (`backend/pdf_generator.py`)
**Protected because:** Produces leadership-facing PDF artifacts. Layout/data-binding changes affect customer-visible output.

**Caution areas**
- Core document layout and data binding
- Watermark/plan-limit behavior dependencies

**Safe change pattern**
- Narrowly scoped section edits only
- Verify generated PDF opens and key sections render after any change

## 5) Core Workspace Flows (frontend)
**Status: Smoke-tested and operator-verified as of 2026-03-18. No longer high-friction protected — treat as careful-but-accessible.**

Files: `frontend/src/pages/Dashboard.tsx`, `frontend/src/pages/ExecutionPage.tsx`, `frontend/src/pages/Upload.tsx`, `frontend/src/pages/ReportsPage.tsx`, `frontend/src/pages/ReportDetail.tsx`

**Caution areas**
- API contract shapes from `/api/*` endpoints — do not change what the frontend sends or expects without a matching backend change
- Action status/owner/due workflow behavior — this is live operator data
- Data fetch logic — preserve existing error handling and loading states

**Safe change pattern**
- UI/narrative/visual changes are fine with inspection + build verification
- Behavior rewrites (fetch logic, state machines, workflow steps) require explicit scope and smoke validation
- Preserve TypeScript types and API call signatures
