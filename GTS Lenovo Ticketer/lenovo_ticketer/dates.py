from __future__ import annotations

from datetime import date, datetime

from openpyxl.utils.datetime import from_excel


def _parse_date(value: object) -> date | None:
    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, (int, float)):
        try:
            return from_excel(value).date()
        except Exception:
            return None
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%m/%d/%y", "%Y/%m/%d"):
            try:
                return datetime.strptime(text, fmt).date()
            except ValueError:
                pass
        try:
            return datetime.fromisoformat(text.replace("Z", "+00:00")).date()
        except ValueError:
            return None
    return None


def format_pickup_date(value: object) -> str:
    parsed = _parse_date(value)
    if parsed:
        return f"{parsed.month}/{parsed.day}/{parsed.year}"
    return "" if value in (None, "") else str(value).strip()


def format_warranty_date(value: object) -> str:
    parsed = _parse_date(value)
    if parsed:
        return parsed.isoformat()
    return "" if value in (None, "") else str(value).strip()


def date_sort_key(value: object) -> tuple[int, str]:
    parsed = _parse_date(value)
    if parsed:
        return (1, parsed.isoformat())
    text = "" if value in (None, "") else str(value).strip()
    return (0, text)
