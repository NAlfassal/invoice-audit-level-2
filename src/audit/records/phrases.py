"""Civil record wording -> Schedule 1 item, from the reviewed template table.

Input: extracted/mappings/civil_phrases.json (26 templates, each with its item, unit and
evidence; built once by reading every record's work line and the Schedule 1 descriptions,
no LLM call). Output: for a record's work line, the item it evidences and the quantity it
states. A record evidences what it says, not the Bill of Quantities wording (Cl.47A p.33).
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from decimal import Decimal
from functools import cache

from audit.config import MAPPINGS_DIR

PHRASES_FILE = MAPPINGS_DIR / "civil_phrases.json"


@dataclass(frozen=True)
class Template:
    """One work-line template and the item it evidences."""

    series: str
    pattern: re.Pattern[str]
    item: str
    unit: str


@dataclass(frozen=True)
class Reading:
    """What a record's work line states: the item, the quantity and its unit."""

    item: str
    quantity: Decimal
    unit: str


@cache
def templates() -> tuple[Template, ...]:
    """Load the reviewed templates; stop if the mapping file is missing."""
    if not PHRASES_FILE.exists():
        raise FileNotFoundError(f"{PHRASES_FILE} is missing: the civil phrase table is committed")
    entries = json.loads(PHRASES_FILE.read_text(encoding="utf-8"))["templates"]
    return tuple(
        Template(e["series"], re.compile("^" + e["pattern"] + "$"), e["item"], e["unit"])
        for e in entries
    )


def read_work_line(series: str, text: str) -> Reading | None:
    """Return the item and quantity a work line states, or None if no template matches."""
    for template in templates():
        if template.series != series:
            continue
        match = template.pattern.match(text)
        if match:
            return Reading(template.item, Decimal(match["quantity"]), template.unit)
    return None
