# Protected Systems — Clarion

These surfaces are high-risk and should not be casually modified.

## 1) Security/Auth/Session Boundary (`backend/app.py`)
**Protected because:** Central auth/session + CSRF + rate-limiting behavior lives here and affects every API/browser flow.

**Caution areas**
- Login/session checks and role guards.
- CSRF handlers and token endpoints.
- Rate-limit decorators/config + security headers.
- Error handlers that differentiate API vs non-API behavior.

**Safe change pattern**
- Prefer additive, route-local changes.
- Avoid modifying global middleware/security defaults unless explicitly required.
- Validate with targeted auth/security smoke checks after any touching.

## 2) Governance Signal Engine (`backend/services/governance_insights.py`)
**Protected because:** Converts analyzed report payloads into deterministic governance signals + recommended actions.

**Caution areas**
- Severity thresholds and ratio normalization.
- Signal/action generation rules and output shapes.

**Safe change pattern**
- Keep outputs backward compatible.
- Add tests/fixtures for any rule adjustment.

## 3) Benchmark + Calibration Pipeline (`backend/services/benchmark_*.py`, `automation/calibration/*.py`)
**Protected because:** Calibration and benchmark scoring reliability depends on consistent inputs/outputs and audit artifacts.

**Caution areas**
- Batch runner behavior and chunking.
- Synthetic top-up generation assumptions.
- Merged/audit artifact handling.

**Safe change pattern**
- Preserve audit artifact separation from API ingestion.
- Validate with dry-run + real-run summaries before merge.

## 4) Governance Brief Rendering (`backend/pdf_generator.py`)
**Protected because:** Produces leadership-facing governance PDF artifacts and can affect customer-visible outputs.

**Caution areas**
- Core document layout/data binding.
- Watermark/plan-limit behavior dependencies.

**Safe change pattern**
- Limit edits to narrowly scoped sections.
- Verify generated PDF opens and key sections render.

## 5) Core Workspace Flows (`frontend/src/pages/Dashboard.tsx`, `frontend/src/pages/ExecutionPage.tsx`, `frontend/src/pages/Upload.tsx`, `frontend/src/pages/ReportsPage.tsx`)
**Protected because:** These routes implement the operational workflow customers use in partner/operator cycles.

**Caution areas**
- Data-fetch and shape assumptions from `/api/*` endpoints.
- Action status/owner/due workflow behavior.

**Safe change pattern**
- Preserve API contracts.
- Prefer additive UI changes over behavior rewrites unless explicitly scoped.
