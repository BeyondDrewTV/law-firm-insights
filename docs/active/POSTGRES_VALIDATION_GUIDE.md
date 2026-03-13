# Clarion — PostgreSQL Pre-Launch Validation Guide

**Purpose:** Catch production-only bugs before they happen.  
**Scope:** `db_compat.py`, `app.py` schema + queries.  
**Goal:** Confirm all critical user flows work identically on PostgreSQL as on SQLite.

---

## Part 1 — Known Compatibility Issues Found by Code Audit

Run these fixes **before** any testing. They are real bugs that will surface on Postgres.

---

### Issue 1 — `sqlite3.Binary()` on line 9372 (CRITICAL)

**File:** `app.py` line ~9372  
**Function:** `_store_report_pdf_artifact()`

**Problem:**  
`sqlite3.Binary(pdf_bytes)` is a SQLite-specific wrapper. It does not exist in psycopg2.
On PostgreSQL this will throw `AttributeError` when saving PDF artifacts.

**Fix in `app.py`:**

```python
# BEFORE
(report_id, user_id, sqlite3.Binary(pdf_bytes), timestamp),

# AFTER
(report_id, user_id, pdf_bytes, timestamp),
```

`psycopg2` accepts raw `bytes` for `BYTEA` columns natively. SQLite also accepts raw bytes.
Remove the `sqlite3.Binary()` wrapper entirely — it is not needed for either database.

---

### Issue 2 — `sqlite3.OperationalError` bare catch (lines 1227, 1447, 10861)

**File:** `app.py`

**Problem:**  
These lines catch `sqlite3.OperationalError` directly. On PostgreSQL, database errors come
as `psycopg2.OperationalError` (or `psycopg2.errors.*`), which does NOT inherit from
`sqlite3.OperationalError`. The `except` blocks will silently not fire, and the original
exception will propagate uncaught.

**Fix in `app.py` — add to imports (top of file, near existing sqlite3 import):**

```python
try:
    import psycopg2
    _PSYCOPG2_AVAILABLE = True
except ImportError:
    psycopg2 = None
    _PSYCOPG2_AVAILABLE = False

# Unified DB operational error tuple for except clauses
_DB_OPERATIONAL_ERRORS = (sqlite3.OperationalError,)
if psycopg2 is not None:
    _DB_OPERATIONAL_ERRORS = (sqlite3.OperationalError, psycopg2.OperationalError)
```

Then replace all three bare `except sqlite3.OperationalError` with:

```python
except _DB_OPERATIONAL_ERRORS as exc:
```

---

### Issue 3 — `datetime('now')` in DDL (lines 1910, schema)

**File:** `app.py` schema block

**Problem:**  
```sql
submitted_at TEXT NOT NULL DEFAULT (datetime('now'))
```
`datetime('now')` is SQLite syntax. PostgreSQL will reject this DDL entirely and `init_db()`
will fail on first startup.

`db_compat.py`'s `_rewrite_sql()` translates `datetime()` in **query** SQL but NOT in DDL
`CREATE TABLE` statements.

**Fix — two options (choose one):**

**Option A (preferred) — use `CURRENT_TIMESTAMP` which is ANSI SQL:**
```python
# In init_db(), change:
submitted_at TEXT   NOT NULL DEFAULT (datetime('now'))
# To:
submitted_at TEXT   NOT NULL DEFAULT (CURRENT_TIMESTAMP)
```

**Option B — extend `db_compat.py` `_rewrite_sql()` to also cover DDL defaults:**
```python
# Add to _rewrite_sql() in db_compat.py, before the existing datetime() rewrite:
rewritten = re.sub(
    r"DEFAULT\s*\(\s*datetime\s*\(\s*['\"]?now['\"]?\s*\)\s*\)",
    "DEFAULT CURRENT_TIMESTAMP",
    rewritten,
    flags=re.IGNORECASE,
)
```

