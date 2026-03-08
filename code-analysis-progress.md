# Clarion — Code Analysis Progress

## Source of Truth for Multi-Chat Continuity

Start every new chat with:
> "Continue code analysis for Clarion — read `code-analysis-progress.md`, use it as the source of truth, and proceed with the next unfinished phase."

---

## Confirmed Project Root Path

```
C:\Users\beyon\OneDrive\Desktop\CLARION\law-firm-insights-main
```

Filesystem tool allowed directories:
- `C:\Users\beyon\OneDrive\Desktop\CLARION`
- `C:\Users\beyon\OneDrive\Desktop\RECALLFLOW`

---

## Technology Stack (Confirmed)

- **Frontend:** React + TypeScript + Vite, Tailwind CSS, React Router v6, TanStack Query
- **Backend:** Python Flask (monolithic `app.py` — 17,289 lines)
- **Database:** SQLite (dev/current)
- **Payments:** Stripe
- **Auth:** Flask-Login, Flask-WTF CSRF, email verification, 2FA routes exist
- **Exports:** PDF generation (`pdf_generator.py` — 105 KB)
- **Scheduling:** APScheduler (optional, guarded import)
- **Rate limiting:** Flask-Limiter (optional, guarded import)
- **LLM:** Anthropic claude-sonnet-4-5 (review classification)

---

## Analysis Settings

- **Scope:** Full codebase, Clarion only
- **Pass style:** Conservative first
- **Tests:** Include in analysis but treat separately from production cleanup
- **Cleanup mode:** Analysis-only for now — no changes without explicit approval

---

## Phases

### ✅ Phase 1 — Discovery (COMPLETE)
Full directory tree mapped. See findings log below.

### ✅ Phase 2 — Backend Scanning (COMPLETE)

**What was scanned:**
- `backend/app.py` (all imports, all 100+ routes)
- All 14 service files in `backend/services/`
- `backend/governance.py`, `preflight_data.py`, `preflight_db.py`
- `backend/implementation_playbook.py`, `backend/smoke_check_option_b.py`
- `backend/api/index.py`
- `backend/templates/` — all 24 templates + emails/ subdirectory
- `backend/legacy/` — full directory

---

### ✅ Phase 3 — Frontend Scanning (IN PROGRESS — Pages Routing Audit COMPLETE)

**Scope:** `frontend/src/pages/`, `frontend/src/components/`, `frontend/src/utils/`, `frontend/src/lib/`, `frontend/src/content/`, `frontend/src/constants/`

**Priority tasks:**
1. Check if all 35 page components are reachable via App.tsx routes (some may be orphaned)
2. Audit `DashboardReports.tsx` — is this used or replaced by `ReportsPage.tsx`?
3. Audit root-level marketing components — are all referenced in Index/Features/HowItWorks?
4. Check `utils/` (freshnessStamp, reportFreshness, reputationScore, trendAnalysis) for usage
5. Check `content/` (coachingTips, marketingCopy) for usage
6. Check `hooks/useCountUp.ts` for usage
7. Check `lib/productFlags.ts` for usage
8. Scan `index.css` for dead CSS classes

**Suggested next prompt:**
> "Continue code analysis for Clarion — read `code-analysis-progress.md`, use it as the source of truth, and proceed with Phase 3: Frontend Scanning."

---

## Phase 3 Findings Log

### Phase 3 — Pass 4: Utils / Lib / Content / Hooks / Constants — Full Import Audit

**Directories scanned:** `utils/`, `lib/`, `content/`, `hooks/`, `constants/`, `config/`, `data/`
**Method:** Parallel content searches for every export name and import path across all `*.ts`/`*.tsx` in `frontend/src/`

---

#### `utils/freshnessStamp.ts` — ✅ DO NOT TOUCH

| Export | Used By |
|--------|---------|
| `formatFreshnessLine` | `pages/Upload.tsx` (live), `pages/DashboardReports.tsx` (orphaned) |
| `formatFreshnessTimestamp` | Only called internally by `formatFreshnessLine` |

**Rationale:** `Upload.tsx` is a routed, protected page — this file is live. When `DashboardReports.tsx` is deleted, this file still has a live consumer. Keep.

---

#### `utils/reportFreshness.ts` — 🔴 SAFE DELETE

| Export | Used By |
|--------|---------|
| `buildReportCreatedTimeline` | **0 external imports** — self-references only |
| `getReportsCreatedWithinDays` | **0 external imports** — self-references only |
| All exported types | **0 external imports** |

**Rationale:** Exhaustive search returns only the file's own content. Zero consumers anywhere in the frontend. Large file (~160 lines) with sophisticated date-bucketing logic — worth archiving in git history before deleting.

---

#### `utils/reputationScore.ts` — ✅ DO NOT TOUCH

| Export | Used By |
|--------|---------|
| `calculateReputationRiskScore` | `components/dashboard/PartnerBriefPanel.tsx` (live) |
| `type ReputationIssuePercentages` | `components/dashboard/PartnerBriefPanel.tsx`, `pages/Dashboard.tsx` (both live) |
| `type ReputationBreakdownItem`, `type ReputationScoreResult` | Internal / transitively live |

**Rationale:** Actively used in the live dashboard component tree. The prior session note about `Dashboard.tsx` importing only the type was partially correct — `PartnerBriefPanel.tsx` imports and calls the function.

---

#### `utils/trendAnalysis.ts` — ✅ DO NOT TOUCH

| Export | Used By |
|--------|---------|
| `analyzeTrendAlerts` | `components/dashboard/PartnerBriefPanel.tsx` (live, called directly) |
| `type TrendAlert` | Transitively live via PartnerBriefPanel |

**Rationale:** Live. Also imports `ReputationIssuePercentages` from `reputationScore.ts` — both files are part of the same active dashboard feature cluster.

---

#### `hooks/useCountUp.ts` — ✅ DO NOT TOUCH

| Export | Used By |
|--------|---------|
| `useCountUp` | `components/dashboard/FirmGovernanceStatus.tsx` (live, called 4× for animated stat counters) |

**Rationale:** Actively used in a live dashboard component. Prior classification as orphaned was incorrect — corrected here.

---

#### `content/coachingTips.ts` — 🔴 SAFE DELETE

| Export | Used By |
|--------|---------|
| `coachingTips` | **0 external imports** — single self-reference only |

**Rationale:** The entire file is a single `as const` object with 4 coaching tip strings. Never imported anywhere in the frontend. Pure dead content.

---

#### `content/marketingCopy.ts` — ✅ DO NOT TOUCH (partially live)

| Export | Used By |
|--------|---------|
| `coreNarrative` | `pages/Security.tsx` (live) |
| `implementationPlanDefinition` | `pages/Features.tsx` (live), `components/PricingSection.tsx` (live) |
| `trendStabilityDefinition` | `pages/HowItWorks.tsx` (live) |
| `confidenceDefinition` | `pages/HowItWorks.tsx` (live), `components/PricingSection.tsx` (live) |
| `coreAudience` | `components/StorySection.tsx` (orphaned — sole consumer) |
| `coreWhyNow` | **0 external imports** — dead export |
| `whyNowRiskLine` | **0 external imports** — dead export |
| `whyNowCycleLine` | **0 external imports** — dead export |

**Rationale:** File must be kept — 4 exports are live. Three exports (`coreWhyNow`, `whyNowRiskLine`, `whyNowCycleLine`) are dead within a live file — minor internal cleanup candidate. `coreAudience` becomes dead when `StorySection.tsx` is deleted.

---

#### `lib/productFlags.ts` — ✅ DO NOT TOUCH (confirmed in Pass 3)

| Export | Used By |
|--------|---------|
| `PRODUCT_FLAGS` | `pages/Security.tsx` (live — `PRODUCT_FLAGS.enableTwoFactorInV1` controls 2FA copy) |

**Rationale:** Confirmed live. Prior classification as orphaned was incorrect.

---

#### `lib/formatting.ts` — 🔴 SAFE DELETE

| Export | Used By |
|--------|---------|
| `formatCount` | **0 external imports** |
| `formatRating` | **0 external imports** |
| `formatPercent` | **0 external imports** |

**Rationale:** All three exported functions have zero consumers anywhere in the frontend. Function names are generic enough that a thorough name-level search was also run — still zero external hits. Dead utility file.

---

#### `lib/passwordStrength.ts` — ✅ DO NOT TOUCH

| Export | Used By |
|--------|---------|
| `evaluatePasswordStrength` | `pages/Signup.tsx` (live — drives password strength meter and progress bar) |
| `PasswordStrengthResult`, `PasswordStrengthLevel` | Transitively live |

**Rationale:** Actively used in the signup flow.

---

#### `lib/dateTime.ts` — ✅ DO NOT TOUCH

| Export | Used By |
|--------|---------|
| `formatApiDate` | `pages/ReportsPage.tsx`, `pages/ReportDetail.tsx`, `pages/DashboardBilling.tsx`, `pages/DashboardPdfPreview.tsx` |
| `formatApiDateTime` | `pages/ReportDetail.tsx`, `pages/DashboardReports.tsx` (orphaned) |
| `parseApiDate` | `pages/DashboardReports.tsx` (orphaned) |
| `toApiTimestamp` | `pages/DashboardPdfPreview.tsx` |
| `safeParseDate`, `toIsoDate`, `formatDate`, `formatDateTime` | Available, usage confirmed in live files |

**Rationale:** Heavily used across all dashboard pages. The orphaned `DashboardReports.tsx` consumes `formatApiDateTime` and `parseApiDate` — those exports remain live via other consumers after deletion.

