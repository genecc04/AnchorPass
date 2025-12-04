from __future__ import annotations
import sqlite3
from typing import Any, Dict
from .db_schema import (
    get_connection, _get_passwords_columns, _ensure_category_chain,
    UNCATEGORIZED, _now_iso
)

def add_entry(site=None, email=None, username=None, password_enc=None, notes=None, category="", **kwargs):
    if kwargs:
        data = {
            "site": site or "",
            "email": email or "",
            "username": username or "",
            "password_enc": password_enc or "",
            "notes": notes or "",
            "category": category or "",
            **kwargs,
        }
        return add_entry_full(data)

    if not category:
        category = UNCATEGORIZED
    with get_connection() as conn:
        c = conn.cursor()
        _ensure_category_chain(c, category)
        cols = _get_passwords_columns()

        base_sql = """
            INSERT INTO passwords (site, email, username, password_enc, notes, category{extra_cols})
            VALUES (?, ?, ?, ?, ?, ?{extra_q});
        """
        extra_names, extra_vals = [], []
        if "date_created" in cols:
            extra_names.append("date_created")
            extra_vals.append(_now_iso())
        if "date_modified" in cols:
            extra_names.append("date_modified")
            extra_vals.append(_now_iso())
        if "status" in cols:
            extra_names.append("status")
            extra_vals.append('active')
            
        extra_cols = ("," + ",".join(extra_names)) if extra_names else ""
        extra_q = ("," + ",".join("?" for _ in extra_names)) if extra_names else ""

        c.execute(
            base_sql.format(extra_cols=extra_cols, extra_q=extra_q),
            (site or "", email or "", username or "", password_enc or "", notes or "", category, *extra_vals),
        )
        conn.commit()
        return c.lastrowid

def update_entry(id_, site=None, email=None, username=None, password_enc=None, notes=None, category="", **kwargs):
    if kwargs:
        data = {}
        if site is not None: data["site"] = site
        if email is not None: data["email"] = email
        if username is not None: data["username"] = username
        if password_enc is not None: data["password_enc"] = password_enc
        if notes is not None: data["notes"] = notes
        if category is not None: data["category"] = category or UNCATEGORIZED
        data.update(kwargs)
        return update_entry_full(id_, data)

    if not category:
        category = UNCATEGORIZED
    with get_connection() as conn:
        c = conn.cursor()
        _ensure_category_chain(c, category)
        cols = _get_passwords_columns()
        if "date_modified" in cols:
            c.execute(
                """
                UPDATE passwords
                SET site=?, email=?, username=?, password_enc=?, notes=?, category=?, date_modified=?
                WHERE id=?;
                """,
                (
                    site or "", email or "", username or "", password_enc or "",
                    notes or "", category, _now_iso(), id_,
                ),
            )
        else:
            c.execute(
                """
                UPDATE passwords
                SET site=?, email=?, username=?, password_enc=?, notes=?, category=?
                WHERE id=?;
                """,
                (site or "", email or "", username or "", password_enc or "", notes or "", category, id_),
            )
        conn.commit()

def delete_entry(id_):
    with get_connection() as conn:
        c = conn.cursor()
        cols = _get_passwords_columns()
        
        if "status" in cols and "deleted_at" in cols:
            c.execute(
                "UPDATE passwords SET status='deleted', deleted_at=?, date_modified=? WHERE id=?;",
                (_now_iso(), _now_iso(), id_)
            )
        else:
            c.execute("DELETE FROM passwords WHERE id=?;", (id_,))
        
        conn.commit()

def fetch_all(include_deleted=False):
    with get_connection() as conn:
        c = conn.cursor()
        
        if include_deleted:
            c.execute(
                """
                SELECT id, site, email, username, password_enc, notes, category
                FROM passwords
                ORDER BY category, site COLLATE NOCASE;
                """
            )
        else:
            c.execute(
                """
                SELECT id, site, email, username, password_enc, notes, category
                FROM passwords
                WHERE status IS NULL OR status != 'deleted'
                ORDER BY category, site COLLATE NOCASE;
                """
            )
        return c.fetchall()

def fetch_by_category(category=None, include_descendants=False, include_deleted=False):
    with get_connection() as conn:
        c = conn.cursor()
        
        deleted_filter = "" if include_deleted else "AND (status IS NULL OR status != 'deleted')"
        
        if not category or category == UNCATEGORIZED:
            c.execute(
                f"""
                SELECT id, site, email, username, password_enc, notes, category
                FROM passwords
                WHERE (category IS NULL OR category='' OR category=?)
                {deleted_filter}
                ORDER BY site COLLATE NOCASE;
                """,
                (UNCATEGORIZED,),
            )
        else:
            if include_descendants:
                c.execute(
                    f"""
                    SELECT id, site, email, username, password_enc, notes, category
                    FROM passwords
                    WHERE (category=? OR category LIKE ?)
                    {deleted_filter}
                    ORDER BY site COLLATE NOCASE;
                    """,
                    (category, f"{category}/%",),
                )
            else:
                c.execute(
                    f"""
                    SELECT id, site, email, username, password_enc, notes, category
                    FROM passwords
                    WHERE category=?
                    {deleted_filter}
                    ORDER BY site COLLATE NOCASE;
                    """,
                    (category,),
                )
        return c.fetchall()

