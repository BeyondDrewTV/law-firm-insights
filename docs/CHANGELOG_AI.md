# AI Pass Changelog

## 2026-03-24 (continued) - Pass 7 — ExecutionPage Governance-Cycle Framing Elevation

### Commit
- `7e02fd1` — design: execution page governance-cycle framing — posture card, brief context, PageWrapper copy

### Files Changed
- `frontend/src/pages/ExecutionPage.tsx`
- `docs/PROJECT_STATE.md`
- `docs/CHANGELOG_AI.md`
- `docs/CURRENT_BUILD.md`

### What Changed
Six targeted copy-only changes. No structural, logic, or API changes.

- **PageWrapper eyebrow**: `"Follow-through"` → `"Assigned Follow-Through"` — matches §3 of the canonical brief spine exactly, tying the page directly to the governance artifact.
- **PageWrapper description**: replaced generic task-state framing with artifact-first framing — leads with what the page is (the brief's follow-through record), then what to do.
- **Posture card label**: `"Current follow-through posture"` → `"Follow-through posture for this cycle"` — grounds the card in the current cycle rather than a free-floating status.
- **Posture card h2**: `"Keep the current cycle credible before the next partner review."` → `"What needs partner attention before the brief goes into a meeting."` — partner-meeting framing rather than internal-ops framing.
- **Brief context card label**: `"Current brief context"` → `"Current governance brief"` — names the artifact directly.
- **Brief context card copy**: rewritten to make the directional link explicit — follow-through status feeds into the brief, not just "aligned."
- **Tab "firm-wide" label**: `"All follow-through"` → `"Brief record"` — names the default tab as the artifact's record.
- **Default-tab section sub-copy**: opening sentence anchors the view to the brief before the directive copy.

### Verification
- `npm run build` clean. 1823 modules. Pre-existing 907kB bundle warning unchanged.
- No backend changes. No TypeScript type changes. No logic or filter changes.


## 2026-03-21 - Landing Narrative-First Visual Modernization Pass

### Files Changed
- `frontend/src/pages/Index.tsx`
- `frontend/src/components/SiteNav.tsx`
- `frontend/src/components/landing/LandingHeroSection.tsx`
- `frontend/src/components/landing/LandingOperatingPreview.tsx`
- `frontend/src/index.css`
- `docs/PROJECT_STATE.md`
- `docs/CURRENT_BUILD.md`
- `docs/CHANGELOG_AI.md`

### What Changed
- Tightened landing visual hierarchy while preserving the existing narrative spine and section order.
- Increased first-glance premium contrast with stronger landing-specific surface treatment (hero framing, card depth, workflow rail paneling, and clearer nav interaction states).
- Rebalanced hero composition so the governance brief artifact carries more visual authority without changing product meaning or CTA structure.
- Kept motion restrained and compatible with the existing reduced-motion behavior.

### Verification
- `npm run build` in `frontend/` — passed
- Pre-existing non-blocking warning remains: Vite large chunk size warning

## 2026-03-21 - Docs-System Hardening + Codex Operating Contract Pass

### Files Changed
- `docs/NORTH_STAR.md`
- `docs/PROJECT_STATE.md`
- `docs/AI_WORKING_RULES.md`
- `docs/CHANGELOG_AI.md`

### What Changed
- Tightened doc-role boundaries so each core doc has one explicit responsibility.
- Reduced duplication in `PROJECT_STATE.md` by removing repeated repository/subsystem blocks and retaining a single authoritative live-state map.
- Added an explicit docs-system contract and stricter Codex execution rules in `AI_WORKING_RULES.md` (ownership confirmation, diagnosis-first, runtime verification requirement, and stop/report when cause is unconfirmed).
- Added a recommendation-only lane format for tool/connector/workflow opportunities with explicit approval required before adoption.
- Replaced live phase text in `NORTH_STAR.md` with a boundary rule that keeps current-state tracking in `PROJECT_STATE.md`.

### Verification
- Docs-only pass (no application code changed, no build required)

## 2026-03-21 - Landing Modern-Motion Polish Pass

### Files Changed
- `frontend/src/pages/Index.tsx`
- `frontend/src/components/SiteNav.tsx`
- `frontend/src/components/landing/LandingHeroSection.tsx`
- `frontend/src/components/landing/LandingTrustSection.tsx`
- `frontend/src/components/landing/LandingWorkflowSection.tsx`
- `frontend/src/components/landing/LandingOutputsSection.tsx`
- `frontend/src/components/landing/LandingAccountabilitySection.tsx`
- `frontend/src/components/landing/LandingMeetingSection.tsx`
- `frontend/src/components/landing/LandingFinalSection.tsx`
- `frontend/src/index.css`
- `docs/PROJECT_STATE.md`
- `docs/CURRENT_BUILD.md`
- `docs/CHANGELOG_AI.md`

### What Changed
- Added a lightweight landing-only IntersectionObserver reveal pass so hero and section content enter with restrained fade-and-rise motion.
- Tuned hero entrance pacing so the eyebrow, headline, supporting copy, CTA row, and governance brief preview settle with a cleaner premium rhythm.
- Added restrained hover and press polish to public nav links, public CTA surfaces, and landing cards without changing the underlying narrative or route structure.
- Added reduced-motion fallbacks so all landing reveals and hover transforms collapse to static presentation when motion reduction is preferred.

### Verification
- `npm run build` in `frontend/`

## 2026-03-21 - Landing Hero Refinement Pass

### Files Changed
- `frontend/src/components/landing/LandingHeroSection.tsx`
- `docs/CURRENT_BUILD.md`
- `docs/CHANGELOG_AI.md`

### What Changed
- Refined the landing hero with a slightly wider editorial text measure, calmer headline scale, looser headline leading, and more vertical breathing room between the eyebrow, headline, body copy, CTAs, and supporting proof notes.
- Rebalanced the hero grid so the left narrative column feels less compressed while the right-side governance brief preview keeps its visual authority.
- Preserved the existing headline, CTA hierarchy, route structure, and product framing. This was a typography-and-layout pass only.

### Verification
- `npm run build` in `frontend/`

## 2026-03-19 - Governance Brief Output Unification Pass

### Files Changed
- `frontend/src/components/reports/EmailBriefPreviewModal.tsx`
- `frontend/src/pages/ReportDetail.tsx`
- `frontend/src/components/pdf/PdfDeckPreview.tsx`
- `frontend/src/pages/DashboardPdfPreview.tsx`
- `backend/templates/partner_brief_email.html`
- `backend/pdf_generator.py`
- `docs/PROJECT_STATE.md`
- `docs/CURRENT_BUILD.md`
- `docs/CHANGELOG_AI.md`

### What Changed
- Aligned all brief output surfaces to the canonical 5-section spine established by `ReportDetail.tsx`:
  Leadership Briefing → Signals That Matter Most → Assigned Follow-Through → Decisions & Next Steps → Supporting Client Evidence

**EmailBriefPreviewModal.tsx**
- Swapped tile order so Decisions & Next Steps (§4) appears before Supporting Client Evidence (§5), matching canonical brief order.

**ReportDetail.tsx**
- Swapped `<tr>` row order in `emailHtmlSummary` inline HTML so Decisions & Next Steps precedes Supporting Client Evidence.

**partner_brief_email.html**
- Relabeled `Metrics` → `Leadership Briefing`
- Relabeled `Top Client Issue` → `Signals That Matter Most`
- Added explicit `Decisions & Next Steps` section label (was `Recommended Discussion`)
- Added explicit `Supporting Client Evidence` section label (quote was previously embedded unlabeled inside Top Client Issue section)
- Changed header eyebrow from `Clarion Client Experience Brief` → `Clarion Governance Brief`
- Changed header title from `Partner Briefing Summary` → `Partner Governance Brief`
- Changed CTA text from `Open Full Dashboard` → `Open Governance Brief`

**PdfDeckPreview.tsx**
- Added `PdfPreviewDecision` type and `decisions` prop
- Added `Decisions & Next Steps` render section between Assigned Follow-Through and Supporting Client Evidence
- Restored missing closing `</div>` tag dropped during prior partial edit

**DashboardPdfPreview.tsx**
- Passed `previewDetail.recommended_changes` mapped as `decisions` prop to `PdfDeckPreview`

**pdf_generator.py** (heading strings only — no logic changed)
- Replaced 5 agenda items with canonical section names
- Replaced `Firm Risk Posture` h2 with `Leadership Briefing`
- Replaced `Governance Signals Summary` h2 with `Signals That Matter Most`
- Replaced `Required Decisions` h2 with `Decisions & Next Steps`
- Replaced `Open Governance Actions` h1 (execution page) with `Assigned Follow-Through`
- Removed 6th agenda item (`- Client Signals`) — canonical spine has 5 sections

### Verification
- `npm run build` in `frontend/` — passed (pre-existing large-chunk warning remains non-blocking)
- `python -m py_compile backend/pdf_generator.py` — PARSE_OK

### What Remains Split
- Backend PDF sub-labels (`Exposure & Escalation`, `Execution Summary`, `Since Last Brief`) are internal operational labels within canonical sections — not competing section spine, acceptable
- Inline email summary (`emailHtmlSummary`) covers 4 of 5 sections — no Assigned Follow-Through row, acceptable for summary format
- `pdf_generator.py` still uses `Exposure & Escalation` as a sub-heading within the Leadership Briefing section — deeper data-plumbing unification deferred


## 2026-03-18 - Public Proof + Brief Continuity Pass

### Files Changed
- `frontend/src/components/SiteNav.tsx`
- `frontend/src/components/landing/LandingHeroSection.tsx`
- `frontend/src/components/landing/LandingFinalSection.tsx`
- `frontend/src/components/pdf/PdfDeckPreview.tsx`
- `frontend/src/components/reports/EmailBriefPreviewModal.tsx`
- `frontend/src/content/landingV3.ts`
- `frontend/src/data/sampleFirmData.ts`
- `frontend/src/pages/Dashboard.tsx`
- `frontend/src/pages/DashboardPdfPreview.tsx`
- `frontend/src/pages/DemoPdfPreview.tsx`
- `frontend/src/pages/DemoReportDetail.tsx`
- `frontend/src/pages/DemoWorkspace.tsx`
- `frontend/src/pages/ExecutionPage.tsx`
- `frontend/src/pages/Features.tsx`
- `frontend/src/pages/HowItWorks.tsx`
- `frontend/src/pages/Pricing.tsx`
- `frontend/src/pages/ReportDetail.tsx`
- `frontend/src/pages/ReportsPage.tsx`
- `frontend/tailwind.config.ts`
- `docs/PROJECT_STATE.md`
- `docs/CURRENT_BUILD.md`
- `docs/CHANGELOG_AI.md`

### What Changed
- Tightened the public proof spine so the sample brief route is now the clearest public proof artifact.
- Reframed `/demo` as secondary mechanics proof rather than a competing primary proof route.
- Reworked `/dashboard` so the strongest top action is opening the current brief.
- Reworked `/dashboard/actions` to reference the current brief packet more directly.
- Tightened frontend output continuity by aligning PDF/email reference language to the canonical 5-section brief.
- Fixed active Tailwind font drift (`Manrope` as sans token, `Newsreader` as serif display token).

### Verification
- `npm run build` in `frontend/`

## 2026-03-18 - Upload-To-First-Brief UX Alignment Pass

### Files Changed
- `frontend/src/pages/Upload.tsx`
- `frontend/src/pages/Onboarding.tsx`
- `frontend/src/components/billing/UploadUsageBar.tsx`
- `docs/PROJECT_STATE.md`
- `docs/CURRENT_BUILD.md`
- `docs/CHANGELOG_AI.md`

### What Changed
- Reworked `/upload` to lead from one CSV into the current report packet.
- Rebuilt post-upload success state with direct links into report, workspace home, and follow-through.
- Onboarding now opens first report directly when setup includes a real CSV upload.
- Replaced upload-usage helper with ASCII-safe version.

### Verification
- `npm run build` in `frontend/`
- live browser check on `/upload`

## 2026-03-18 - Report-Detail Governance-Brief UX Alignment Pass

### Files Changed
- `frontend/src/pages/ReportDetail.tsx`
- `frontend/src/components/WorkspaceLayout.tsx`
- `docs/PROJECT_STATE.md`
- `docs/CURRENT_BUILD.md`
- `docs/CHANGELOG_AI.md`

### What Changed
- Reworked `/dashboard/reports/:id` to open as a governance brief artifact.
- Added Leadership Briefing section with cycle readiness, top signal, follow-through posture, first decision, and briefing bullets.
- Reordered report packet to: leadership briefing → signals → follow-through → decisions → evidence.

### Verification
- `npm run build` in `frontend/`
- live browser check on `/dashboard/reports/8`

## 2026-03-18 - Actions Follow-Through UX Alignment Pass

### Files Changed
- `frontend/src/pages/ExecutionPage.tsx`
- `frontend/src/components/actions/ActionCard.tsx`
- `frontend/src/components/WorkspaceLayout.tsx`
- `docs/PROJECT_STATE.md`
- `docs/CURRENT_BUILD.md`
- `docs/CHANGELOG_AI.md`

### What Changed
- Reworked `/dashboard/actions` to lead with follow-through accountability posture.
- Added top posture block for overdue, unowned, blocked, and active-needs-review work.
- Demoted filters to secondary refinement panel.

### Verification
- `npm run build` in `frontend/`
- live browser check on `/dashboard/actions`

## 2026-03-18 - Dashboard Workspace-Home Refinement Pass

### Files Changed
- `frontend/src/pages/Dashboard.tsx`
- `docs/PROJECT_STATE.md`
- `docs/CURRENT_BUILD.md`
- `docs/CHANGELOG_AI.md`

### What Changed
- Reworked `/dashboard` to lead with current cycle and latest brief.
- Demoted OversightBand, GovernanceNarrativeRail, and recent-brief history into supporting-context tier.

### Verification
- `npm run build` in `frontend/`

## 2026-03-18 - First Authenticated Product UX Alignment Pass

### Files Changed
- `frontend/src/components/WorkspaceLayout.tsx`
- `frontend/src/pages/Dashboard.tsx`
- `frontend/src/pages/Onboarding.tsx`
- `frontend/src/pages/Login.tsx`
- `frontend/src/pages/Signup.tsx`
- `frontend/src/pages/Upload.tsx`
- `frontend/src/index.css`
- `docs/PROJECT_STATE.md`
- `docs/CURRENT_BUILD.md`
- `docs/CHANGELOG_AI.md`

### What Changed
- Reframed authenticated workspace shell around current-cycle language.
- Updated sidebar labels and grouping to governance-cycle nav model.
- Updated login/signup/onboarding to governance-cycle framing.

### Verification
- `npm run build` in `frontend/`

## 2026-03-18 - Public-Site Polish And Consistency Cleanup

### Files Changed
- `frontend/src/components/SiteNav.tsx`
- `frontend/src/pages/Privacy.tsx`
- `frontend/src/pages/Terms.tsx`
- `frontend/src/pages/Contact.tsx`
- `frontend/src/pages/Docs.tsx`
- `frontend/src/pages/DemoWorkspace.tsx`
- `frontend/src/pages/DemoReportDetail.tsx`
- `frontend/src/pages/DemoPdfPreview.tsx`
- `docs/PROJECT_STATE.md`
- `docs/CURRENT_BUILD.md`
- `docs/CHANGELOG_AI.md`

### What Changed
- Polished all user-reachable public React routes to one coherent Clarion system.
- Renamed public demo experience to `sample workspace` throughout.
- Fixed stale `isDarkMarketingChrome` references in `SiteNav.tsx`.

### Verification
- `npm run build` in `frontend/`

## 2026-03-18 - Secondary Public React Route Alignment

### Files Changed
- `frontend/src/components/PageLayout.tsx`
- `frontend/src/components/SiteNav.tsx`
- `frontend/src/components/MarketingProofBar.tsx`
- `frontend/src/components/PricingSection.tsx`
- `frontend/src/data/pricingPlans.ts`
- `frontend/src/pages/Features.tsx`
- `frontend/src/pages/HowItWorks.tsx`
- `frontend/src/pages/Pricing.tsx`
- `frontend/src/pages/Security.tsx`
- `frontend/src/index.css`
- `docs/PROJECT_STATE.md`
- `docs/CURRENT_BUILD.md`
- `docs/CHANGELOG_AI.md`

### What Changed
- Rebuilt shared public shell around lighter V3 editorial chrome.
- Rewrote `/features`, `/how-it-works`, `/pricing`, `/security` around canonical governance-brief positioning.
- Fixed React key warning on pricing comparison table.

### Verification
- `npm run build` in `frontend/`

## 2026-03-18 - In-House V3 Landing Implementation On Canonical React Route

### Files Changed
- `frontend/index.html`
- `frontend/src/pages/Index.tsx`
- `frontend/src/index.css`
- `frontend/src/content/landingV3.ts`
- `frontend/src/components/landing/Landing*.tsx` (all 7 section components)
- `docs/PROJECT_STATE.md`
- `docs/CURRENT_BUILD.md`
- `docs/CHANGELOG_AI.md`

### What Changed
- Implemented approved V3 landing on canonical React route `/`.
- Governance-brief-centered, partner-facing hierarchy: hero → trust → workflow → outputs → accountability → meeting → CTA.

### Verification
- `npm run build` in `frontend/`
- live browser check at `http://127.0.0.1:8081/`

## 2026-03-18 - Lovable Purge + Canonical Landing Surface Consolidation

### Files Changed
- `backend/app.py`
- `README.md`
- `docs/PROJECT_STATE.md`
- `docs/CURRENT_BUILD.md`
- `docs/CHANGELOG_AI.md`

### What Changed
- Flask overlapping public routes (`/features`, `/how-it-works`, `/pricing`, `/security`, `/privacy`, `/terms`) now serve built React app when `frontend/dist` exists; legacy templates remain fallback only.

### Verification
- `python -m py_compile backend/app.py`

## 2026-03-18 - Release-Candidate Stabilization + Clean Seeded Smoke Confirmation

### Files Changed
- `tools/ensure_e2e_user.py`
- `tools/reset_e2e_state.py`
- `frontend/package.json`
- `frontend/src/components/ui/button.tsx`
- `frontend/src/components/governance/PageTabs.tsx`
- `frontend/src/components/governance/GovernanceCard.tsx`
- `frontend/vite.config.ts`
- `README.md`
- `tools/README.md`
- `docs/PROJECT_STATE.md`
- `docs/CURRENT_BUILD.md`
- `docs/CHANGELOG_AI.md`

### What Changed
- Seeded smoke tools now resolve same DB as running app.
- Clean Team workspace smoke confirmed: login → upload → report → action → PDF → email.
- Removed Tailwind ambiguous utility warnings in shared governance/button components.

### Verification
- `npm run build` in `frontend/`
- Clean seeded smoke: all API calls 200/201.

## 2026-03-18 - Operator Workflow / Release Smoke Pass

### Files Changed
- `frontend/vite.config.ts`
- `frontend/src/api/authService.ts`
- `backend/app.py`
- `backend/services/email_service.py`
- `docs/PROJECT_STATE.md`
- `docs/CURRENT_BUILD.md`
- `docs/CHANGELOG_AI.md`

### What Changed
- Vite `/api` proxy now configurable.
- Restored missing upload-success helpers in `backend/app.py`.
- Fixed naive/aware datetime comparison in exposure snapshot and PDF path.
- Fixed Resend email attachment serialization.

### Verification
- Full local smoke pass confirmed all workflow segments.

## 2026-03-15 - Live Tagger Validation + Definitive Calibration Pass
- Live phrase work moved from `bench/deterministic_tagger.py` into `benchmark_engine.py`.
- Stored run `20260315_200410`: `27.3%` clean-review agreement (`39/143`).

## Prior Notable Passes
- `b9a8a97` - calibration wave 2 phrase additions + bug fixes
- `3f6aba0` - outbound email quality and content SEO improvements
- `d2647c5` - calibration + agent office pipeline fix
- `30cb290` - approval queue dashboard/backend integration pass

## 2026-03-24 - Dashboard Hierarchy + Reports Brief Library Elevation

### Commits
- `d95877d` — fix: meeting mode render + approval queue admin gate
- `49f7cba` — design: align Dashboard to canonical governance token language
- `5a83f3d` — layout: brief card full-width first-viewport anchor, FirmGovernanceStatus demoted
- `8ccd5d2` — design: reduce FirmGovernanceStatus visual weight to secondary supporting context
- `8a5974b` — docs: record Pass 4 state
- `733fe87` — design: reports page brief library elevation — framing, tab labels, CTA hierarchy

### Files Changed
- `frontend/src/pages/Dashboard.tsx`
- `frontend/src/components/workspace/FirmGovernanceStatus.tsx`
- `frontend/src/pages/ReportsPage.tsx`
- `frontend/src/components/governance/GovernanceBriefCard.tsx`
- `frontend/src/layouts/WorkspaceLayout.tsx`
- `frontend/src/App.tsx`
- `docs/PROJECT_STATE.md`

### What Changed

**Pass 1 — Meeting Mode + Approval Queue gate (d95877d)**
- `partnerMode` conditional in Dashboard.tsx was rendering null — added the brief-first meeting view block (brief card, PDF button, 3-stat row, cycle attention strip).
- Approval Queue gated at three layers: WorkspaceLayout nav (sidebar item hidden for non-admin), App.tsx route (AdminRoute wrapper), ApprovalQueuePage defense-in-depth check. Law firm users cannot reach `/dashboard/approval-queue`.
- Date/time display confirmed correct — `toLocaleString` already uses browser local timezone, no bug.

**Pass 2 — Dashboard token language (49f7cba)**
- Suppressed anchored-to metadata strip (cluttered, low value).
- Renamed brief card title to "Current governance brief".
- Removed PartnerBriefPanel (80/100 score contradicts posture label — needs engine audit before showing again).
- Cleaned "Brief handoff" label copy.

**Pass 3 — Brief card first-viewport anchor (5a83f3d)**
- Brief card promoted to full-width first-viewport element.
- Removed `xl:grid-cols` side-by-side layout from Tier 1 — FirmGovernanceStatus now renders below the brief, not beside it.
- Dashboard.tsx only.

**Pass 4 — FirmGovernanceStatus visual weight reduction (8ccd5d2)**
- Title: `text-base font-semibold text-neutral-900` → `text-sm font-medium text-neutral-500`
- Status badge: `px-4 py-2 text-base font-semibold` → `px-3 py-1 text-sm font-medium`
- All 4 metric counters: `text-[36px] font-bold` → `text-[24px] font-semibold`
- Subtitle reworded: "Supporting posture context for the current brief."
- FirmGovernanceStatus.tsx only.

**Pass 5 — Reports/brief library elevation (733fe87)**
- ReportsPage eyebrow: "Leadership Artifact" → "Governance Brief Library"
- Description: generic feature copy → artifact-authoritative copy
- Section label: "Current brief library" → "About this library"
- Section h2: generic → "The governance brief is the primary artifact of each review cycle."
- Body copy: rewritten to position current brief as canonical, archive as reference
- Stat block: removed usage-meter "This month / plan limit" → replaced with "Latest" date stat
- Tab label: "Upcoming Meetings" → "Current Brief"
- Active brief eyebrow: "Prepared for next meeting" → "Active governance brief"
- GovernanceBriefCard: "View brief" promoted to primary dark CTA; "Download PDF" demoted to secondary; `isPast=false` card gets `border-t-2 border-t-[#0EA5C2]` top accent stripe.

### Verification
- All passes: `npm run build` clean. 1823 modules. Pre-existing 906kB bundle warning.
- No backend changes in any pass.
- No TypeScript type changes.


## 2026-03-24 (continued) - Signals Page Evidence Layer Reframe

### Commit
- `7929bbe` — design: signals page reframed as governance-cycle evidence layer

### Files Changed
- `frontend/src/pages/SignalsPage.tsx`
- `docs/PROJECT_STATE.md`

### What Changed
Signals page framing updated so the page reads as the evidence layer feeding the governance brief, not a generic data table or review surface.

- Eyebrow: "Review Surface" → "Client Feedback Evidence"
- Description: rewritten to position page as evidence source behind each governance brief
- Framing section h2: changed from directive ("Start with…") to descriptive ("Recurring client feedback patterns from [date] — the evidence this governance cycle is built on")
- Tab "All Signals" → "Current Cycle" (default tab)
- Tab "Triage" → "Needs Action"
- Section label for default tab: "Issue queue" → "Current cycle evidence"
- Sub-copy for default tab: reframed around governance-cycle purpose ("These are the patterns the governance brief is built on…")
- Sub-copy for needs-action tab: updated to connect to brief finalization workflow
- Bottom attribution: "Based on: …" → clean italic provenance line ("Evidence sourced from… cycle dated…")

No structural, logic, or API changes. SignalsPage.tsx only.

### Verification
- `npm run build` clean. 1823 modules. Pre-existing 906kB bundle warning unchanged.

