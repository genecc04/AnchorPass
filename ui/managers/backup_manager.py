from __future__ import annotations
import re
from datetime import datetime, date
from calendar import monthrange
from typing import Tuple, Optional

class BackupManager:
    
    def __init__(self, settings_manager):
        self.settings = settings_manager
    
    def parse_backup_time(self, time_str: str) -> Tuple[int, int]:
        s = (time_str or "").strip()

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
                if ap == "AM":
                    return (0 if hh == 12 else hh), mm
                else:
                    return (12 if hh == 12 else hh + 12), mm

        return 2, 0

    def is_backup_configured(self) -> Tuple[bool, Optional[str], str]:
        if bool(self.settings.get("backup_disabled", False)):
            return False, "Scheduled backup skipped: 'Don't back up' is enabled.", ""

        sched_enabled = bool(self.settings.get("backup_sched_enabled", False)) or \
                       bool(self.settings.get("enable_backup", False))
        if not sched_enabled:
            return False, "Scheduled backup skipped: scheduler disabled.", ""

        interval = (self.settings.get("backup_interval", "") or "").strip() or \
                   (self.settings.get("backup_schedule", "") or "").strip() or "Daily"
        if interval.lower() == "manual":
            return False, "Scheduled backup skipped: schedule is set to Manual.", "Manual"

        folder = (self.settings.get("backup_path", "") or "").strip() or \
                (self.settings.get("backup_dir", "") or "").strip()
        if not folder:
            return False, "Scheduled backup skipped: no backup folder set.", interval

        return True, None, interval

    def should_run_backup(self, interval: str, last_run: Optional[str]) -> bool:
        today = date.today()
        last_date = None
        
        if last_run:
            try:
                last_date = datetime.strptime(last_run, "%Y-%m-%d").date()
            except Exception:
                last_date = None

        if interval.lower() == "daily":
            return last_date != today
        elif interval.lower() == "weekly":
            return not last_date or (today - last_date).days >= 7
        else:
            if not last_date:
                return True
            y, m, d = last_date.year, last_date.month, last_date.day
            y2, m2 = (y + 1, 1) if m == 12 else (y, m + 1)
            d2 = min(d, monthrange(y2, m2)[1])
            return today >= date(y2, m2, d2)

    def get_target_time(self) -> datetime:
        time_str = self.settings.get("backup_time", "02:00")
        hh, mm = self.parse_backup_time(time_str)
        now = datetime.now()
        return now.replace(hour=hh, minute=mm, second=0, microsecond=0)