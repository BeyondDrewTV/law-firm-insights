# services/review_classifier.py

import hashlib
import json
import logging
import time

from jsonschema import validate, ValidationError

from schemas.classification_schema import (
    SCHEMA_VERSION,
    CLASSIFICATION_SCHEMA,
    FALLBACK_CLASSIFICATION,
    ALLOWED_THEMES,
)
from services.llm_client import call_model, MODEL_VERSION

logger = logging.getLogger("review_classifier")

LOW_CONFIDENCE_THRESHOLD = 0.65

# Plan caps for classification (mirrors report analysis caps)
CLASSIFY_CAP_TRIAL = 30
CLASSIFY_CAP_ONETIME = 500
CLASSIFY_CAP_PRO = 5000  # matches MAX_CSV_ROWS

VOCAB_LINE = ", ".join(ALLOWED_THEMES)

USER_PROMPT_TEMPLATE = """\
THEME VOCABULARY (use ONLY these exact strings for themes[].name):
{vocab}

REVIEW TEXT:
\"\"\"
{review_text}
\"\"\"

Classify the review. Return JSON only. No other text."""


def compute_review_hash(review_text: str, rating, date) -> str:
    """
    Deterministic sha256 of (review_text + rating + date).
    Deduplication key for review_classifications.
    """
    normalized = f"{str(review_text).strip()}|{str(rating).strip()}|{str(date).strip()}"
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _build_user_prompt(review_text: str) -> str:
    safe_text = review_text.strip()[:800]
    return USER_PROMPT_TEMPLATE.format(vocab=VOCAB_LINE, review_text=safe_text)


def _parse_and_validate(raw: str) -> dict:
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"JSON parse error: {exc}") from exc
    try:
        validate(instance=parsed, schema=CLASSIFICATION_SCHEMA)
    except ValidationError as exc:
        raise ValueError(f"Schema validation error: {exc.message}") from exc
    return parsed


def _classify_review_text(review_text: str) -> tuple:
    """
    Call model with up to 2 attempts.
    Returns (result_dict, classification_failed: bool).
    Never raises.
    """
    prompt = _build_user_prompt(review_text)
    last_error = None

    for attempt in range(1, 3):
        raw = None
        try:
            raw = call_model(prompt)
            result = _parse_and_validate(raw)
            logger.info(
                "classify attempt=%d confidence=%.2f themes=%d",
                attempt,
                result["confidence"],
                len(result["themes"]),
            )
            return result, False
        except Exception as exc:
            last_error = exc
            logger.warning(
                "classify attempt=%d error=%s raw_preview=%s",
                attempt,
                exc,
                (raw or "")[:200],
            )
            if attempt < 2:
                time.sleep(1.0)

    logger.error("classify failed both attempts error=%s", last_error)
    return FALLBACK_CLASSIFICATION.copy(), True


def get_existing_classification(conn, review_hash: str) -> dict | None:
    """
    Return stored classification dict if (review_hash, schema_version) exists.
    Returns None on miss.
    """
    c = conn.cursor()
    c.execute(
        """
        SELECT result_json
        FROM review_classifications
        WHERE review_hash = ? AND schema_version = ?
        """,
        (review_hash, SCHEMA_VERSION),
    )
    row = c.fetchone()
    if not row:
        return None
    try:
        return json.loads(row[0])
    except (TypeError, json.JSONDecodeError):
        return None


def _get_existing_row_meta(conn, review_hash: str) -> dict | None:
    """
    Return metadata for (review_hash, schema_version), or None if no row exists.
    """
    c = conn.cursor()
    c.execute(
        """
        SELECT result_json, classification_failed
        FROM review_classifications
        WHERE review_hash = ? AND schema_version = ?
        """,
        (review_hash, SCHEMA_VERSION),
    )
    row = c.fetchone()
    if not row:
        return None
    return {"result_json": row[0], "classification_failed": bool(row[1])}


def _delete_existing_classification(conn, review_id: int, review_hash: str) -> None:
    """
    Delete an existing classification row and its related theme rows so a
    fresh INSERT can replace it without hitting the UNIQUE constraint.
    Does NOT commit — caller must commit.
    """
    c = conn.cursor()
    c.execute(
        "DELETE FROM review_classification_themes WHERE review_id = ?",
        (review_id,),
    )
    c.execute(
        """
        DELETE FROM review_classifications
        WHERE review_hash = ? AND schema_version = ?
        """,
        (review_hash, SCHEMA_VERSION),
    )


