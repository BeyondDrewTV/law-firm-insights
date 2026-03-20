# Clarion Project State

_This file reflects current live state. Historical detail lives in `CHANGELOG_AI.md`. Design direction and product identity live in `NORTH_STAR.md`._

---

## Current Phase

Release-candidate ready. Operator smoke passed. V3 landing active. Authenticated UX aligned around the governance brief as center of gravity. All brief output surfaces (on-screen, PDF, email) use the canonical 5-section spine.

**Active focus:** narrative continuity tightening (signals page, reports list next). Domain cutover to `clarion.co` pending.

---

## Canonical Brief Section Spine (Locked)

```
1. Leadership Briefing
2. Signals That Matter Most
3. Assigned Follow-Through
4. Decisions & Next Steps
5. Supporting Client Evidence
```

**Surface alignment status:**
- On-screen brief (`ReportDetail.tsx`) — canonical, source of truth ✓
- Email preview modal (`EmailBriefPreviewModal.tsx`) — aligned ✓
- Inline email HTML (`emailHtmlSummary`) — aligned ✓
- Backend Jinja2 email template (`partner_brief_email.html`) — aligned ✓
- PDF reference layout (`PdfDeckPreview.tsx`) — aligned ✓
- Backend PDF generator (`pdf_generator.py`) — heading strings aligned ✓
- Still split (acceptable): backend PDF sub-labels (Exposure & Escalation, Execution Summary, Since Last Brief) are internal operational labels within canonical sections — not competing spine

---

## Architecture Notes (Critical — Do Not Lose)

**Calibration engines are separate:**
- `backend/services/benchmark_engine.py` — used by `/internal/benchmark/batch` (live calibration path, all phrase/guard changes go here)
- `backend/services/bench/deterministic_tagger.py` — standalone harness only, not called by Flask

**Data layer:** SQLite with Postgres compatibility scaffolding. Render Postgres is production DB.

**Stack:** Flask monolith backend + React/TypeScript/Vite frontend. Deployed on Render. `https://law-firm-feedback-saas.onrender.com`.

---

## Operator Smoke State

Full local smoke pass confirmed 2026-03-18. Clean seeded Team workspace smoke confirmed same day.

Verified segments: login → CSV upload → report detail → signals → action creation → PDF preview → partner-brief email send.

Remaining non-blocking: large JS chunk warning in build (pre-existing), report brief text uses stored plan-at-run provenance (expected behavior).

---

## Calibration State (Stable — Hold)

Last fresh live run: `data/calibration/runs/20260317_223428`. Agreement rate 43.4% (62/143). Label variance confirmed as AI nondeterminism, not engine defect. Hold stable. Do not treat calibration as the main project story.

---

## Public Surface State

- `/` — V3 landing, governance-brief-centered hierarchy: hero → trust → workflow → outputs → accountability (dark anchor) → meeting → final CTA (dark)
- `/demo/reports/:id` — canonical public proof artifact (sample governance brief)
- `/demo` — secondary mechanics proof, explicitly framed as such
- `/features`, `/how-it-works`, `/pricing`, `/security`, `/privacy`, `/terms` — React-owned, share editorial shell
- Legacy Flask templates remain fallback/archive-only for overlapping routes

---

## Authenticated Surface State

Route structure unchanged and correct:
- `/dashboard` — current-cycle staging surface, brief-first
- `/upload` — single-CSV cycle entry point
- `/dashboard/signals` — evidence layer
- `/dashboard/actions` — follow-through accountability, brief-descendant framing
- `/dashboard/reports` + `/dashboard/reports/:id` — brief system, canonical artifact

WorkspaceLayout: sidebar nav labeled "Current cycle" / "Workspace settings". Topbar page notes are brief-oriented per route.

---

## Domain Cutover Checklist (Pending)

When ready to move to `clarion.co`:
- [ ] Render custom domain configuration
- [ ] Stripe webhook URL update
- [ ] Resend domain verification
- [ ] Frontend `VITE_API_BASE_URL` update
- [ ] CORS allowed origins update in `backend/app.py`

---

## Last Completed Pass

2026-03-19 — Authenticated Continuity Audit + Standards Evolution

- ReportDetail.tsx: Present brief button promoted to primary dark
- DemoWorkspace.tsx: Step 5 brief render replaced with document-forward artifact card
- AI_DEV_STANDARDS.md, PROTECTED_SYSTEMS.md, CODEX_BUILD_RULES.md, CLARION_OVERVIEW.md: evolved to match project maturity
- NORTH_STAR.md: created

---

## Next Pass Options

1. Signals page audit (`/dashboard/signals`) — confirm it reads as part of the governance cycle, not a detached data list
2. ReportsPage audit (`/dashboard/reports`) — confirm brief list presentation quality
3. Domain cutover execution
4. Legacy Flask template retirement (if deploy constraints allow)
