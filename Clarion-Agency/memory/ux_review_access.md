# ux_review_access.md
# Clarion — UX Review Access Protocol
# Version: 1.0 | 2026-03-12
# Read by: Product Experience Agent (required), Site Health Monitor
# Maintained by: CEO only

---

## PURPOSE
Define how the Product Experience Agent inspects the live Clarion product safely —
without causing false incidents, contaminating analytics, or requiring risky production access.

Live site: https://law-firm-feedback-saas.onrender.com/

---

## SECTION 1: COLD-START BEHAVIOR (RENDER)

Clarion is hosted on Render's free tier. The app cold-starts after inactivity.

**Cold-start retry rule (mandatory for all agents):**
- If the site is unreachable or returns a timeout on first attempt, DO NOT immediately classify as down.
- Retry with a wait interval: attempt at T+0, T+60s, T+2m, T+3m, T+5m.
- Intermediate classification during retry window: BOOTING_OR_UNKNOWN — not FAILING.
- Only classify as FAILING if the site is still unreachable after the full 5-minute window.
- A cold-start boot (site responds after 1-4 retries) is NORMAL — do not log as an incident.
- Log a boot event as informational only if it causes a meaningful inspection delay.

**What boot tolerance does NOT cover:**
- A site that responds with a 5xx error (not timeout) on first load — this may be a real error, not a boot delay. Investigate and apply severity classification normally.
- A site that responds but has broken pages or failed functionality — cold-start does not explain functional failures once the app is running.

---

## SECTION 2: ALLOWED INSPECTION SURFACES

The following surfaces may be inspected by read-only public access:

| Surface | URL pattern | Inspection method |
|---------|------------|-------------------|
| Landing page | / (root) | Public read |
| Pricing page | /pricing (if exists) | Public read |
| Signup page | /signup or /register | Public read — observe form, do NOT submit |
| Login page | /login | Public read — observe only |
| Demo / onboarding flow | /demo or guided entry (if public) | Public read |
| Public marketing pages | /about, /how-it-works, etc. | Public read |

**Dashboard and in-app pages** require authenticated access (see Section 4).

---

## SECTION 3: SAFE READ-ONLY BEHAVIOR RULES

Every inspection must follow these rules:

DO:
- Load and observe pages
- Inspect visible copy, hierarchy, CTAs, layout, and credibility signals
- Note what is present and what is absent
- Document observations in product_experience_log.md
- Distinguish between a boot delay and a functional failure (see Section 1)

DO NOT:
- Submit any form, including signup, login, contact, or demo request forms
- Click "create account", "start trial", or any CTA that creates a record
- Enter any real email address or personal data into any field
- Upload any file
- Click links that may trigger email sends or external integrations
- Interact with any chat widget, feedback form, or support tool
- Perform any action that would leave a trace in production analytics or the database
- Attempt to access admin routes or any route not reachable via public navigation

**If a form must be inspected visually**, the agent describes what it observes in the DOM/UI without submitting it.

---

## SECTION 4: SAFE IN-APP ACCESS MODEL

### Current State (Pre-Launch)
A dedicated internal review account and seeded demo workspace do not yet exist.
Until they are provisioned, the in-app surfaces (dashboard, onboarding flow, governance report view) cannot be safely inspected without risking production data contamination.

### Target Model (to be implemented before first customer)

**Option A — Internal Review Account (preferred)**
- A dedicated account created specifically for UX review (e.g., ux-review@clarionapp.com or equivalent)
- Seeded with synthetic demo data: a realistic but non-real law firm name, synthetic client feedback entries, and pre-scored governance themes
- Account is flagged internally so its sessions do not contaminate production analytics
- Login credentials stored securely in the team's password manager (never in any agent file, memory file, or source code)
- The account is reset to a known demo state monthly or after each major review cycle

**Option B — Demo Workspace Seed**
- A seeded firm workspace with controlled synthetic data is created as part of the product's internal demo mode
- Accessible via a demo login path that is distinct from real customer accounts
- Demo sessions are excluded from all usage analytics

**Until Option A or B is implemented:**
- In-app inspection is limited to what can be observed from public pages
- Dashboard and post-login UX findings must be based on founder screenshots, screen recordings, or direct access walkthroughs shared with the agent
- The Product Experience Agent documents gaps in in-app coverage and flags the setup of Option A or B as a proposed action

### What the UX Review Account May Do
- Log in and navigate the product
- View existing demo data
- Trigger governance theme scoring on synthetic feedback (if demo data is seeded)
- Navigate the onboarding flow
- View a completed governance report

### What the UX Review Account May NOT Do
- Modify, delete, or export any data
- Invite real users or send emails from within the product
- Change account settings, billing, or subscription state
- Access any other firm's workspace or data
- Leave any feedback or review submission that goes to external systems

### Data That Must Never Be Modified
- Any real customer firm's data
- Any real client feedback record
- Any production scoring output
- Any billing or Stripe record
- Any user authentication record outside the dedicated review account

---

## SECTION 5: DISTINGUISHING PRODUCT FRICTION FROM BOOT DELAY

Use this decision tree before logging any finding related to site availability:

1. Did the site fail to load on first attempt?
   → Apply cold-start retry rule (Section 1). Wait up to 5 minutes.

2. Did the site load after retry?
   → Boot event. Do not log as incident. Note the boot time in report as informational.
   → Proceed with normal inspection.

3. Did the site load but with a functional error (5xx, broken page, missing content)?
   → This is a real finding. Log according to severity. Not a cold-start issue.

4. Did the site fail to load after the full 5-minute retry window?
   → Classify as FAILING. Log incident. Escalate per site_health.md rules.

5. Did the site load slowly but successfully?
   → Note load time. If load time exceeds 8 seconds after cold-start is ruled out, log as MEDIUM severity.

---

## SECTION 6: HOW OBSERVATIONS ARE DOCUMENTED

Every observation must be documented in memory/product_experience_log.md using the defined entry format:

```
DATE:           [YYYY-MM-DD]
AREA:           [homepage | pricing | signup | onboarding | dashboard | pilot_collateral]
SURFACE:        [landing | pricing | signup | onboarding | dashboard | pilot collateral]
ISSUE_TYPE:     [clarity | conversion | trust | hierarchy | visual_age | friction | proof_gap | navigation]
SEVERITY:       [HIGH | MEDIUM | LOW]
OBSERVATION:    [Specific and factual — what was seen]
WHY_IT_MATTERS: [Commercial consequence — one sentence]
PROPOSED_CHANGE:[Specific proposed fix — non-technical, founder-readable]
STATUS:         proposed
```

For each observation, the agent must also note:
- Whether the finding was observed on the live site directly, or inferred from partial access
- Whether a cold-start delay affected the inspection (and whether the finding persists after boot)

---

## SECTION 7: WHEN TO STOP AND LOG A PRODUCT-ACCESS ISSUE

Stop the UX inspection and log a product-access issue (not a product incident) when:

- The site is still unreachable after the full 5-minute retry window
- The site loads but displays only an error page with no product content
- Login to the review account fails and cannot be resolved (once Option A is provisioned)
- The demo workspace data appears to have been wiped or corrupted

Log a product-access issue in the weekly report under PRODUCT ACCESS STATUS — not in the incidents log.
Only escalate to the incidents log if the failure is confirmed as a site-wide functional failure (not an access configuration issue).
