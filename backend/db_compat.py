import re
import sqlite3
from typing import Any, Optional

from sqlalchemy import create_engine


def _is_postgres_url(database_url: str) -> bool:
    value = (database_url or "").strip().lower()
    return value.startswith("postgres://") or value.startswith("postgresql://")


class CompatCursor:
    def __init__(self, conn: "CompatConnection", raw_cursor):
        self._conn = conn
        self._cursor = raw_cursor
        self._synthetic_rows: Optional[list[tuple[Any, ...]]] = None
        self._synthetic_index = 0
        self.lastrowid = None

    def _set_synthetic(self, rows: list[tuple[Any, ...]]):
        self._synthetic_rows = rows
        self._synthetic_index = 0

    def _rewrite_sql(self, sql: str) -> str:
        rewritten = sql

        # SQLite DDL compatibility
        rewritten = re.sub(
            r"\bINTEGER\s+PRIMARY\s+KEY\s+AUTOINCREMENT\b",
            "SERIAL PRIMARY KEY",
            rewritten,
            flags=re.IGNORECASE,
        )
        rewritten = re.sub(
            r"\bid\s+INTEGER\s+PRIMARY\s+KEY\b",
            "id SERIAL PRIMARY KEY",
            rewritten,
            flags=re.IGNORECASE,
        )

        # SQLite INSERT OR IGNORE compatibility
        if re.match(r"^\s*INSERT\s+OR\s+IGNORE\s+INTO\s+", rewritten, flags=re.IGNORECASE):
            rewritten = re.sub(
                r"^\s*INSERT\s+OR\s+IGNORE\s+INTO\s+",
                "INSERT INTO ",
                rewritten,
                count=1,
                flags=re.IGNORECASE,
            )
            if "ON CONFLICT" not in rewritten.upper():
                rewritten = rewritten.rstrip().rstrip(";") + " ON CONFLICT DO NOTHING"

        # SQLite datetime() helper compatibility
        # Special-case datetime('now') / datetime("now") first → CURRENT_TIMESTAMP
        rewritten = re.sub(
            r"\bdatetime\s*\(\s*['\"]now['\"]\s*\)",
            "CURRENT_TIMESTAMP",
            rewritten,
            flags=re.IGNORECASE,
        )
        # General datetime(expr) → CAST(expr AS timestamp)
        rewritten = re.sub(r"\bdatetime\(([^)]+)\)", r"CAST(\1 AS timestamp)", rewritten, flags=re.IGNORECASE)

        # SQLite BLOB type → Postgres BYTEA
        rewritten = re.sub(r"\bBLOB\b", "BYTEA", rewritten, flags=re.IGNORECASE)

        # DB-API placeholder compatibility: ? -> %s
        rewritten = rewritten.replace("?", "%s")
        return rewritten

    def _try_set_lastrowid(self, sql: str):
        """lastrowid is set by appending RETURNING id to INSERTs — see execute()."""
        self.lastrowid = None

    def execute(self, sql: str, params=None):
        if params is None:
            params = ()
        self._synthetic_rows = None
        self._synthetic_index = 0

        if not self._conn.is_postgres:
            self._cursor.execute(sql, params)
            self.lastrowid = getattr(self._cursor, "lastrowid", None)
            return self

        stripped = sql.strip()
        lower = stripped.lower()

        # SQLite PRAGMA compatibility no-ops
        if lower.startswith("pragma foreign_keys") or lower.startswith("pragma journal_mode"):
            self._set_synthetic([])
            return self

        # SQLite PRAGMA table_info(<table>) compatibility
        pragma_match = re.match(r"^pragma\s+table_info\(([^)]+)\)", lower, flags=re.IGNORECASE)
        if pragma_match:
            table = pragma_match.group(1).strip().strip("'\"")
            self._cursor.execute(
                """
                SELECT column_name, data_type, is_nullable, column_default
                FROM information_schema.columns
                WHERE table_schema = 'public' AND table_name = %s
                ORDER BY ordinal_position
                """,
                (table,),
            )
            rows = []
            for idx, row in enumerate(self._cursor.fetchall()):
                col_name = row[0]
                col_type = row[1]
                is_nullable = row[2]
                col_default = row[3]
                not_null = 0 if str(is_nullable).upper() == "YES" else 1
                is_pk = 1 if col_name == "id" else 0
                rows.append((idx, col_name, col_type, not_null, col_default, is_pk))
            self._set_synthetic(rows)
            return self

        # SQLite sqlite_master compatibility
        if "from sqlite_master" in lower:
            table_name = None
            if params and len(params) > 0:
                table_name = params[0]
            else:
                m = re.search(r"name\s*=\s*'([^']+)'", stripped, flags=re.IGNORECASE)
                if m:
                    table_name = m.group(1)
            if table_name:
                self._cursor.execute(
                    """
                    SELECT table_name
                    FROM information_schema.tables
                    WHERE table_schema = 'public' AND table_name = %s
                    """,
                    (table_name,),
                )
                fetched = self._cursor.fetchall()
                self._set_synthetic([(row[0],) for row in fetched])
            else:
                self._set_synthetic([])
            return self

        rewritten = self._rewrite_sql(sql)

        # For INSERT ... VALUES statements on Postgres, append RETURNING id so
        # lastrowid works. Skip INSERT ... SELECT (no RETURNING on set-based inserts).
        stripped_upper = rewritten.upper()
        is_insert = stripped_upper.lstrip().startswith("INSERT ")
        is_insert_select = bool(re.search(r"\bINSERT\b.+\bSELECT\b", rewritten, flags=re.IGNORECASE | re.DOTALL))
        has_returning = "RETURNING" in stripped_upper
        add_returning = is_insert and not is_insert_select and not has_returning

        if add_returning:
            rewritten = rewritten.rstrip().rstrip(";") + " RETURNING id"

        self._cursor.execute(rewritten, params)

        # Capture the returned id from RETURNING id clause
        if add_returning:
            try:
                row = self._cursor.fetchone()
                self.lastrowid = int(row[0]) if row else None
            except Exception:
                self.lastrowid = None
        else:
            self.lastrowid = None

        return self

    def executemany(self, sql: str, seq_of_params):
        if not self._conn.is_postgres:
            self._cursor.executemany(sql, seq_of_params)
            return self
        rewritten = self._rewrite_sql(sql)
        self._cursor.executemany(rewritten, seq_of_params)
        return self

    def fetchone(self):
        if self._synthetic_rows is not None:
            if self._synthetic_index >= len(self._synthetic_rows):
                return None
            row = self._synthetic_rows[self._synthetic_index]
            self._synthetic_index += 1
            return row
        return self._cursor.fetchone()

    def fetchall(self):
        if self._synthetic_rows is not None:
            rows = self._synthetic_rows[self._synthetic_index :]
            self._synthetic_index = len(self._synthetic_rows)
            return rows
        return self._cursor.fetchall()

    def __iter__(self):
        if self._synthetic_rows is not None:
            return iter(self._synthetic_rows)
        return iter(self._cursor)

    def __getattr__(self, item):
        return getattr(self._cursor, item)


class CompatConnection:
    def __init__(self, raw_conn, is_postgres: bool):
        self._conn = raw_conn
        self.is_postgres = is_postgres
        self.row_factory = None

    def cursor(self):
        return CompatCursor(self, self._conn.cursor())

    def execute(self, sql: str, params=None):
        return self.cursor().execute(sql, params or ())

    def commit(self):
        return self._conn.commit()

    def rollback(self):
        return self._conn.rollback()

    def close(self):
        return self._conn.close()

    def __getattr__(self, item):
        return getattr(self._conn, item)


class DatabaseConnector:
    def __init__(self, database_url: str):
        self.database_url = database_url
        self.is_postgres = _is_postgres_url(database_url)
        self._engine = None
        if self.is_postgres:
            # SQLAlchemy Core engine + psycopg2 DBAPI under the hood.
            self._engine = create_engine(database_url, pool_pre_ping=True, future=True)

    def connect(self):
        if self.is_postgres:
            raw_conn = self._engine.raw_connection()
            return CompatConnection(raw_conn, is_postgres=True)

        sqlite_path = self.database_url.replace("sqlite:///", "", 1)
        conn = sqlite3.connect(sqlite_path, timeout=5)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return CompatConnection(conn, is_postgres=False)
