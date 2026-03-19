# Clarion Project State

## Current Phase
Release-candidate-ready product. V3 landing active, public and authenticated surfaces aligned, operator smoke confirmed, and governance brief output unification pass now completed so the on-screen brief, PDF preview, and email outputs all use the same canonical 5-section vocabulary and order.

## Brief Output Unification State (as of 2026-03-19)
- **Canonical brief section spine:** Leadership Briefing → Signals That Matter Most → Assigned Follow-Through → Decisions & Next Steps → Supporting Client Evidence
- **On-screen brief (`ReportDetail.tsx`):** canonical — unchanged, source of truth
- **Email preview modal (`EmailBriefPreviewModal.tsx`):** tile order now matches canonical spine
- **Inline email HTML (`emailHtmlSummary` in `ReportDetail.tsx`):** row order now matches canonical spine
- **Backend Jinja2 email template (`partner_brief_email.html`):** all section labels now use canonical vocabulary; CTA now reads "Open Governance Brief"
- **PDF reference layout (`PdfDeckPreview.tsx`):** Decisions & Next Steps section added; all 5 canonical sections now present
- **Backend PDF generator (`pdf_generator.py`):** agenda items and section headings now use canonical vocabulary (strings only, no logic changed)
- **Still split:** backend PDF sub-labels (Exposure & Escalation, Execution Summary, Since Last Brief) remain internal operational labels within canonical sections — acceptable, not competing section spine; inline email summary covers 4 of 5 sections (no Assigned Follow-Through — acceptable for summary format)

## Current Focus
- Hold the replay-stable live engine in place and stop treating calibration as the main project story.
- Keep the new partner-facing public story grounded in the real workflow: upload, structure, assign, review, and bring the brief into meetings.
- Keep the canonical public proof centered on the sample brief route, with the sample workspace available as secondary mechanics proof rather than a competing story.
- Treat legacy Flask public surfaces as fallback/archive-only until they can be fully retired.

## Calibration State (as of 2026-03-17)
- **Live benchmark engine file:** `backend/services/benchmark_engine.py` (NOT `backend/services/bench/deterministic_tagger.py`)
- **Last stored calibration run:** `data/calibration/runs/20260315_200410`
- **Stored run agreement rate:** 27.3% clean-review agreement (`39/143` zero-disagreement reviews)
- **Previous replay after theme hardening:** 34.3% clean-review agreement (`49/143` zero-disagreement reviews) with `wrong_severity` regressing to `19`
- **Previous replay after severity hardening:** 37.8% clean-review agreement (`54/143` zero-disagreement reviews)
- **Current replay against that same stored run:** 44.1% clean-review agreement (`63/143` zero-disagreement reviews)
- **Current replay deltas vs stored run baseline:** `missing_theme` `152 -> 103`, `extra_theme` `38 -> 22`, `wrong_polarity` `2 -> 0`, `wrong_severity` `11 -> 0`
- **Fresh live endpoint-backed validation is now feasible from this shell:** `automation/calibration/run_calibration_workflow.py` completed a real 8-chunk localhost run at `data/calibration/runs/20260317_223428`
- **Current fresh live 143-review endpoint pass:** clean-review agreement `43.4%` (`62/143`), `missing_theme` `105`, `extra_theme` `20`, `wrong_polarity` `0`, `wrong_severity` `1`
- **Fresh live validation remains noisier than replay because AI labels are regenerated live:** the remaining live-only tail is now small and concrete: `wrong_severity` on `without achieving any meaningful progress`, `missed_severe_phrase` on `horrible with communication`, and one `likely_context_guard_failure` on `charged me the full amount`
- **Fresh live rerun on 2026-03-18 confirmed label variance rather than a stable engine defect:** clean-review agreement drifted to `39.9%` (`57/143`), `missing_theme` stayed `105`, `extra_theme` moved to `23`, `wrong_polarity` stayed `0`, `wrong_severity` moved to `2`, and the exact tail cases changed review-to-review.
- **Current diagnosis of the prior named tail cases:** `without achieving any meaningful progress` currently matches replay and fresh live as `negative`; `horrible with communication` still splits replay/live on severity; `charged me the full amount` currently aligns, while the same review's live-only disagreement shifted to `i was stuck without legal council`.
- **Validation workflow fixes:** `automation/calibration/analyze_disagreements.py`, `automation/calibration/run_calibration_workflow.py`, and `automation/calibration/generate_synthetic_topup.py` now use ASCII-safe console output on this Windows shell

