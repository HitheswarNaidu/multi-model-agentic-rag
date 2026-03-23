"""SQLite database — single source of truth for all RAG pipeline metadata.

Tables
------
documents   – one row per ingested file
chunks      – one row per indexed chunk (FK → documents)
jobs        – ingestion job tracking
query_logs  – per-query timing, quality, plan, feature flags
answers     – LLM answer payloads
audit_events – append-only structured event log
"""

from __future__ import annotations

import json
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

_DB_PATH: Path | None = None
_LOCAL = threading.local()

# ---------------------------------------------------------------------------
# Connection management (one connection per thread)
# ---------------------------------------------------------------------------

def set_db_path(path: Path | str) -> None:
    global _DB_PATH
    _DB_PATH = Path(path)
    _DB_PATH.parent.mkdir(parents=True, exist_ok=True)


def get_db_path() -> Path:
    if _DB_PATH is None:
        raise RuntimeError("Database path not set — call set_db_path() first")
    return _DB_PATH


def _get_conn() -> sqlite3.Connection:
    conn = getattr(_LOCAL, "conn", None)
    if conn is None:
        conn = sqlite3.connect(str(get_db_path()), timeout=30)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        _LOCAL.conn = conn
    return conn


@contextmanager
def transaction():
    conn = _get_conn()
    conn.execute("BEGIN")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise


def execute(sql: str, params: tuple | dict = ()) -> sqlite3.Cursor:
    return _get_conn().execute(sql, params)


def executemany(sql: str, seq) -> sqlite3.Cursor:
    return _get_conn().executemany(sql, seq)


def commit() -> None:
    _get_conn().commit()


def fetchone(sql: str, params: tuple | dict = ()) -> dict | None:
    row = _get_conn().execute(sql, params).fetchone()
    return dict(row) if row else None


def fetchall(sql: str, params: tuple | dict = ()) -> list[dict]:
    return [dict(r) for r in _get_conn().execute(sql, params).fetchall()]


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------

_SCHEMA = """
CREATE TABLE IF NOT EXISTS documents (
    doc_id          TEXT PRIMARY KEY,
    doc_type        TEXT NOT NULL DEFAULT '',
    source_path     TEXT,
    source_hash     TEXT,
    chunk_count     INTEGER NOT NULL DEFAULT 0,
    ingested_at     TEXT NOT NULL,
    deleted_at      TEXT
);

CREATE TABLE IF NOT EXISTS chunks (
    chunk_id            TEXT PRIMARY KEY,
    doc_id              TEXT NOT NULL REFERENCES documents(doc_id) ON DELETE CASCADE,
    doc_type            TEXT NOT NULL DEFAULT '',
    chunk_type          TEXT NOT NULL DEFAULT 'paragraph',
    page                INTEGER NOT NULL DEFAULT 0,
    section             TEXT NOT NULL DEFAULT '',
    content             TEXT NOT NULL DEFAULT '',
    parent_content      TEXT,
    table_id            TEXT,
    confidence          REAL NOT NULL DEFAULT 1.0,
    source_path         TEXT,
    source_hash         TEXT,
    ingest_timestamp_utc TEXT,
    is_table            INTEGER NOT NULL DEFAULT 0,
    is_image            INTEGER NOT NULL DEFAULT 0,
    semantic_group_id   TEXT,
    boundary_reason     TEXT,
    index_id            TEXT
);

CREATE INDEX IF NOT EXISTS idx_chunks_doc_id ON chunks(doc_id);
CREATE INDEX IF NOT EXISTS idx_chunks_chunk_type ON chunks(chunk_type);
CREATE INDEX IF NOT EXISTS idx_chunks_page ON chunks(doc_id, page);

CREATE TABLE IF NOT EXISTS jobs (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id          TEXT NOT NULL,
    status          TEXT NOT NULL DEFAULT 'pending',
    files_detected  INTEGER NOT NULL DEFAULT 0,
    processed_files INTEGER NOT NULL DEFAULT 0,
    files_indexed   INTEGER NOT NULL DEFAULT 0,
    chunks_indexed  INTEGER NOT NULL DEFAULT 0,
    errors          TEXT NOT NULL DEFAULT '[]',
    timing_ms       TEXT NOT NULL DEFAULT '{}',
    error           TEXT,
    error_code      TEXT,
    created_at      TEXT NOT NULL,
    updated_at      TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_jobs_job_id ON jobs(job_id);

CREATE TABLE IF NOT EXISTS query_logs (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    request_id          TEXT NOT NULL UNIQUE,
    original_question   TEXT,
    question_hash       TEXT,
    rewritten_question  TEXT,
    mode                TEXT,
    filters             TEXT,
    plan                TEXT,
    intent              TEXT,
    execution_log       TEXT,
    validation          TEXT,
    feature_flags       TEXT,
    timing_ms           TEXT NOT NULL DEFAULT '{}',
    quality             TEXT NOT NULL DEFAULT '{}',
    created_at          TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_query_logs_request_id ON query_logs(request_id);

CREATE TABLE IF NOT EXISTS answers (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    request_id      TEXT NOT NULL UNIQUE,
    answer          TEXT NOT NULL DEFAULT '',
    provenance      TEXT NOT NULL DEFAULT '[]',
    conflict        INTEGER NOT NULL DEFAULT 0,
    llm_provider    TEXT,
    llm_model       TEXT,
    fallback_used   INTEGER NOT NULL DEFAULT 0,
    raw_payload     TEXT NOT NULL DEFAULT '{}',
    created_at      TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_answers_request_id ON answers(request_id);

CREATE TABLE IF NOT EXISTS audit_events (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp_utc   TEXT NOT NULL,
    event_type      TEXT NOT NULL,
    payload         TEXT NOT NULL DEFAULT '{}'
);

CREATE INDEX IF NOT EXISTS idx_audit_event_type ON audit_events(event_type);
CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_events(timestamp_utc);
"""