---

#### `data/pricingPlans.ts` — ✅ DO NOT TOUCH

| Export | Used By |
|--------|---------|
| `pricingPlans` | `pages/Pricing.tsx` (live), `components/PricingSection.tsx` (live) |
| `PricingPlan`, `PricingPlanId` | Transitively live via both consumers |

**Rationale:** Core pricing data used by two live consumers.

---

#### `constants/displayLabels.ts` — ✅ DO NOT TOUCH

| Used By |
|---------|
| `pages/Dashboard.tsx`, `pages/ReportsPage.tsx`, `pages/ReportDetail.tsx`, `pages/SignalsPage.tsx`, `pages/SignalDetail.tsx`, `pages/ExecutionPage.tsx`, `pages/Onboarding.tsx`, `components/WorkspaceLayout.tsx`, `components/dashboard/GovernanceLoop.tsx`, `components/dashboard/SinceLastReview.tsx` |

**Rationale:** Used across the entire workspace/dashboard surface. Core shared label constants.

---

#### `config/planLimits.ts` — ✅ DO NOT TOUCH

| Used By |
|---------|
| `pages/Dashboard.tsx`, `pages/ReportsPage.tsx`, `pages/Upload.tsx`, `pages/DashboardPdfPreview.tsx` |

**Rationale:** Core plan enforcement logic used across all workspace pages.

---

#### `hooks/use-mobile.tsx`, `hooks/use-toast.ts` — ✅ DO NOT TOUCH (not searched — standard Shadcn hooks, expected live)

---

### Pass 4 Classification Summary

| File | Classification | Notes |
|------|---------------|-------|
| `utils/freshnessStamp.ts` | ✅ **DO NOT TOUCH** | Live in Upload.tsx |
| `utils/reportFreshness.ts` | 🔴 **SAFE DELETE** | Zero consumers anywhere |
| `utils/reputationScore.ts` | ✅ **DO NOT TOUCH** | Live in PartnerBriefPanel, Dashboard |
| `utils/trendAnalysis.ts` | ✅ **DO NOT TOUCH** | Live in PartnerBriefPanel |
| `hooks/useCountUp.ts` | ✅ **DO NOT TOUCH** | Live in FirmGovernanceStatus — prior orphan classification was wrong |
| `content/coachingTips.ts` | 🔴 **SAFE DELETE** | Zero consumers anywhere |
| `content/marketingCopy.ts` | ✅ **DO NOT TOUCH** | 4 live exports; 3 dead exports inside (minor cleanup candidate) |
| `lib/productFlags.ts` | ✅ **DO NOT TOUCH** | Live in Security.tsx — prior orphan classification was wrong |
| `lib/formatting.ts` | 🔴 **SAFE DELETE** | All 3 exports have zero consumers |
| `lib/passwordStrength.ts` | ✅ **DO NOT TOUCH** | Live in Signup.tsx |
| `lib/dateTime.ts` | ✅ **DO NOT TOUCH** | Heavily used across dashboard |
| `data/pricingPlans.ts` | ✅ **DO NOT TOUCH** | Live in Pricing.tsx + PricingSection |
| `constants/displayLabels.ts` | ✅ **DO NOT TOUCH** | Used across 10+ files |
| `config/planLimits.ts` | ✅ **DO NOT TOUCH** | Used across 4 live pages |

**Prior classification corrections in this pass:**
- `hooks/useCountUp.ts` — was logged as orphaned; confirmed live in `FirmGovernanceStatus.tsx`
- `lib/productFlags.ts` — was logged as orphaned; confirmed live in `Security.tsx` (already corrected in Pass 3, reaffirmed here)

---

### Phase 3 — Pass 3: Root-Level Marketing Components — Full Import Audit

**Scope:** All 30 root-level files in `frontend/src/components/` (excludes subdirectories: `actions/`, `dashboard/`, `governance/`, `pdf/`, `reports/`, `ui/`)
**Search method:** Content search for component name and import path patterns across all `*.ts` / `*.tsx` files in `frontend/src/`
**New components found (not in prior notes):** `MarketingProofBar.tsx`, `SecuritySection.tsx`, `SkipToMainContent.tsx`

---

#### Components confirmed LIVE — DO NOT TOUCH

| Component | Used By | Notes |
|-----------|---------|-------|
| `ShowDetails.tsx` | `pages/Security.tsx` (imported and JSX used 3×) | Collapsible detail section for security disclosures. Previously mis-classified as orphaned — corrected here. |
| `MarketingProofBar.tsx` | `pages/Docs.tsx`, `pages/Privacy.tsx`, `pages/Terms.tsx`, `pages/Security.tsx`, `pages/Contact.tsx` | Proof-points bar rendered at top of all static/legal pages. Newly discovered component not in prior pass notes. |
| `SkipToMainContent.tsx` | `components/PageLayout.tsx` | Accessibility skip-link. Used in `PageLayout`, which is the shell for all marketing pages. Newly discovered. |
| `SiteNav.tsx` | `pages/Index.tsx`, `components/PageLayout.tsx` | Global navigation — confirmed live. |
| `SiteFooter.tsx` | `pages/Index.tsx`, `components/PageLayout.tsx` | Global footer — confirmed live. |
| `PageLayout.tsx` | `pages/Features.tsx`, `pages/HowItWorks.tsx`, `pages/DemoWorkspace.tsx`, `pages/DemoReportDetail.tsx`, many static pages | Marketing page shell. |
| `HeroSection.tsx` | `pages/Index.tsx` | |
| `ProblemSection.tsx` | `pages/Index.tsx` | |
| `WorkflowSection.tsx` | `pages/Index.tsx` | |
| `FeaturesSection.tsx` | `pages/Index.tsx` | |
| `CredibilityStrip.tsx` | `pages/Index.tsx` | |
| `PricingSection.tsx` | `pages/Index.tsx` | |
| `FinalCTA.tsx` | `pages/Index.tsx` | |
| `MarketingReportPreview.tsx` | `pages/Features.tsx`, `pages/HowItWorks.tsx` | |
| `MarketingDashboardPreview.tsx` | `components/HeroSection.tsx` | |
| `InfoTooltip.tsx` | `pages/Features.tsx`, `pages/SignalsPage.tsx` | |
| `ClientQuoteCard.tsx` | `pages/ReportDetail.tsx`, `pages/SignalDetail.tsx` | |
| `ProtectedRoute.tsx` | `App.tsx` | |
| `RouteErrorBoundary.tsx` | `App.tsx` | |
| `UpgradeModal.tsx` | `App.tsx` | |
| `WorkspaceLayout.tsx` | `App.tsx` (DashboardRouteShell) | |

---

#### Components confirmed ORPHANED — SAFE DELETE

| Component | Evidence | Rationale |
|-----------|----------|-----------|
| `FounderSection.tsx` | **0 imports anywhere.** Only hit is the file itself (self-reference on line 1). | "Why We Built This" founder narrative section. Never placed in Index.tsx or any other page. Confirmed dead. |
| `StorySection.tsx` | **0 imports anywhere.** Only hit is the file itself (self-reference on line 1). | "Who It Is For" persona section. Also imports `coreNarrative` and `coreAudience` from `marketingCopy.ts` — those two exports become dead when this file is deleted. |
| `ValueStrip.tsx` | **0 imports anywhere.** Only self-references found. | 3-item value proposition strip (time / price / contracts). Never placed in any page. |
| `ReportSection.tsx` | **0 imports anywhere.** Only self-references found. | "How firms run Clarion" governance workflow section. Imports `MarketingDashboardPreview` and `MarketingReportPreview` — those remain live via other consumers, no cascade. |
| `SecuritySection.tsx` | **0 imports anywhere.** Only self-references found. | "Trust and Security" card grid. Not used in `Index.tsx` (confirmed — Index does not import it). Not used in `pages/Security.tsx` (that page uses `ShowDetails` + direct JSX instead). Completely orphaned. |
| `NavLink.tsx` | **0 import-path matches anywhere.** `SiteNav.tsx` uses `NavLink` extensively but imports it directly from `react-router-dom`, not from this file. | Thin wrapper around react-router-dom NavLink with `activeClassName`/`pendingClassName` compat props. Superseded — `SiteNav.tsx` uses the native `NavLink` with an inline className function instead. |

---

#### Side-effect findings from this pass

- **`lib/productFlags.ts` — now confirmed LIVE:** `pages/Security.tsx` imports `PRODUCT_FLAGS` from it (`PRODUCT_FLAGS.enableTwoFactorInV1` controls 2FA copy on the Security page). Previous classification as dead (F-A9) was incorrect — **revise to DO NOT TOUCH**.
- **`content/marketingCopy.ts` — `coreNarrative` export:** Used by `pages/Security.tsx` (`{coreNarrative}` rendered inline). Previously only noted as used by `Features.tsx` and `HowItWorks.tsx`. This adds a third live consumer. File remains fully live.
- **`StorySection.tsx` deletion cascade:** Deleting `StorySection.tsx` removes the only consumer of `coreNarrative` and `coreAudience` exports from `marketingCopy.ts`... **except** `coreNarrative` is also used by `Security.tsx`. So only `coreAudience` becomes a dead export after `StorySection` deletion.

---

#### Pass 3 Classification Summary