## Architecture Note (Critical)
The calibration harness uses two separate deterministic engines:
1. `backend/services/benchmark_engine.py` - used by `/internal/benchmark/batch` (live calibration path)
2. `backend/services/bench/deterministic_tagger.py` - standalone harness tool only, not called by Flask

All live calibration phrase and guard changes must land in `benchmark_engine.py`.

## Clarion Version (Repo Snapshot)
- Backend: Flask monolith (`backend/app.py`) with benchmark/calibration services, governance services, email, and scheduling support
- Frontend: React + TypeScript + Vite workspace + marketing routes
- Data layer: SQLite with Postgres compatibility scaffolding in code

## Operator Smoke State (as of 2026-03-18)
- A full local operator smoke pass is now completed against a controlled local stack: frontend on `http://127.0.0.1:8081` and backend on `http://127.0.0.1:5051`.
- Verified successful workflow segments:
  - operator login
  - CSV upload and analysis from the real upload UI
  - dashboard/workspace data population
  - governance brief detail page load
  - signals list and signal detail load
  - action creation and status update flow
  - PDF preview/download path
  - partner-brief email modal preview and send
- Smoke-test blockers fixed in code:
  - Vite `/api` proxy can now target a configured backend instead of assuming `127.0.0.1:5000`
  - post-upload API success path no longer crashes after commit because missing helper functions were restored in `backend/app.py`
  - exposure snapshot / PDF generation no longer fail on naive-vs-aware due date comparison
  - partner-brief email attachment serialization now matches the Resend client contract
- A second shorter smoke pass has now been confirmed on a clean seeded Team workspace using `tools/ensure_e2e_user.py` + `tools/reset_e2e_state.py`.
- Clean-seeded smoke verification passed through:
  - login from the intentional empty-state overview
  - CSV header check
  - CSV upload and analysis
  - report detail load
  - action creation and workspace visibility
  - PDF download/preview
  - partner-brief email send
- Seeded smoke tooling now resolves the same database as the live app by reading backend env config instead of assuming `backend/feedback.db`.
- Remaining release-readiness issues are now non-blocking:
  - frontend production build still warns about one large JS chunk
  - report brief text uses stored plan-at-run provenance, which is expected and aligned when the workspace plan is set before upload

## Authenticated Product UX State (as of 2026-03-18)
- The authenticated route structure already matches the real operator workflow and remains unchanged in this pass:
  - workspace home `/dashboard`
  - upload `/upload`
  - signals `/dashboard/signals`
  - follow-through `/dashboard/actions`
  - briefs `/dashboard/reports`
- The first UX alignment pass is focused on making the authenticated product read more like:
  - current governance cycle
  - latest brief readiness
  - follow-through and accountability
  and less like:
  - a generic dashboard
  - a flat feature list
  - account-setup SaaS onboarding
- The main implementation targets are:
  - `frontend/src/components/WorkspaceLayout.tsx`
  - `frontend/src/pages/Dashboard.tsx`
  - `frontend/src/pages/Onboarding.tsx`
  - `frontend/src/pages/Login.tsx`
  - `frontend/src/pages/Signup.tsx`
  - `frontend/src/pages/Upload.tsx`
- Workspace home is now being tightened in a second pass so `/dashboard` reads more explicitly in this order:
  - current cycle
  - latest brief
  - attention now
  - follow-through review
  - supporting context
- The dashboard still uses the same live data and route structure, but lower-value context blocks have now been demoted so the page behaves less like a control panel and more like a review home for the current governance cycle.
- `/dashboard/actions` has now been tightened so follow-through reads more like accountability control for the current cycle and less like filtered task administration.
- `/dashboard/actions` now prioritizes, in order:
  - overdue follow-through
  - unowned follow-through
  - blocked follow-through
  - items that need review before the next partner discussion
  - completed follow-through as cycle history
