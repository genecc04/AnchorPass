from __future__ import annotations
from .db_schema import get_connection, _get_passwords_columns
from typing import Iterable

def search_entries( query: str, *, exclude_fields: Iterable[str] | None = None, status: str | None = None, category: str | None = None, ):

    q = f"%{query}%"
    ex = set(exclude_fields or ())

    with get_connection() as conn:
        c = conn.cursor()
        cols = set(_get_passwords_columns())

        fields = ["site", "email", "username", "notes", "category"]

        if "tags" in cols:
            fields.append("tags")
        if "site_link" in cols:
            fields.append("site_link")

        fields = [f for f in fields if f not in ex]

        if not fields:
            return []

        like_clause = " OR ".join(f"{f} LIKE ?" for f in fields)

        where_parts = [f"({like_clause})"]
        params: list[object] = [q for _ in fields]

        if status:
            where_parts.append("status = ?")
            params.append(status)

        if category:
            where_parts.append("category = ?")
            params.append(category)

        where_sql = " AND ".join(where_parts)

        sql = f"""
            SELECT id, site, email, username, password_enc, notes, category
            FROM passwords
            WHERE {where_sql}
            ORDER BY site COLLATE NOCASE;
        """

        c.execute(sql, tuple(params))
        return c.fetchall()