def init_db(db_path: Path | str | None = None) -> None:
    """Create tables if they don't exist. Safe to call multiple times."""
    if db_path is not None:
        set_db_path(db_path)
    conn = _get_conn()
    conn.executescript(_SCHEMA)


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _json_dumps(obj) -> str:
    if isinstance(obj, str):
        return obj
    return json.dumps(obj, ensure_ascii=True, default=str)


# ---------------------------------------------------------------------------
# Documents
# ---------------------------------------------------------------------------

def upsert_document(
    doc_id: str,
    doc_type: str = "",
    source_path: str | None = None,
    source_hash: str | None = None,
    chunk_count: int = 0,
) -> None:
    execute(
        """INSERT INTO documents (doc_id, doc_type, source_path, source_hash, chunk_count, ingested_at)
           VALUES (?, ?, ?, ?, ?, ?)
           ON CONFLICT(doc_id) DO UPDATE SET
               doc_type=excluded.doc_type,
               source_path=excluded.source_path,
               source_hash=excluded.source_hash,
               chunk_count=excluded.chunk_count,
               ingested_at=excluded.ingested_at,
               deleted_at=NULL""",
        (doc_id, doc_type, source_path, source_hash, chunk_count, _utc_now()),
    )
    commit()


def delete_document(doc_id: str) -> int:
    """Soft-delete a document. Returns chunks removed."""
    count = execute("SELECT COUNT(*) FROM chunks WHERE doc_id=?", (doc_id,)).fetchone()[0]
    with transaction():
        execute("DELETE FROM chunks WHERE doc_id=?", (doc_id,))
        execute("UPDATE documents SET deleted_at=?, chunk_count=0 WHERE doc_id=?", (_utc_now(), doc_id))
    return count


def list_documents() -> list[dict]:
    return fetchall("SELECT * FROM documents WHERE deleted_at IS NULL ORDER BY doc_id")


def get_document(doc_id: str) -> dict | None:
    return fetchone("SELECT * FROM documents WHERE doc_id=? AND deleted_at IS NULL", (doc_id,))


# ---------------------------------------------------------------------------
# Chunks
# ---------------------------------------------------------------------------

