import json
import sqlite3
from datetime import datetime, timezone
from app.core.config import get_settings

settings = get_settings()

# Columns added after the first version of the table; added in place for existing databases.
_NEW_COLUMNS = {
    "user_id": "INTEGER",
    "email": "TEXT",
    "role": "TEXT",
    "guardrail_result": "TEXT NOT NULL DEFAULT 'allow'",
    "blocked_reason": "TEXT",
}


def init_db() -> None:
    con = sqlite3.connect(settings.audit_db_path)
    con.execute(
        """CREATE TABLE IF NOT EXISTS query_audit (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL,
            question TEXT NOT NULL,
            source_used TEXT NOT NULL,
            trace_json TEXT NOT NULL
        )"""
    )
    existing = {row[1] for row in con.execute("PRAGMA table_info(query_audit)")}
    for name, definition in _NEW_COLUMNS.items():
        if name not in existing:
            con.execute(f"ALTER TABLE query_audit ADD COLUMN {name} {definition}")
    con.commit()
    con.close()


def write_audit(question: str, source_used: str, trace: list[str], user=None, guardrail: dict | None = None) -> None:
    """Record one chat request: who asked, what happened, and whether a guardrail blocked it."""
    blocked = bool(guardrail) and guardrail.get("action") == "block"
    con = sqlite3.connect(settings.audit_db_path)
    con.execute(
        "INSERT INTO query_audit(created_at, question, source_used, trace_json, user_id, email, role,"
        " guardrail_result, blocked_reason) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            datetime.now(timezone.utc).isoformat(),
            question,
            source_used,
            json.dumps(trace),
            getattr(user, "id", None),
            getattr(user, "email", None),
            getattr(user, "role", None),
            "block" if blocked else "allow",
            guardrail.get("reason") if blocked else None,
        ),
    )
    con.commit()
    con.close()


def list_audit(limit: int = 100, blocked_only: bool = False) -> list[dict]:
    con = sqlite3.connect(settings.audit_db_path)
    con.row_factory = sqlite3.Row
    sql = (
        "SELECT id, created_at, user_id, email, role, question, source_used, guardrail_result,"
        " blocked_reason, trace_json FROM query_audit"
    )
    if blocked_only:
        sql += " WHERE guardrail_result = 'block'"
    rows = con.execute(sql + " ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    con.close()
    out = []
    for r in rows:
        d = dict(r)
        d["trace"] = json.loads(d.pop("trace_json"))
        out.append(d)
    return out
