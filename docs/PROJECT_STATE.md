# Clarion Project State

## Current Phase
Operational hardening + positioning clarity.

## Current Focus
- Preserve and harden core governance workflow reliability.
- Continue deterministic calibration alignment work against benchmark disagreements.
- Keep calibration workflow reliability and auditability stable.

## Clarion Version (Repo Snapshot)
- Backend: Flask monolith (`backend/app.py`) with service modules for governance, email, scheduling, benchmark/calibration support.
- Frontend: React + TypeScript + Vite workspace + marketing routes.
- Data layer: SQLite with Postgres compatibility scaffolding in code.

## Last Completed Pass
- `b9a8a97` — calibration wave 2 phrase additions and bug fixes.

## Previous Pass
- `3f6aba0` — outbound email quality and content SEO improvements.

## Next Pass
- Continue deterministic phrase/guard tuning for remaining high-priority disagreement themes.

## Upcoming Passes (Likely)
1. Calibration completion/hardening validation pass.
2. Engine robustness pass for production-safe edge cases.
3. Landing conversion clarity pass (copy/IA emphasis, no core workflow drift).

## Protected Systems Summary
- Security/auth/session/rate-limit/CSRF surfaces in `backend/app.py`.
- Deterministic governance generation in `backend/services/governance_insights.py`.
- Benchmark and calibration engine services in `backend/services/benchmark_*.py` and `automation/calibration/*.py`.
- Governance brief rendering in `backend/pdf_generator.py`.

## Core Operator/Customer Workflow
1. Upload reviews (CSV) via workspace upload flow.
2. Backend parses, validates, analyzes, and stores report artifacts.
3. Deterministic governance signals and recommended actions are generated.
4. Team uses dashboard/report/action surfaces to assign owners, due dates, and statuses.
5. Governance brief PDF/email outputs support leadership review cycles.
6. Repeated cycles provide trend and follow-through visibility over time.
