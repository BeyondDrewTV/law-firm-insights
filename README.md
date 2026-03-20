# Clarion — Law Firm Client Feedback Governance

> Built by [Andrew Yomantas](https://linkedin.com/in/andrew-yomantas-94a7383b0) — AI Product & Operations Builder, Loves Park IL.

---

## What This Is

Clarion is a governance-focused SaaS platform for small law firms.

Law firm managing partners have no structured way to turn client feedback into actionable governance decisions. Reviews come in, patterns go unnoticed, complaints don't loop back into operations. Partners walk into meetings without a clear record of what clients are actually saying.

Clarion closes that loop.

Upload client feedback → classify it into governance themes → surface recurring signals and recommended actions → produce partner-ready governance briefs that drive real meeting decisions.

**Status:** Release-candidate ready. Operator smoke-tested end-to-end. Active development ongoing toward first pilot.

---

## What This Demonstrates

**Systems thinking at depth**
- Fully deterministic classification engine — 10 governance themes, negation/contrast guards, severity escalation. Zero LLM dependency in production scoring; labels are reproducible and auditable.
- Workspace-scoped data isolation so each firm's data is structurally separated
- Append-only audit log for governance decisions — immutable by design, not convention
- Calibration harness that benchmarks the deterministic engine against AI-generated labels, with stored run artifacts for regression tracking

**AI-directed product execution**
- Scoped, designed, architected, and built solo without a traditional engineering team
- Directed AI assistants to implement production-grade architecture across frontend and backend
- Every major design decision was specified before code was written — architecture-first, not vibe-coding
- Internal AI agent office (separate from the law firm product) handles Clarion's own outbound operations: 22 agents across 5 divisions with structured authority matrices and bounded execution gates

**Full-stack product ownership**
- From blank canvas to operator-smoke-tested platform
- Pricing, billing, and plan enforcement implemented (Stripe, Free/Team/Firm tiers)
- Email verification, rate limiting, CSRF, session management — real security posture
- PDF generation, email delivery, and shareable brief outputs in the same governance cycle

**Domain specificity**
- Built for a specific vertical with specific accountability structures — not generic CRM
- The operative loop is: issue → action → owner → follow-through/trend
- Governance brief outputs are designed for managing partners, not operators or analysts

---

## Core Product Workflow

1. Upload client feedback (CSV export from reviews, surveys, or post-matter feedback)
2. Classify reviews into 10 governance themes — deterministically, no LLM
3. Generate structured governance signals and recommended actions
4. Assign actions with owner, due date, and status tracking
5. Produce governance brief outputs: on-screen, PDF, and email summary
6. Repeat each cycle to monitor what changed and what stalled

---

## Architecture Highlights

| Layer | Description |
|---|---|
| Classification Engine | Deterministic, rule-based. 10 themes, negation/contrast guards, severity escalation. No LLM in scoring path. Reproducible outputs. |
| Governance Brief Output | 5-section canonical spine. ReportLab-generated PDFs. Present mode for partner meetings. Email delivery via Resend. |
| Calibration Harness | Benchmarks deterministic engine vs. AI-generated labels. Bearer-token gated. Stored run artifacts for regression tracking. |
| Billing & Plan Enforcement | Stripe integration. Free, Team ($179/mo), and Firm ($449/mo) tiers. Plan-scoped feature gating throughout. |
| Agent Office (Internal) | 22-agent autonomous operations system for Clarion's own business. 5 divisions, structured authority matrices, bounded execution. Separate from the law firm product. |
| Frontend | React / TypeScript / Vite. Custom governance design system. Brief-first IA. Present mode for partner meetings. |
| Backend | Python / Flask monolith. SQLite (dev) / PostgreSQL (production on Render). Redis. Sentry. |

---

## Tech Stack

**Frontend:** React, TypeScript, Vite, Tailwind CSS  
**Backend:** Python, Flask, SQLite / PostgreSQL  
**Infrastructure:** Render, Redis, Sentry  
**Billing:** Stripe  
**Email:** Resend  
**PDF Generation:** ReportLab  
**Agent Office:** Python, custom orchestration layer  

---

## Repository Structure

```
clarion/
├── backend/                     # Flask API + deterministic scoring engine
│   ├── app.py                   # Main application, auth, session, rate limiting
│   ├── services/                # Governance insights, benchmark engine, scoring
│   ├── routes/                  # API route handlers
│   └── pdf_generator.py         # Governance brief PDF generation (ReportLab)
│
├── frontend/                    # React SPA
│   └── src/
│       ├── pages/               # Workspace routes + public marketing routes
│       └── components/          # Governance design system components
│
├── Clarion-Agency/              # Internal AI agent office (Clarion's own operations)
│   ├── agents/                  # Per-division agent definitions
│   ├── execution/               # Bounded execution layer (L1/L2/L3 authority model)
│   └── memory/                  # Agent memory, standing orders, approved actions
│
├── automation/calibration/      # Benchmark calibration workflow scripts
├── data/calibration/            # Calibration inputs, synthetic reviews, run outputs
└── tools/                       # Smoke test helpers and seeded workspace tooling
```

---

## Contact

**Andrew Yomantas**  
[LinkedIn](https://linkedin.com/in/andrew-yomantas-94a7383b0) · drewyomantas@gmail.com · [GitHub](https://github.com/BeyondDrewTV)
