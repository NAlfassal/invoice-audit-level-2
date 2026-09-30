"""Parse the Schedule of Variations and each supplement / amendment page.

Input: corrected OCR pages. Output: one dict per instrument with its issue and effective
dates, substituted rates (each with its own effective date), monthly re-published rates,
discount and term extension, every value carrying its page. Both contracts print their
instruments in the same form, so one parser serves both; the instrument page must agree
with the Schedule of Variations on both dates, or extraction stops.
"""

from __future__ import annotations

import re
from decimal import Decimal

from audit.extract.ocr_text import (
    ISO_DAY,
    Pages,
    parse_amount,
    parse_day_text,
    parse_iso_day,
    parse_month_name,
    section,
    table_rows,
)
from audit.extract.values import term

MONEY = re.compile(r"\d{1,3}(?:,\d{3})*\.\d{2}")  # always two decimals, so "1200 mm" never matches
DAY_TEXT = r"(\d{1,2}\s*[A-Z][a-z]+\s*\d{4})"
HEADER = re.compile(rf"Reference\s+(\S+?)\.\s*Issued\s*{DAY_TEXT}\s+and taking effect\s+{DAY_TEXT}")
DISCOUNT = re.compile(
    r"A discount of (\d+) per cent is allowed on the (?:items|services) listed below for "
    rf"(?:work executed|services performed) on or after {DAY_TEXT}"
)
EXTENSION = re.compile(rf"is extended to {DAY_TEXT}")
NEXT_HEADING = "\n## "


def schedule_of_variations(pages: Pages, page: int) -> dict[str, dict]:
    """Instrument name -> issue and effective dates from the Schedule of Variations table."""
    schedule = {}
    for cells in table_rows(pages.text(page)):
        name = cells[0].replace(" ", "")
        if not name.startswith(("Supplement", "Amendment")):
            continue
        where = f"p.{page} Schedule of Variations, {cells[0]}"
        schedule[name] = {
            "issued": parse_iso_day(cells[1], where),
            "effective": parse_iso_day(cells[2], where),
            "changes": cells[3],
        }
    return schedule


def parse_instrument(pages: Pages, page: int, code: re.Pattern[str]) -> dict:
    """Everything one supplement or amendment page states, with its source."""
    text = pages.text(page)
    title = text.splitlines()[0].lstrip("# ").strip()
    header = HEADER.search(text)
    if not header:
        raise ValueError(f"{pages.contract} p.{page}: no 'Reference ... Issued ...' line")
    source = f"p.{page} {title.split(' TO ')[0].title()}"
    instrument = {
        "title": title,
        "reference": header.group(1),
        "issued": term(parse_day_text(header.group(2), source), source),
        "effective": term(parse_day_text(header.group(3), source), source),
        "rates": substituted_rates(text, code, source),
        "monthly_rates": monthly_rates(text, code, source),
        "discount": discount(text, code, source),
    }
    extension = EXTENSION.search(text)
    if extension:
        instrument["term_end"] = term(parse_day_text(extension.group(1), source), source)
    return instrument


def substituted_rates(text: str, code: re.Pattern[str], source: str) -> dict[str, dict]:
    """Item -> previous rate, substituted rate and the item's own effective date."""
    if "Substituted rates" not in text:
        return {}
    block = section(text, "Substituted rates", "Save as stated")
    block = block.split(NEXT_HEADING)[0]  # a discount section may follow before "Save as stated"
    rates = {}
    for cells in table_rows(block):
        row = " ".join(cells)
        found_code = code.search(row)
        if not found_code:
            continue
        # Remove item codes first: "B.23.010" would otherwise read as the amount "23.01".
        figures = code.sub(" ", row)
        amounts = MONEY.findall(figures)
        days = ISO_DAY.findall(figures)
        if len(amounts) != 2 or len(days) != 1:
            raise ValueError(f"{source}: cannot read previous / new rate / date in row {row!r}")
        where = f"{source} {found_code.group(0)}"
        previous, new = (parse_amount(amount, where) for amount in amounts)
        effective = parse_iso_day("-".join(days[0]), where)
        rates[found_code.group(0)] = term(new, source, previous=previous, effective=effective)
    return rates


def monthly_rates(text: str, code: re.Pattern[str], source: str) -> dict[str, dict]:
    """Item -> {month: rate} from a 'Monthly re-...' section, if the instrument has one."""
    heading = re.search(r"## [\d.]+ ?Monthly re-\w+, item (\S+)", text)
    if not heading:
        return {}
    item = code.search(heading.group(1))
    block = section(text, heading.group(0), NEXT_HEADING)
    months: dict[str, Decimal] = {}
    for cells in table_rows(block)[1:]:  # row 0 is the header
        where = f"{source} {item.group(0)} {cells[0]}"
        months[parse_month_name(cells[0], where)] = parse_amount(cells[1], where)
    # "the rate last published applies until it is superseded" (same words in every instrument)
    return {
        item.group(0): term(
            {month: str(rate) for month, rate in months.items()},
            source,
            carry_forward_last_month=True,
        )
    }


def discount(text: str, code: re.Pattern[str], source: str) -> dict | None:
    """Discount percentage, start date and the items it covers, if the instrument has one."""
    match = DISCOUNT.search(text.replace("\n", " "))
    if not match:
        return None
    block = section(text, "Discount on principal", "Save as stated")
    items = [
        code.search(" ".join(cells)).group(0)
        for cells in table_rows(block)
        if code.search(" ".join(cells))
    ]
    start = parse_day_text(match.group(2), source)
    return term(Decimal(match.group(1)), source, start=start, items=items)
