"""Read OCR pages with the recorded corrections applied, and parse their cells strictly.

Input: extracted/ocr/<contract>/page_XX.md and extracted/contracts/ocr_corrections.json.
Output: page text, markdown table rows, and Decimal / date values. A correction either
replaces an exact piece of OCR text (it must be found, or extraction fails) or appends rows
the OCR lost. Parsers raise on anything that is not a clean number, so an OCR misread is
never silently turned into a value: it must be corrected, with a reason, in the file.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from pathlib import Path

from audit.config import CONTRACTS_DIR, OCR_DIR

CORRECTIONS_FILE = CONTRACTS_DIR / "ocr_corrections.json"
PAGE_FILE = "page_{:02d}.md"

AMOUNT = re.compile(r"\d{1,3}(?:,\d{3})*(?:\.\d+)?")
PERCENT = re.compile(r"(\d+(?:\.\d+)?)\s*%")
ISO_DAY = re.compile(r"(20\d\d)-(\d\d)-(\d\d)")
MONTH = re.compile(r"20\d\d-(?:0[1-9]|1[0-2])")
MONTH_NAMES = {
    name: number
    for number, name in enumerate(
        [
            "January",
            "February",
            "March",
            "April",
            "May",
            "June",
            "July",
            "August",
            "September",
            "October",
            "November",
            "December",
        ],
        start=1,
    )
}


@dataclass
class Pages:
    """The OCR pages of one contract, with its corrections applied on first read."""

    contract: str
    corrections: list[dict] = field(default_factory=list)
    _cache: dict[int, str] = field(default_factory=dict)
    applied: list[dict] = field(default_factory=list)

    def text(self, page: int) -> str:
        """Corrected markdown of one page."""
        if page not in self._cache:
            raw = (OCR_DIR / self.contract / PAGE_FILE.format(page)).read_text(encoding="utf-8")
            self._cache[page] = self._correct(page, raw)
        return self._cache[page]

    def _correct(self, page: int, text: str) -> str:
        for fix in self.corrections:
            if fix["page"] != page:
                continue
            if "append" in fix:
                text = text + "\n" + fix["append"] + "\n"
            elif fix["ocr_text"] in text:
                text = text.replace(fix["ocr_text"], fix["corrected"])
            else:
                raise ValueError(
                    f"{self.contract} p.{page}: correction text {fix['ocr_text']!r} not found"
                )
            self.applied.append(fix)
        return text


def load_pages(contract: str) -> Pages:
    """Pages of `contract` ("civil" or "drilling") with that contract's corrections."""
    corrections = []
    if CORRECTIONS_FILE.exists():
        all_fixes = json.loads(CORRECTIONS_FILE.read_text(encoding="utf-8"))
        corrections = [fix for fix in all_fixes if fix["contract"] == contract]
    return Pages(contract, corrections)


def section(text: str, start: str, end: str | None = None) -> str:
    """Return the part of `text` from the first `start` up to the next `end` (or the end)."""
    begin = text.index(start)
    stop = text.find(end, begin + len(start)) if end else -1
    return text[begin:] if stop == -1 else text[begin:stop]


def table_rows(text: str) -> list[list[str]]:
    """Every markdown table row in `text` as stripped cells; separator rows are skipped."""
    rows = []
    for line in text.splitlines():
        line = line.strip()
        if not line.startswith("|") or set(line) <= {"|", "-", " ", ":"}:
            continue
        rows.append([cell.strip() for cell in line.strip("|").split("|")])
    return rows


def rows_starting_with(text: str, code: re.Pattern[str]) -> list[list[str]]:
    """Table rows whose first non-empty cell starts with an item code."""
    found = []
    for row in table_rows(text):
        cells = [cell for cell in row if cell]
        if cells and code.match(cells[0]):
            found.append(cells)
    return found


def parse_amount(text: str, where: str) -> Decimal:
    """'1,480.00' -> Decimal('1480.00'); anything else raises naming where it was read."""
    cleaned = text.strip().rstrip(".")
    if not AMOUNT.fullmatch(cleaned):
        raise ValueError(f"{where}: {text!r} is not an amount")
    return Decimal(cleaned.replace(",", ""))


def parse_percent(text: str, where: str) -> Decimal:
    """'18%' -> Decimal('18'); a reversed '%96' or any other shape raises."""
    match = PERCENT.fullmatch(text.strip().rstrip("."))
    if not match:
        raise ValueError(f"{where}: {text!r} is not a percentage")
    return Decimal(match.group(1))


def parse_iso_day(text: str, where: str) -> date:
    """'2025-05-01' -> date."""
    match = ISO_DAY.fullmatch(text.strip())
    if not match:
        raise ValueError(f"{where}: {text!r} is not YYYY-MM-DD")
    return date(*(int(part) for part in match.groups()))


def parse_day_text(text: str, where: str) -> date:
    """'1 May 2025' (or the OCR's '17August 2026') -> date."""
    match = re.fullmatch(r"(\d{1,2})\s*([A-Z][a-z]+)\s*(\d{4})", text.strip())
    if not match or match.group(2) not in MONTH_NAMES:
        raise ValueError(f"{where}: {text!r} is not 'D Month YYYY'")
    day, month, year = match.groups()
    return date(int(year), MONTH_NAMES[month], int(day))


def parse_month_name(text: str, where: str) -> str:
    """'May 2025' -> '2025-05'."""
    parts = text.replace(".", " ").split()
    if len(parts) != 2 or parts[0] not in MONTH_NAMES or not parts[1].isdigit():
        raise ValueError(f"{where}: {text!r} is not 'Month YYYY'")
    return f"{parts[1]}-{MONTH_NAMES[parts[0]]:02d}"


def month_table(text: str, where: str, expected: int = 24) -> dict[str, Decimal]:
    """Read a two-column-pair month table (month, value, month, value) in row order.

    The OCR often fuses a value with the next month ('101.802026-04'), so each row is read
    as a token stream: months and amounts must alternate, and `expected` months must be found.
    """
    token = re.compile(r"(20\d\d-(?:0[1-9]|1[0-2]))|(\d{2,3}\.\d{2})")
    values: dict[str, Decimal] = {}
    for row in table_rows(text):
        tokens = token.findall(" ".join(row))
        if not tokens or not tokens[0][0]:
            continue  # header row
        pairs = [(m or v) for m, v in tokens]
        if len(pairs) % 2 or not all(MONTH.fullmatch(pairs[i]) for i in range(0, len(pairs), 2)):
            raise ValueError(f"{where}: cannot pair months and values in row {row}")
        for i in range(0, len(pairs), 2):
            values[pairs[i]] = Decimal(pairs[i + 1])
    if len(values) != expected:
        raise ValueError(f"{where}: {len(values)} months read, {expected} expected")
    return dict(sorted(values.items()))


def source_path(contract: str, page: int) -> Path:
    """Return the OCR file a value was read from (for messages)."""
    return OCR_DIR / contract / PAGE_FILE.format(page)