| Component | Classification |
|-----------|---------------|
| `FounderSection.tsx` | 🔴 **SAFE DELETE** |
| `StorySection.tsx` | 🔴 **SAFE DELETE** (deletes `coreAudience` as only consumer) |
| `ValueStrip.tsx` | 🔴 **SAFE DELETE** |
| `ReportSection.tsx` | 🔴 **SAFE DELETE** |
| `SecuritySection.tsx` | 🔴 **SAFE DELETE** |
| `NavLink.tsx` | 🔴 **SAFE DELETE** |
| `ShowDetails.tsx` | ✅ **DO NOT TOUCH** (live in Security.tsx) |
| `MarketingProofBar.tsx` | ✅ **DO NOT TOUCH** (live in 5 pages) |
| `SkipToMainContent.tsx` | ✅ **DO NOT TOUCH** (live in PageLayout.tsx) |
| `lib/productFlags.ts` | ✅ **DO NOT TOUCH** — **revises prior classification F-A9** (live in Security.tsx) |

---

### Phase 3 — Pass 2: Orphaned Pages — Full Import Audit

**Source files searched:** All `*.ts`, `*.tsx`, `*.js`, `*.jsx`, `*.json`, `*.html` in `frontend/` (entire frontend tree, not just `src/`)
**Search method:** Content search for component name strings, file name strings, and `import` patterns
**Barrel export check:** No `index.ts` / `index.tsx` barrel file exists in `frontend/src/pages/` — no re-export path possible

---

#### `pages/DashboardReports.tsx`

| Check | Result |
|-------|--------|
| Direct `import` in any file | **0 matches** outside the file itself |
| Dynamic `import()` call | **0 matches** |
| Barrel/re-export | No barrel file in `pages/` |
| String reference (e.g. lazy-load path) | **0 matches** |
| Referenced in `App.tsx` | **No** — route `/dashboard/reports` imports `ReportsPage.tsx` |

**All 22 search results were internal self-references** (lines within `DashboardReports.tsx` containing its own component name and surrounding code). No external file references the component by any mechanism.

**Classification: 🔴 SAFE DELETE**
**Rationale:** Completely orphaned. Zero imports, zero dynamic references, no barrel path. Superseded by `ReportsPage.tsx`. The file wraps itself in `<WorkspaceLayout>` — the old pre-`DashboardRouteShell` page pattern. Its unique features (matter labels, deleted reports table, action board sidebar) are not replicated in `ReportsPage.tsx` and should be archived in git before the file is removed.

---

#### `pages/DashboardActions.tsx`

| Check | Result |
|-------|--------|
| Direct `import` in any file | **0 matches** outside the file itself |
| Dynamic `import()` call | **0 matches** |
| Barrel/re-export | No barrel file in `pages/` |
| String reference (e.g. lazy-load path) | **0 matches** |
| Referenced in `App.tsx` | **No** — route `/dashboard/actions` imports `ExecutionPage.tsx` |

**All 21 search results were internal self-references** (lines within `DashboardActions.tsx` containing its own component name and surrounding code). No external file references the component by any mechanism.

**Classification: 🔴 SAFE DELETE**
**Rationale:** Completely orphaned. Zero imports, zero dynamic references, no barrel path. Superseded by `ExecutionPage.tsx`. Same old `<WorkspaceLayout>` wrapper pattern. Its unique features (cross-report action deduplication, "why this matters" detail panel, grouped action rows) are not present in `ExecutionPage.tsx` and should be archived in git before the file is removed.

---

#### Pass 2 Summary

| File | Referenced By | Classification |
|------|--------------|----------------|
| `pages/DashboardReports.tsx` | Nothing — self-references only | 🔴 **SAFE DELETE** (archive first) |
| `pages/DashboardActions.tsx` | Nothing — self-references only | 🔴 **SAFE DELETE** (archive first) |

Both files are confirmed dead by exhaustive search. No direct imports, no dynamic imports, no barrel exports, no string-path references anywhere in the entire frontend directory tree.

---

### Phase 3 — Pass 1: Pages Routing Audit

**Source files read:** `App.tsx`, `frontend/src/pages/` directory listing

**Total page files on disk:** 35
**Total pages imported and routed in App.tsx:** 33
**Non-routed (orphaned) pages:** 2

---

#### Routed Pages (33) — Confirmed reachable via App.tsx

| File | Route(s) | Notes |
|------|----------|-------|
| `Index.tsx` | `/` | Marketing home |
| `Signup.tsx` | `/signup` | |
| `CheckEmail.tsx` | `/check-email` | |
| `VerifySuccess.tsx` | `/verify-success` | |
| `VerifyEmail.tsx` | `/verify-email/:token`, `/verified`, `/verified/:token` | Handles 3 routes |
| `VerifyComplete.tsx` | `/verify-complete` | |
| `Login.tsx` | `/login` | |
| `ForgotPassword.tsx` | `/forgot-password` | |
| `ResetPassword.tsx` | `/reset-password/:token` | |
| `Onboarding.tsx` | `/onboarding` | |
| `Pricing.tsx` | `/pricing` | |
| `Features.tsx` | `/features` | |
| `HowItWorks.tsx` | `/how-it-works` | |
| `Docs.tsx` | `/docs` | |
| `Security.tsx` | `/security` | |
| `DemoWorkspace.tsx` | `/demo` | |
| `DemoReportDetail.tsx` | `/demo/reports/:id` | |
| `DemoPdfPreview.tsx` | `/demo/reports/:id/pdf` | |
| `Dashboard.tsx` | `/dashboard` | Protected, inside DashboardRouteShell |
| `ReportsPage.tsx` | `/dashboard/reports` | |
| `SignalsPage.tsx` | `/dashboard/signals` | |
| `ReportDetail.tsx` | `/dashboard/reports/:id` | |
| `SignalDetail.tsx` | `/dashboard/signals/:signalId`, `/signals/:signalId` | 2 routes |
| `ExecutionPage.tsx` | `/dashboard/actions` | |
| `DashboardBilling.tsx` | `/dashboard/billing` | |
| `DashboardSecurity.tsx` | `/dashboard/security` | |
| `DashboardAccount.tsx` | `/dashboard/account` | |
| `DashboardPdfPreview.tsx` | `/dashboard/brief-customization` | Old `/dashboard/pdf-preview` redirects here |
| `Upload.tsx` | `/upload` | Inside DashboardRouteShell (protected) |
| `Privacy.tsx` | `/privacy` | |
| `Terms.tsx` | `/terms` | |
| `Contact.tsx` | `/contact` | |
| `NotFound.tsx` | `*` | Catch-all 404 |

---

#### Non-Routed Pages (2) — ORPHANED

| File | Confidence | Evidence | Likely Reason |
|------|-----------|----------|---------------|
| `DashboardReports.tsx` | **High** | Not imported in App.tsx. Not referenced anywhere in the frontend. The route `/dashboard/reports` resolves to `ReportsPage.tsx` instead. | **Superseded** — old full-page implementation that wrapped itself in `<WorkspaceLayout>` directly. Replaced by `ReportsPage.tsx` when `DashboardRouteShell` pattern was introduced. Contains unique features (matter labels, deleted reports table, action board sidebar) not present in `ReportsPage.tsx`. Archive before deleting. |
| `DashboardActions.tsx` | **High** | Not imported in App.tsx. Not referenced anywhere in the frontend. The route `/dashboard/actions` resolves to `ExecutionPage.tsx` instead. | **Superseded** — same old pattern as DashboardReports.tsx (self-contained WorkspaceLayout wrapper). Replaced by `ExecutionPage.tsx`. Contains unique logic (cross-report deduplication, "why this matters" detail panel) not in `ExecutionPage.tsx`. Archive before deleting. |

---

#### Routing Notes

- **`/dashboard/pdf-preview`** → `<Navigate to="/dashboard/brief-customization" replace />` — redirect artifact from a URL rename. Low risk, can be cleaned up if no external links depend on the old path.
- **`/signals/:signalId`** (no `/dashboard/` prefix) — maps to `SignalDetail.tsx` inside `DashboardRouteShell` (protected). Intentional for direct signal deep-linking but unusual URL pattern.
- **`VerifyEmail.tsx`** handles 3 separate routes (`/verify-email/:token`, `/verified`, `/verified/:token`) — component is shared across email verification flow variants.

---

### 🔲 Phase 4 — Analysis & Report (TODO)
### 🔲 Phase 5 — Cleanup (TODO — requires explicit approval)

---

## Phase 2 Findings Log

### CATEGORY A — SAFE / HIGH CONFIDENCE (strong cleanup candidates)

---

#### A1. `backend/legacy/` — Entire directory is dead code
- **Type:** Dead directory (old app version)
- **Confidence:** High
- **Evidence:** Not referenced anywhere in `app.py` (zero imports, no path references). Contains its own `app.py`, `requirements.txt`, `pdf_generator.py`, and 9 HTML templates — clearly a complete older copy of the application.
- **Risk if removed:** None — it is entirely self-contained and never imported.
- **Recommended action:** Safe to delete after git checkpoint.

---

#### A2. `backend/implementation_playbook.py` — Stub file
- **Type:** Dead stub
- **Confidence:** High
- **Evidence:** File is 2 lines: `def build_theme_action(*args, **kwargs): return None`. Never imported anywhere in app.py or services.
- **Risk if removed:** None.
- **Recommended action:** Safe to delete.

---

#### A3. `backend/preflight_data.py` — One-off dev script
- **Type:** Dev/diagnostic script
- **Confidence:** High
- **Evidence:** Runs as a standalone script that connects to `feedback.db` and prints SQL query results. No imports in app.py. Not part of the application runtime.
- **Risk if removed:** None — it's a data integrity diagnostic tool, not production code.
- **Recommended action:** Safe to delete or move to scripts/.

---

