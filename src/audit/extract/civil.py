"""Build the civil contract (CW-2025-0417-CIV) JSON from its corrected OCR pages.

Input: `Pages` for "civil". Output: a dict of schedules and instruments, every value a
`term` with its page and schedule. Page numbers below are where each schedule sits in the
43-page scan; the reader for each table is in extract.tables / extract.instruments.
"""

from __future__ import annotations

import re

from audit.extract.instruments import parse_instrument, schedule_of_variations
from audit.extract.ocr_text import (
    Pages,
    month_table,
    parse_amount,
    parse_percent,
    rows_starting_with,
    section,
    table_rows,
)
from audit.extract.tables import (
    codes_in,
    factor_table,
    limit_table,
    percent_table,
    rate_table,
    schedule_rows,
)
from audit.extract.values import term

CODE = re.compile(r"[A-E]\.\d{2}\.\d{3}")
ZONE = re.compile(r"Z\d")
GROUND = re.compile(r"G\d")
RECORD_SERIES = re.compile(r"[A-Z]{2}")
BAND = re.compile(r"(?:(\d[\d,]*) to (\d[\d,]*)|above (\d[\d,]*))")
RATE_BEFORE_UNIT = 2  # Schedules 2A and 2B print "code | description | rate | unit"

SCHEDULE_1_PAGES = (17, 18, 19)
ZONE_PAGE, INDEXED_PAGE, USD_PAGE, GROUND_PAGE = 20, 21, 22, 23
UPLIFT_PAGE, BANDS_PAGES, LIMITS_PAGES, RECORDS_PAGE = 24, (24, 25), (25, 26), 27
DAYWORK_PAGES, PROVISIONAL_PAGE, PRELIMINARIES_PAGE = (28, 29), 30, 31
VARIATIONS_PAGE, INSTRUMENT_PAGES = 38, (39, 40, 41, 42, 43)


def civil_contract(pages: Pages) -> dict:
    """Every schedule and instrument of the civil contract that pricing or checks use."""
    return {
        "contract_ref": "CW-2025-0417-CIV",
        "items": schedule_1(pages),
        "zone_factors": factor_table(pages.text(ZONE_PAGE), ZONE, f"p.{ZONE_PAGE} Schedule 2"),
        "ground": ground(pages),
        "night_uplift": uplifts(pages, "Part 1", "Part 2"),
        "rest_day_uplift": uplifts(pages, "Part 2", "Part 3"),
        "bands": bands(pages),
        "daily_limits": daily_limits(pages),
        "exclusions": exclusions(pages),
        "surveyed_items": surveyed_items(pages),
        "record_series": record_series(pages),
        "indexed": indexed(pages),
        "usd": usd(pages),
        "daywork": daywork(pages),
        "provisional_sums": sums_table(pages, PROVISIONAL_PAGE, "Schedule 7"),
        "preliminaries": preliminaries(pages),
        "instruments": instruments(pages),
    }


def schedule_1(pages: Pages) -> dict[str, dict]:
    """Item -> description, unit and base rate (Schedule 1, pp.17-19)."""
    items: dict[str, dict] = {}
    for page in SCHEDULE_1_PAGES:
        items.update(schedule_rows(pages.text(page), CODE, f"p.{page} Schedule 1"))
    return items


def ground(pages: Pages) -> dict:
    """Ground classification factors and the only items they apply to (Schedule 3, Cl.29)."""
    text = pages.text(GROUND_PAGE)
    source = f"p.{GROUND_PAGE} Schedule 3"
    listed = section(text, "Items to which Schedule 3 applies", "G2 Firm Sabkha is the datum")
    return {
        "factors": factor_table(text, GROUND, source),
        "items": term(codes_in(listed, CODE), source),
    }


def uplifts(pages: Pages, part: str, next_part: str) -> dict[str, dict]:
    """Item -> uplift % from Schedule 4 Part 1 (night) or Part 2 (rest day)."""
    text = section(pages.text(UPLIFT_PAGE), f"## {part}", f"## {next_part}")
    return percent_table(text, CODE, f"p.{UPLIFT_PAGE} Schedule 4 {part}")


def bands(pages: Pages) -> dict[str, list[dict]]:
    """Item -> quantity bands per Contract Year with the % of rate (Schedule 4 Part 3)."""
    text = section(pages.text(BANDS_PAGES[0]), "## Part 3") + section(
        pages.text(BANDS_PAGES[1]), "|", "## Part 4"
    )
    source = "pp.24-25 Schedule 4 Part 3"
    banded: dict[str, list[dict]] = {}
    for cells in rows_starting_with(text, CODE):
        item = CODE.match(cells[0]).group(0)
        where = f"{source} {item} {cells[2]}"
        match = BAND.fullmatch(cells[2])
        if not match:
            raise ValueError(f"{where}: band {cells[2]!r} is not 'a to b' or 'above a'")
        low, high, above = match.groups()
        lower = parse_amount(low or above, where) + (1 if above else 0)
        upper = parse_amount(high, where) if high else None
        percent = parse_percent(cells[-1], where)
        banded.setdefault(item, []).append(term(percent, source, from_qty=lower, to_qty=upper))
    return banded


def daily_limits(pages: Pages) -> dict[str, dict]:
    """Item -> quantity measurable per work area per day (Schedule 4 Part 4, Cl.31)."""
    text = section(pages.text(LIMITS_PAGES[0]), "## Part 4") + section(
        pages.text(LIMITS_PAGES[1]), "|", "## Part 5"
    )
    return limit_table(text, CODE, "pp.25-26 Schedule 4 Part 4")


