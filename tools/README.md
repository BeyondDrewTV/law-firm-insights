# tools/

One-off maintenance and operational scripts. These are not part of the regular automated workflow.

| Script | Purpose |
|--------|---------|
| `security_smoke.py` | Quick smoke test for auth/security endpoints |
| `ensure_e2e_user.py` | Create or verify the E2E test user account |
| `reset_e2e_state.py` | Reset E2E test state between runs |
| `export_released_outreach.py` | Export released outreach items from Clarion-Agency queue to CSV/JSON |
| `export_released_content.py` | Export released content items from Clarion-Agency queue |
| `export_released_account_setup.py` | Export released account setup items from Clarion-Agency queue |

## Usage

Run from repo root:

```bash
python tools/security_smoke.py
python tools/export_released_outreach.py --format csv
python tools/export_released_content.py
```

## Seeded E2E / RC Smoke Helpers

`ensure_e2e_user.py` and `reset_e2e_state.py` now resolve the active DB from backend env config (`backend/.env`) so they target the same SQLite/Postgres connection as the running app.

Common environment variables:

```bash
E2E_SMOKE_EMAIL=smoke.e2e@lawfirminsights.local
E2E_SMOKE_PASSWORD=SmokeTest123
E2E_SMOKE_FIRM="Smoke LLP"
E2E_SMOKE_PLAN=team   # free | team | firm
```

Example:

```bash
backend\venv312\Scripts\python.exe tools\ensure_e2e_user.py
backend\venv312\Scripts\python.exe tools\reset_e2e_state.py
```
