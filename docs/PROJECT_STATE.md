# Clarion Project State

_This file reflects current live state. Historical detail lives in `CHANGELOG_AI.md`. Design direction and product identity live in `NORTH_STAR.md`. Working rules and protected systems live in `AI_WORKING_RULES.md`. Engineering practices and repo hygiene live in `ENGINEERING_PRACTICES.md`._

---

## Startup Reads (Every Session)
1. `NORTH_STAR.md` — product identity, design direction, canonical brief spine
2. `PROJECT_STATE.md` (this file) — live state, active issues, next pass priorities
3. `AI_WORKING_RULES.md` — pass discipline, protected systems, hygiene rules
4. `ENGINEERING_PRACTICES.md` — repo hygiene, commit format, cleanup checkpoint checklist

---

## Document Role Boundary (Authoritative)
- `NORTH_STAR.md` — product identity, narrative spine, design lane, canonical brief truth
- `PROJECT_STATE.md` — live implementation truth, current phase, active pass priorities
- `AI_WORKING_RULES.md` — execution discipline, protected-system handling, verification rules
- `CHANGELOG_AI.md` — append-only historical record of completed passes
- `ENGINEERING_PRACTICES.md` — repo hygiene standards, cleanup checklist, known technical debt

---

## Repository & Deployment

- **GitHub:** https://github.com/DrewYomantas/Clarion (renamed from BeyondDrewTV/law-firm-insights — local remote updated)
- **Live site:** https://law-firm-feedback-saas.onrender.com (Render — may be on stale deploy, see Render section below)
- **Local git remote:** confirmed pointing to DrewYomantas/Clarion as of 2026-03-21

### Render Deploy Status (ACTION NEEDED)
Render is likely deploying an old commit. The repo was renamed on GitHub and Render may have lost its webhook.
To fix: Render dashboard → service Settings → Build & Deploy → reconnect to `DrewYomantas/Clarion` → Manual Deploy → Deploy latest commit.
Latest commit to deploy: `fa276e5` (chore: update GitHub link to DrewYomantas/Clarion)

---

## Repository Structure
- `backend/` — Flask monolith, APIs, services, templates, pdf_generator
- `frontend/src/` — React/TypeScript/Vite SPA (marketing + authenticated workspace)
- `Clarion-Agency/` — Agent office runtime, per-division agents, memory, execution layer
- `automation/calibration/` — Calibration pipeline scripts
- `data/calibration/` — Calibration inputs and synthetic reviews (run artifacts gitignored)
- `docs/` — This doc set
- `tools/` — Smoke test helpers, seeded workspace tooling

## Major Subsystems (Verified File Paths)
- Feedback ingestion: `backend/app.py`, `frontend/src/pages/Upload.tsx`
- Governance signal engine: `backend/services/governance_insights.py`
- Calibration: `automation/calibration/`, `backend/services/benchmark_engine.py`
- Brief/PDF output: `backend/pdf_generator.py` + report PDF routes in `backend/app.py`
- Action tracking: `frontend/src/pages/ExecutionPage.tsx` + action APIs in `backend/app.py`
- Landing: `frontend/src/pages/Index.tsx`, `frontend/src/components/landing/`
- Agent office: `Clarion-Agency/` — 21-agent autonomous ops system, approval queue wired into dashboard

---

## Current Phase

**Design system reset complete (2026-03-21).** Workspace canvas warmed, card elevation increased, sidebar identity upgraded with SVG mark + Newsreader wordmark + gold accent, topbar refined. Build passes clean.

**Repo hygiene pass complete (2026-03-21).** Junk untracked, .gitignore overhauled, README rewritten, ENGINEERING_PRACTICES.md created.

**Bug fixed (2026-03-21).** Email verification 500 crash fixed — removed spurious `RETURNING user_id` from verify-email upsert.

