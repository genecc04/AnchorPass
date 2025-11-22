from __future__ import annotations
from datetime import datetime
from core.settings_manager import SettingsManager

def _read_bool(s: SettingsManager, key: str, default=False) -> bool:
    try:
        return bool(s.get(key, default))
    except Exception:
        return default

def _read_str(s: SettingsManager, key: str, default="") -> str:
    v = s.get(key, default)
    return v if isinstance(v, str) else str(v)

def parse_time_maybe_12h(hhmm: str) -> tuple[int, int]:
    """Accept 'HH:mm' or 'h:mm AM/PM'. Returns (hour, minute) in 24h."""
    try:
        t = datetime.strptime((hhmm or "").strip(), "%H:%M")
        return t.hour, t.minute
    except Exception:
        pass
    try:
        t = datetime.strptime((hhmm or "").strip(), "%I:%M %p")
        return t.hour, t.minute
    except Exception:
        return 2, 0  # default 02:00

def scheduled_is_due_now(s: SettingsManager) -> bool:
    if _read_bool(s, "backup_disabled", False):
        return False
    enabled = _read_bool(s, "backup_sched_enabled", _read_bool(s, "enable_backup", False))
    if not enabled:
        return False

    interval = (_read_str(s, "backup_interval", "") or _read_str(s, "backup_schedule", "Daily")).strip().lower()
    hh, mm = parse_time_maybe_12h(_read_str(s, "backup_time", "02:00"))

    now = datetime.now()
    target = now.replace(hour=hh, minute=mm, second=0, microsecond=0)

    last_run_raw = _read_str(s, "backup_last_run", "")
    try:
        last_date = datetime.strptime(last_run_raw, "%Y-%m-%d").date()
    except Exception:
        last_date = None

    if interval == "daily":
        if last_date == now.date():
            return False
        return now >= target

    if interval == "weekly":
        if last_date and (now.date() - last_date).days < 7:
            return False
        return now >= target

    if interval == "monthly":
        if last_date and (now.date() - last_date).days < 28:
            return False
        return now >= target

    return False

def maybe_run_scheduled_backup(host_with_export_backup) -> bool:
    s = _resolve_settings_from_host(host_with_export_backup)

    if not scheduled_is_due_now(s):
        return False

    saved = None
    try:
        saved = host_with_export_backup.export_backup(reason="scheduled")
    except Exception:
        saved = None

    if saved:
        s.set("backup_last_run", datetime.now().strftime("%Y-%m-%d"))
        try:
            host_with_export_backup.statusBar().showMessage("Scheduled backup saved", 3000)
        except Exception:
            pass
        return True
    return False

def schedule_debug_snapshot() -> str:
    if s is None:
        s = SettingsManager()

    now = datetime.now()

    enabled = _read_bool(s, "backup_sched_enabled", _read_bool(s, "enable_backup", False))
    disabled_master = _read_bool(s, "backup_disabled", False)
    interval = _read_str(s, "backup_interval", _read_str(s, "backup_schedule", "Daily"))
    hhmm = _read_str(s, "backup_time", "02:00")
    hh, mm = parse_time_maybe_12h(hhmm)
    target = now.replace(hour=hh, minute=mm, second=0, microsecond=0)
    last = _read_str(s, "backup_last_run", "")
    bpath = (_read_str(s, "backup_path", "") or _read_str(s, "backup_dir", "")).strip()

    try:
        from core import db
        dbp = getattr(db, "get_db_path", lambda: None)() or getattr(db, "DB_PATH", "")
    except Exception:
        dbp = ""

    due = scheduled_is_due_now(s)

    parts = [
        f"Now:             {now:%Y-%m-%d %H:%M:%S}",
        f"Enabled:         {enabled}   (master 'Don't back up'={disabled_master})",
        f"Interval:        {interval}",
        f"Time setting:    {hhmm}  -> parsed {hh:02d}:{mm:02d}",
        f"Target today:    {target:%Y-%m-%d %H:%M:%S}  (due when now >= target)",
        f"Last run (date): {last or '<none>'}",
        f"Backup folder:   {bpath or '<not set>'}",
        f"DB path:         {dbp or '<unknown>'}",
        f"Would run now?:  {due}",
    ]
    return "\n".join(parts)

def _resolve_settings_from_host(host) -> SettingsManager:
    # If host has a helper, prefer that
    if hasattr(host, "_get_settings") and callable(getattr(host, "_get_settings")):
        try:
            sm = host._get_settings()
            if isinstance(sm, SettingsManager):
                return sm
        except Exception:
            pass

    # If host exposes .settings directly
    if hasattr(host, "settings") and isinstance(host.settings, SettingsManager):
        return host.settings

    # Fallback: global settings
    return SettingsManager()
