# Clarion Overview

## What Clarion Is
Clarion is a law-firm client feedback governance platform that turns uploaded feedback into partner-ready operating intelligence: recurring issues, governance signals, recommended actions, and governance brief outputs.

## Who It Is For
- Managing partners
- Operations leaders
- Reputation/client-experience owners in law firms

## Core Workflow
1. Upload feedback (CSV ingestion in workspace).
2. Analyze reviews into structured report artifacts.
3. Generate governance signals + recommended actions.
4. Assign/track actions with owner, due date, and status.
5. Review governance outputs (dashboard/report detail/PDF/email brief).
6. Repeat cycle to monitor change over time.

## Repository Structure (High-Level)
- `backend/`: Flask application, APIs, services, templates, tests.
- `frontend/`: React SPA (marketing + authenticated workspace routes).
- `automation/calibration/`: calibration pipeline scripts.
- `data/calibration/`: calibration inputs/synthetic/runs artifacts.
- `docs/active/`: operational guides/runbooks.
- `docs/reference/`: reference workflows (including calibration workflow doc).
- `Clarion-Agency/`: agent office runtime and mission memory files.

## Major Subsystems (Verified)
- Feedback ingestion + upload endpoints (`backend/app.py`, `frontend/src/pages/Upload.tsx`).
- Deterministic governance insight generation (`backend/services/governance_insights.py`).
- Benchmark/calibration workflow (`automation/calibration/`, `backend/services/benchmark_*.py`).
- Governance brief/PDF output (`backend/pdf_generator.py`, report PDF routes in `backend/app.py`).
- Action tracking workflow (`frontend/src/pages/ExecutionPage.tsx`, report action APIs in `backend/app.py`).
- Marketing/landing layer (`frontend/src/pages/Index.tsx`, marketing components).

## Major Current Priorities
- Keep core governance engine reliable for real meeting use.
- Complete/validate calibration quality work.
- Improve landing/marketing clarity so capabilities are communicated accurately.
- Maintain clean AI handoff discipline to reduce drift across sessions.

## Product Truths (Non-Drift)
- Clarion is not generic analytics software.
- Core value is governance decision support for law-firm leadership.
- The operative loop is issue → action → owner → follow-through/trend.
- Charts support the workflow; they are not the product center.
- Marketing may need clearer positioning, but core product workflow should not be casually reimagined in that process.
