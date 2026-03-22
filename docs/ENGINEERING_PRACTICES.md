# Engineering Practices

_This document explains how Clarion is built, what standards we follow, and what a developer picking up this codebase should know. It also serves as the working rules for AI-assisted development sessions._

---

## How This Project Is Built

Clarion is built by a solo non-developer product owner using AI-assisted development. Every architecture decision, product requirement, and scope boundary was specified by the product owner before code was written. AI assistants implemented those specifications.

This is not a negative — it means the product has strong product judgment and real architecture behind it. It does mean a few things a collaborator should know:

- **The codebase is intentional, not accidental.** The docs in `/docs/` are working authority documents, not generated boilerplate. Read them.
- **`app.py` is a large Flask monolith.** This is a known limitation. Refactoring into Flask blueprints is a planned future pass.
- **The frontend is a single JS bundle.** Code splitting is a planned future pass.
- **Calibration run data is excluded from the repo.** The `data/calibration/runs/` directory is gitignored. Run outputs live locally.

---

## Repository Hygiene Rules

These apply to every AI-assisted session and every human contributor:

### What belongs in version control
- Source code (Python, TypeScript, CSS)
- Configuration files (`tailwind.config.ts`, `vite.config.ts`, `requirements.txt`)
- Documentation (`docs/`, `README.md`, component-level comments)
- Migration scripts and schema definitions
- The `.gitignore` itself

### What does NOT belong in version control
- Database files (`*.db`, `*.sqlite`) — always gitignored
- Environment files (`.env`, `.env.*`) — always gitignored
- Calibration run artifacts (`data/calibration/runs/`) — generated outputs, not source
- Temporary or diagnostic scripts (`diag_*.py`, `tmp/`) — gitignored
- Operational batch files (`*.bat`, `*.ps1`) that are local convenience tools — gitignored
- The `archive/` folder — legacy reference only
- Log files and compiled output

### Commit message format
Use the pattern: `scope: short description`

Examples:
```
design-system: warm canvas tokens and card elevation pass
fix: remove RETURNING clause from verify-email upsert
feat: meeting mode present overlay for partner briefs
docs: update PROJECT_STATE for design system reset pass
```

Avoid: `fix bug`, `update`, `changes`, `WIP` as standalone commit messages.

---

## Cleanup Checkpoint Practice

Real projects accumulate clutter — diagnostic scripts, temp files, debug artifacts. Professional codebases run periodic cleanup passes to prevent this from building up.

**Rule:** At the end of every 5–10 development sessions, run a cleanup checkpoint before the next feature pass.

**Cleanup checkpoint checklist:**
- [ ] Root folder: any loose scripts, `.bat` files, or `.py` diagnostics that should be deleted or moved to `tools/`
- [ ] `tmp/` contents: clear anything that isn't intentionally committed
- [ ] `.gitignore`: does it still cover everything it should?
- [ ] `docs/PROJECT_STATE.md`: is it current?
- [ ] `docs/CHANGELOG_AI.md`: is the last pass recorded?
- [ ] Commit history: any "WIP" or unnamed commits that should be cleaned up?

This is not a big production — it takes 15–20 minutes and makes the repo look maintained rather than abandoned.

---

## Protected Systems

These files require deliberate justification before editing. See `docs/AI_WORKING_RULES.md` for full detail.

| File | Why Protected |
|---|---|
| `backend/app.py` auth/session block | Login, CSRF, rate limiting, security headers |
| `backend/services/governance_insights.py` | Live scoring engine — changes affect all output |
| `backend/services/benchmark_engine.py` | Classification phrase library — additive-only changes |
| `backend/pdf_generator.py` | Brief PDF layout and data binding |

---

## Known Technical Debt (Planned, Not Forgotten)

| Item | Priority | Notes |
|---|---|---|
| `app.py` monolith → Flask blueprints | Later | 17k lines, functional, refactor when stable collaborator available |
| Frontend code splitting | Later | Single 911kB bundle, not a performance issue at current scale |
| Postgres compatibility audit | Before pilot launch | `POSTGRES_VALIDATION_GUIDE.md` documents known issues |
| GDPR compliance checklist | Before EU exposure | Checklist exists in docs, largely incomplete |
| Stripe webhook edge cases | Before launch | Failed payments, expired cards need end-to-end confirmation |
