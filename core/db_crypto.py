from __future__ import annotations
import sqlite3
from typing import Dict
from core import crypto
from .db_schema import get_connection, _get_passwords_columns, _now_iso

_ENC_MAP = {
    "email": "email_enc",
    "pin": "pin_enc",
    "security_code": "security_code_enc",
    "app_password": "app_password_enc",
    "otp_secret": "otp_secret_enc",
    "recovery_email": "recovery_email_enc",
    "recovery_phone": "recovery_phone_enc",
    "security_questions": "security_questions_enc",
    "password": "password_enc",
}

def encrypted_fields_present() -> Dict[str, str]:
    cols = set(_get_passwords_columns())
    present = {}
    for plain, enc in _ENC_MAP.items():
        if enc in cols:
            present[plain] = enc
    return present

def _try_dec_multi(cipher, value: str, extra_ciphers=None) -> str:
    if not value:
        return ""
    if isinstance(value, bytes):
        try:
            value = value.decode()
        except Exception:
            return ""

    pt = crypto.decrypt_text(cipher, value)
    if pt != "[Decryption failed]":
        return pt

    for c in (extra_ciphers or []):
        pt = crypto.decrypt_text(c, value)
        if pt != "[Decryption failed]":
            return pt
    return ""

def decrypt_row_to_plain(row: dict, cipher, extra_ciphers=None) -> dict:
    if not isinstance(row, dict):
        row = dict(row)
    out = dict(row)
    present = encrypted_fields_present()
    for plain, enc in present.items():
        enc_val = row.get(enc, "") or ""
        if enc_val:
            dec = _try_dec_multi(cipher, enc_val, extra_ciphers=extra_ciphers)
            out[plain] = dec or (row.get(plain, "") or "")
        else:
            out[plain] = row.get(plain, "") or ""
    if "password" not in out:
        out["password"] = row.get("password", "") or ""
    return out

def encrypt_plain_to_row( plain: dict, cipher, base_row: dict | None = None, 
                         mirror_plaintext: bool = True, preserve_existing_cipher_on_empty: bool = False, ) -> dict:

    row = dict(base_row or {})
    present = encrypted_fields_present()

    if "id" in plain:
        row["id"] = plain["id"]

    for k in ("site", "site_link", "username", "notes", "category",
              "date_created", "date_modified", "tags", "favorite"):
        if k in plain:
            row[k] = plain[k]

    cols = set(_get_passwords_columns())

    for p, enc in present.items():
        user_supplied = (p in plain)
        value = plain.get(p, "")
        value = "" if value is None else value

        if user_supplied and value == "":
            row[enc] = ""
        else:
            if value == "" and preserve_existing_cipher_on_empty and base_row and base_row.get(enc):
                row[enc] = base_row.get(enc)
            else:
                row[enc] = crypto.encrypt_text(cipher, value) if value else ""

        if mirror_plaintext and user_supplied:
            row[p] = value

    if "password" in plain and "password_enc" in cols:
        pw = plain.get("password", "") or ""
        if pw == "":
            row["password_enc"] = ""
        else:
            if pw == "" and preserve_existing_cipher_on_empty and base_row and base_row.get("password_enc"):
                row["password_enc"] = base_row.get("password_enc")
            else:
                row["password_enc"] = crypto.encrypt_text(cipher, pw) if pw else ""

    if not row.get("category"):
        row["category"] = "Uncategorized"

    if "date_modified" in cols:
        row["date_modified"] = _now_iso()
    if "date_created" in cols and not row.get("date_created"):
        row["date_created"] = _now_iso()

    return row

def normalize_enc_from_plain(new_cipher) -> int:
    present = encrypted_fields_present()
    if not present:
        return 0

    enc_cols = list(set(present.values()))
    plain_to_enc = {p: enc for p, enc in present.items() if p != "password"}

    written = 0

    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        c = conn.cursor()

        select_cols = ["id"] + enc_cols + list(plain_to_enc.keys())
        select_cols = ["id"] + [col for col in enc_cols if col != "id"] + [col for col in plain_to_enc.keys() if col != "id"]

        c.execute(f"SELECT {','.join(select_cols)} FROM passwords;")
        rows = c.fetchall()

        for row in rows:
            rid = row["id"]
            updates = {}

            for plain, enc in plain_to_enc.items():
                enc_val = row[enc]
                plain_val = row[plain] if plain in row.keys() else ""
                if (enc_val is None or enc_val == "") and (plain_val not in (None, "")):
                    updates[enc] = crypto.encrypt_text(new_cipher, plain_val)
            if updates:
                sets = ",".join(f"{k}=?" for k in updates.keys())
                vals = list(updates.values()) + [rid]
                c.execute(f"UPDATE passwords SET {sets} WHERE id=?;", vals)
                written += len(updates)

        cols = set(_get_passwords_columns())
        if written > 0 and "date_modified" in cols:
            c.execute("UPDATE passwords SET date_modified=? WHERE id IN (SELECT id FROM passwords);", (_now_iso(),))

        conn.commit()

    return written

def rewrap_all_encrypted_fields(old_cipher, new_cipher, extra_ciphers=None) -> dict:
    present = encrypted_fields_present()
    enc_cols = list(set(present.values()))
    stats = {"rows": 0, "updated_cells": 0, "left_unchanged": 0}

    if not enc_cols:
        return stats

    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        select_cols = ["id"] + enc_cols
        c.execute(f"SELECT {','.join(select_cols)} FROM passwords;")
        rows = c.fetchall()
        stats["rows"] = len(rows)

        updated_any = False

        for row in rows:
            rid = row["id"]
            updates = {}
            for enc in enc_cols:
                ct = row[enc]
                if not ct:
                    continue

                pt = _try_dec_multi(old_cipher, ct, extra_ciphers=extra_ciphers)
                if pt == "":
                    stats["left_unchanged"] += 1
                    continue

                new_ct = crypto.encrypt_text(new_cipher, pt) if pt else ""
                if new_ct and new_ct != ct:
                    updates[enc] = new_ct

            if updates:
                sets = ",".join(f"{k}=?" for k in updates.keys())
                vals = list(updates.values()) + [rid]
                c.execute(f"UPDATE passwords SET {sets} WHERE id=?;", vals)
                stats["updated_cells"] += len(updates)
                updated_any = True

        cols = set(_get_passwords_columns())
        if updated_any and "date_modified" in cols:
            c.execute("UPDATE passwords SET date_modified=? WHERE id IN (SELECT id FROM passwords);", (_now_iso(),))

        conn.commit()

    return stats

def fetch_all_entries() -> list[dict]:
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute("SELECT * FROM passwords;")
        return [dict(r) for r in c.fetchall()]
