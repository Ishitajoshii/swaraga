"""Parsing of the free-text ``period`` column into structured fields.

Observed forms in the raw data::

    "Classical"
    "16th century"
    "20th century"
    "18th century (1775-1835)"
    "18th-19th century"
    "18th-19th century (1762-1827)"

The composer's life years, where present, are the useful part; the century
label is kept as a coarse fallback.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Optional

from .text_norm import clean_text

#: A four-digit year pair, separated by an en dash or a hyphen.
_YEAR_RANGE_RE = re.compile(r"\((\d{4})\s*[–—-]\s*(\d{4})\)")

#: An ordinal century, optionally a range of two.
_CENTURY_RE = re.compile(
    r"(\d{1,2})(?:st|nd|rd|th)(?:\s*[–—-]\s*(\d{1,2})(?:st|nd|rd|th))?\s*century",
    re.IGNORECASE,
)


@dataclass
class PeriodResult:
    """Structured view of one ``period`` string."""

    text: str                           # cleaned original
    century: Optional[str] = None       # e.g. "18th", "18th-19th"
    birth_year: Optional[int] = None
    death_year: Optional[int] = None
    issues: List[str] = field(default_factory=list)


def parse_period(value: str) -> PeriodResult:
    """Parse one ``period`` string into century and life years."""
    cleaned, issues = clean_text(value or "")

    if not cleaned:
        return PeriodResult(text="", issues=issues + ["period_missing"])

    result = PeriodResult(text=cleaned, issues=list(issues))

    years = _YEAR_RANGE_RE.search(cleaned)
    if years:
        birth, death = int(years.group(1)), int(years.group(2))
        if birth >= death:
            result.issues.append(f"period_years_implausible:{birth}-{death}")
        else:
            result.birth_year, result.death_year = birth, death

    century = _CENTURY_RE.search(cleaned)
    if century:
        first, second = century.group(1), century.group(2)
        result.century = f"{_ordinal(first)}-{_ordinal(second)}" if second else _ordinal(first)
    elif result.birth_year is None:
        # Labels like "Classical" carry no date at all.
        result.issues.append("period_undated")

    return result


def _ordinal(number: str) -> str:
    """Render a century number with its English ordinal suffix."""
    value = int(number)
    if 10 <= value % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(value % 10, "th")
    return f"{value}{suffix}"
