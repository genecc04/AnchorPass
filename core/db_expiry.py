from __future__ import annotations
from datetime import date, timedelta
from typing import List, Tuple
from .db_schema import get_connection, _now_iso
from .db_ops import fetch_entry_dict, add_entry_history_snapshot

def set_expiry_date(id_: int, expiry_date: str | None) -> None:
    """
    Args:
        id_: Entry ID
        expiry_date: ISO date string (YYYY-MM-DD) or None to clear
    """
    with get_connection() as conn:
        c = conn.cursor()
        c.execute(
            "UPDATE passwords SET expiry_date=?, date_modified=? WHERE id=?;",
            (expiry_date, _now_iso(), id_)
        )
        conn.commit()

def change_status(id_: int, new_status: str) -> None:
    """
    Args:
        id_: Entry ID
        new_status: One of 'active', 'expired', 'archived', 'deleted'
    """
    valid_statuses = ['active', 'expired', 'archived', 'deleted']
    if new_status not in valid_statuses:
        raise ValueError(f"Invalid status: {new_status}. Must be one of {valid_statuses}")
    
    original_entry = fetch_entry_dict(id_)
    if not original_entry:
        raise ValueError(f"Entry with id {id_} not found")

    summary = f"Changed status to {new_status}"

    try:
        add_entry_history_snapshot(id_, original_entry, summary)
    except Exception as e:
        print(f"Error while adding history snapshot: {e}")
    
    with get_connection() as conn:
        c = conn.cursor()
        now = _now_iso()
        
        if new_status == 'expired':
            c.execute(
                "UPDATE passwords SET status=?, expired_at=?, date_modified=? WHERE id=?;",
                (new_status, now, now, id_)
            )
        elif new_status == 'archived':
            c.execute(
                "UPDATE passwords SET status=?, archived_at=?, date_modified=? WHERE id=?;",
                (new_status, now, now, id_)
            )
        elif new_status == 'deleted':
            c.execute(
                "UPDATE passwords SET status=?, deleted_at=?, date_modified=? WHERE id=?;",
                (new_status, now, now, id_)
            )
        else:
            c.execute(
                """UPDATE passwords 
                   SET status=?, expired_at=NULL, archived_at=NULL, deleted_at=NULL, date_modified=? 
                   WHERE id=?;""",
                (new_status, now, id_)
            )
        
        conn.commit()

def restore_entry(id_: int) -> None:
    change_status(id_, 'active')

def permanently_delete_entry(id_: int) -> None:
    with get_connection() as conn:
        c = conn.cursor()
        c.execute("DELETE FROM passwords WHERE id=?;", (id_,))
        conn.commit()

def check_and_expire_entries() -> List[int]:
    today = date.today().isoformat()
    expired_ids = []
    
    with get_connection() as conn:
        c = conn.cursor()
        c.execute(
            """SELECT id FROM passwords 
               WHERE status='active' 
               AND expiry_date IS NOT NULL 
               AND expiry_date <= ?;""",
            (today,)
        )
        
        entries = c.fetchall()
        now = _now_iso()
        
        for (id_,) in entries:
            c.execute(
                "UPDATE passwords SET status='expired', expired_at=?, date_modified=? WHERE id=?;",
                (now, now, id_)
            )
            expired_ids.append(id_)
        
        conn.commit()
    
    return expired_ids

def get_entries_expiring_soon(days: int = 5) -> List[int]:
    today = date.today()
    upper = today + timedelta(days=days)

    today_iso = today.isoformat()
    upper_iso = upper.isoformat()

    with get_connection() as conn:
        c = conn.cursor()
        c.execute(
            """
            SELECT id FROM passwords
            WHERE status='active'
              AND expiry_date IS NOT NULL
              AND expiry_date > ?   -- strictly after today (not yet expired)
              AND expiry_date <= ?; -- within N days
            """,
            (today_iso, upper_iso)
        )
        rows = c.fetchall()

    return [id_ for (id_,) in rows]

def fetch_by_status(status: str) -> List[Tuple]:
    """
    Args:
        status: One of 'active', 'expired', 'archived', 'deleted'
    
    Returns:
        List of tuples: (id, site, email, username, password_enc, notes, category, status, expiry_date)
    """
    with get_connection() as conn:
        c = conn.cursor()
        c.execute(
            """SELECT id, site, email, username, password_enc, notes, category, status, expiry_date
               FROM passwords
               WHERE status=?
               ORDER BY category, site COLLATE NOCASE;""",
            (status,)
        )
        return c.fetchall()

def fetch_expiring_soon(days: int = 7) -> List[Tuple]:
    """
    Args:
        days: Number of days to look ahead (default: 7)
    
    Returns:
        List of tuples: (id, site, email, username, category, expiry_date, days_until_expiry)
    """
    today = date.today()
    future_date = (today + timedelta(days=days)).isoformat()
    
    with get_connection() as conn:
        c = conn.cursor()
        c.execute(
            """SELECT id, site, email, username, category, expiry_date,
                      CAST(julianday(expiry_date) - julianday('now') AS INTEGER) as days_until_expiry
               FROM passwords
               WHERE status='active' 
               AND expiry_date IS NOT NULL
               AND expiry_date > ?
               AND expiry_date <= ?
               ORDER BY expiry_date ASC;""",
            (today.isoformat(), future_date)
        )
        return c.fetchall()

def get_status_counts() -> dict:
    with get_connection() as conn:
        c = conn.cursor()
        c.execute(
            """SELECT status, COUNT(*) as count 
               FROM passwords 
               GROUP BY status;"""
        )
        results = c.fetchall()
        return {row[0] or 'active': row[1] for row in results}