**Active design direction:** Dashboard workspace overhaul — premium, modern, "Mercury Bank meets a Cravath partner meeting." See NORTH_STAR.md for full design direction. See screenshot audit below for specific issues.

---

## Canonical Brief Section Spine (Locked)

```
1. Leadership Briefing
2. Signals That Matter Most
3. Assigned Follow-Through
4. Decisions & Next Steps
5. Supporting Client Evidence
```

All output surfaces aligned: on-screen brief, email preview modal, inline email HTML, Jinja2 email template, PDF reference layout, PDF generator.

---

## Dashboard Workspace — Screenshot Audit (2026-03-21)

A full walk-through of the authenticated workspace was captured in screenshots. Here is the honest assessment of every surface, ready for the next pass.

### What's Working Well (Don't Break)
- Sidebar: CLARION wordmark with SVG mark, gold "CLIENT INTELLIGENCE" label, gold active nav indicator — this looks sharp, keep it
- Navigation IA is correct: Workspace Home → Upload Cycle → Signals → Follow-Through → Briefs → Approval Queue
- First-run empty state (Image 1) — copy is clear, 3-step flow is readable, layout is clean
- Upload page (Images 2-3) — plan limit warning is clear, upload success state with cycle details is functional
- "Supporting Cycle Context" section (Image 8) — the 4-card governance cycle rail (Evidence → Signals → Follow-Through → Briefs) is a genuinely good component, keep it
- Approval Queue (Images 11-12) — this is the Agent Office command center. The dark card layout with PENDING badges, Outreach/Content/Account Setup tabs, and the side-panel detail view (Approve / Hold / Reject) is the best-looking surface in the workspace. This is the design direction to pull FROM for the rest of the dashboard.

### Critical Issues to Fix (Next Pass Priority Order)

**ISSUE 1 — Dashboard page is too long / no hierarchy**
The workspace home scrolls through: header → baseline notice → history notice → anchor bar → brief card + posture card → attention now divider → guidance card → suggested actions (3 cards) → follow-through card → recent follow-through card → supporting context divider → since last review → recent briefs → oversight band → governance cycle rail → partner brief panel → escalations → workspace reference divider → plan card.
That is ~18 distinct sections on one page. A managing partner will not scroll this. The brief is buried.
Fix: Collapse to 3 visual tiers maximum. Tier 1 = the brief (dominant, takes up first viewport). Tier 2 = what needs action now (compact). Tier 3 = supporting context (collapsed or linked).

**ISSUE 2 — Meeting View shows blank page (Image 5)**
When Meeting View is toggled on, the dashboard renders only the header and breadcrumb — the entire content area is empty white. This is a broken feature. The Meeting View toggle (`partnerMode` state in Dashboard.tsx) is not rendering its content.
Fix: Read the `partnerMode` conditional in Dashboard.tsx and find why the meeting-view content block is not rendering. This is likely a conditional render that evaluates to null.

**ISSUE 3 — Date/time display appears wrong**
User flagged that time and date are wrong. The topbar shows "Last processed Mar 22, 2026, 04:02 AM" — this is likely a timezone display issue (server stores UTC, frontend displays UTC without local conversion).
Fix: Audit `formatDateTime` in Dashboard.tsx — check if it uses `toLocaleString` with timezone awareness or is just rendering raw UTC.

**ISSUE 4 — Approval Queue is visible to all authenticated users**
The Approval Queue (Images 11-12) contains Agent Office output: outreach drafts, LinkedIn posts, prospect target lists, content articles. This is Clarion's internal operations data — it should NOT be visible to law firm users. It is currently in the sidebar and accessible at `/dashboard/approval-queue` for all users.
Fix: Gate the Approval Queue route and sidebar item behind a `is_founder` or `is_admin` flag. Law firm workspace users should never see this page.

**ISSUE 5 — "Create Governance Action" button styling (Image 6)**
The dark navy CTA buttons ("Create Governance Action", "Open actions workspace") are heavy and generic. They read as "generic SaaS button" not "Clarion governance action." Minor but visible.
Fix: In the next visual pass, these get the same refinement treatment as the rest of the card components.

