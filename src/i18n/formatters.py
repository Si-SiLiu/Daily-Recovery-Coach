"""Locale-aware display formatting; stored values and metric units stay unchanged."""

from datetime import date, datetime

from .locale import normalize_language
from .translator import t


ENGLISH_MONTHS = (
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
)


def _as_date(value: date | datetime | str) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value)[:10])


def format_date(value: date | datetime | str | None, language: str = "zh-CN") -> str:
    if value in (None, ""):
        return t("common.no_data", language)
    try:
        parsed = _as_date(value)
    except (TypeError, ValueError):
        return str(value)
    if normalize_language(language) == "en":
        return f"{ENGLISH_MONTHS[parsed.month - 1]} {parsed.day}, {parsed.year}"
    return f"{parsed.year}年{parsed.month}月{parsed.day}日"


def format_datetime(value: datetime | str | None, language: str = "zh-CN") -> str:
    if value in (None, ""):
        return t("common.no_data", language)
    try:
        parsed = value if isinstance(value, datetime) else datetime.fromisoformat(str(value))
    except (TypeError, ValueError):
        return str(value)
    return f"{format_date(parsed, language)} {parsed:%H:%M}"


def format_number(value: object, language: str = "zh-CN", digits: int = 2) -> str:
    if value in (None, ""):
        return t("common.no_data", language)
    if isinstance(value, float):
        return f"{value:.{digits}f}".rstrip("0").rstrip(".")
    return str(value)


def format_percent(value: object, language: str = "zh-CN", digits: int = 1) -> str:
    return t("common.no_data", language) if value is None else f"{float(value):.{digits}f}%"


def format_duration(minutes: object, language: str = "zh-CN") -> str:
    if minutes is None:
        return t("common.no_data", language)
    total = max(int(round(float(minutes))), 0)
    hours, remainder = divmod(total, 60)
    if hours and remainder:
        return t("format.duration_hours_minutes", language, hours=hours, minutes=remainder)
    if hours:
        return t("format.duration_hours", language, hours=hours)
    return t("format.duration_minutes", language, minutes=remainder)
