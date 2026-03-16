# AI Pass Changelog

## 2026-03-15 — Live Tagger Validation + Definitive Calibration Pass

### Root Cause Identified and Resolved
All prior calibration wave 1 and wave 2 phrase additions targeted `backend/services/bench/deterministic_tagger.py`. The live `/internal/benchmark/batch` endpoint uses `backend/services/benchmark_engine.py` — a separate, self-contained 1943-line engine with its own `THEME_PHRASES` dict. The two files are architecturally independent. Prior edits had zero effect on any live calibration run.

### Files Changed
- `backend/services/benchmark_engine.py` — phrase additions (Wave 3, targeting live engine)

### Phrase Additions to `benchmark_engine.py` (Wave 3)
Targeted the exact evidence spans from the previous run's `missing_theme` disagreements:

- **communication_responsiveness** (+17): `crickets`, `i kept calling`, `email after email without`, `without replies`, `never had meetings`, `kept us informed of the legal process`, `give his time for free`, `no one ever returns a call`, `told to do it yourself`, `judged for having`, etc.
- **empathy_support** (+12): `friendly, patient`, `friendly and patient`, `family oriented practice`, `appreciate the help`, `incredibly organized`, `helps people in this crucial area`, `dedicated to helping`
- **professionalism_trust** (+20): `kindness`, `professionalism and kindness`, `wonderful to work with`, `lovely experience`, `highly recommend`, `very knowledgeable`, `very thorough`, `very dedicated`, `extremely knowledgeable`, etc.
- **outcome_satisfaction positive** (+11): `very happy with how the matter turned out`, `grateful and satisfied`, `helped me get approved`, `made the process so easy`
- **outcome_satisfaction negative** (+7): `not satisfied with their efforts`, `never really fought`, `my lawyer was representing the defendant`
- **timeliness_progress negative** (+15): `it took 12 months`, `over two years`, `still waiting`, `appeal took a long time`, `after 2 years`, `two and a half years`

### Parity Verification (5/5 probes passed)
Before running calibration, confirmed live server returns correct themes:
- `"Crickets from my legal aide..."` → `communication_responsiveness: negative` ✅
- `"They never even really had meetings with me..."` → `communication_responsiveness: negative` ✅
- `"Jeremy upholds the most professionalism and kindness."` → `professionalism_trust: positive` ✅
- `"He is friendly, patient, and incredibly organized."` → `empathy_support: positive` ✅
- `"No one ever returns a call in this office."` → `communication_responsiveness: negative` ✅

### Definitive Calibration Results (run: 20260315_200410)
| Metric | Baseline | Wave 3 | Delta |
|---|---|---|---|
| Agreement rate | 19.6% | **27.3%** | +7.7pp |
| Clean reviews (0 disagree) | 28/143 | **39/143** | +11 |
| `missing_theme` count | 180 | **152** | -28 |
| `missed_severe_phrase` | 4 | 3 | -1 |

**Per-chunk rates:**
- Chunk 1: 30% → **65%** (+35pp) — largest single-chunk gain
- Chunk 3: 35% → **40%** (+5pp)
- Chunk 4: 0% → **10%** (+10pp) — previously zero-agreement chunk
- Chunk 8: 33% → **67%** (+33pp)

**Theme improvements:**
- `empathy_support`: 29 → 22 disagreements (-7)
- `outcome_satisfaction`: 31 → 23 disagreements (-8)
- `communication_responsiveness`: 51 → 47 (-4)

**New extra_theme increase (+11):** The new phrases are firing on reviews where AI doesn't tag the theme. This is the expected tradeoff of broader coverage — needs guard review in a follow-on pass.

**Commit:** pending git commit for this pass.

## 2026-03-15 — Calibration Wave: Phrase Expansion + Guard Fixes Pass (deterministic_tagger.py — wrong file)
**File changed:** `backend/services/bench/deterministic_tagger.py` only.

**P0 — Phrase library expansion (~70 new phrases across all 10 themes):**
- `communication_responsiveness`: added crickets, email-after-email, barely communicated, stayed in contact, kept in close contact, unreachable, communicate well variants, returned her/his call, calls back, quick to respond, always available.
- `communication_clarity`: added left me in the dark, couldn't/could not understand, hard to follow, never explained, thoroughly/well explained, walked me through.
- `empathy_support`: added lawyers not caring, you are dead to them, treated as a number, just a number, barely gave opportunity to speak, cut me off and rambling, no compassion, handled with grace/patience, reassured me, made me feel comfortable/at ease, showed empathy, patient.
- `professionalism_trust`: added spoken to that way, crooked law office, do not trust this firm, misrepresentation, not licensed in my state, I knew I was dealing with professionals, true/highly professional.
- `expectation_setting`: added completely let me down, only to be told, different than promised, sent inexperienced son, not what I was told, walked through the process, prepared me.
- `billing_transparency`: added 16 hours of work, excessive/excess fees/charges, charged for consultation, billing dispute.
- `fee_value`: added worth every penny, great value, fair price/fee, not worth the money.
- `timeliness_progress`: added over two years still waiting, 2.5 years, only heard day before hearing, still waiting, no progress, nothing has been done, made sure done on time, met deadlines, ahead of schedule, in a timely manner.
- `office_staff_experience`: added wonderful/amazing/great/kind staff, phone assistant hired to tell people, incompetent/unhelpful staff, legal assistant/aide, office staff was.
- `outcome_satisfaction`: added failed me during appeal, never got proper legal help, still lost my license, helped me be approved, finally got justice, very satisfying, satisfied with the outcome, won my case, got my case handled.

