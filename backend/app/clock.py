from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from app.config import get_settings

IST = ZoneInfo("Asia/Kolkata")


def now_ist() -> datetime:
    settings = get_settings()
    if settings.demo_now_ist:
        return datetime.fromisoformat(settings.demo_now_ist).replace(tzinfo=IST)
    return datetime.now(IST)


def is_quiet_hours(moment: datetime | None = None) -> bool:
    moment = moment or now_ist()
    hour = moment.hour
    return hour >= 21 or hour < 9


def next_send_window(moment: datetime | None = None) -> datetime:
    moment = moment or now_ist()
    if not is_quiet_hours(moment):
        return moment
    if moment.hour >= 21:
        return moment.replace(hour=9, minute=0, second=0, microsecond=0) + __import__(
            "datetime"
        ).timedelta(days=1)
    return moment.replace(hour=9, minute=0, second=0, microsecond=0)