#### A4. `backend/preflight_db.py` — One-off dev/migration inspection script
- **Type:** Dev/diagnostic script
- **Confidence:** High
- **Evidence:** Standalone script that checks table existence and column presence in `feedback.db`. Not imported anywhere.
- **Risk if removed:** None.
- **Recommended action:** Safe to delete or move to scripts/.

---

#### A5. `backend/smoke_check_option_b.py` — Dev smoke test script
- **Type:** Dev test artifact (not a pytest test)
- **Confidence:** High
- **Evidence:** Standalone script in the backend root that creates a temporary SQLite DB, runs test client calls, and asserts responses. "option_b" naming confirms it was from a specific implementation branch. It uses `app.test_client()` directly — it's not structured as a pytest test and lives outside the `tests/` directory.
- **Risk if removed:** Low. If this smoke test is still being run as a release gate, that should be confirmed first.
- **Recommended action:** Move to `tests/` and convert to pytest, OR delete after confirming `tests/test_release_smoke.py` covers the same scenarios.

---

#### A6. `backend/services/slack_notify.py` — Duplicate of slack_service.py
- **Type:** Duplicate service
- **Confidence:** High
- **Evidence:** Both files export `send_slack_alert(message)` with identical behavior (post to SLACK_WEBHOOK_URL env var). `app.py` imports exclusively from `slack_service.py` (line 185). `slack_notify.py` has zero imports anywhere.
- **Difference:** `slack_notify.py` returns a bool; `slack_service.py` returns None. The behavior is otherwise identical.
- **Risk if removed:** None — `slack_notify.py` is the dead duplicate.
- **Recommended action:** Delete `slack_notify.py`. Keep `slack_service.py`.

---

#### A7. `backend/services/risk_engine.py` — Entirely unused service
- **Type:** Dead service module
- **Confidence:** High
- **Evidence:** Not imported anywhere in `app.py` or any other file in the codebase. Contains sophisticated risk scoring logic (`compute_theme_risk_metrics`, `compute_theme_metrics`) that is never called. Also contains a `compute_theme_metrics()` function docstring that says "Legacy aggregation used by analyze_reviews()" — but `app.py` uses its own internal `analyze_reviews()` and does NOT call this.
- **Risk if removed:** None currently — however, this may represent intent to migrate to Risk Engine Phase 1 that was never completed.
- **Recommended action:** Confirm no migration plan is pending, then delete or archive.

---

#### A8. `backend/services/risk_persistence.py` — Entirely unused service
- **Type:** Dead service module
- **Confidence:** High
- **Evidence:** Not imported anywhere in `app.py` or any other file. Provides DB write helpers for `report_theme_metrics` and `theme_ledger` tables — but `app.py` never calls any of these functions.
- **Risk if removed:** Same caveat as risk_engine.py — part of an incomplete Risk Engine migration.
- **Recommended action:** Archive together with risk_engine.py.

---

#### A9. `backend/governance.py` — Unused standalone governance brief generator
- **Type:** Dead module (superseded)
- **Confidence:** High
- **Evidence:** Not imported anywhere in `app.py`. `scheduler.py` imports from it (`from governance import generate_governance_brief`), but the scheduler itself is not wired into `app.py` via `start_weekly_scheduler()` calls in the route setup — the import `from services.scheduler import start_scheduler as start_weekly_scheduler` exists in app.py but usage needs verification. `governance.py` opens a raw `sqlite3.connect()` directly — it predates the current `db_compat.py` pattern.
- **Risk:** Medium — the scheduler wraps `governance.py`; need to confirm `start_weekly_scheduler()` is actually called.
- **Recommended action:** Verify whether `start_weekly_scheduler()` is called in app.py startup, then assess.

---

#### A10. `backend/services/scheduler.py` — Imports from unused governance.py
- **Type:** Potentially superseded scheduler
- **Confidence:** Medium
- **Evidence:** `app.py` imports `start_weekly_scheduler` from this module, but a separate monthly partner brief email job is registered directly in `app.py` using APScheduler. The `scheduler.py` version only handles weekly briefs via the old `governance.py` path. The modern approach (`_run_monthly_partner_brief_email_job`) is directly in `app.py`.
- **Risk:** Medium — need to confirm whether `start_weekly_scheduler()` is called at app startup.
- **Recommended action:** Search `app.py` for calls to `start_weekly_scheduler()` before removing.

---

### CATEGORY B — NEEDS VERIFICATION

---

#### B1. Backend templates — server-side rendered marketing pages (8 templates)
- **Files:** `marketing_home.html`, `how_it_works.html`, `features.html`, `case_studies.html`, `pricing.html`, `privacy.html`, `terms.html`, `security.html`
- **Situation:** All rendered server-side by Flask routes. The SPA also has corresponding pages (`/how-it-works`, `/features`, `/pricing`, etc.).
- **Issue:** This creates two parallel implementations of the same pages. It's unclear whether the Flask routes are the canonical entry points (pre-SPA-redirect) or whether they're still the live pages being served.
- **Key finding:** `/` serves `marketing_home.html` (Flask template). The SPA `Index.tsx` component also covers `/`. Depending on how the app is deployed, one or the other is served.
- **`/case-studies`** specifically: This route has NO counterpart in the SPA router (`App.tsx`). If the SPA is the live frontend, this Flask page is either dead or an orphaned legacy page.
- **Risk:** Medium — cannot determine liveness without knowing deploy architecture.
- **Recommended action:** Clarify: does the Flask backend serve the marketing pages, or does the SPA serve them with Flask as API-only? `/case-studies` is the strongest dead-code candidate.

---

#### B2. Legacy server-side auth templates (partially active)
- **Files still rendering templates:**
  - `register.html` — rendered on POST validation failures (GET redirects to SPA)
  - `login_2fa.html` — fully server-side rendered (2FA still uses this template)
  - `forgot_password.html` — rendered by `/forgot-password-form` route (not the main forgot-password path)
  - `reset_password.html` — rendered by `/reset-password-form/<token>` route
- **Files confirmed DEAD (zero references in app.py):**
  - `login.html` — GET `/login` redirects to SPA; login POST redirects on success/failure; never renders this template
  - `upload.html` — GET `/upload` redirects to SPA
  - `account.html` — GET `/account` redirects to SPA
- **Risk:** Medium for the still-rendered templates. `login_2fa.html` in particular appears to be a live server-side flow.
- **Recommended action:**
  - `login.html`, `upload.html`, `account.html`: Safe to delete (confirmed zero refs)
  - `login_2fa.html`, `register.html`, `forgot_password.html`, `reset_password.html`: Do NOT remove — still rendered

---

#### B3. `backend/templates/governance_email.html`, `partner_brief_email.html`, `report.html`, `report_results.html` — Zero refs in app.py
- **Confidence:** High (zero render_template calls for these)
- **Evidence:** grep confirms 0 references to any of these 4 filenames in app.py.
- **`governance_email.html`** — possibly used by email_service.py `send_governance_email()` function (which IS called from app.py). Need to check email_service.py.
- **`report.html`** and **`report_results.html`** — likely from when reports were server-rendered; now SPA handles reports via API.
- **Risk:** Medium for governance_email.html (indirect usage possible). Low for report.html/report_results.html.
- **Recommended action:** Read `email_service.py` to confirm governance_email.html usage before flagging.

---

#### B4. `backend/services/meeting_summary.py` — Very simple, low usage
- **Type:** Minimal service
- **Confidence:** Medium
- **Evidence:** `generate_partner_summary()` is called in 2 places in app.py (lines 16726 and 16900) — both in the `/api/partner-summary` route area. The function produces a plaintext string summary. It's only 30 lines.
- **Issue:** The function is alive but extremely primitive. It may be a stub that was never properly completed.
- **Risk:** Low — it IS used, but minimal.
- **Recommended action:** Keep, but note for future consolidation with email_brief.py.

---

#### B5. `/buy-one-time` and `/subscribe` — Server-side Stripe checkout pages
- **Templates:** `buy-one-time.html` and `subscribe.html`
- **Status:** Both routes still render server-side templates and process Stripe via form POST.
- **Issue:** The SPA has a `DashboardBilling.tsx` page with `/api/billing/checkout` as the API endpoint. Two separate billing flows appear to exist.
- **Risk:** High — do not touch billing code without explicit verification.
- **Recommended action:** Flag for review. Determine which billing path is active for new users.

---

#### B6. `/feedback` and `/thank-you` — Public feedback form
- **Templates:** `feedback_form.html` and `thank_you.html`
- **Status:** Both routes render server-side templates. No SPA counterpart found.
- **Issue:** This is a standalone public feedback form, not client review upload. May still be intentionally active.
- **Risk:** Medium — unclear if this is a live feature or a legacy public-facing page.
- **Recommended action:** Verify whether this form is still being used or promoted.

---

#### B7. `backend/services/plan_limits.py` + `plan_service.py` — NOT duplicates, properly layered
- **Verdict:** These are NOT duplicates. `plan_limits.py` is a pure data constant file (the PLAN_LIMITS dict). `plan_service.py` imports from it and provides enforcement functions. `app.py` imports both correctly (PLAN_LIMITS for the data, plan_service for enforcement). The architecture is clean.
- **Minor issue:** `app.py` also defines its own `FREE_PLAN_REPORT_LIMIT = 1` and `FREE_PLAN_MAX_REVIEWS_PER_REPORT = 50` constants that partially duplicate what's in PLAN_LIMITS (free tier limits). These are used in legacy per-user flows vs. firm-scoped flows.
- **Risk:** Low — the dual constant definitions are worth noting but are intentional backward-compat.
- **Recommended action:** No action needed for plan_limits.py/plan_service.py. Flag the dual constants for future consolidation.