Option A is cleaner. `CURRENT_TIMESTAMP` works on both SQLite and PostgreSQL.

---

### Issue 4 — `datetime()` calls in WHERE/ORDER clauses (multiple lines)

**File:** `app.py` lines 3844, 3864, 5061, 5091, 5405–5407, 5919, 5934, 5949, 12454, 12456, 13571, 15460, 15465, 15605

**Examples:**
```sql
AND datetime(purge_at) <= datetime('now')
ORDER BY datetime(r.created_at) DESC
AND datetime(created_at) >= datetime(?)
```

**Problem:**  
`db_compat.py` already has a rewrite rule for `datetime()`:
```python
rewritten = re.sub(r"\bdatetime\(([^)]+)\)", r"CAST(\1 AS timestamp)", ...)
```

However, `datetime('now')` would rewrite to `CAST('now' AS timestamp)` which is **invalid
PostgreSQL**. PostgreSQL uses `NOW()` or `CURRENT_TIMESTAMP` for the current time.

**Fix in `db_compat.py` — add a special-case rule BEFORE the general datetime() rewrite:**

```python
# Handle datetime('now') / datetime("now") specifically FIRST
rewritten = re.sub(
    r"\bdatetime\s*\(\s*['\"]now['\"]\s*\)",
    "CURRENT_TIMESTAMP",
    rewritten,
    flags=re.IGNORECASE,
)
# Then the existing general rule (already present):
rewritten = re.sub(r"\bdatetime\(([^)]+)\)", r"CAST(\1 AS timestamp)", rewritten, ...)
```

This ensures `datetime('now')` → `CURRENT_TIMESTAMP` and
`datetime(some_column)` → `CAST(some_column AS timestamp)`.

---

### Issue 5 — `SELECT sql FROM sqlite_master` for firms table (lines ~2240)

**File:** `app.py` inside `init_db()`, the firms table migration block

**Problem:**  
```python
c.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='firms'")
```
`sqlite_master` does not exist in PostgreSQL. `db_compat.py` intercepts `FROM sqlite_master`
queries and emulates them with `information_schema.tables`, but it only returns the
**table name** — NOT the `sql` DDL string that the code then inspects for the legacy
`CHECK(plan IN ...)` constraint.

On PostgreSQL, `firms_table_sql_row` will be `None` or empty, so `legacy_plan_check` will
always be `False`. This means the firms table migration block is silently skipped — harmless
if the schema is fresh, but a bug for any existing PostgreSQL database.

**Fix — guard the DDL inspection with a database-type check:**

```python
firms_table_sql_row = None
if not _db_connector.is_postgres:
    c.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='firms'")
    firms_table_sql_row = c.fetchone()
firms_table_sql = str(firms_table_sql_row[0] or '').lower() if firms_table_sql_row else ''
legacy_plan_check = "check(plan in ('trial','professional','leadership'))" in firms_table_sql
```

On PostgreSQL, `legacy_plan_check` will be `False` (correct — the table never had the legacy
constraint in a Postgres deployment).

---

### Issue 6 — `PRAGMA foreign_keys=OFF` in firms migration block

**File:** `app.py` inside `init_db()`

**Problem:**  
```python
c.execute('PRAGMA foreign_keys=OFF')
```
`db_compat.py` has a no-op handler for `PRAGMA foreign_keys` so this won't throw, but the
intent — disabling FK checks during a table rebuild — has **no effect** on PostgreSQL.
The subsequent `DROP TABLE firms` will fail if any rows in `reports` or `firm_users`
reference `firms.id` due to FK constraints.

**Status:** This migration block only triggers when `legacy_plan_check` is `True`.
After applying the fix in Issue 5, it will never run on PostgreSQL. No additional change needed
beyond Issue 5's fix.

---

### Issue 7 — `INSERT OR IGNORE` / `INSERT OR REPLACE` (multiple locations)

**File:** `app.py` lines 2506, 2789, 6547, 6731, 10299, 5577