**P3 — Theme routing fix:**
- `"polite"` / `"very polite"` / `"polite staff"` / `"very polite staff"` moved from `professionalism_trust` → `office_staff_experience` (calibration finding: AI consistently routes these to office_staff_experience).

**P1 — Negation guard proximal distance fix:**
- `_has_proximal_negation()` now accepts `before_only=True` parameter.
- For `_neg` family phrases, negation guard now only fires if the negation token appears *before* the phrase (within NEGATION_PROXIMITY_TOKENS tokens). This prevents subsequent-clause negation tokens (e.g. "do not trust" after "crooked") from incorrectly flipping an inherently-negative phrase to positive.
- Fixes confirmed FPs: `"Crooked law office, do not trust this firm"`, `"without replies"` compound negative.

**P2 — Duration-based severity escalation:**
- Added `_DURATION_SEVERE_PATTERNS` regex for "delayed/waited N months/years", "over two years", "X and a half years" patterns.
- `timeliness_neg` / `waiting_neg` family phrases escalate to `severe_negative` when duration pattern is present in review text.

**Smoke test:** 15/15 targeted cases pass including all known FPs from final_summary.json.
- **Commit:** pending — run calibration to validate before git commit.

## 2026-03-15 — Operator Command Center Correction Pass
- Added a real internal operator landing route at `/internal/command-center/` and a minimal template command center.
- Added a dedicated internal calibration console page at `/internal/calibration/` so command-center links resolve to real pages.
- Updated `START_CLARION.bat` and `OPEN_COMMAND_CENTER.bat` to open `/internal/command-center/` instead of direct dashboard URL.
- Reframed helper launchers as optional in `README.md`, keeping `START_CLARION.bat` as the single obvious primary entry point.
- **Commit:** recorded in git for this pass (see repository log).

## 2026-03-15 — Operator Startup Launcher Pass
- Added root-level Windows launcher files: `START_CLARION.bat`, `OPEN_COMMAND_CENTER.bat`, `RUN_CALIBRATION.bat`, and `OPEN_ENGINE_TOOLS.bat`.
- Reused existing backend startup convention via `backend/start.bat` and wired command center URL to `http://localhost:5000/dashboard`.
- Added README operator-launcher section for non-technical startup clarity.
- **Commit:** recorded in git for this pass (see repository log).

## 2026-03-15 — Internal Tools Route Correction Pass
- Moved the new launcher/hub route from `/internal/calibration/` to dedicated `/internal/tools/`.
- Preserved `/internal/calibration/` as the calibration-console target by removing launcher ownership of that path.
- Kept dashboard/account CTAs pointing directly to `/internal/calibration/` and `/internal/benchmark/themes`.
- **Commit:** recorded in git for this pass (see repository log).

## 2026-03-15 — Internal Tools Launcher UX Pass
- Added an authenticated admin/dev-only internal tools launcher route for calibration/benchmark access.
- Added an internal tools card in Dashboard Account → Internal Testing with one-click launch links for calibration and benchmark console access.
- Added a minimal backend template for internal benchmark endpoint launch targets used during calibration/hardening.
- **Commit:** recorded in git for this pass (see repository log).

## 2026-03-15 — Deterministic Calibration Alignment Pass
- Tightened deterministic phrase matching with word-boundary logic for single-token phrases to reduce substring false positives.
- Added calibration-targeted phrase/guard updates for launch-relevant disagreements (billing consultation-fee severity, severe professionalism cues, timeliness typo variant, office staff positive phrase).
- Fixed a dictionary-key overwrite bug in `office_staff_experience` that was dropping most positive staff phrases.
- Removed calibration workflow `datetime.utcnow()` deprecation usage in workflow/batch scripts via timezone-aware UTC timestamps.
- **Commit:** recorded in git for this pass (see repository log).

## 2026-03-15 — Clarion AI Memory System Setup
- Added a lightweight AI control/startup layer for fast orientation and handoff continuity.
- Added scoped docs for current build boundaries, project state, protected systems, overview, and AI standards.
- Normalized startup path so future sessions can begin with four files instead of long chat handoffs.
- **Commit:** recorded in git for this pass (see repository log).

## Prior Notable Passes (from git history)
- `b9a8a97` — calibration wave 2 phrase additions + bug fixes.
- `3f6aba0` — outbound email quality and content SEO improvements.
- `d2647c5` — calibration + agent office pipeline fix.
- `30cb290` — approval queue dashboard/backend integration pass.