def _store_classification(
    conn,
    review_id: int,
    review_hash: str,
    result: dict,
    classification_failed: bool,
) -> None:
    """
    Write classification result. INSERT OR IGNORE is safe for new rows.
    For retries the caller must first call _delete_existing_classification.
    Does not commit — caller commits.
    """
    c = conn.cursor()

    c.execute(
        """
        INSERT OR IGNORE INTO review_classifications
            (review_id, review_hash, model_version, schema_version,
             result_json, confidence, classification_failed)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            review_id,
            review_hash,
            MODEL_VERSION,
            SCHEMA_VERSION,
            json.dumps(result, ensure_ascii=False),
            float(result.get("confidence", 0.0)),
            1 if classification_failed else 0,
        ),
    )

    # Only write theme rows if we actually inserted (not ignored by UNIQUE constraint).
    if c.rowcount == 0:
        return

    for theme in result.get("themes", []):
        c.execute(
            """
            INSERT INTO review_classification_themes
                (review_id, theme_name, polarity, severity)
            VALUES (?, ?, ?, ?)
            """,
            (
                review_id,
                theme["name"],
                theme["polarity"],
                theme["severity"],
            ),
        )


def ensure_classifications_for_report(
    conn,
    user_id: int,
    review_rows: list,
    access_type: str,
    db_connect=None,
) -> dict:
    """
    Classify reviews that either:
      (a) have no stored classification for the current SCHEMA_VERSION, OR
      (b) have a stored classification with classification_failed=1 (retry).

    Respects plan caps:
      trial   -> classify at most CLASSIFY_CAP_TRIAL reviews
      onetime -> classify at most CLASSIFY_CAP_ONETIME reviews
      monthly / annual -> classify at most CLASSIFY_CAP_PRO reviews

    review_rows: list of dicts with keys: id, review_text, rating, date

    db_connect: callable that returns a fresh SQLite connection configured the
                same way as app.db_connect(). When provided, all internal
                connections are opened via this callable (no path guessing).
                When omitted, falls back to importing db_connect from app.

    IMPORTANT: This function CLOSES the passed-in conn after the initial
    cache-check read, then opens a fresh short-lived connection for each write.
    This prevents holding the SQLite write lock across slow LLM API calls.

    Returns:
      {
        "classified": int,   # newly classified (includes successful retries)
        "skipped":    int,   # already had a successful stored classification
        "failed":     int,   # stored as fallback (classification_failed=1) this call
        "retried":    int,   # rows that were previously failed and re-attempted
      }
    """
    # Resolve the connection factory once.
    if db_connect is None:
        try:
            from app import db_connect as _app_db_connect
            db_connect = _app_db_connect
        except Exception:
            # Last-resort fallback: build a minimal factory from DATABASE_PATH env var.
            import os
            import sqlite3 as _sqlite3

            _db_path = os.environ.get("DATABASE_PATH") or "feedback.db"

            def db_connect():  # type: ignore[no-redef]
                _c = _sqlite3.connect(_db_path, timeout=20)
                _c.execute("PRAGMA foreign_keys = ON")
                _c.execute("PRAGMA journal_mode = WAL")
                return _c

    cap_map = {
        "trial":   CLASSIFY_CAP_TRIAL,
        "onetime": CLASSIFY_CAP_ONETIME,
        "monthly": CLASSIFY_CAP_PRO,
        "annual":  CLASSIFY_CAP_PRO,
    }
    cap = cap_map.get(access_type, CLASSIFY_CAP_TRIAL)
    capped_rows = review_rows[:cap]

    classified = 0
    skipped = 0
    failed = 0
    retried = 0

    for row in capped_rows:
        review_hash = compute_review_hash(row["review_text"], row["rating"], row["date"])

        # --- Read phase: quick read-only check, short lock window ---
        read_conn = db_connect()
        existing_meta = _get_existing_row_meta(read_conn, review_hash)
        read_conn.close()

        is_retry = False

        if existing_meta is not None:
            if not existing_meta["classification_failed"]:
                # Successful classification already stored — skip.
                skipped += 1
                continue
            # Previously failed — schedule a retry.
            is_retry = True
            retried += 1

        # --- LLM call: NO db connection held during the API call ---
        result, is_failed = _classify_review_text(row["review_text"])

        # --- Write phase: open, write, commit, close immediately ---
        write_conn = db_connect()
        try:
            if is_retry:
                # Remove stale failed row so the fresh INSERT lands cleanly.
                _delete_existing_classification(write_conn, row["id"], review_hash)
            _store_classification(write_conn, row["id"], review_hash, result, is_failed)
            write_conn.commit()
        finally:
            write_conn.close()

        classified += 1
        if is_failed:
            failed += 1

    # Close the originally passed-in conn — it's no longer needed.
    try:
        conn.close()
    except Exception:
        pass

    return {"classified": classified, "skipped": skipped, "failed": failed, "retried": retried}


def fetch_stored_classifications(conn, review_ids: list) -> list:
    """
    Return stored classification dicts for the given review_ids.
    Reviews with no stored classification for current SCHEMA_VERSION are omitted.
    """
    if not review_ids:
        return []

    placeholders = ",".join("?" * len(review_ids))
    c = conn.cursor()
    c.execute(
        f"""
        SELECT rc.review_id, rc.result_json
        FROM review_classifications rc
        WHERE rc.review_id IN ({placeholders})
          AND rc.schema_version = ?
        """,
        (*review_ids, SCHEMA_VERSION),
    )
    rows = c.fetchall()

    id_to_result = {}
    for review_id, result_json in rows:
        try:
            id_to_result[review_id] = json.loads(result_json)
        except (TypeError, json.JSONDecodeError):
            pass

    return [id_to_result[rid] for rid in review_ids if rid in id_to_result]