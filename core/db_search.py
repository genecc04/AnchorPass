from __future__ import annotations
from .db_schema import get_connection, _get_passwords_columns

def search_entries(query: str):
    q = f"%{query}%"
    with get_connection() as conn:
        c = conn.cursor()
        cols = set(_get_passwords_columns())

        fields = ["site", "email", "username", "notes", "category"]

        if "tags" in cols:
            fields.append("tags")
        if "site_link" in cols:
            fields.append("site_link")

        where_clause = " OR ".join(f"{f} LIKE ?" for f in fields)

        sql = f"""
            SELECT id, site, email, username, password_enc, notes, category
            FROM passwords
            WHERE {where_clause}
            ORDER BY site COLLATE NOCASE;
        """

        params = tuple(q for _ in fields)
        c.execute(sql, params)
        return c.fetchall()