def insert_chunks(records: list[dict]) -> int:
    if not records:
        return 0
    sql = """INSERT OR REPLACE INTO chunks
             (chunk_id, doc_id, doc_type, chunk_type, page, section, content,
              parent_content, table_id, confidence, source_path, source_hash,
              ingest_timestamp_utc, is_table, is_image, semantic_group_id,
              boundary_reason, index_id)
             VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)"""
    rows = []
    for r in records:
        rows.append((
            r.get("chunk_id", ""),
            r.get("doc_id", ""),
            r.get("doc_type", ""),
            r.get("chunk_type", "paragraph"),
            r.get("page", 0),
            r.get("section", ""),
            r.get("content", ""),
            r.get("parent_content"),
            r.get("table_id"),
            r.get("confidence", 1.0),
            r.get("source_path"),
            r.get("source_hash"),
            r.get("ingest_timestamp_utc"),
            1 if r.get("is_table") else 0,
            1 if r.get("is_image") else 0,
            r.get("semantic_group_id"),
            r.get("boundary_reason"),
            r.get("index_id"),
        ))
    with transaction():
        executemany(sql, rows)
    return len(rows)


def get_all_chunks() -> list[dict]:
    return fetchall("SELECT * FROM chunks ORDER BY doc_id, page, chunk_id")


def get_chunks_by_doc(doc_id: str) -> list[dict]:
    return fetchall("SELECT * FROM chunks WHERE doc_id=? ORDER BY page, chunk_id", (doc_id,))


def delete_chunks_by_doc(doc_id: str) -> int:
    count = execute("SELECT COUNT(*) FROM chunks WHERE doc_id=?", (doc_id,)).fetchone()[0]
    execute("DELETE FROM chunks WHERE doc_id=?", (doc_id,))
    commit()
    return count


# ---------------------------------------------------------------------------
# Jobs
# ---------------------------------------------------------------------------

def create_job(job_id: str, payload: dict | None = None) -> dict:
    now = _utc_now()
    p = payload or {}
    execute(
        """INSERT INTO jobs (job_id, status, files_detected, processed_files,
           files_indexed, chunks_indexed, errors, timing_ms, error, error_code,
           created_at, updated_at)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
        (
            job_id,
            p.get("status", "pending"),
            p.get("files_detected", 0),
            p.get("processed_files", 0),
            p.get("files_indexed", 0),
            p.get("chunks_indexed", 0),
            _json_dumps(p.get("errors", [])),
            _json_dumps(p.get("timing_ms", {})),
            p.get("error"),
            p.get("error_code"),
            p.get("created_at", now),
            now,
        ),
    )
    commit()
    return get_job(job_id) or {"job_id": job_id}


def update_job(job_id: str, patch: dict) -> dict:
    now = _utc_now()
    existing = get_job(job_id)
    if not existing:
        patch["job_id"] = job_id
        return create_job(job_id, patch)
    # Insert a new row (latest row wins — same append-only semantics)
    merged = {**existing, **patch}
    execute(
        """INSERT INTO jobs (job_id, status, files_detected, processed_files,
           files_indexed, chunks_indexed, errors, timing_ms, error, error_code,
           created_at, updated_at)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
        (
            job_id,
            merged.get("status", "pending"),
            merged.get("files_detected", 0),
            merged.get("processed_files", 0),
            merged.get("files_indexed", 0),
            merged.get("chunks_indexed", 0),
            _json_dumps(merged.get("errors", [])),
            _json_dumps(merged.get("timing_ms", {})),
            merged.get("error"),
            merged.get("error_code"),
            merged.get("created_at", now),
            now,
        ),
    )
    commit()
    return get_job(job_id) or {"job_id": job_id}


def get_job(job_id: str) -> dict | None:
    row = fetchone(
        "SELECT * FROM jobs WHERE job_id=? ORDER BY id DESC LIMIT 1",
        (job_id,),
    )
    if row:
        row["errors"] = json.loads(row.get("errors") or "[]")
        row["timing_ms"] = json.loads(row.get("timing_ms") or "{}")
    return row


