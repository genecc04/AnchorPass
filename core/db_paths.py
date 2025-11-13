from __future__ import annotations
from pathlib import Path
from typing import Optional
import os

from core.settings_manager import SettingsManager
def get_user_documents_dir() -> Path:
    home = Path(os.path.expanduser("~"))
    docs = Path(os.path.expanduser("~/Documents"))
    return docs if docs.exists() else home

APP_ROOT_DIR = get_user_documents_dir() / "securepasswordmanager"
DEFAULT_DB_DIR = APP_ROOT_DIR / "data"

def get_default_db_path() -> Path:
    DEFAULT_DB_DIR.mkdir(parents=True, exist_ok=True)
    return DEFAULT_DB_DIR / "vault.db"

_DB_PATH: Optional[Path] = None

def set_db_path(path: Path | str | None) -> None:
    global _DB_PATH
    if path:
        p = Path(path)
        _DB_PATH = p
        SettingsManager().set("database_path", str(p))
    else:
        _DB_PATH = None

def get_db_path() -> Optional[Path]:
    if _DB_PATH is not None:
        return _DB_PATH
    v = SettingsManager().get("database_path", "")
    return Path(v) if v else None

def load_last_db() -> Optional[Path]:
    v = SettingsManager().get("database_path", "")
    if not v:
        return None
    p = Path(v)
    return p if p.exists() else None

def save_last_db(path: Path | str) -> None:
    p = Path(path)
    SettingsManager().set("database_path", str(p))
    set_db_path(p)