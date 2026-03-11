# Clarion Agency

Internal AI operations system for Clarion — a B2B SaaS platform for law firms.

## Structure

```
Clarion-Agency/
├── agents/              # Agent prompt files organized by division
│   ├── executive/       # Chief of Staff
│   ├── revenue/         # Head of Growth, Funnel Conversion, Sales Development, Revenue Strategy
│   ├── market/          # Customer Discovery, Competitive Intelligence, Market Trends, ICP Analyst
│   ├── customer/        # Customer Health & Onboarding, VoC & Product Demand, Retention Intelligence
│   ├── product_insight/ # Product Usage Analyst, Release Impact Analyst (coming)
│   ├── product_integrity/ # Dictionary Calibration, Scoring Quality, Data Quality (coming)
│   ├── operations/      # Process Analyst, Cost & Resource (coming)
│   ├── comms/           # Content & SEO Agent (coming)
│   └── people/          # People & Ops Intelligence Agent (coming)
├── memory/              # Grounding files injected into agent prompts
├── reports/             # Agent report outputs (written at runtime)
│   └── ceo_brief/       # Weekly CEO briefs from Chief of Staff
├── workflows/           # Python runners for each agent
├── config.json          # Model assignments, token budgets, cadences
├── comms_protocol.md    # Communication rules all agents follow
└── agent_prompt_template.md  # Template for writing new agent prompts
```

## Setup

1. Copy `.env.example` to `.env` and add your `OPENROUTER_API_KEY`
2. Install dependencies: `pip install openai python-dotenv`
3. Run an agent: `python workflows/customer_discovery_agent.py`

## Key Rules

- Agents do NOT communicate with each other
- All reports flow to the Chief of Staff
- Chief of Staff produces the weekly CEO brief
- No agent may modify production systems, the phrase dictionary, or send external communications
- All recommendations require human review before action

## Grounding Files

All agents reference these memory files:
- `memory/product_truth.md` — what Clarion is and does
- `memory/brand_canon.md` — how Clarion speaks and positions
- `memory/customer_insights.md` — ICP and customer segments
- `memory/office_policies.md` — agent operating rules
- `memory/calibration_log.md` — phrase dictionary change history
