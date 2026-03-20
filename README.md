# Clarion — Law Firm Client Feedback Governance Platform

> Designed and built by [Andrew Yomantas](https://linkedin.com/in/andrew-yomantas-94a7383b0) — AI Product & Operations Builder based in Loves Park, IL.

---

## What This Is

Clarion is a governance-focused SaaS platform for small law firms.

It solves a specific, underserved problem: law firm managing partners have no structured way to turn client feedback into actionable governance decisions. Reviews come in, patterns go unnoticed, issues don't loop back into operations.

Clarion closes that loop.

Upload client feedback → classify it into governance themes → surface signals and action plans → deliver partner-ready briefs that drive real meeting decisions.

---

## What This Demonstrates

This project is proof-of-concept architecture built to production standards. No users yet — but the architecture, design decisions, and system patterns are real.

**Systems thinking at depth:**
- Fully deterministic classification engine — 10 governance themes, negation/contrast guards, severity escalation, zero LLM dependency in production scoring
- Workspace-scoped data isolation so each firm's data is structurally separated
- Append-only audit log for governance decisions — immutable by design, not convention

**AI-assisted product execution:**
- 25-agent internal operations office across 10 functional divisions
- Per-division authority matrices with bounded execution model
- Agents operate within structured approval gates — no autonomous action without authorization

**Full-stack product ownership:**
- Scoped, designed, architected, and built solo without a traditional engineering team
- Directed AI to implement production-grade architecture across both frontend and backend
- Every major design decision (CEO approval gate, agent bus pattern, calibration harness) was specified before code was written

**Domain expertise:**
- Built for a specific vertical with specific accountability structures — not generic CRM
- The core loop is: issue → action → owner → follow-through/trend
- Governance brief outputs are designed for managing partners, not operators or analysts

---

## Core Workflow

1. Upload client feedback (CSV ingestion into workspace)
2. Classify reviews into 10 governance themes — deterministically, no LLM
3. Generate structured governance signals and recommended actions
4. Assign actions with owner, due date, and status tracking
5. Produce governance brief outputs (dashboard, PDF, email brief)
6. Repeat cycle to monitor change over time

---

## Architecture Highlights

| Layer | Description |
|---|---|
| Classification Engine | Deterministic, rule-based. 10 themes, negation/contrast guards, severity escalation. No LLM in scoring path. |
| Agent Office (Clarion-Agency) | 25 agents across 10 divisions. Structured authority matrices. Append-only audit log. Bounded execution. |
| Governance Brief Output | ReportLab-generated PDFs. Partner-ready formatting. Designed for law firm meeting use. |
| Calibration Harness | Benchmarks deterministic engine vs. AI-generated labels via OpenRouter. Bearer-token gated. Flask Blueprint. |
| Frontend | React / TypeScript / Vite. Governance-focused design system. Four-tier dashboard layout. |
| Backend | Python / Flask monolith. SQLite (dev) / PostgreSQL (production). Stripe billing. Redis. Sentry. |

---

## Tech Stack

- **Frontend:** React, TypeScript, Vite, Tailwind CSS
- **Backend:** Python, Flask, SQLite / PostgreSQL
- **Infrastructure:** Render (deployment), Redis, Sentry
- **Billing:** Stripe
- **PDF Generation:** ReportLab
- **Agent Office:** Python, custom orchestration layer

---

## Repository Structure

```
law-firm-insights-main/
├── backend/                     # Flask API + deterministic scoring engine
│   ├── app.py                   # Main application
│   ├── services/                # Core business logic (governance insights, benchmark, scoring)
│   ├── routes/                  # API route handlers
│   └── pdf_generator.py         # Governance brief PDF generation
│
├── frontend/                    # React SPA
│   └── src/
│
├── Clarion-Agency/              # AI Agent Office (25 agents / 10 divisions)
│   ├── run_clarion_agent_office.py
│   ├── agents/                  # Per-division agent definitions
│   ├── execution/               # Autonomous execution layer (L1/L2/L3)
│   └── memory/                  # Agent memory and standing orders
│
├── automation/calibration/      # Benchmark calibration workflow
├── data/calibration/            # Calibration inputs, synthetic reviews, run outputs
├── docs/                        # Operational guides and reference docs
└── tools/                       # Maintenance and smoke test helpers
```

---

## Quick Start

### Backend
```bash
cd backend
python app.py
```

### Frontend
```bash
cd frontend
npm install && npm run dev
```

### Agent Office
```bash
cd Clarion-Agency
python run_clarion_agent_office.py
```

### Calibration Harness
```bash
python automation/calibration/run_calibration_workflow.py --csv data/calibration/inputs/real_reviews.csv
```

---

## Project Status

Pre-launch. Architecture and core product workflow are complete. Calibration and governance engine validated. Active development ongoing.

---

## Contact

**Andrew Yomantas**
[LinkedIn](https://linkedin.com/in/andrew-yomantas-94a7383b0) · drewyomantas@gmail.com · [GitHub](https://github.com/BeyondDrewTV)