---

### CATEGORY C — DO NOT TOUCH YET

| Item | Reason |
|------|--------|
| `backend/templates/login_2fa.html` | Still actively rendered by `/login-2fa` route |
| `backend/templates/register.html` | Still rendered on POST validation failure |
| `backend/templates/forgot_password.html` | Rendered by `/forgot-password-form` route |
| `backend/templates/reset_password.html` | Rendered by `/reset-password-form/<token>` route |
| `backend/templates/buy-one-time.html` | Active Stripe checkout (legacy billing path) |
| `backend/templates/subscribe.html` | Active Stripe subscription checkout (legacy) |
| `backend/templates/emails/` (all 19 files) | Used by send_templated_email() in email_service.py |
| `backend/services/email_brief.py` | Actively used in 8 places in app.py |
| `backend/services/email_service.py` | Core email infrastructure, heavily used |
| `backend/services/review_classifier.py` | Core upload/analysis pipeline |
| `backend/services/llm_client.py` | Anthropic API wrapper, used by review_classifier |
| `backend/services/governance_insights.py` | Used in app.py (line 181) |
| `backend/services/signal_monitor.py` | Used in app.py (line 184) |
| `backend/services/plan_limits.py` | Used in app.py (line 182) |
| `backend/services/plan_service.py` | Used throughout app.py |
| `/download-pdf`, `/download-report/<id>` | Legacy download routes — may still be used |
| `backend/api/index.py` | Vercel serverless entry point — deployment artifact |
| `backend/scripts/` (all 3 scripts) | Admin/backup scripts — intentional tools |

---

### CATEGORY D — CONFIRMED CLEAN (not dead, no action needed)

- `backend/app.py` imports: All top-level stdlib imports (`hashlib`, `smtplib`, `socket`, `zoneinfo`, `BytesIO`, `StringIO`, `Counter`, `perf_counter`, `EmailMessage`) are all used in the file.
- `backend/db_compat.py` — Used via `DatabaseConnector` import in app.py
- `backend/pdf_generator.py` — Used via `generate_pdf_report` import in app.py
- `backend/config.py` — Used via `Config` import in app.py
- `backend/gunicorn.conf.py` — Deployment config
- `backend/vercel.json` — Deployment config
- `backend/requirements.txt` — Dependency manifest

---

## Phase 2 Summary — Safe Cleanup Candidates

### Immediate safe deletes (high confidence, no risk):
1. `backend/legacy/` — entire directory
2. `backend/implementation_playbook.py`
3. `backend/preflight_data.py`
4. `backend/preflight_db.py`
5. `backend/services/slack_notify.py` (keep slack_service.py)
6. `backend/services/risk_engine.py`
7. `backend/services/risk_persistence.py`
8. `backend/templates/login.html`
9. `backend/templates/upload.html`
10. `backend/templates/account.html`

### Verify before deleting (medium confidence):
11. `backend/smoke_check_option_b.py` — check if covered by tests/test_release_smoke.py
12. `backend/governance.py` — check if start_weekly_scheduler() is actually called at startup
13. `backend/services/scheduler.py` — same check
14. `backend/templates/governance_email.html` — check email_service.py for indirect usage
15. `backend/templates/report.html` and `report_results.html` — check email_service.py
16. `backend/templates/case_studies.html` — no SPA counterpart, but backend route exists

### Needs architecture clarification before touching:
17. All 8 server-side marketing templates — depends on deploy architecture
18. `/buy-one-time` and `/subscribe` billing paths — parallel to SPA billing

---

## Notes on Uncertainty

- Whether the Flask server still serves the marketing pages or whether the SPA does — this determines the fate of 8 templates and their routes
- Whether `start_weekly_scheduler()` is actually invoked at app startup (need to search app.py for the call)
- Whether `governance.py` is still a live dependency of the scheduler job
- Whether `governance_email.html` is used indirectly via `send_governance_email()` in email_service.py

---

## File Locations

| File | Location |
|------|----------|
| This progress file | `law-firm-insights-main/code-analysis-progress.md` |
| Cleanup reports (future) | TBD |

---

## Phase 3 — Pass 5: CSS Audit

**Files scanned:** `frontend/src/index.css` (~1,700 lines), `frontend/src/App.css` (~35 lines)
**Method:** Full read of both files; content searches to verify class usage in `frontend/src/`

---

### CSS-A1 — `App.css` — 🔴 SAFE DELETE (entire file)

**Evidence:** Zero imports of `App.css` anywhere in `frontend/src/`. Content search for `App\.css` returns 0 matches. The file is a Vite scaffold remnant (contains `.logo`, `.logo:hover`, `.logo.react:hover`, `@keyframes logo-spin`, `.card`, `.read-the-docs`, `#root` with `max-width: 1280px`). None of these selectors correspond to any component in the project. The `#root` rule conflicts with Tailwind's full-width layout pattern actually used by the app.

**Classification:** Category A — Safe Delete. No cascade risk.

---

### CSS-B1 — `.js-focus-visible` block — 🟡 STALE (dead library dependency)

**Selector:** `.js-focus-visible :focus:not(.focus-visible)`

**Evidence:** Content search for `js-focus-visible` returns 0 matches in any `.tsx`, `.ts`, `.html`, or `package.json` within the project. The `js-focus-visible` polyfill library is not installed. This block was added to suppress focus rings for mouse users but the polyfill that adds the `.js-focus-visible` class to `<body>` is never loaded — so the selector never matches anything.

**Classification:** Category B — Verify Before Deleting. The `:focus-visible` pseudo-class (used elsewhere in `index.css`) handles the same accessibility concern natively in all modern browsers. Removing this block has zero visible effect. Low risk, but confirm no polyfill import is hidden in `index.html` or a vendor bundle before deleting.

---

### CSS-C1 — Disabled animation classes — 🟡 DEAD CODE (keyframes with `animation: none` overrides)

The following animation classes have their `animation` property explicitly set to `none`. Their keyframe definitions exist but are permanently disabled by overrides elsewhere in the same file:

| Class | Keyframe defined | Override location |
|-------|-----------------|-------------------|
| `.animate-workspace-route` | `@keyframes workspace-route-enter` | Conformance override block ~line 1440 |
| `.animate-page-enter` | `@keyframes page-enter` | Conformance override block ~line 1440 |
| `.route-shell-in` | `@keyframes route-shell-enter` | Conformance override block ~line 1440 |
| `.page-transition` | `@keyframes fadeIn` (via `fade-enter`) | `animation: none` inline |
| `.stage-sequence > *` | `@keyframes dashboard-section-enter` | Conformance override block ~line 1440 |

**Evidence:** Each class has its `animation` property set to `none` in the conformance override block (the large `/* Conformance overrides */` comment section). The keyframe `@keyframes` blocks are still defined above but produce no visible output. These were disabled during a performance/motion audit pass and never cleaned up.

**Note:** `.fade-enter` still has a keyframe (`fadeIn`) and an `animation:` rule, but the class is applied nowhere in live source files (zero content search matches in `.tsx`). **Candidate for deletion separately** — see CSS-C2.

**Classification:** Category B — Verify Before Deleting. The conformance override block at the bottom that disables these is intentional and should be kept as-is. The dead keyframes above it can be cleaned up, but do no active harm. Recommend removing: the `@keyframes` blocks for `workspace-route-enter`, `page-enter`, `route-shell-enter`, `dashboard-section-enter` (these are never referenced now that their classes have `animation: none`). Keep `fadeIn` for now until `.fade-enter` fate is confirmed.

---

### CSS-C2 — `.fade-enter` — 🟡 LIKELY DEAD (class unused in live components)

**Selector:** `.fade-enter`

**Evidence:** Content search for `fade-enter` in `frontend/src/` returns 0 matches in any `.tsx`/`.ts` source file. The class has a real `animation: fadeIn 0.9s ease forwards` rule (not overridden to `none`) but is never applied to any element. Note: `animate-fade-in` (different class) is live and used.

**Classification:** Category B — Verify Before Deleting. Confirm not dynamically applied via string concatenation before deleting.

---

### CSS-D1 — Duplicate `gov-btn-primary` / `gov-btn-secondary` definitions — 🟡 DUPLICATION

**Evidence:** `gov-btn-primary` is defined **three times** in `index.css`:
1. First definition: inside `@layer components` — uses `@apply inline-flex ...` with Tailwind utilities + `border`, `background`, `color`, `box-shadow: none`
2. Second definition: inside the second `@layer components` block — uses plain CSS (`display: inline-flex`, `border-radius: 4px`, `padding: 8px 16px`, `font-size: 12px`)
3. Third definition: in the "Modern SaaS foundation overrides" section at the bottom (outside any layer) — overrides `border-radius`, `border`, `background`, `color` using `--navy-900` variables

Similarly, `gov-btn-secondary` is defined **three times** in the same three locations.

**Effect:** Because all three definitions target the same class, the last writer wins. The third definition (bottom of file, outside `@layer`) overrides the first two at runtime. The first two definitions are dead at runtime.

**Classification:** Category B — Duplication candidate. The triple-definition pattern is the result of iterative CSS refactoring without cleanup. The safest fix is to consolidate into the final definition block. Requires careful diffing before touching.

---

### CSS-D2 — Duplicate `gov-clickable` definitions — 🟡 DUPLICATION