- `/dashboard/reports/:id` now reads more unmistakably as Clarion's canonical governance brief artifact.
- `/dashboard/reports/:id` now prioritizes, in order:
  - leadership briefing for the current cycle
  - signals that matter most
  - assigned follow-through and ownership posture
  - decisions and next steps
  - supporting client evidence beneath the core review artifact
- `/dashboard` now behaves more explicitly like a current-cycle staging surface:
  - the strongest dashboard action is opening the current brief
  - the brief handoff is stated directly on the page
  - follow-through review now references the current brief packet instead of reading as a parallel control center
- `/dashboard/actions` now references the current brief packet more explicitly so follow-through reads as part of the same governance cycle rather than a detached task workspace.
- The current authenticated UX alignment pass is now focused on the first live cycle handoff from `/upload` into the current report packet.
- `/upload` now points more explicitly to:
  - one CSV for one review period
  - the current report packet as the first destination after analysis
  - follow-through and brief controls as the next review steps after opening that packet
- Onboarding now opens the first report directly when setup already included a real CSV upload, instead of always dropping the user back into workspace home first.

## Last Completed Pass
- 2026-03-19 - Governance Brief Output Unification Pass

## Previous Pass
- 2026-03-18 - Public Proof + Brief Continuity Pass

## Next Pass Options
1. Signals/supporting-workflows pass so supporting views stay clearly subordinate to the current cycle and latest brief
2. Frontend-to-backend brief deeper output unification (PDF layout data plumbing so generated PDF sections mirror on-screen brief more precisely)
3. Retire legacy Flask marketing templates completely if deploy/runtime constraints no longer require fallback pages
4. Consider route-level code splitting only if bundle size becomes a measured implementation issue

## Public Landing State (as of 2026-03-18)
- Canonical public marketing route: `/`
- Canonical public source files: `frontend/src/App.tsx`, `frontend/src/pages/Index.tsx`, and `frontend/index.html`
- React-owned overlapping public routes now include `/features`, `/how-it-works`, `/pricing`, `/security`, `/privacy`, and `/terms` whenever the built frontend exists.
- Legacy Flask templates under `backend/templates/` remain fallback/archive-only for those overlapping routes when no React build is present.
- Still-reachable but non-canonical legacy public surfaces remain:
  - `/case-studies`
  - `/app`
- Active public landing result:
  - `/` now implements the approved V3 hierarchy on the React surface:
    - hero
    - trust / fit
    - workflow
    - outputs
    - action / accountability
    - meeting-ready visibility
    - final CTA
  - the hero and previews now lead with governance brief, action ownership, and meeting follow-through rather than dashboard collage framing
  - the public tone is now calmer, editorial, and document-forward instead of generic SaaS/dashboard-first marketing
  - `/features`, `/how-it-works`, `/pricing`, and `/security` now share the same lighter editorial shell, sample-brief CTA behavior, and partner-facing law-firm positioning
  - `/privacy` and `/terms` now use simpler reference/legal wording that fits the same calmer public shell
  - `/contact`, `/docs`, and the public sample-workspace routes (`/demo`, `/demo/reports/:id`, `/demo/reports/:id/pdf`) now use the same sample-workspace / partner-review language instead of older internal pipeline/demo framing
- Public proof continuity is now tighter:
  - canonical public proof artifact: `/demo/reports/:id`
  - sample workspace route `/demo` remains available, but is now framed as secondary mechanics proof
  - public nav/resources and supporting-page CTAs now point to the sample brief first instead of splitting proof attention evenly between the two demo models

## Protected Systems Summary
- Security/auth/session/rate-limit/CSRF surfaces in `backend/app.py`
- Deterministic governance generation in `backend/services/governance_insights.py`
- Benchmark and calibration engine services in `backend/services/benchmark_engine.py` and `automation/calibration/*.py`
- Governance brief rendering in `backend/pdf_generator.py`

## Core Operator/Customer Workflow
1. Upload reviews (CSV) via workspace upload flow
2. Backend parses, validates, analyzes, and stores report artifacts
3. Deterministic governance signals and recommended actions are generated
4. Team uses dashboard/report/action surfaces to assign owners, due dates, and statuses
5. Governance brief PDF/email outputs support leadership review cycles
6. Repeated cycles provide trend and follow-through visibility over time