**ISSUE 6 — Suggested actions cards have left amber border but no surface treatment**
The suggested action cards (Image 6) use a left amber border accent but the card itself is plain white. High-severity items should feel more urgent — a very subtle warm amber tint on the card surface would communicate urgency without shouting.

**ISSUE 7 — "Firm Reputation Risk Score: 80/100" with breakdown (Image 9)**
This score (80/100, Communication: Moderate, Professionalism: Moderate, Case Outcomes: Moderate) uses the word "Moderate" three times and shows a score of 80 that seems disconnected from the "High Risk" posture shown elsewhere on the same page. This is confusing — if everything is Moderate why is the posture "High Exposure"? Either the score calculation or the label needs audit.

**ISSUE 8 — "Pricing Model Report - Mar 22 (#9)" report name (Image 3)**
The auto-generated report name includes "Pricing Model" which is a test artifact from the upload CSV used. In production, report naming should be cleaner. This is likely from the test data used, not a bug — but it should be addressed in the upload flow to generate better default names.

### Visual Design Assessment (vs. Target Direction)

Current state vs. target ("Mercury Bank meets Cravath partner meeting"):
- Canvas color: ✓ Warm parchment applied, significant improvement over cold gray
- Card elevation: ✓ Improved, cards now sit on the canvas
- Sidebar: ✓ Identity moment working, gold accent correct
- Topbar: ✓ Warm and refined
- Dashboard content: ✗ Still feels like a long admin report, not a premium command center
- Brief as visual anchor: ✗ The brief is one card among 18. It needs to be THE dominant element in the first viewport
- Typography: ✗ No Newsreader serif moments in the workspace yet (only in the brief artifact itself)
- Meeting Mode: ✗ Broken — must fix before any demo

The Approval Queue (dark card layout) and the 4-card governance rail are the two best-looking components. The next design pass should pull visual language FROM those and apply it to the dashboard primary tier.

---

## Active / Next Passes (Priority Order)

### IMMEDIATE (must fix before showing to anyone)
1. **Meeting Mode broken** — ✅ FIXED (d95877d). partnerMode block now renders brief-first view with Open/PDF buttons, 3-stat row, cycle attention strip.
2. **Approval Queue access control** — ✅ FIXED (d95877d). Gated at nav (WorkspaceLayout), route (App.tsx AdminRoute), and page level (ApprovalQueuePage). NOTE: In DEV_MODE, backend returns is_admin=true for all sessions — gate is correct, backend dev behavior expected.

### NEXT DESIGN PASS
3. **Dashboard hierarchy collapse** — Brief as dominant first-viewport element, everything else secondary/tertiary. Reference: Approval Queue dark card language + governance cycle rail as design inspiration within the product.
4. **Date/timezone display** — Audit formatDateTime in Dashboard.tsx for UTC vs local display.

### SUBSEQUENT PASSES
5. **Signals page** — Does it read as governance-cycle evidence or detached data list?
6. **ReportsPage** — Brief list presentation quality
7. **Meeting Mode elevation** — Once unbroken, make it genuinely premium (full-screen, artifact-forward, one-click)
8. **Logo iteration** — Current logo (GPT-generated C with gold pivot needle) is good DNA but needs flat variant and needs to work without the "CLIENT INTELLIGENCE" descriptor

### LATER
9. **Domain cutover** to `clarion.co` (checklist in this file below)
10. **Render reconnect** to `DrewYomantas/Clarion` (see Render section above)
11. **Agent Office audit** — 21-agent system is real and in play, but was built early. Needs a full read-through and honest assessment of what's working vs placeholder.
12. **Code splitting** — 911kB JS bundle (pre-existing warning, not urgent)
13. **app.py → Flask blueprints** (17k lines, planned for when stable collaborator available)

---

