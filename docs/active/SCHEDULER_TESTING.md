# Scheduler Testing Guide

## Manual trigger (don't wait for Monday 08:00)

```python
# From the backend directory with venv active:
cd C:\Users\beyon\OneDrive\Desktop\CLARION\law-firm-insights-main\backend
venv312\Scripts\python -c "
import os
os.chdir(r'C:\Users\beyon\OneDrive\Desktop\CLARION\law-firm-insights-main\backend')
from services.scheduler import weekly_brief
weekly_brief()
print('Done')
"
```

## SQL: Create test schedules

```sql
-- Firm A: user_id = 1, two recipients
INSERT OR REPLACE INTO report_pack_schedules
    (user_id, enabled, cadence, recipients_json, next_send_at, created_at, updated_at)
VALUES
    (1, 1, 'weekly', '["partner1@test.com"]',
     datetime('now', '+7 days'), datetime('now'), datetime('now'));

-- Firm B: user_id = 2, one recipient
INSERT OR REPLACE INTO report_pack_schedules
    (user_id, enabled, cadence, recipients_json, next_send_at, created_at, updated_at)
VALUES
    (2, 1, 'weekly', '["partner2@test.com"]',
     datetime('now', '+7 days'), datetime('now'), datetime('now'));

-- Verify schedules are enabled
SELECT user_id, enabled, cadence, recipients_json, last_sent_at
FROM report_pack_schedules
WHERE enabled = 1;
```

## Verify no crosstalk

After triggering, check last_sent_at was stamped for both rows:

```sql
SELECT user_id, enabled, last_sent_at, recipients_json
FROM report_pack_schedules
ORDER BY user_id;
```

Each user_id should show its own last_sent_at timestamp.
The query in _generate_brief_html_for_user() is scoped by WHERE r.user_id = ?
so reports are never mixed between users.

## email_service.py attachment support

send_email_with_pdf() in email_service.py is available if PDF attachments are
needed in future. The current scheduler sends HTML-only briefs (same as before).
To add PDF: call generate_pdf_report() then pass bytes to send_email_with_pdf().
