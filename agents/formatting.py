"""Indian number formatting, backend side.

Mirrors ui/frontend/src/lib/format.js exactly. Every formatted string that
leaves the API is built here or in agents/registry.py -- never in a route
handler, and never by string-concatenating a rupee sign somewhere ad hoc.
"""

from __future__ import annotations

RUPEE = "₹"
LAKH = 100_000
CRORE = 10_000_000


def group_indian(digits: str) -> str:
    """Group an integer string the Indian way: last three, then pairs."""
    if len(digits) <= 3:
        return digits
    last3, rest = digits[-3:], digits[:-3]
    groups: list[str] = []
    while len(rest) > 2:
        groups.insert(0, rest[-2:])
        rest = rest[:-2]
    if rest:
        groups.insert(0, rest)
    return f"{','.join(groups)},{last3}"


def format_number(value: float | int | None) -> str:
    """4,82,300"""
    if value is None:
        return "--"
    sign = "-" if value < 0 else ""
    return sign + group_indian(str(round(abs(value))))


def format_currency(value: float | int | None) -> str:
    """Rs 4,82,300 -- exact to the rupee."""
    if value is None:
        return "--"
    return RUPEE + format_number(value)


def format_compact_currency(value: float | int | None) -> str:
    """Rs 48.20L / Rs 1.24Cr -- headline figures only."""
    if value is None:
        return "--"
    magnitude = abs(value)
    sign = "-" if value < 0 else ""
    if magnitude >= CRORE:
        return f"{sign}{RUPEE}{magnitude / CRORE:.2f}Cr"
    if magnitude >= LAKH:
        return f"{sign}{RUPEE}{magnitude / LAKH:.2f}L"
    return format_currency(value)


def format_percent(value: float | None, decimals: int = 1) -> str:
    """61.2%"""
    if value is None:
        return "--"
    return f"{value:.{decimals}f}%"


def format_points(value: float | None, decimals: int = 1) -> str:
    """+3.5 pts / -1.2 pts -- percentage-point movement, always signed."""
    if value is None:
        return "--"
    sign = "+" if value > 0 else "-" if value < 0 else ""
    return f"{sign}{abs(value):.{decimals}f} pts"


def format_signed_currency(value: float | int | None) -> str:
    """+Rs 684 / -Rs 1,204 -- a movement, never a level."""
    if value is None:
        return "--"
    sign = "+" if value > 0 else "-" if value < 0 else ""
    return f"{sign}{format_currency(abs(value))}"


def format_count(value: int | None, noun: str, plural: str | None = None) -> str:
    """6 events / 1 event"""
    if value is None:
        return "--"
    word = noun if value == 1 else (plural or f"{noun}s")
    return f"{format_number(value)} {word}"


def format_date_long(iso: str | None) -> str:
    """14 September 2026"""
    if not iso:
        return "--"
    months = [
        "January", "February", "March", "April", "May", "June",
        "July", "August", "September", "October", "November", "December",
    ]
    y, m, d = (int(part) for part in iso.split("-"))
    return f"{d} {months[m - 1]} {y}"