**Status: ALREADY HANDLED** by `db_compat.py`.  
The `_rewrite_sql()` method rewrites `INSERT OR IGNORE INTO` →
`INSERT INTO ... ON CONFLICT DO NOTHING`. Verify this is working during testing.

---

### Issue 8 — `ON CONFLICT(report_id) DO UPDATE` upsert (line ~9351)

**File:** `app.py`, `_store_report_pdf_artifact()`

**Status: Works on PostgreSQL as-is.** PostgreSQL natively supports
`ON CONFLICT(col) DO UPDATE SET ...` syntax. This is fine.

---

## Part 2 — PostgreSQL Setup (Local)

### Option A — Docker (recommended, no system install needed)

```bash
# Start PostgreSQL 15
docker run --name clarion-pg \
  -e POSTGRES_USER=clarion \
  -e POSTGRES_PASSWORD=clarion_dev \
  -e POSTGRES_DB=clarion_test \
  -p 5432:5432 \
  -d postgres:15

# Verify it's running
docker exec clarion-pg psql -U clarion -d clarion_test -c "SELECT version();"
```

### Option B — Native Windows install

Download from https://www.postgresql.org/download/windows/ and install.
Then in psql:
```sql
CREATE USER clarion WITH PASSWORD 'clarion_dev';
CREATE DATABASE clarion_test OWNER clarion;
```

---

## Part 3 — Configure Clarion to Use PostgreSQL

In `backend/.env`, set:

```env
DATABASE_URL=postgresql://clarion:clarion_dev@localhost:5432/clarion_test
```

Comment out or remove `DATABASE_PATH` if present. The app will print:
```
[DB] Using DATABASE_URL: postgresql://...
```
at startup to confirm it picked up the Postgres URL.

Install the driver if not already installed (into venv312):
```bash
venv312\Scripts\pip install psycopg2-binary
```

---

## Part 4 — Apply Code Fixes Before Testing

Apply all fixes from Part 1 **before** running any tests.

Quick fix summary:
1. Remove `sqlite3.Binary()` wrapper in `_store_report_pdf_artifact()` in `app.py`
2. Add `_DB_OPERATIONAL_ERRORS` tuple and replace bare `sqlite3.OperationalError` catches
3. Change `DEFAULT (datetime('now'))` → `DEFAULT (CURRENT_TIMESTAMP)` in DDL
4. Add `datetime('now')` → `CURRENT_TIMESTAMP` rewrite in `db_compat.py`
5. Guard `sqlite_master` DDL inspection with `if not _db_connector.is_postgres`

---

## Part 5 — Test Execution Checklist

Run these flows in order. Each flow verifies a distinct code path.

### ✅ Flow 1 — Schema Initialization

```bash
cd backend
venv312\Scripts\python app.py
```

**Pass:** Server starts, no SQL errors in output.  
**Watch for:** Any `ERROR` lines mentioning table creation, DDL syntax errors, or
`datetime()` parse failures.

---

### ✅ Flow 2 — User Registration

Via the frontend or curl:
```bash
curl -X POST http://localhost:5000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"Test1234!","firm_name":"Test Firm","username":"testuser"}'
```

**Pass:** `{"success": true}` response, row appears in `users` table.  
**Watch for:** Any unique constraint errors, column type errors.

---

### ✅ Flow 3 — Login

```bash
curl -c cookies.txt -X POST http://localhost:5000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"Test1234!"}'
```

**Pass:** Session cookie returned, `{"success": true}`.

---

### ✅ Flow 4 — CSV Upload

Use the frontend Upload page, or:
```bash
curl -b cookies.txt -X POST http://localhost:5000/api/upload \
  -F "file=@sample_data/sample_reviews.csv"
```

**Pass:** Reviews stored in `reviews` + `review_ownership`.  
**Watch for:** `INSERT OR IGNORE` translation errors (Issue 7).

---

