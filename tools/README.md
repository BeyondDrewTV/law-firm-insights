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