**Evidence:** `gov-clickable` is defined **twice**:
1. First definition (inside `@layer components`): uses `hsl(220 10% 80%)` border colors, `hsl(210 18% 98%)` background, `outline: 2px solid hsl(220 12% 36%)` on focus-visible.
2. Second definition (outside `@layer`, "Modern SaaS foundation" block): uses `var(--gov-border)`, `var(--gov-surface)`, `var(--gov-primary)` tokens with `border-radius: 0.625rem` and an `active` state.

The second definition wins at runtime. The first definition (and its `hover`, `focus-visible` sub-rules) are dead.

**Classification:** Category B — Duplication candidate.

---

### CSS-D3 — Duplicate `gov-level-1` / `gov-level-2` definitions — 🟡 DUPLICATION

**Evidence:** Both `gov-level-1` and `gov-level-2` are defined twice:
1. First definition (inside second `@layer components` block): layout-only (`display: flex`, `flex-direction: column`, `gap`, `padding`, `border`, `background`, `box-shadow`)
2. Second definition (outside `@layer`, "Modern SaaS foundation" block): overrides `background`, `border`, adds `border-radius: 12px`, `box-shadow: 0 4px 16px`, different `padding`

The second (bottom) definitions win. The first definitions are rendered inert.

There is also a `.dark .gov-level-2` block inside `@layer components` that sets `border: 1px solid hsl(220 10% 78%)` and `background: hsl(0 0% 100%)` — identical to the light mode version, which appears unintentional (dark mode overrides normally darken backgrounds, not keep them white). No dark mode toggling is implemented in the app yet, so this is low risk, but the duplicate is suspicious.

**Classification:** Category B — Duplication candidate.

---

### CSS-D4 — Duplicate `gov-h1` / `gov-h2` / `gov-micro-label` / `gov-module-title` definitions — 🟡 DUPLICATION

**Evidence:** Typography classes defined twice following the same pattern as D1–D3:
- First definitions: inside `@layer components` (using `hsl()` values)
- Second definitions: in "Modern SaaS foundation" block (using `var(--text-primary)`, `var(--text-secondary)` tokens, different font sizes — `gov-h1` goes from `30px/600` to `2rem/700`)

Second definitions win. First definitions are dead at runtime.

**Classification:** Category B — Duplication candidate.

---

### CSS-E1 — `--gov-canvas` token defined but partially superseded — ℹ️ LOW PRIORITY

`--gov-canvas` is defined in `:root` as `214 22% 88%` (an HSL value for use with `hsl(var(--gov-canvas))`). It is referenced in `body { background: hsl(var(--gov-canvas)) }` and `.dark body`. However, the "Modern SaaS foundation" block redefines `body { background: var(--background) }` and `.gov-canvas { background: var(--background) }`, using the `--background` token instead. In practice, the `--gov-canvas` body rule is overridden and `var(--background)` wins.

**Classification:** Not a deletion candidate — the token is still referenced in component class definitions elsewhere. Low-priority internal inconsistency note only.

---

### CSS-F1 — Orphaned marketing component selectors — 🟡 MEDIUM CONFIDENCE

The following utility/component CSS classes in `index.css` were defined to support components now confirmed as orphaned (Category A deletes from Pass 1–3):

| CSS class | Defined for (deleted component) | Evidence |
|-----------|--------------------------------|----------|
| `.supporting-section`, `.supporting-lead`, `.supporting-subtle`, `.supporting-cta-strip`, `.supporting-divider-list` | `StorySection.tsx`, `ReportSection.tsx`, `ValueStrip.tsx` — all orphaned | These component names appear nowhere in routed components; class names are only used in orphaned files |
| `.trust-stack`, `.trust-intro`, `.trust-section`, `.trust-section-body`, `.trust-divider-list` | `SecuritySection.tsx` — orphaned (pages/Security.tsx does not use this component) | No live component uses these classes |

**Classification:** Category B — Verify Before Deleting. Confirm these classes are not applied by any remaining live component (quick content search recommended at deletion time). Safe to remove once orphaned component files are deleted.

---

### CSS Summary Table

| ID | Item | Category | Action |
|----|------|----------|--------|
| CSS-A1 | `App.css` (entire file) | A — Safe Delete | Delete file; not imported anywhere |
| CSS-B1 | `.js-focus-visible` block | B — Verify | Remove after confirming no polyfill in index.html |
| CSS-C1 | Dead animation keyframes (`workspace-route-enter`, `page-enter`, `route-shell-enter`, `dashboard-section-enter`) | B — Verify | Remove @keyframes blocks; classes already set to `animation: none` |
| CSS-C2 | `.fade-enter` class | B — Verify | Remove; no live usage found, but confirm no dynamic application |
| CSS-D1 | `gov-btn-primary` / `gov-btn-secondary` triple definitions | B — Duplication | Consolidate to final definition block |
| CSS-D2 | `gov-clickable` duplicate definition | B — Duplication | Consolidate to final definition block |
| CSS-D3 | `gov-level-1` / `gov-level-2` duplicate definitions | B — Duplication | Consolidate; also review suspicious `.dark .gov-level-2` (white bg in dark mode) |
| CSS-D4 | `gov-h1` / `gov-h2` / typography duplicate definitions | B — Duplication | Consolidate to final definition block |
| CSS-E1 | `--gov-canvas` token vs `--background` token split | — Low priority | Note only; no action needed now |
| CSS-F1 | `.supporting-*` and `.trust-*` classes (orphaned component styling) | B — Verify | Remove alongside orphaned components |

---

### CONFIRMED LIVE CSS (Do Not Touch)

- All `@layer base` `:root` CSS custom properties — used by Tailwind, Shadcn, and component styles throughout
- `.dark` color token overrides — standard dark mode palette
- `.skip-link` / `SkipToMainContent.tsx` — live accessibility component (confirmed live in Pass 3)
- `:focus-visible` rules — live accessibility implementation
- `.reveal`, `.reveal--visible`, `.no-observer .reveal` — used in `HeroSection.tsx` (confirmed live)
- `.marketing-hero`, `.marketing-hero-title`, etc. — used in live marketing pages
- `.section-container`, `.section-padding`, `.section-alt`, `.feature-card`, `.marketing-panel` — used in live marketing components
- `.gov-page`, `.gov-level-1`, `.gov-level-2` (final definitions) — heavily used across dashboard pages
- `.gov-btn-*`, `.gov-badge-*`, `.gov-clickable`, `.gov-affordance`, etc. (final definitions) — heavily used in dashboard
- `.workspace-sidebar`, `.workspace-topbar`, `.workspace-canvas` — used in `WorkspaceLayout.tsx`
- `.workspace-kpi-card`, `.workspace-stat-card` — used in dashboard components
- `.workspace-shell-*`, `.workspace-inline-stats` etc. — used in dashboard layout
- `.animate-fade-in`, `.animate-slide-up`, `.animate-scale-in`, `.animate-fade-up*` (live variants) — used throughout
- `.auth-shell`, `.auth-card` — used in auth pages
- `.gov-cta-primary`, `.gov-cta-secondary`, `.gov-link-action` — used in dashboard/marketing components
- `.gov-chip-*` — used in dashboard components
- `.gov-table`, `.gov-field`, `.gov-textarea`, `.gov-alert` — used in dashboard/form components
- `.marketing-shell` scoped overrides — used via PageLayout/SiteNav on public pages

---

---

## Phase 3 — Pass 6: Component Subdirectory Audit

**Scope:** `components/actions/`, `components/dashboard/`, `components/governance/`, `components/pdf/`, `components/reports/`, `components/ui/`
**Method:** Content search for every component name and import path across all `*.ts`/`*.tsx` in `frontend/src/`. Results cross-referenced against live routed pages only (orphaned pages `DashboardReports.tsx` and `DashboardActions.tsx` excluded from "live consumer" counts).

---

### `components/actions/` — 2 files

#### `ActionCard.tsx` — ✅ DO NOT TOUCH
**Imported by:** `pages/ExecutionPage.tsx` (live, used in kanban board across all 4 action status columns)

#### `ActionForm.tsx` — ✅ DO NOT TOUCH
**Imported by:** `pages/SignalsPage.tsx` (live), `pages/SignalDetail.tsx` (live), `pages/ReportDetail.tsx` (live), `pages/ExecutionPage.tsx` (live) — 4 live consumers

---

### `components/dashboard/` — 11 files

#### `ActionTracking.tsx` — ✅ DO NOT TOUCH
**Imported by:** `components/MarketingDashboardPreview.tsx` (live) — used in the "operations" variant of the marketing preview

#### `DashboardCard.tsx` — ✅ DO NOT TOUCH
**Imported by:** `pages/Dashboard.tsx` (live) — used as a card wrapper for multiple dashboard sections
**Note:** `pages/Dashboard.tsx` imports `DashboardCard` from `@/components/ui/card`, not from `dashboard/DashboardCard.tsx`. Search confirms `dashboard/DashboardCard.tsx` is also imported directly by `Dashboard.tsx` in addition to the ui/card version. This file is live.

#### `ExposureMetrics.tsx` — 🔴 SAFE DELETE
**Evidence:** Zero imports anywhere outside its own file. Content search for `ExposureMetrics` returns only the component's own source lines. Not used by `Dashboard.tsx`, `MarketingDashboardPreview.tsx`, or any other file. This component was built to display exposure status summary cards but was replaced by `FirmGovernanceStatus.tsx` in the live dashboard.

#### `ExposureSignals.tsx` — ✅ DO NOT TOUCH
**Imported by:** `components/MarketingDashboardPreview.tsx` (live, "overview" variant)

#### `FirmGovernanceStatus.tsx` — ✅ DO NOT TOUCH
**Imported by:** `pages/Dashboard.tsx` (live), `components/MarketingDashboardPreview.tsx` (live) — 2 live consumers