def exclusions(pages: Pages) -> dict[str, dict]:
    """Excluded item -> excluding item and days (Schedule 4 Part 5, Cl.32)."""
    text = section(pages.text(26), "## Part 5", "## Part 6")
    source = "p.26 Schedule 4 Part 5"
    found = {}
    for cells in rows_starting_with(text, CODE):
        days = parse_amount(cells[2].replace("days", "").strip(), f"{source} {cells[0]}")
        found[cells[0]] = term(days, source, excluded_by=cells[1])
    return found


def surveyed_items(pages: Pages) -> dict:
    """Items measured only against a joint survey sheet (Schedule 4 Part 6, Cl.33)."""
    text = section(pages.text(26), "## Part 6")
    return term([cells[0] for cells in rows_starting_with(text, CODE)], "p.26 Schedule 4 Part 6")


def record_series(pages: Pages) -> dict[str, dict]:
    """Item -> record reference series required before payment (Schedule 5, Cl.46)."""
    source = f"p.{RECORDS_PAGE} Schedule 5"
    series = {}
    for cells in rows_starting_with(pages.text(RECORDS_PAGE), CODE):
        if not RECORD_SERIES.fullmatch(cells[-1]):
            raise ValueError(f"{source} {cells[0]}: series {cells[-1]!r} is not two letters")
        series[cells[0]] = term(cells[-1], source)
    return series


def indexed(pages: Pages) -> dict:
    """Schedule 2A items and the Site Materials Index by month (Cl.29A)."""
    text = pages.text(INDEXED_PAGE)
    source = f"p.{INDEXED_PAGE} Schedule 2A"
    items = section(text, "| Code", "Site Materials Index, as published")
    index = section(text, "Site Materials Index, as published")
    return {
        "items": rate_table(items, CODE, source, rate_column=RATE_BEFORE_UNIT),
        "index": term(month_table(index, source), source),
    }


def usd(pages: Pages) -> dict:
    """Schedule 2B items (rates in USD) and halalas per USD by month (Cl.26A)."""
    text = pages.text(USD_PAGE)
    source = f"p.{USD_PAGE} Schedule 2B"
    items = section(text, "| Code", "Rate of exchange")
    exchange = section(text, "Rate of exchange")
    return {
        "items": rate_table(items, CODE, source, rate_column=RATE_BEFORE_UNIT),
        "halalas_per_usd": term(month_table(exchange, source), source),
    }


def daywork(pages: Pages) -> dict:
    """Daywork labour and plant rates and percentage additions (Schedule 6)."""
    text = pages.text(DAYWORK_PAGES[0]) + pages.text(DAYWORK_PAGES[1])
    source = "pp.28-29 Schedule 6"
    rates, additions = {}, {}
    for cells in table_rows(text):
        if cells[-1].endswith("%"):
            additions[cells[0]] = term(parse_percent(cells[-1], f"{source} {cells[0]}"), source)
        elif len(cells) == 3 and cells[1] in {"hour", "week"}:
            rate = parse_amount(cells[2], f"{source} {cells[0]}")
            rates[cells[0]] = term(rate, source, unit=cells[1])
    return {"rates": rates, "additions": additions}


def sums_table(pages: Pages, page: int, schedule: str) -> dict[str, dict]:
    """Read reference -> sum from a 'reference | description | sum' table."""
    source = f"p.{page} {schedule}"
    sums = {}
    for cells in table_rows(pages.text(page)):
        if re.fullmatch(r"P[SC]\.\d{2}", cells[0]):
            amount = parse_amount(cells[-1], f"{source} {cells[0]}")
            sums[cells[0]] = term(amount, source, description=cells[1])
    return sums


def preliminaries(pages: Pages) -> dict[str, dict]:
    """Preliminary item -> unit and amount (Schedule 8)."""
    source = f"p.{PRELIMINARIES_PAGE} Schedule 8"
    items = {}
    for cells in table_rows(pages.text(PRELIMINARIES_PAGE)):
        if re.fullmatch(r"PR\.\d{2}", cells[0]):
            amount = parse_amount(cells[-1], f"{source} {cells[0]}")
            items[cells[0]] = term(amount, source, unit=cells[2], description=cells[1])
    return items


def instruments(pages: Pages) -> list[dict]:
    """Every supplement and amendment, checked against the Schedule of Variations (p.38)."""
    schedule = schedule_of_variations(pages, VARIATIONS_PAGE)
    parsed = [parse_instrument(pages, page, CODE) for page in INSTRUMENT_PAGES]
    return check_against_schedule(parsed, schedule, VARIATIONS_PAGE)


def check_against_schedule(parsed: list[dict], schedule: dict, page: int) -> list[dict]:
    """Stop if an instrument page and the Schedule of Variations disagree on a date."""
    for instrument in parsed:
        name = instrument["title"].split(" TO ")[0].replace(" ", "")
        row = next((row for key, row in schedule.items() if key.lower() == name.lower()), None)
        if row is None:
            raise ValueError(f"{instrument['title']}: not in the Schedule of Variations p.{page}")
        for field in ("issued", "effective"):
            if instrument[field]["value"] != row[field].isoformat():
                raise ValueError(
                    f"{instrument['title']}: {field} {instrument[field]['value']} on its page, "
                    f"{row[field]} in the Schedule of Variations p.{page}"
                )
        instrument["schedule_changes"] = row["changes"]
    return parsed
