# product_truth.md
# Clarion — Canonical Product Facts
# Version: 1.0 | All agents must treat this file as ground truth.

---

## What Clarion Is

Clarion is a B2B SaaS platform built for law firms. It collects client reviews, analyzes them, and converts them into structured governance insights that managing partners and operations leaders can act on.

---

## How the Scoring System Works

- Reviews are submitted by clients and ingested via CSV or equivalent structured format.
- A **curated phrase dictionary** maps specific phrases to predefined governance themes.
- Scoring is **fully deterministic** — the same input always produces the same output.
- **AI is not involved in production scoring.** No model inference occurs in the scoring pipeline.
- The phrase dictionary is maintained manually by authorized humans only.

---

## How AI Is Used at Clarion

AI is used **internally only**, for:

- Analyzing review trends and patterns
- Generating marketing and content ideas
- Calibrating and stress-testing the phrase dictionary (proposals only)
- Supporting internal operations and reporting

AI is **never** used to score client reviews or generate client-facing governance outputs.

---

## Target Users

| Role | Primary Need |
|---|---|
| Managing Partners | Governance insights, firm-level trends |
| Operations Leaders | Process improvement, escalation signals |
| Marketing / Reputation Managers | Review sentiment, messaging opportunities |

---

## Hard Constraints — Agents Must Never

- Modify production code or the phrase dictionary
- Access production databases
- Send external communications automatically
- Give legal advice of any kind

---

## Agent Scope — Agents May Only

- Analyze data and information provided to them
- Produce internal reports and summaries
- Propose ideas or recommendations for human review
- Escalate issues to the appropriate human or agent layer
