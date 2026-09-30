"""Readers for the table shapes both contracts use: rates, factors, percentages, limits.

Input: the corrected text of one table (or page section). Output: dicts of `term` values
keyed by item code or class. Each reader takes the value from a fixed column position
counted from the end of the row, because the OCR sometimes merges or empties the leading
description cells but keeps the numeric columns at the right.
"""

from __future__ import annotations

import re

from audit.extract.ocr_text import (
    parse_amount,
    parse_percent,
    rows_starting_with,
    table_rows,
)
from audit.extract.values import term

NOT_CHARGEABLE = "not chargeable"


def clean_code(cell: str, code: re.Pattern[str], where: str) -> str:
    """Return the item code at the start of a cell, without OCR punctuation ('D.43.020.')."""
    match = code.match(cell.strip())
    if not match:
        raise ValueError(f"{where}: {cell!r} does not start with an item code")
    return match.group(0)


def rate_table(
    text: str, code: re.Pattern[str], source: str, rate_column: int = -1
) -> dict[str, dict]:
    """Code -> rate from rows 'code | description | ...', the rate in `rate_column`."""
    rates = {}
    for cells in rows_starting_with(text, code):
        item = clean_code(cells[0], code, source)
        where = f"{source} {item}"
        rate = parse_amount(cells[rate_column], where)
        rates[item] = term(rate, source, description=cells[1])
    return rates


def schedule_rows(text: str, code: re.Pattern[str], source: str) -> dict[str, dict]:
    """Schedule 1 rows: code, description, unit and rate (the rate may be a reference text)."""
    items = {}
    for cells in rows_starting_with(text, code):
        item = clean_code(cells[0], code, source)
        where = f"{source} {item}"
        rate_cell = cells[-1]
        if re.search(r"\d", rate_cell) and not rate_cell.startswith(("Schedule", "Clause")):
            rate = term(parse_amount(rate_cell, where), source)
        else:
            rate = term(rate_cell, source)  # e.g. "Schedule 2", "Clause 31": priced elsewhere
        items[item] = {"description": cells[1], "unit": cells[2], "rate": rate}
    return items


def factor_table(text: str, key: re.Pattern[str], source: str) -> dict[str, dict]:
    """Class -> factor from rows 'class label | ... | factor' whose first cell matches `key`."""
    factors = {}
    for cells in table_rows(text):
        match = key.match(cells[0])
        if not match:
            continue
        name = match.group(0)
        factors[name] = term(parse_amount(cells[-1], f"{source} {name}"), source, label=cells[0])
    return factors


def percent_table(text: str, code: re.Pattern[str], source: str) -> dict[str, dict]:
    """Code -> percentage (last cell); 'Not chargeable' is kept as that text."""
    percents = {}
    for cells in rows_starting_with(text, code):
        item = clean_code(cells[0], code, source)
        cell = cells[-1]
        if cell.lower().replace(".", " ").replace("  ", " ") == NOT_CHARGEABLE:
            percents[item] = term(NOT_CHARGEABLE, source)
        else:
            percents[item] = term(parse_percent(cell, f"{source} {item}"), source)
    return percents


def limit_table(text: str, code: re.Pattern[str], source: str) -> dict[str, dict]:
    """Code -> daily limit from rows 'code | description | limit | unit'."""
    limits = {}
    for cells in rows_starting_with(text, code):
        item = clean_code(cells[0], code, source)
        limit = parse_amount(cells[-2], f"{source} {item}")
        limits[item] = term(limit, source, unit=cells[-1])
    return limits


def codes_in(text: str, code: re.Pattern[str]) -> list[str]:
    """Every item code mentioned in `text`, in order, without repeats."""
    seen: list[str] = []
    for found in code.findall(text):
        if found not in seen:
            seen.append(found)
    return seen
