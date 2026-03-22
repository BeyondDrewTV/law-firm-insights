# Clarion — Client Feedback Governance for Law Firms

> **Live demo:** [law-firm-feedback-saas.onrender.com](https://law-firm-feedback-saas.onrender.com)
> · Built by [Andrew Yomantas](https://linkedin.com/in/andrew-yomantas-94a7383b0)

---

## What It Is

Law firm managing partners have no structured way to turn client feedback into governance decisions. Reviews come in across email, surveys, and post-matter feedback — patterns go unnoticed, complaints don't loop back into operations, and partners walk into meetings without a clear record of what clients are actually saying.

Clarion closes that loop.

**The workflow:**
1. Upload a CSV export of client reviews
2. Clarion classifies each review into governance themes — deterministically, no LLM dependency
3. Recurring signals and recommended actions surface automatically
4. Partners assign owners and due dates to each action
5. A governance brief is generated — readable on-screen, exportable as PDF, deliverable by email
6. Repeat each cycle to track what changed, what stalled, and what needs escalation

The output is a partner-ready governance brief with a canonical 5-section spine: Leadership Briefing → Signals That Matter Most → Assigned Follow-Through → Decisions & Next Steps → Supporting Evidence.

---

## Live Product

| Surface | URL |
|---|---|
| Landing page | [law-firm-feedback-saas.onrender.com](https://law-firm-feedback-saas.onrender.com) |
| Sample governance brief | [/demo/reports/sample](https://law-firm-feedback-saas.onrender.com/demo/reports/sample) |
| Sample workspace | [/demo](https://law-firm-feedback-saas.onrender.com/demo) |

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React 18, TypeScript, Vite, Tailwind CSS |
| Backend | Python 3.14, Flask |
| Database | SQLite (dev) / PostgreSQL (production) |
| Hosting | Render |
| Billing | Stripe (Free / Team / Firm tiers) |
| Email | Resend |
| PDF Generation | ReportLab |
| Monitoring | Sentry |


---

## Repository Structure

```
clarion/
├── backend/                    # Flask API — auth, billing, governance engine
│   ├── app.py                  # Main application: routes, session, rate limiting, security
│   ├── pdf_generator.py        # ReportLab-based governance brief PDF generation
│   └── services/
│       ├── governance_insights.py   # Signal extraction, severity scoring, action generation
│       ├── benchmark_engine.py      # Deterministic classification engine (10 themes)
│       └── email_service.py         # Resend-based partner brief email delivery
│
├── frontend/                   # React SPA — marketing site + authenticated workspace
│   └── src/
│       ├── pages/              # Route-level components (Dashboard, Signals, Reports, etc.)
│       └── components/
│           ├── landing/        # Public marketing components
│           ├── governance/     # Shared design system components (cards, chips, wrappers)
│           └── dashboard/      # Dashboard-specific modules
│
├── Clarion-Agency/             # Internal AI agent office — Clarion's own operations
│   ├── agents/                 # Per-division agent definitions and prompts
│   ├── execution/              # Bounded execution layer (L1/L2/L3 authority model)
│   └── memory/                 # Standing orders, approved actions, agent memory
│
├── automation/calibration/     # Benchmark calibration pipeline scripts
├── data/calibration/           # Calibration inputs and synthetic review data
├── docs/                       # Architecture docs, working rules, project state
└── tools/                      # Smoke test helpers and seeded workspace tooling
```

---

## Architecture Notes

**Classification engine** (`backend/services/benchmark_engine.py`)
- Fully deterministic — no LLM in the scoring path
- 10 governance themes with negation/contrast guards and severity escalation
- Outputs are reproducible and auditable across runs
- Benchmarked against AI-generated labels via a separate calibration harness

**Governance brief output**
- 5-section canonical spine, locked across all output surfaces
- On-screen brief, ReportLab PDF, and Resend email delivery from the same data source
- Present mode for displaying the brief on a screen in partner meetings

**Billing and plan enforcement**
- Stripe integration with Free, Team ($179/mo), and Firm ($449/mo) tiers
- Plan-scoped feature gating throughout: report limits, PDF watermarks, seat caps

**Security posture**
- Session-based auth with Flask-Login
- CSRF protection, rate limiting, security headers
- Workspace-scoped data isolation — each firm's data is structurally separated at the query level

---

## Project Status

Release-candidate ready. Operator smoke-tested end-to-end:
login → CSV upload → report generation → signals view → action creation → PDF export → partner brief email delivery

Active development: dashboard visual hierarchy pass, design system refinement, domain cutover to `clarion.co`.

---

## Running Locally

**Requirements:** Python 3.11+, Node 18+

```bash
# Backend
cd backend
pip install -r requirements.txt
cp .env.example .env   # fill in RESEND_API_KEY, SECRET_KEY, STRIPE_* keys
python app.py

# Frontend (separate terminal)
cd frontend
npm install
npm run dev
```

The frontend dev server proxies `/api/*` requests to the Flask backend automatically.

---

## Contact

**Andrew Yomantas** — AI Product & Operations Builder, Loves Park IL
[LinkedIn](https://linkedin.com/in/andrew-yomantas-94a7383b0) · drewyomantas@gmail.com · [GitHub](https://github.com/BeyondDrewTV)
