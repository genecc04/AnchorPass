from datetime import datetime, timezone
import pytz

try:
    import time
    if time.daylight:
        utc_offset = -time.altzone
    else:
        utc_offset = -time.timezone
    hours = utc_offset // 3600
    minutes = abs(utc_offset % 3600) // 60
    
    for tz_name in pytz.all_timezones:
        tz = pytz.timezone(tz_name)
        if tz.utcoffset(datetime.now()).total_seconds() == utc_offset:
            DEFAULT_TIMEZONE = tz
            break
    else:
        DEFAULT_TIMEZONE = timezone(datetime.now().astimezone().utcoffset())
except Exception:
    DEFAULT_TIMEZONE = pytz.timezone('Asia/Manila')


def parse_datetime(when) -> datetime | None:
    """
    Parse various datetime formats into a datetime object.
    
    Handles:
    - datetime objects
    - ISO format strings (with or without timezone)
    - Common datetime string formats
    - Unix timestamps (seconds or milliseconds)
    
    Args:
        when: Input value (datetime, string, or numeric timestamp)
        
    Returns:
        datetime object or None if parsing fails
    """
    if not when:
        return None
    
    if isinstance(when, datetime):
        return when
    
    s = str(when).strip()
    dt = None
    
    if s.isdigit():
        try:
            ts = int(s)
            if ts > 10_000_000_000:
                ts = ts / 1000.0
            dt = datetime.utcfromtimestamp(ts)
            dt = pytz.utc.localize(dt)
            return dt
        except (ValueError, OSError):
            pass
    
    try:
        s_iso = s.replace("Z", "+00:00")
        dt = datetime.fromisoformat(s_iso)
        return dt
    except (ValueError, AttributeError):
        pass
    
    formats = (
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M:%S.%f",
        "%Y-%m-%d %H:%M",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M:%S.%f",
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%S.%f%z",
        "%Y-%m-%d",
    )
    
    for fmt in formats:
        try:
            dt = datetime.strptime(s, fmt)
            if dt.tzinfo is None:
                dt = pytz.utc.localize(dt)
            return dt
        except ValueError:
            continue
    
    return None


def format_datetime(when, format_str: str = "%b %d, %Y %I:%M %p", timezone=None) -> str:
    """
    Format a datetime value to a localized string.
    
    Args:
        when: Input datetime (various formats supported via parse_datetime)
        format_str: strftime format string (default: "Jan 15, 2024 3:45 PM")
        timezone: Target timezone (default: user's local timezone)
        
    Returns:
        Formatted datetime string, or empty string if parsing fails
    """
    dt = parse_datetime(when)
    if not dt:
        return ""
    
    try:
        if dt.tzinfo is None:
            dt = pytz.utc.localize(dt)
        
        if timezone is None:
            dt_local = dt.astimezone()
        else:
            dt_local = dt.astimezone(timezone)
        
        result = dt_local.strftime(format_str)
        
        if "%I" in format_str:
            result = result.replace(" 0", " ").lstrip("0")
        
        return result
    except Exception:
        return str(when)


def format_datetime_compact(when, timezone=None) -> str:
    """
    Format datetime in compact style: "Jan 15, 2024 3:45PM"
    (No space before AM/PM, leading zeros removed)
    """
    dt = parse_datetime(when)
    if not dt:
        return ""
    
    try:
        if dt.tzinfo is None:
            dt = pytz.utc.localize(dt)
        
        if timezone is None:
            dt_local = dt.astimezone()
        else:
            dt_local = dt.astimezone(timezone)
        
        date_str = dt_local.strftime("%b %d, %Y")
        time_str = dt_local.strftime("%I:%M %p")
        
        time_str = time_str.lstrip("0").replace(" ", "")
        
        return f"{date_str} {time_str}"
    except Exception:
        return str(when)


def format_datetime_with_separator(when, timezone=None) -> str:
    """
    Format datetime with middle dot separator: "Jan 15, 2024 · 3:45 PM"
    """
    dt = parse_datetime(when)
    if not dt:
        return "—"
    
    try:
        if dt.tzinfo is None:
            dt = pytz.utc.localize(dt)
        
        if timezone is None:
            dt_local = dt.astimezone()
        else:
            dt_local = dt.astimezone(timezone)
        
        return dt_local.strftime("%b %d, %Y · %I:%M %p").lstrip("0").replace(" 0", " ")
    except Exception:
        return "—"


def format_date_only(when, timezone=None) -> str:
    """
    Format only the date part: "Jan 15, 2024"
    """
    return format_datetime(when, format_str="%b %d, %Y", timezone=timezone)


def format_time_only(when, timezone=None) -> str:
    """
    Format only the time part: "3:45 PM"
    """
    result = format_datetime(when, format_str="%I:%M %p", timezone=timezone)
    return result.lstrip("0").replace(" 0", " ")