def add_entry_full(data: Dict[str, Any]) -> int:
    cols = _get_passwords_columns()
    d = dict(data)
    if not d.get("category"):
        d["category"] = UNCATEGORIZED

    if "date_created" in cols and not d.get("date_created"):
        d["date_created"] = _now_iso()
    if "date_modified" in cols and not d.get("date_modified"):
        d["date_modified"] = _now_iso()
    if "status" in cols and not d.get("status"):
        d["status"] = 'active'

    use_cols = [k for k in d.keys() if k in cols and k != "id"]
    if not use_cols:
        return add_entry(
            d.get("site", ""), d.get("email", ""), d.get("username", ""),
            d.get("password_enc", ""), d.get("notes", ""), d.get("category", UNCATEGORIZED),
        )

    with get_connection() as conn:
        c = conn.cursor()
        _ensure_category_chain(c, d.get("category", UNCATEGORIZED))
        placeholders = ",".join("?" for _ in use_cols)
        sql = f"INSERT INTO passwords ({','.join(use_cols)}) VALUES ({placeholders});"
        c.execute(sql, tuple(d[k] for k in use_cols))
        conn.commit()
        return c.lastrowid

def update_entry_full(id_: int, data: Dict[str, Any]) -> None:
    cols = _get_passwords_columns()
    d = {k: v for k, v in data.items() if k in cols and k != "id"}
    if not d:
        return
    if "date_modified" in cols and "date_modified" not in d:
        d["date_modified"] = _now_iso()
    sets = ",".join(f"{k}=?" for k in d.keys())
    with get_connection() as conn:
        c = conn.cursor()
        if "category" in d:
            _ensure_category_chain(c, d["category"])
        c.execute(f"UPDATE passwords SET {sets} WHERE id=?;", (*d.values(), id_))
        conn.commit()

def fetch_entry_dict(id_: int) -> dict | None:
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute("SELECT * FROM passwords WHERE id=?;", (id_,))
        row = c.fetchone()
        if not row:
            return None
        return {k: row[k] for k in row.keys()}

def fetch_categories() -> list[str]:
    with get_connection() as conn:
        c = conn.cursor()
        c.execute("SELECT name FROM categories;")
        reg = {r[0] for r in c.fetchall() if r and r[0]}
        c.execute("SELECT DISTINCT category FROM passwords WHERE category IS NOT NULL AND category<>'';")
        from_entries = {r[0] for r in c.fetchall() if r and r[0]}
        cats = reg | from_entries
        cats.add(UNCATEGORIZED)

        def sort_key(p: str):
            return (p == UNCATEGORIZED, p.count("/"), p.lower())

        return sorted(cats, key=sort_key)

def add_category(path: str) -> None:
    if not path or path == "/":
        return
    with get_connection() as conn:
        c = conn.cursor()
        _ensure_category_chain(c, path)
        conn.commit()

def rename_category(old_path: str, new_path: str) -> None:
    if not old_path or not new_path or old_path == new_path or old_path == UNCATEGORIZED:
        return
    with get_connection() as conn:
        c = conn.cursor()
        conn.execute("BEGIN IMMEDIATE;")
        conflict = c.execute(
            "SELECT 1 FROM categories WHERE name=? OR name LIKE ?;",
            (new_path, f"{new_path}/%",),
        ).fetchone()
        if conflict:
            conn.rollback()
            raise ValueError(f"A folder named '{new_path}' already exists.")

        rows = c.execute(
            "SELECT name FROM categories WHERE name=? OR name LIKE ?;",
            (old_path, f"{old_path}/%",),
        ).fetchall()
        old_paths = [r[0] for r in rows]
        old_paths.sort(key=len, reverse=True)
        renames = [(op, op.replace(old_path, new_path, 1)) for op in old_paths]

        _ensure_category_chain(c, new_path)

        for old_name, new_name in renames:
            c.execute("DELETE FROM categories WHERE name=?;", (new_name,))
            c.execute("UPDATE categories SET name=? WHERE name=?;", (new_name, old_name,))

        c.execute(
            """
            UPDATE passwords
            SET category = REPLACE(category, ?, ?)
            WHERE category=? OR category LIKE ?;
            """,
            (old_path, new_path, old_path, f"{old_path}/%",),
        )
        conn.commit()

def delete_category(path: str) -> None:
    if not path or path == UNCATEGORIZED:
        return
    with get_connection() as conn:
        c = conn.cursor()
        c.execute(
            """
            UPDATE passwords
            SET category=?
            WHERE category=? OR category LIKE ?;
            """,
            (UNCATEGORIZED, path, f"{path}/%",),
        )
        c.execute("DELETE FROM categories WHERE name=? OR name LIKE ?;", (path, f"{path}/%",))
        conn.commit()

def get_setting(key: str) -> str | None:
    with get_connection() as conn:
        c = conn.cursor()
        c.execute("SELECT value FROM settings WHERE key=?;", (key,))
        row = c.fetchone()
        return row[0] if row else None

def set_setting(key: str, value: str) -> None:
    with get_connection() as conn:
        c = conn.cursor()
        c.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?);", (key, value))
        conn.commit()

def category_exists(name: str) -> bool:
    if not name:
        return False
    
    norm = "/".join([p for p in str(name).split("/") if p])
    with get_connection() as conn:
        c = conn.cursor()
        c.execute("SELECT 1 FROM categories WHERE name = ? LIMIT 1;", (norm,))
        return c.fetchone() is not None
    
def duplicate_entry(id_: int) -> int:
    original = fetch_entry_dict(id_)
    if not original:
        raise ValueError(f"Entry {id_} not found")

    d = dict(original)
    d.pop("id", None)
    d.pop("date_created", None)
    d.pop("date_modified", None)
    d.pop("deleted_at", None)

    d["status"] = "active"
    if d.get("site"):
        d["site"] = f"{d['site']} (copy)"

    new_id = add_entry_full(d)
    return new_id