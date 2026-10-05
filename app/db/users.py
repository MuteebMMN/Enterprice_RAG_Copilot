"""Login accounts. Separate from the HR data: this DB holds password hashes and roles."""
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from pydantic import BaseModel
from app.core.config import get_settings

ROLES = ("employee", "hr", "admin")
MAX_FAILED_ATTEMPTS = 5
LOCKOUT_MINUTES = 15


class User(BaseModel):
    id: int
    email: str
    role: str
    employee_id: str
    active: bool
    password_hash: str
    failed_attempts: int = 0
    locked_until: str | None = None


def _connect() -> sqlite3.Connection:
    con = sqlite3.connect(get_settings().app_db_path)
    con.row_factory = sqlite3.Row
    return con


def init_users_db() -> None:
    Path(get_settings().app_db_path).parent.mkdir(parents=True, exist_ok=True)
    con = _connect()
    con.execute(
        """CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL CHECK (role IN ('employee','hr','admin')),
            employee_id TEXT NOT NULL UNIQUE,
            active INTEGER NOT NULL DEFAULT 1,
            failed_attempts INTEGER NOT NULL DEFAULT 0,
            locked_until TEXT,
            created_at TEXT NOT NULL
        )"""
    )
    con.commit()
    con.close()


def _row_to_user(row: sqlite3.Row | None) -> User | None:
    if row is None:
        return None
    data = dict(row)
    data["active"] = bool(data["active"])
    data.pop("created_at", None)
    return User(**data)


def create_user(email: str, password_hash: str, role: str, employee_id: str) -> User:
    if role not in ROLES:
        raise ValueError(f"Invalid role '{role}'")
    con = _connect()
    try:
        cur = con.execute(
            "INSERT INTO users (email, password_hash, role, employee_id, created_at) VALUES (?,?,?,?,?)",
            (email.strip().lower(), password_hash, role, employee_id, datetime.now(timezone.utc).isoformat()),
        )
        con.commit()
        return get_user_by_id(cur.lastrowid)
    finally:
        con.close()


def get_user_by_email(email: str) -> User | None:
    con = _connect()
    try:
        return _row_to_user(con.execute("SELECT * FROM users WHERE email = ?", (email.strip().lower(),)).fetchone())
    finally:
        con.close()


def get_user_by_id(user_id: int) -> User | None:
    con = _connect()
    try:
        return _row_to_user(con.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone())
    finally:
        con.close()


def list_users() -> list[User]:
    con = _connect()
    try:
        return [_row_to_user(r) for r in con.execute("SELECT * FROM users ORDER BY id").fetchall()]
    finally:
        con.close()


def set_password_hash(user_id: int, password_hash: str) -> None:
    con = _connect()
    con.execute(
        "UPDATE users SET password_hash = ?, failed_attempts = 0, locked_until = NULL WHERE id = ?",
        (password_hash, user_id),
    )
    con.commit()
    con.close()


def set_active(user_id: int, active: bool) -> None:
    con = _connect()
    con.execute("UPDATE users SET active = ? WHERE id = ?", (int(active), user_id))
    con.commit()
    con.close()


def is_locked(user: User) -> bool:
    if not user.locked_until:
        return False
    return datetime.fromisoformat(user.locked_until) > datetime.now(timezone.utc)


def register_failed_login(user_id: int) -> None:
    """Count a failed attempt; lock the account after MAX_FAILED_ATTEMPTS."""
    con = _connect()
    con.execute("UPDATE users SET failed_attempts = failed_attempts + 1 WHERE id = ?", (user_id,))
    attempts = con.execute("SELECT failed_attempts FROM users WHERE id = ?", (user_id,)).fetchone()[0]
    if attempts >= MAX_FAILED_ATTEMPTS:
        until = (datetime.now(timezone.utc) + timedelta(minutes=LOCKOUT_MINUTES)).isoformat()
        con.execute("UPDATE users SET locked_until = ?, failed_attempts = 0 WHERE id = ?", (until, user_id))
    con.commit()
    con.close()


def register_successful_login(user_id: int) -> None:
    con = _connect()
    con.execute("UPDATE users SET failed_attempts = 0, locked_until = NULL WHERE id = ?", (user_id,))
    con.commit()
    con.close()
