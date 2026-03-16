# Clarion Project State

## Current Phase
Operational hardening + calibration improvement.

## Current Focus
- Calibration engine agreement rate improvement against AI benchmark.
- Core governance workflow reliability.

## Calibration State (as of 2026-03-15)
- **Live benchmark engine file:** `backend/services/benchmark_engine.py` (NOT deterministic_tagger.py)
- **Last calibration run:** `data/calibration/runs/20260315_200410`
- **Agreement rate:** 27.3% (baseline was 19.6%, +7.7pp)
- **Clean reviews (0 disagreements):** 39/143 (was 28)
- **Remaining `missing_theme` count:** 152 (was 180)
- **New `extra_theme` increase:** +11 — new phrases firing where AI doesn't tag; needs guard review pass

## Architecture Note (Critical)
The calibration harness uses TWO separate deterministic engines:
1. `backend/services/benchmark_engine.py` — used by `/internal/benchmark/batch` endpoint (live calibration)
2. `backend/services/bench/deterministic_tagger.py` — standalone harness tool only, NOT called by Flask

All phrase additions for calibration improvement must go to `benchmark_engine.py`.

## Clarion Version (Repo Snapshot)
- Backend: Flask monolith (`backend/app.py`) with service modules for governance, email, scheduling, benchmark/calibration support.
- Frontend: React + TypeScript + Vite workspace + marketing routes.
- Data layer: SQLite with Postgres compatibility scaffolding in code.

## Last Completed Pass
- 2026-03-15 — Live Tagger Validation + Definitive Calibration (Wave 3 phrase additions to benchmark_engine.py)

## Previous Pass
- 2026-03-15 — Calibration Wave phrase expansion to deterministic_tagger.py (retroactively identified as wrong file)

## Next Pass Options
1. **extra_theme guard review** — 38 extra_theme disagreements after Wave 3. Review which new phrases are over-firing and add guards or reduce weights.
2. **professionalism_trust disagreements jumped** (+8) — new broad phrases (kindness, recommend, knowledgeable) triggering FPs. Scope a targeted weight reduction or context guard pass.
3. **Chunks 5, 6, 7 still low** (25%, 10%, 5%) — inspect their specific evidence spans for next phrase additions.
4. Calibration completion/hardening validation.
5. Landing/marketing clarity pass.

## Protected Systems Summary
- Security/auth/session/rate-limit/CSRF surfaces in `backend/app.py`.
- Deterministic governance generation in `backend/services/governance_insights.py`.
- Benchmark and calibration engine services in `backend/services/benchmark_engine.py` and `automation/calibration/*.py`.
- Governance brief rendering in `backend/pdf_generator.py`.

## Core Operator/Customer Workflow
1. Upload reviews (CSV) via workspace upload flow.
2. Backend parses, validates, analyzes, and stores report artifacts.
3. Deterministic governance signals and recommended actions are generated.
4. Team uses dashboard/report/action surfaces to assign owners, due dates, and statuses.
5. Governance brief PDF/email outputs support leadership review cycles.
6. Repeated cycles provide trend and follow-through visibility over time.

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
