"""New York timezone and NYSE calendar helpers."""

import datetime
from typing import Tuple

try:
    import zoneinfo
    NY_TZ = zoneinfo.ZoneInfo("America/New_York")
except Exception:
    import pytz
    NY_TZ = pytz.timezone("America/New_York")

# NYSE Holidays for 2026 and 2027 (from original trader-scanner / trader-alerts)
NYSE_HOLIDAYS = {
    "2026-01-01": "New Year's Day",
    "2026-01-19": "Martin Luther King, Jr. Day",
    "2026-02-16": "Washington's Birthday",
    "2026-04-03": "Good Friday",
    "2026-05-25": "Memorial Day",
    "2026-06-19": "Juneteenth National Independence Day",
    "2026-07-03": "Independence Day (observed)",
    "2026-09-07": "Labor Day",
    "2026-11-26": "Thanksgiving Day",
    "2026-12-25": "Christmas Day",
    "2027-01-01": "New Year's Day",
    "2027-01-18": "Martin Luther King, Jr. Day",
    "2027-02-15": "Washington's Birthday",
    "2027-03-26": "Good Friday",
    "2027-05-31": "Memorial Day",
    "2027-06-18": "Juneteenth National Independence Day (observed)",
    "2027-07-05": "Independence Day (observed)",
    "2027-09-06": "Labor Day",
    "2027-11-25": "Thanksgiving Day",
    "2027-12-24": "Christmas Day (observed)",
}

# NYSE 1:00 PM Early Close days
NYSE_EARLY_CLOSES = {
    "2026-11-27": "Day after Thanksgiving",
    "2026-12-24": "Christmas Eve",
    "2027-11-26": "Day after Thanksgiving",
}


def get_ny_now() -> datetime.datetime:
    """Return current datetime localized to America/New_York."""
    now_utc = datetime.datetime.now(datetime.timezone.utc)
    return now_utc.astimezone(NY_TZ)


def is_nyse_open(dt: datetime.datetime = None) -> Tuple[bool, str]:
    """Check whether the NYSE is currently in regular trading hours.

    Returns (is_open, reason).
    """
    if dt is None:
        dt = get_ny_now()
    else:
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=NY_TZ)
        else:
            dt = dt.astimezone(NY_TZ)

    date_str = dt.strftime("%Y-%m-%d")
    weekday = dt.weekday()  # 0=Mon ... 4=Fri, 5=Sat, 6=Sun

    if weekday >= 5:
        return False, f"Weekend ({dt.strftime('%A')})"

    if date_str in NYSE_HOLIDAYS:
        return False, f"Holiday: {NYSE_HOLIDAYS[date_str]}"

    close_time = datetime.time(13, 0) if date_str in NYSE_EARLY_CLOSES else datetime.time(16, 0)
    open_time = datetime.time(9, 30)

    cur_time = dt.time()

    if cur_time < open_time:
        return False, f"Pre-market (opens at 09:30 ET, current: {cur_time.strftime('%H:%M:%S')} ET)"
    if cur_time >= close_time:
        close_desc = "13:00 early close" if date_str in NYSE_EARLY_CLOSES else "16:00 close"
        return False, f"After-hours (closed at {close_desc}, current: {cur_time.strftime('%H:%M:%S')} ET)"

    return True, f"Regular Trading Hours (closes at {close_time.strftime('%H:%M')} ET)"


def format_ny_time(dt: datetime.datetime = None, include_date: bool = True) -> str:
    """Format datetime as human readable New York time string."""
    if dt is None:
        dt = get_ny_now()
    elif dt.tzinfo is None:
        dt = dt.replace(tzinfo=NY_TZ)
    else:
        dt = dt.astimezone(NY_TZ)

    if include_date:
        return dt.strftime("%Y-%m-%d %H:%M:%S ET")
    return dt.strftime("%H:%M:%S ET")
