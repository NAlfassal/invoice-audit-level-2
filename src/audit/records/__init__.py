"""Parsers for site records: civil records and Daily Drilling Reports (Phase 4).

This module holds what both parsers share: reading a signature line.
"""

from __future__ import annotations

import re

LETTER = re.compile(r"[A-Za-z]")


def signature(value: str | None) -> str:
    """Return a signature as written, or "" when the line is blank or holds no letters.

    A line of underscores ("____") is an unsigned space on the form, not a name (civil Cl.47
    p.8, drilling Cl.15 p.5).
    """
    text = (value or "").strip()
    return text if LETTER.search(text) else ""
