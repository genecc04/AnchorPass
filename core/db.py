from pathlib import Path

from .db_schema import init, get_connection, UNCATEGORIZED
from .db_paths import set_db_path, get_db_path, load_last_db, save_last_db
from .db_ops import (
    add_entry, update_entry, delete_entry, fetch_all, fetch_by_category,
    add_entry_full, update_entry_full, fetch_entry_dict,
    fetch_categories, add_category, rename_category, delete_category,
    get_setting, set_setting, category_exists,
)
from .db_search import search_entries
from .db_crypto import (
    encrypted_fields_present, decrypt_row_to_plain, encrypt_plain_to_row,
    normalize_enc_from_plain, rewrap_all_encrypted_fields, fetch_all_entries,
)

from .db_expiry import (
    set_expiry_date, change_status, restore_entry, permanently_delete_entry,
    check_and_expire_entries, fetch_by_status, fetch_expiring_soon,
    get_status_counts,
)

def __getattr__(name: str):
    if name == "DB_PATH":
        from . import db_paths
        return Path(db_paths.get_db_path() or "vault.db")
    raise AttributeError(name)