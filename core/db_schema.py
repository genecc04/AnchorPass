from __future__ import annotations
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import List
from . import db_paths

UNCATEGORIZED = "Uncategorized"

_PASSWORDS_COLS: List[str] | None = None

def get_connection() -> sqlite3.Connection:
    db_path = Path(db_paths.get_db_path() or "vault.db")
    try:
        db_path.parent.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def _get_passwords_columns() -> list[str]:
    global _PASSWORDS_COLS
    if _PASSWORDS_COLS is not None:
        return _PASSWORDS_COLS
    with get_connection() as conn:
        c = conn.cursor()
        c.execute("PRAGMA table_info(passwords);")
        _PASSWORDS_COLS = [r[1] for r in c.fetchall()]
    return _PASSWORDS_COLS

def _bust_columns_cache() -> None:
    global _PASSWORDS_COLS
    _PASSWORDS_COLS = None

def _ensure_passwords_columns() -> None:
    want = [
        ("email_enc", "TEXT"),
        ("pin_enc", "TEXT"),
        ("security_code_enc", "TEXT"),
        ("app_password_enc", "TEXT"),
        ("otp_secret_enc", "TEXT"),
        ("recovery_email", "TEXT"),
        ("recovery_phone", "TEXT"),
        ("security_questions", "TEXT"),
        ("recovery_email_enc", "TEXT"),
        ("recovery_phone_enc", "TEXT"),
        ("security_questions_enc", "TEXT"),
        ("tags", "TEXT"),
        ("favorite", "INTEGER DEFAULT 0"),
        ("date_created", "TEXT"),
        ("date_modified", "TEXT"),
        ("site_link", "TEXT"),
        ("expiry_date", "TEXT"),
        ("status", "TEXT DEFAULT 'active'"),
        ("expired_at", "TEXT"),
        ("archived_at", "TEXT"),
        ("deleted_at", "TEXT"),
    ]
    with get_connection() as conn:
        c = conn.cursor()
        c.execute("PRAGMA table_info(passwords);")
        have = {r[1] for r in c.fetchall()}
        for col, coltype in want:
            if col not in have:
                c.execute(f"ALTER TABLE passwords ADD COLUMN {col} {coltype};")
        conn.commit()
        
        c.execute("""
            CREATE INDEX IF NOT EXISTS idx_status ON passwords(status);
        """)
        c.execute("""
            CREATE INDEX IF NOT EXISTS idx_expiry_status ON passwords(expiry_date, status);
        """)
        c.execute("""
            CREATE INDEX IF NOT EXISTS idx_deleted_at ON passwords(deleted_at);
        """)
        conn.commit()
    _bust_columns_cache()

def init() -> None:
    with get_connection() as conn:
        c = conn.cursor()
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS passwords (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                site TEXT,
                email TEXT,
                username TEXT,
                password_enc TEXT,
                notes TEXT,
                category TEXT DEFAULT ''
            );
            """
        )
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            );
            """
        )
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS categories (
                name TEXT PRIMARY KEY
            );
            """
        )
        c.execute("INSERT OR IGNORE INTO categories (name) VALUES (?);", (UNCATEGORIZED,))
        conn.commit()
    _ensure_passwords_columns()

def _ensure_category_chain(c, path: str) -> None:
    if not path:
        return
    parts = [p for p in path.split("/") if p]
    prefix = ""
    for part in parts:
        prefix = part if not prefix else f"{prefix}/{part}"
        c.execute("INSERT OR IGNORE INTO categories (name) VALUES (?);", (prefix,))

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()