## Agent Office (Clarion-Agency/)

The `Clarion-Agency/` folder contains a 21-agent autonomous operations system for running Clarion's own business. Divisions: Prospect Intelligence, Outbound Sales, Content Engine, Product Experience, Executive (Chief of Staff). The Approval Queue in the dashboard is the founder review interface for staged agent output.

**Current state:** Agents are structured and configured. SMTP credentials not set, LinkedIn/social API tokens missing. Several data files are placeholder-only. The system produces output (35 items pending in queue as of 2026-03-21) but cannot send/publish without credentials.

**Agent count: 25 agents across 10 divisions.** This is the verified count from `agent_org.md`. Do not use any other number.

**Audit needed:** System was built early in the project. A full file-by-file read is needed to assess what's actually functional vs skeleton. Schedule as a dedicated session.

**IMPORTANT:** The Approval Queue must be gated from law firm users before any pilot. See Issue 4 above.

---

## Locked Architecture Truths (Live)

**Calibration engines are separate:**
- `backend/services/benchmark_engine.py` — live calibration path; phrase/guard changes go here
- `backend/services/bench/deterministic_tagger.py` — standalone harness only, not called by Flask

**Data layer:** SQLite with Postgres compatibility scaffolding. Render Postgres is production DB.

**Stack:** Flask monolith backend + React/TypeScript/Vite frontend. Deployed on Render.

---

## Operator Smoke State

Full local smoke pass confirmed 2026-03-18. Clean seeded Team workspace smoke confirmed same day.
Verified segments: login → CSV upload → report detail → signals → action creation → PDF preview → partner-brief email send.
Email verification bug fixed 2026-03-21 (RETURNING clause crash).

---

## Calibration State (Stable — Hold)

Last fresh live run: `data/calibration/runs/20260317_223428`. Agreement rate 43.4% (62/143). Label variance confirmed as AI nondeterminism, not engine defect. Hold stable.

---

## Public Surface State

- `/` — V3 landing, governance-brief-centered hierarchy
- `/demo/reports/:id` — canonical public proof artifact (sample governance brief)
- `/demo` — secondary mechanics proof
- `/features`, `/how-it-works`, `/pricing`, `/security`, `/privacy`, `/terms` — React-owned

---

## Domain Cutover Checklist (Pending — clarion.co)

- [ ] Render custom domain configuration
- [ ] Stripe webhook URL update
- [ ] Resend domain verification
- [ ] Frontend `VITE_API_BASE_URL` update
- [ ] CORS allowed origins update in `backend/app.py`

---

## Last Completed Passes (This Session — 2026-03-24)
1. Pass 1 — Meeting View fixed (partnerMode block added to Dashboard.tsx)
2. Pass 1 — Approval Queue gated behind is_admin (WorkspaceLayout nav, App.tsx route, ApprovalQueuePage defense-in-depth)
3. Pass 1 — Date/time display confirmed correct (toLocaleString already uses browser local TZ — no bug)
4. Pass 2 — Dashboard hierarchy: suppressed "anchored to" metadata strip, renamed brief card title to "Current governance brief", removed PartnerBriefPanel (80/100 score — contradicts posture label, needs engine audit), cleaned "Brief handoff" label copy
5. Commit: d95877d
6. Pass 3 — Brief card promoted to full-width first-viewport anchor; FirmGovernanceStatus demoted to secondary row below it (removed xl:grid-cols side-by-side layout from Tier 1). Dashboard.tsx only. Build clean.
7. Commit: 5a83f3d

## Last Completed Passes (This Session — 2026-03-21)
1. Design system token reset — warm canvas, card elevation, sidebar identity, topbar
2. verify-email RETURNING crash fix
3. Repo hygiene — .gitignore overhaul, README rewrite, ENGINEERING_PRACTICES.md created
4. Git remote updated to DrewYomantas/Clarion
5. Dashboard screenshot audit documented (this file)