#### `GovernanceGuidance.tsx` — ✅ DO NOT TOUCH
**Imported by:** `pages/Dashboard.tsx` (live), `components/MarketingDashboardPreview.tsx` (live) — 2 live consumers

#### `GovernanceLoop.tsx` — ✅ DO NOT TOUCH
**Imported by:** `pages/Dashboard.tsx` (live)

#### `NextBrief.tsx` — 🔴 SAFE DELETE
**Evidence:** Zero imports anywhere outside its own file. Content search for `NextBrief` returns only the component's own source lines (28 lines). Not used by `Dashboard.tsx` or any other file. Small component that displayed a "Next Governance Brief" scheduled date card.

#### `NextStepPanel.tsx` — 🔴 SAFE DELETE
**Evidence:** Zero imports anywhere outside its own file. Content search for `NextStepPanel` returns only the component's own source lines (6 lines, minified). A small directive panel showing "High Exposure / Watchlist / On Track" mode. Never placed in any page.

#### `PartnerBriefPanel.tsx` — ✅ DO NOT TOUCH
**Imported by:** `pages/Dashboard.tsx` (live)

#### `PlanBadge.tsx` — ✅ DO NOT TOUCH
**Imported by:** `pages/Dashboard.tsx` (live)

#### `QuickActions.tsx` — 🔴 SAFE DELETE
**Evidence:** Zero imports anywhere outside its own file. Content search for `QuickActions` returns only the component's own source lines (41 lines). Three-button quick action bar (Upload Feedback / Create Action / Generate Brief). Never placed in any page or parent component.

#### `RecentGovernanceBriefs.tsx` — ✅ DO NOT TOUCH
**Imported by:** `pages/Dashboard.tsx` (live), `components/MarketingDashboardPreview.tsx` (live) — 2 live consumers

#### `ReportsPanel.tsx` — ⚠️ VERIFY BEFORE DELETING
**Imported by:** `pages/DashboardReports.tsx` (orphaned — the only live consumer is the orphaned page). No live routed page imports this component directly. Once `DashboardReports.tsx` is deleted, `ReportsPanel.tsx` will have zero consumers.
**Note:** `ReportsPanel` is a substantial component (~200+ lines) with delete confirmation dialog logic using `AlertDialog`. If the reports list functionality is ever re-introduced into `ReportsPage.tsx`, this component is the logical reuse candidate. Archive before deleting.

#### `SinceLastReview.tsx` — ✅ DO NOT TOUCH
**Imported by:** `pages/Dashboard.tsx` (live), `components/MarketingDashboardPreview.tsx` (live) — 2 live consumers

#### `TriageBand.tsx` — 🔴 SAFE DELETE
**Evidence:** Zero imports anywhere outside its own file. Content search for `TriageBand` returns only the component's own source lines. A color-coded exposure level banner (`High / Watchlist / On Track`). Not used by any live page or component.

---

### `components/governance/` — 5 files

#### `GovBadge.tsx` — ⚠️ VERIFY BEFORE DELETING
**Evidence:** Content search for `GovBadge` in `frontend/src/pages/` returns zero matches in any live page. Only consumers found are `DashboardActions.tsx` (orphaned) and the component's own source file. When `DashboardActions.tsx` is deleted, `GovBadge` will have zero live consumers.
**Note:** The component itself is small (~20 lines) — a styled badge for `neutral / watch / high / escalated` governance states. If there's a plan to use it in future pages it's reasonable to keep; otherwise it becomes dead on `DashboardActions.tsx` deletion.

#### `GovPageHeader.tsx` — ✅ DO NOT TOUCH
**Imported by:** `pages/DashboardBilling.tsx` (live), `pages/DashboardAccount.tsx` (live), `pages/DashboardActions.tsx` (orphaned) — 2 live consumers

#### `GovSectionCard.tsx` — ✅ DO NOT TOUCH
**Imported by:** `pages/Upload.tsx` (live), `pages/DashboardBilling.tsx` (live), `pages/DashboardAccount.tsx` (live), `pages/DashboardActions.tsx` (orphaned) — 3 live consumers

#### `GovStatCard.tsx` — ✅ DO NOT TOUCH
**Imported by:** `pages/DashboardBilling.tsx` (live), `pages/DashboardActions.tsx` (orphaned) — 1 live consumer. Remains live after orphaned page deletion.

#### `PageWrapper.tsx` — ✅ DO NOT TOUCH
**Imported by:** `pages/SignalsPage.tsx` (live), `pages/SignalDetail.tsx` (live), `pages/ExecutionPage.tsx` (live) — 3 live consumers

---

### `components/pdf/` — 1 file

#### `PdfDeckPreview.tsx` — ✅ DO NOT TOUCH
**Imported by:** `pages/DashboardPdfPreview.tsx` (live, route `/dashboard/brief-customization`), `pages/DemoPdfPreview.tsx` (live, route `/demo/reports/:id/pdf`), `components/MarketingReportPreview.tsx` (live) — 3 live consumers

---

### `components/reports/` — 1 file

#### `EmailBriefPreviewModal.tsx` — ✅ DO NOT TOUCH
**Imported by:** `pages/ReportDetail.tsx` (live) — confirmed live consumer

---

### `components/ui/` — 47 files

Shadcn/ui components. Many are installed by the `shadcn` CLI but never actually used in the application. Searched for all import paths across the full source tree.

#### Confirmed LIVE (imported by at least one non-ui file)

| Component | Imported By |
|-----------|------------|
| `accordion.tsx` | `components/PricingSection.tsx` |
| `alert-dialog.tsx` | `components/dashboard/ReportsPanel.tsx` |
| `button.tsx` | `pages/Dashboard.tsx`, `components/dashboard/ExposureSignals.tsx`, `components/dashboard/QuickActions.tsx`, `components/dashboard/FirmGovernanceStatus.tsx`, and many others |
| `card.tsx` | `pages/Dashboard.tsx` (imports `DashboardCard` named export), `components/dashboard/*` (many files) |
| `dialog.tsx` | `pages/SignalsPage.tsx`, `pages/ExecutionPage.tsx`, `pages/ReportDetail.tsx`, `components/reports/EmailBriefPreviewModal.tsx`, `components/ui/command.tsx` |
| `form.tsx` | Imports from `label.tsx` internally |
| `label.tsx` | `components/ui/form.tsx` (internal ui dependency) |
| `input.tsx` | `components/ui/sidebar.tsx` (internal), and broader usage |
| `progress.tsx` | `pages/Upload.tsx` |
| `separator.tsx` | `components/ui/sidebar.tsx` (internal) |
| `sheet.tsx` | `components/ui/sidebar.tsx` (internal) |
| `skeleton.tsx` | `components/ui/sidebar.tsx` (internal) |
| `sonner.tsx` | `App.tsx` |
| `toast.tsx` | `hooks/use-toast.ts`, `components/ui/toaster.tsx` (internal chain) |
| `toaster.tsx` | `App.tsx` |
| `tooltip.tsx` | `App.tsx`, `components/dashboard/FirmGovernanceStatus.tsx`, `components/ui/sidebar.tsx` |
| `use-toast.ts` | `hooks/use-toast.ts` (re-exported hook) |
| `SeverityBadge.tsx` | `components/dashboard/ExposureSignals.tsx` |

#### UNUSED — Shadcn components with zero external consumers

The following Shadcn components are installed but have **no imports** anywhere in the application outside of internal ui-to-ui dependencies:

| Component | Evidence | Notes |
|-----------|----------|-------|
| `aspect-ratio.tsx` | 0 imports outside `ui/` | Standard shadcn install artifact |
| `avatar.tsx` | 0 imports outside `ui/` | Standard shadcn install artifact |
| `breadcrumb.tsx` | 0 imports outside `ui/` | Standard shadcn install artifact |
| `calendar.tsx` | 0 imports outside `ui/` | No date pickers in the app |
| `carousel.tsx` | 0 imports outside `ui/` | Standard shadcn install artifact |
| `chart.tsx` | 0 imports outside `ui/` | No chart library usage found in source |
| `checkbox.tsx` | 0 imports outside `ui/` | Forms use raw inputs |
| `collapsible.tsx` | 0 imports outside `ui/` | Standard shadcn install artifact |
| `command.tsx` | 0 imports outside `ui/` | No command palette in the app (imports `dialog.tsx` internally but is itself unused) |
| `context-menu.tsx` | 0 imports outside `ui/` | Standard shadcn install artifact |
| `drawer.tsx` | 0 imports outside `ui/` | Standard shadcn install artifact |
| `dropdown-menu.tsx` | 0 imports outside `ui/` | Menus use custom implementations |
| `hover-card.tsx` | 0 imports outside `ui/` | Standard shadcn install artifact |
| `input-otp.tsx` | 0 imports outside `ui/` | OTP/2FA uses server-side template (`login_2fa.html`) |
| `menubar.tsx` | 0 imports outside `ui/` | Standard shadcn install artifact |
| `navigation-menu.tsx` | 0 imports outside `ui/` | Nav uses custom `SiteNav.tsx` |
| `pagination.tsx` | 0 imports outside `ui/` | No paginated lists use shadcn pagination |
| `popover.tsx` | 0 imports outside `ui/` | Standard shadcn install artifact |
| `radio-group.tsx` | 0 imports outside `ui/` | Forms use raw inputs |
| `resizable.tsx` | 0 imports outside `ui/` | Standard shadcn install artifact |
| `scroll-area.tsx` | 0 imports outside `ui/` | Standard shadcn install artifact |
| `select.tsx` | 0 imports outside `ui/` | Selects use raw `<select>` elements |
| `sidebar.tsx` | 0 imports outside `ui/` | App uses custom `WorkspaceLayout.tsx` sidebar; this Shadcn sidebar is never mounted |
| `slider.tsx` | 0 imports outside `ui/` | Standard shadcn install artifact |
| `switch.tsx` | 0 imports outside `ui/` | Standard shadcn install artifact |
| `table.tsx` | 0 imports outside `ui/` | Tables use raw `<table>` elements with gov-table CSS class |
| `tabs.tsx` | 0 imports outside `ui/` | Tabs use raw elements or URL params |
| `textarea.tsx` | 0 imports outside `ui/` | Forms use raw `<textarea>` elements |
| `toggle.tsx` | 0 imports outside `ui/` | Standard shadcn install artifact |
| `toggle-group.tsx` | 0 imports outside `ui/` | Only imports from `toggle.tsx` — itself unused |
| `badge.tsx` | 0 imports outside `ui/` | App uses custom `gov-badge-*` CSS classes |