### ✅ Flow 5 — Report Analysis (triggers LLM classification)

Click "Analyze" in the frontend, or:
```bash
curl -b cookies.txt -X POST http://localhost:5000/api/analyze/<report_id>
```

**Pass:** Report record updated with analysis JSON, signals generated.  
**Watch for:** Any `datetime()` errors in the signals/reports query (Issue 4).

---

### ✅ Flow 6 — Governance Signals

```bash
curl -b cookies.txt http://localhost:5000/api/signals
```

**Pass:** Array of signal objects returned.  
**Watch for:** `ORDER BY datetime(...)` errors.

---

### ✅ Flow 7 — Action Creation

```bash
curl -b cookies.txt -X POST http://localhost:5000/api/reports/<report_id>/actions \
  -H "Content-Type: application/json" \
  -d '{"title":"Review communication process","owner":"Operations Partner","status":"open"}'
```

**Pass:** Action row created, returned in subsequent GET.

---

### ✅ Flow 8 — PDF Brief Generation

```bash
curl -b cookies.txt http://localhost:5000/api/reports/<report_id>/pdf --output test.pdf
```

**Pass:** Valid PDF returned, `report_pdf_artifacts` row stored.  
**Watch for:** `sqlite3.Binary()` error (Issue 1) — this is the highest-risk item.

---

### ✅ Flow 9 — Scheduled Brief (manual trigger)

In a Python shell (with venv active and DATABASE_URL set):
```python
from services.scheduler import start_scheduler
# Or call the brief generation function directly:
from services.email_brief import build_partner_brief_html
```

Check that no SQL errors fire when the scheduler reads report data.

---

## Part 6 — Verification Queries

Run these directly in psql after completing the flows above to confirm data integrity:

```sql
-- All tables created
SELECT table_name FROM information_schema.tables
WHERE table_schema = 'public'
ORDER BY table_name;

-- Users created
SELECT id, email, subscription_type, email_verified FROM users;

-- Reviews uploaded
SELECT COUNT(*) FROM reviews;
SELECT COUNT(*) FROM review_ownership;

-- Reports analyzed
SELECT id, total_reviews, avg_rating, created_at FROM reports ORDER BY id DESC LIMIT 5;

-- Signals generated
SELECT * FROM governance_signals ORDER BY id DESC LIMIT 10;

-- Actions created
SELECT * FROM report_action_items ORDER BY id DESC LIMIT 5;

-- PDF artifact stored (binary, just check row exists)
SELECT report_id, user_id, length(pdf_blob) as pdf_size_bytes, generated_at
FROM report_pdf_artifacts;
```

---

## Part 7 — Rollback Plan

If a blocking issue is found during validation:

1. Keep `DATABASE_URL` set to Postgres for production.
2. Set `DATABASE_URL` back to empty (SQLite fallback) in `.env` for local dev.
3. The `DatabaseConnector` in `db_compat.py` switches automatically — no code changes needed.

The SQLite dev database is never affected by Postgres testing.

---

## Summary of Code Changes Required

| # | File | Change | Severity |
|---|------|--------|----------|
| 1 | `app.py` line ~9372 | Remove `sqlite3.Binary()` wrapper | **CRITICAL** — will crash PDF save on PG |
| 2 | `app.py` lines 1227, 1447, 10861 | Replace bare `sqlite3.OperationalError` with unified tuple | **HIGH** — silent catch failures |
| 3 | `app.py` DDL (public_feedback) | `DEFAULT (datetime('now'))` → `DEFAULT (CURRENT_TIMESTAMP)` | **HIGH** — schema init will fail |
| 4 | `db_compat.py` | Add `datetime('now')` → `CURRENT_TIMESTAMP` rewrite rule | **HIGH** — query errors in filters |
| 5 | `app.py` init_db() | Guard `sqlite_master` DDL inspection with `is_postgres` check | **MEDIUM** — silent skip on PG |
