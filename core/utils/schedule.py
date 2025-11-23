from __future__ import annotations
import re

def parse_backup_time(s: str) -> tuple[int, int]:
    """Accepts 'HH:mm' or 'h:mm AM/PM'. Returns (hour_24, minute)."""
    s = (s or "").strip()

    m = re.fullmatch(r"\s*(\d{1,2}):(\d{2})\s*", s)
    if m:
        hh, mm = int(m.group(1)), int(m.group(2))
        if 0 <= hh <= 23 and 0 <= mm <= 59:
            return hh, mm

    m = re.fullmatch(r"\s*(\d{1,2}):(\d{2})\s*([AaPp][Mm])\s*", s)
    if m:
        hh, mm = int(m.group(1)), int(m.group(2))
        ap = m.group(3).upper()
        if 1 <= hh <= 12 and 0 <= mm <= 59:
            return ((0 if hh == 12 else hh), mm) if ap == "AM" else ((12 if hh == 12 else hh + 12), mm)

    return 2, 0  # default

def scheduled_backup_is_configured(settings) -> tuple[bool, str | None, str]:
    """
    Returns (ok, msg, interval_str) respecting both new and legacy keys.
    `settings` must expose .get(key, default=None).
    """
    if bool(settings.get("backup_disabled", False)):
        return False, "Scheduled backup skipped: 'Don't back up' is enabled.", ""

    sched_enabled = bool(settings.get("backup_sched_enabled", False)) \
                    or bool(settings.get("enable_backup", False))
    if not sched_enabled:
        return False, "Scheduled backup skipped: scheduler disabled.", ""

    interval = (settings.get("backup_interval", "") or "").strip() \
               or (settings.get("backup_schedule", "") or "").strip() or "Daily"
    if interval.lower() == "manual":
        return False, "Scheduled backup skipped: schedule is set to Manual.", "Manual"

    folder = (settings.get("backup_path", "") or "").strip() \
             or (settings.get("backup_dir", "") or "").strip()
    if not folder:
        return False, "Scheduled backup skipped: no backup folder set.", interval

    return True, None, interval
