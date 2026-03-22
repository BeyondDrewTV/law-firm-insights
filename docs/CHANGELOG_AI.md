# AI Pass Changelog

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
