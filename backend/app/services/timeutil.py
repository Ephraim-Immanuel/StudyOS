"""Timezone helpers.

Rule used everywhere: datetimes are STORED in UTC. "Which day is it?" questions are
answered in the USER's own timezone (users.timezone)."""
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from app.models import User


def user_tz(user: User) -> ZoneInfo:
    try:
        return ZoneInfo(user.timezone)
    except (ZoneInfoNotFoundError, ValueError):
        return ZoneInfo("UTC")


def local_today(user: User, now: datetime) -> date:
    return now.astimezone(user_tz(user)).date()


def to_local_date(dt: datetime, user: User) -> date:
    return dt.astimezone(user_tz(user)).date()


def day_bounds_utc(day: date, user: User) -> tuple[datetime, datetime]:
    """[start, end) of a local calendar day expressed in UTC."""
    tz = user_tz(user)
    start = datetime.combine(day, time.min, tzinfo=tz)
    end = datetime.combine(day + timedelta(days=1), time.min, tzinfo=tz)
    return start.astimezone(timezone.utc), end.astimezone(timezone.utc)


def ensure_aware(dt: datetime, user: User) -> datetime:
    """Naive input (no offset) is interpreted in the user's timezone."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=user_tz(user)).astimezone(timezone.utc)
    return dt.astimezone(timezone.utc)