def list_jobs() -> list[dict]:
    """Latest state per job_id, newest first."""
    rows = fetchall(
        """SELECT * FROM jobs WHERE id IN (
               SELECT MAX(id) FROM jobs GROUP BY job_id
           ) ORDER BY updated_at DESC"""
    )
    for r in rows:
        r["errors"] = json.loads(r.get("errors") or "[]")
        r["timing_ms"] = json.loads(r.get("timing_ms") or "{}")
    return rows


def has_completed_job() -> bool:
    row = fetchone(
        """SELECT 1 FROM jobs WHERE status='completed'
           AND id IN (SELECT MAX(id) FROM jobs GROUP BY job_id) LIMIT 1"""
    )
    return row is not None


# ---------------------------------------------------------------------------
# Query logs
# ---------------------------------------------------------------------------

def save_query_log(request_id: str, data: dict) -> None:
    execute(
        """INSERT OR REPLACE INTO query_logs
           (request_id, original_question, question_hash, rewritten_question,
            mode, filters, plan, intent, execution_log, validation,
            feature_flags, timing_ms, quality, created_at)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (
            request_id,
            data.get("original_question"),
            data.get("question_hash"),
            data.get("rewritten_question"),
            data.get("mode"),
            _json_dumps(data.get("filters")),
            _json_dumps(data.get("plan")),
            data.get("intent"),
            _json_dumps(data.get("execution_log")),
            _json_dumps(data.get("validation")),
            _json_dumps(data.get("feature_flags")),
            _json_dumps(data.get("timing_ms", {})),
            _json_dumps(data.get("quality", {})),
            _utc_now(),
        ),
    )
    commit()


def get_query_stats() -> tuple[float, float]:
    """Returns (citation_rate_pct, avg_latency_ms)."""
    row = fetchone("""
        SELECT
            COUNT(*) as total,
            SUM(CASE WHEN json_extract(quality, '$.citation_hit') = 1 THEN 1 ELSE 0 END) as hits,
            AVG(json_extract(timing_ms, '$.total_ms')) as avg_latency
        FROM query_logs
    """)
    if not row or not row["total"]:
        return 0.0, 0.0
    rate = (row["hits"] / row["total"] * 100) if row["total"] > 0 else 0.0
    latency = row["avg_latency"] or 0.0
    return round(rate, 1), round(latency, 1)


def get_all_query_logs() -> list[dict]:
    rows = fetchall("SELECT * FROM query_logs ORDER BY created_at DESC")
    for r in rows:
        for col in ("filters", "plan", "execution_log", "validation", "feature_flags", "timing_ms", "quality"):
            if r.get(col):
                try:
                    r[col] = json.loads(r[col])
                except (json.JSONDecodeError, TypeError):
                    pass
    return rows


# ---------------------------------------------------------------------------
# Answers
# ---------------------------------------------------------------------------

def save_answer(request_id: str, payload: dict) -> None:
    execute(
        """INSERT OR REPLACE INTO answers
           (request_id, answer, provenance, conflict, llm_provider, llm_model,
            fallback_used, raw_payload, created_at)
           VALUES (?,?,?,?,?,?,?,?,?)""",
        (
            request_id,
            payload.get("answer", ""),
            _json_dumps(payload.get("provenance", [])),
            1 if payload.get("conflict") else 0,
            payload.get("_llm_provider"),
            payload.get("_llm_model"),
            1 if payload.get("_llm_fallback_used") else 0,
            _json_dumps(payload),
            _utc_now(),
        ),
    )
    commit()


def get_all_answers() -> list[dict]:
    rows = fetchall("SELECT * FROM answers ORDER BY created_at DESC")
    for r in rows:
        r["provenance"] = json.loads(r.get("provenance") or "[]")
        r["raw_payload"] = json.loads(r.get("raw_payload") or "{}")
        r["conflict"] = bool(r.get("conflict"))
        r["fallback_used"] = bool(r.get("fallback_used"))
    return rows


# ---------------------------------------------------------------------------
# Audit events
# ---------------------------------------------------------------------------

def log_audit_event(event_type: str, **payload) -> dict:
    now = _utc_now()
    event = {"timestamp_utc": now, "event_type": event_type, **payload}
    execute(
        "INSERT INTO audit_events (timestamp_utc, event_type, payload) VALUES (?,?,?)",
        (now, event_type, _json_dumps(event)),
    )
    commit()
    return event


def get_audit_events(event_type: str | None = None, limit: int = 500) -> list[dict]:
    if event_type:
        rows = fetchall(
            "SELECT * FROM audit_events WHERE event_type=? ORDER BY id DESC LIMIT ?",
            (event_type, limit),
        )
    else:
        rows = fetchall(
            "SELECT * FROM audit_events ORDER BY id DESC LIMIT ?",
            (limit,),
        )
    for r in rows:
        r["payload"] = json.loads(r.get("payload") or "{}")
    return rows


# ---------------------------------------------------------------------------
# Migration: import existing file-based data into SQLite
# ---------------------------------------------------------------------------

def migrate_from_files(
    chunk_catalog_path: Path | None = None,
    jobs_jsonl_path: Path | None = None,
    events_jsonl_path: Path | None = None,
    answers_dir: Path | None = None,
    logs_dir: Path | None = None,
) -> dict:
    """One-time import of existing JSONL/JSON files into SQLite. Idempotent."""
    stats: dict[str, int] = {}

    # Chunks
    if chunk_catalog_path and chunk_catalog_path.exists():
        rows = []
        with chunk_catalog_path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        rows.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
        if rows:
            # Also populate documents table
            doc_map: dict[str, dict] = {}
            for r in rows:
                did = r.get("doc_id", "")
                if did and did not in doc_map:
                    doc_map[did] = {
                        "doc_type": r.get("doc_type", ""),
                        "source_path": r.get("source_path"),
                        "source_hash": r.get("source_hash"),
                    }
            for did, info in doc_map.items():
                count = sum(1 for r in rows if r.get("doc_id") == did)
                upsert_document(did, info["doc_type"], info["source_path"], info["source_hash"], count)
            stats["chunks"] = insert_chunks(rows)
            stats["documents"] = len(doc_map)

    # Jobs
    if jobs_jsonl_path and jobs_jsonl_path.exists():
        count = 0
        with jobs_jsonl_path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    continue
                jid = row.get("job_id")
                if jid:
                    now = _utc_now()
                    execute(
                        """INSERT INTO jobs (job_id, status, files_detected, processed_files,
                           files_indexed, chunks_indexed, errors, timing_ms, error, error_code,
                           created_at, updated_at)
                           VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                        (
                            jid,
                            row.get("status", "unknown"),
                            row.get("files_detected", 0),
                            row.get("processed_files", 0),
                            row.get("files_indexed", 0),
                            row.get("chunks_indexed", 0),
                            _json_dumps(row.get("errors", [])),
                            _json_dumps(row.get("timing_ms", {})),
                            row.get("error"),
                            row.get("error_code"),
                            row.get("created_at", now),
                            row.get("updated_at", now),
                        ),
                    )
                    count += 1
        commit()
        stats["jobs"] = count

    # Audit events
    if events_jsonl_path and events_jsonl_path.exists():
        count = 0
        with events_jsonl_path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    continue
                execute(
                    "INSERT INTO audit_events (timestamp_utc, event_type, payload) VALUES (?,?,?)",
                    (
                        row.get("timestamp_utc", _utc_now()),
                        row.get("event_type", "unknown"),
                        _json_dumps(row),
                    ),
                )
                count += 1
        commit()
        stats["audit_events"] = count

    # Answers
    if answers_dir and answers_dir.exists():
        count = 0
        for path in sorted(answers_dir.glob("answer_*.json")):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                req_id = path.stem.replace("answer_", "")
                save_answer(req_id, data)
                count += 1
            except (json.JSONDecodeError, OSError):
                continue
        stats["answers"] = count

    # Query logs
    if logs_dir and logs_dir.exists():
        count = 0
        for path in sorted(logs_dir.glob("log_*.json")):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                req_id = data.get("request_id", path.stem.replace("log_", ""))
                save_query_log(req_id, data)
                count += 1
            except (json.JSONDecodeError, OSError):
                continue
        stats["query_logs"] = count

    return stats
