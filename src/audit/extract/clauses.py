"""Contract terms stated in prose, typed in by hand and checked against the OCR text.

Input: extracted/contracts/<contract>_clauses.json (each term with its page, clause, the
quote it was read from and the value as written) and the corrected OCR pages. Output: the
terms as `term` values keyed by name. A term is accepted only if its quote appears word for
word on its page and the value as written appears in the quote, so a typed-in term can never
drift from the contract text.
"""

from __future__ import annotations

import json
import re
from datetime import date
from decimal import Decimal

from audit.config import CONTRACTS_DIR
from audit.extract.ocr_text import Pages
from audit.extract.values import term

CLAUSES_FILE = "{contract}_clauses.json"


def _normalise(text: str) -> str:
    """Collapse whitespace so line breaks and table padding do not break a quote match."""
    return re.sub(r"\s+", " ", text).strip()


def _typed(entry: dict) -> object:
    """Return the entry's value as its declared type."""
    kind, value = entry["type"], entry["value"]
    if kind == "date":
        return date.fromisoformat(value)
    if kind == "decimal":
        return Decimal(value)
    if kind in {"int", "text", "list"}:
        return value
    raise ValueError(f"{entry['key']}: unknown type {kind!r}")


def load_clause_terms(pages: Pages) -> dict[str, dict]:
    """Every hand-read term of the contract, after checking its quote against the OCR page."""
    path = CONTRACTS_DIR / CLAUSES_FILE.format(contract=pages.contract)
    entries = json.loads(path.read_text(encoding="utf-8"))
    terms = {}
    for entry in entries:
        where = f"{path.name} {entry['key']} (p.{entry['page']} {entry['clause']})"
        quote = _normalise(entry["quote"])
        if quote not in _normalise(pages.text(entry["page"])):
            raise ValueError(f"{where}: quote not found on the OCR page: {entry['quote']!r}")
        if entry["as_written"] not in quote:
            raise ValueError(f"{where}: {entry['as_written']!r} is not in its quote")
        source = f"p.{entry['page']} {entry['clause']}"
        terms[entry["key"]] = term(_typed(entry), source, quote=entry["quote"])
    return terms
