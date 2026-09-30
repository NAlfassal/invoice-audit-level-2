"""The shape of every extracted contract value: value, source, verified, evidence.

Input: a Python value (Decimal, date, str, int or a list of them) and where it was read.
Output: a JSON-ready dict. Decimals are written as strings so no float ever holds money.
A value starts unverified; extract.verify sets `verified` and `evidence` once the invoices
reproduce it, and the rest go to the eye check.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

JsonValue = str | int | bool | list | dict | None


def to_json(value: object) -> JsonValue:
    """Decimal -> str, date -> ISO string, lists and dicts element by element."""
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, list | tuple):
        return [to_json(item) for item in value]
    if isinstance(value, dict):
        return {str(key): to_json(item) for key, item in value.items()}
    if isinstance(value, bool):
        return value
    if value is None or isinstance(value, str | int):
        return value
    raise TypeError(f"cannot store {value!r} ({type(value).__name__}) in the contract JSON")


def term(value: object, source: str, **extra: object) -> dict:
    """Build a contract value with its source; unverified until a check confirms it."""
    entry = {"value": to_json(value), "source": source, "verified": False, "evidence": ""}
    entry.update({key: to_json(item) for key, item in extra.items()})
    return entry