**Important note on `sidebar.tsx`:** This component internally imports from `input.tsx`, `separator.tsx`, `sheet.tsx`, `skeleton.tsx`, and `tooltip.tsx`. However, since `sidebar.tsx` itself is never imported or used, those 5 components are only "live" for this chain. `input.tsx`, `separator.tsx`, `skeleton.tsx` have no other external consumers — they are transitively dead via the unused sidebar. `sheet.tsx` also has no other consumer.

**Recommendation:** Shadcn unused components are safe to delete but low priority — they add no runtime overhead (tree-shaken by Vite). Delete only if repo cleanliness is a priority.

---

### Pass 6 — Duplicate Component Note

**`DashboardCard` exists in two places:**
- `components/ui/card.tsx` exports `DashboardCard` as a named export — this is the live, used version
- `components/dashboard/DashboardCard.tsx` — a separate standalone file

Targeted search for `from "@/components/dashboard/DashboardCard"` returned **0 matches**. `Dashboard.tsx` imports `{ DashboardCard }` from `@/components/ui/card`. The `components/dashboard/DashboardCard.tsx` file is a **confirmed dead duplicate** — safe to delete.

**`SeverityBadge` vs inline severity logic:**
- `components/ui/SeverityBadge.tsx` exists and is imported by `ExposureSignals.tsx`
- `pages/SignalsPage.tsx` and `pages/SignalDetail.tsx` implement their own inline severity badge helper functions (`severityBadge()`) rather than using the shared component
- This is a duplication of logic (not a dead file) — the shared component is live but underused

---

### Pass 6 Classification Summary

#### `components/actions/`

| File | Classification |
|------|---------------|
| `ActionCard.tsx` | ✅ DO NOT TOUCH — live in ExecutionPage |
| `ActionForm.tsx` | ✅ DO NOT TOUCH — live in 4 pages |

#### `components/dashboard/`

| File | Classification |
|------|---------------|
| `ActionTracking.tsx` | ✅ DO NOT TOUCH — live in MarketingDashboardPreview |
| `DashboardCard.tsx` | 🔴 SAFE DELETE — confirmed dead duplicate; `DashboardCard` is exported from `ui/card.tsx` instead; zero imports of this file found |
| `ExposureMetrics.tsx` | 🔴 SAFE DELETE — zero imports anywhere |
| `ExposureSignals.tsx` | ✅ DO NOT TOUCH — live in MarketingDashboardPreview |
| `FirmGovernanceStatus.tsx` | ✅ DO NOT TOUCH — live in Dashboard + Marketing |
| `GovernanceGuidance.tsx` | ✅ DO NOT TOUCH — live in Dashboard + Marketing |
| `GovernanceLoop.tsx` | ✅ DO NOT TOUCH — live in Dashboard |
| `NextBrief.tsx` | 🔴 SAFE DELETE — zero imports anywhere |
| `NextStepPanel.tsx` | 🔴 SAFE DELETE — zero imports anywhere |
| `PartnerBriefPanel.tsx` | ✅ DO NOT TOUCH — live in Dashboard |
| `PlanBadge.tsx` | ✅ DO NOT TOUCH — live in Dashboard |
| `QuickActions.tsx` | 🔴 SAFE DELETE — zero imports anywhere |
| `RecentGovernanceBriefs.tsx` | ✅ DO NOT TOUCH — live in Dashboard + Marketing |
| `ReportsPanel.tsx` | ⚠️ VERIFY — only consumer is orphaned DashboardReports.tsx; becomes dead on its deletion |
| `SinceLastReview.tsx` | ✅ DO NOT TOUCH — live in Dashboard + Marketing |
| `TriageBand.tsx` | 🔴 SAFE DELETE — zero imports anywhere |

#### `components/governance/`

| File | Classification |
|------|---------------|
| `GovBadge.tsx` | ⚠️ VERIFY — only live consumer is orphaned DashboardActions.tsx; becomes dead on its deletion |
| `GovPageHeader.tsx` | ✅ DO NOT TOUCH — live in DashboardBilling + DashboardAccount |
| `GovSectionCard.tsx` | ✅ DO NOT TOUCH — live in Upload + DashboardBilling + DashboardAccount |
| `GovStatCard.tsx` | ✅ DO NOT TOUCH — live in DashboardBilling |
| `PageWrapper.tsx` | ✅ DO NOT TOUCH — live in SignalsPage + SignalDetail + ExecutionPage |

#### `components/pdf/`

| File | Classification |
|------|---------------|
| `PdfDeckPreview.tsx` | ✅ DO NOT TOUCH — live in 3 consumers |

#### `components/reports/`

| File | Classification |
|------|---------------|
| `EmailBriefPreviewModal.tsx` | ✅ DO NOT TOUCH — live in ReportDetail |

#### `components/ui/` — Unused Shadcn installs

| File | Classification |
|------|---------------|
| `aspect-ratio.tsx` | 🟡 LOW PRIORITY DELETE — unused shadcn install |
| `avatar.tsx` | 🟡 LOW PRIORITY DELETE — unused shadcn install |
| `breadcrumb.tsx` | 🟡 LOW PRIORITY DELETE — unused shadcn install |
| `calendar.tsx` | 🟡 LOW PRIORITY DELETE — unused shadcn install |
| `carousel.tsx` | 🟡 LOW PRIORITY DELETE — unused shadcn install |
| `chart.tsx` | 🟡 LOW PRIORITY DELETE — unused shadcn install |
| `checkbox.tsx` | 🟡 LOW PRIORITY DELETE — unused shadcn install |
| `collapsible.tsx` | 🟡 LOW PRIORITY DELETE — unused shadcn install |
| `command.tsx` | 🟡 LOW PRIORITY DELETE — unused (internally imports dialog.tsx but is itself unused) |
| `context-menu.tsx` | 🟡 LOW PRIORITY DELETE — unused shadcn install |
| `drawer.tsx` | 🟡 LOW PRIORITY DELETE — unused shadcn install |
| `dropdown-menu.tsx` | 🟡 LOW PRIORITY DELETE — unused shadcn install |
| `hover-card.tsx` | 🟡 LOW PRIORITY DELETE — unused shadcn install |
| `input-otp.tsx` | 🟡 LOW PRIORITY DELETE — unused shadcn install |
| `menubar.tsx` | 🟡 LOW PRIORITY DELETE — unused shadcn install |
| `navigation-menu.tsx` | 🟡 LOW PRIORITY DELETE — unused shadcn install |
| `pagination.tsx` | 🟡 LOW PRIORITY DELETE — unused shadcn install |
| `popover.tsx` | 🟡 LOW PRIORITY DELETE — unused shadcn install |
| `radio-group.tsx` | 🟡 LOW PRIORITY DELETE — unused shadcn install |
| `resizable.tsx` | 🟡 LOW PRIORITY DELETE — unused shadcn install |
| `scroll-area.tsx` | 🟡 LOW PRIORITY DELETE — unused shadcn install |
| `select.tsx` | 🟡 LOW PRIORITY DELETE — unused shadcn install |
| `sidebar.tsx` | 🟡 LOW PRIORITY DELETE — unused; pulls in input/separator/sheet/skeleton transitively |
| `slider.tsx` | 🟡 LOW PRIORITY DELETE — unused shadcn install |
| `switch.tsx` | 🟡 LOW PRIORITY DELETE — unused shadcn install |
| `table.tsx` | 🟡 LOW PRIORITY DELETE — unused shadcn install |
| `tabs.tsx` | 🟡 LOW PRIORITY DELETE — unused shadcn install |
| `textarea.tsx` | 🟡 LOW PRIORITY DELETE — unused shadcn install |
| `toggle.tsx` | 🟡 LOW PRIORITY DELETE — unused shadcn install |
| `toggle-group.tsx` | 🟡 LOW PRIORITY DELETE — unused (only imports toggle.tsx) |
| `badge.tsx` | 🟡 LOW PRIORITY DELETE — unused shadcn install |

**Transitively unused (only consumed by the unused sidebar):**
- `input.tsx`, `separator.tsx`, `sheet.tsx`, `skeleton.tsx` — alive only via sidebar.tsx dependency chain. If sidebar.tsx is deleted, these become dead too. If sidebar.tsx is kept (e.g. for future use), keep these.

---

### ✅ Phase 3 — COMPLETE

All frontend subdirectories have been fully scanned. All findings documented.

---

## Phase 3 Next Steps → Phase 4

**Phase 4:** Consolidate all findings from Passes 1–6 into a single prioritised cleanup plan. No pending verifications remain — all classifications are final.
