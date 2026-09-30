"""Build the drilling contract (DDS-2025-118) JSON from its corrected OCR pages.

Input: `Pages` for "drilling". Output: a dict of schedules and instruments, every value a
`term` with its page and schedule. Page numbers below are where each schedule sits in the
42-page scan.
"""

from __future__ import annotations

import re

from audit.extract.civil import check_against_schedule
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

CODE = re.compile(r"[A-Z]{2}-\d{3}")
HOLE_SECTION = re.compile(r'\d+(?:-\d/\d)?"')
WELL_CLASS = re.compile(r"Standard|Extended Reach|HPHT")
DEPTH_RANGE = re.compile(r"(?:over )?([\d,]+) m to ([\d,]+) m|over ([\d,]+) m")
METRES_RANGE = re.compile(r"([\d,]+) m to ([\d,]+) m|above ([\d,]+) m")
DDR_PART = re.compile(r"Part ([A-E])$")
MINIMUM_HOURS = re.compile(r"(DD-\d{3}): not less than (\d+) hours")
RATE_BEFORE_UNIT = 2  # Schedule 2C prints "code | description | base rate | unit"

SCHEDULE_1_PAGES = (15, 16)
DEPTH_BANDS_PAGE, INDEXED_PAGE, SAR_VALUES_PAGE = 17, 18, 19
FACTORS_PAGES, LIMITS_PAGES, DDR_PAGE, LOST_IN_HOLE_PAGE = (20, 21), (21, 22), 24, 25
APPENDIX_G_PAGE, VARIATIONS_PAGE, INSTRUMENT_PAGES = 36, 37, (38, 39, 40, 41, 42)


def drilling_contract(pages: Pages) -> dict:
    """Every schedule and instrument of the drilling contract that pricing or checks use."""
    factors_text = pages.text(FACTORS_PAGES[0])
    return {
        "contract_ref": "DDS-2025-118",
        "items": schedule_1(pages),
        "depth_bands": depth_bands(pages),
        "contract_year_bands": contract_year_bands(pages),
        "indexed": indexed(pages),
        "section_factors": {
            "factors": factor_table(
                section(factors_text, "Part 1", "Part 2"), HOLE_SECTION, "p.20 Schedule 3 Part 1"
            ),
            "items": term(
                codes_in(section(factors_text, "Section-rated services", "## Part 2"), CODE),
                "p.20 Schedule 3 Part 1",
            ),
        },
        "class_factors": {
            "factors": factor_table(
                section(factors_text, "## Part 2", "## Part 3"),
                WELL_CLASS,
                "p.20 Schedule 3 Part 2",
            ),
            "items": term(
                codes_in(section(factors_text, "Class-rated services", "## Part 3"), CODE),
                "p.20 Schedule 3 Part 2",
            ),
        },
        "standby": standby(pages),
        "daily_limits": daily_limits(pages),
        "once_per_well": term(
            codes_in(section(pages.text(22), "## Part 6", "## Part 7"), CODE),
            "p.22 Schedule 3 Part 6",
        ),
        "minimum_hours": minimum_hours(pages),
        "ddr_parts": ddr_parts(pages),
        "lost_in_hole": lost_in_hole(pages),
        "report_terms": report_terms(pages),
        "instruments": instruments(pages),
    }


def schedule_1(pages: Pages) -> dict[str, dict]:
    """Service -> description, unit and rate (Schedule 1, pp.15-16)."""
    items: dict[str, dict] = {}
    for page in SCHEDULE_1_PAGES:
        items.update(schedule_rows(pages.text(page), CODE, f"p.{page} Schedule 1"))
    return items


def _range(match: re.Match[str], where: str) -> tuple:
    """(lower, upper) from a matched 'a to b' / 'over a' / 'above a'; upper None if open."""
    low, high, open_low = match.groups()
    if open_low:
        return parse_amount(open_low, where), None
    return parse_amount(low, where), parse_amount(high, where)


def depth_bands(pages: Pages) -> list[dict]:
    """PD-210 rate per measured-depth band (Schedule 2).

    Cl.23: a boundary depth belongs to the shallower band, so 'over a to b' includes b.
    """
    text = section(pages.text(DEPTH_BANDS_PAGE), "| Band", "## Part 2")
    source = f"p.{DEPTH_BANDS_PAGE} Schedule 2"
    bands = []
    for cells in table_rows(text)[1:]:
        where = f"{source} {cells[0]}"
        match = DEPTH_RANGE.fullmatch(cells[1])
        if not match:
            raise ValueError(f"{where}: depth range {cells[1]!r} not understood")
        lower, upper = _range(match, where)
        rate = parse_amount(cells[2], where)
        bands.append(term(rate, source, band=cells[0], over_m=lower, to_m=upper))
    return bands


def contract_year_bands(pages: Pages) -> list[dict]:
    """PD-210 % of rate by metres already drilled on the well in the Contract Year."""
    text = section(pages.text(DEPTH_BANDS_PAGE), "## Part 2")
    source = f"p.{DEPTH_BANDS_PAGE} Schedule 2 Part 2"
    bands = []
    for cells in table_rows(text)[1:]:
        where = f"{source} {cells[0]}"
        match = METRES_RANGE.fullmatch(cells[1])
        if not match:
            raise ValueError(f"{where}: metres range {cells[1]!r} not understood")
        lower, upper = _range(match, where)
        if match.group(3):
            lower += 1  # "above 120,000 m" starts at the next metre
        percent = parse_percent(cells[2], where)
        bands.append(term(percent, source, band=cells[0], from_m=lower, to_m=upper))
    return bands


def indexed(pages: Pages) -> dict:
    """Schedule 2C services and the Rig Services Index by month (Cl.17A)."""
    text = pages.text(INDEXED_PAGE)
    source = f"p.{INDEXED_PAGE} Schedule 2C"
    items = section(text, "| Code", "Rig Services Index, as published")
    index = section(text, "Rig Services Index, as published")
    return {
        "items": rate_table(items, CODE, source, rate_column=RATE_BEFORE_UNIT),
        "index": term(month_table(index, source), source),
    }


def standby(pages: Pages) -> dict[str, dict]:
    """Service -> % of the operating rate on a Standby day, or 'not chargeable' (Cl.20)."""
    text = section(pages.text(FACTORS_PAGES[0]), "## Part 3") + section(
        pages.text(FACTORS_PAGES[1]), "|", "## Part 4"
    )
    return percent_table(text, CODE, "pp.20-21 Schedule 3 Part 3")


def daily_limits(pages: Pages) -> dict[str, dict]:
    """Service -> maximum quantity per day (Schedule 3 Part 5, Cl.22)."""
    text = section(pages.text(LIMITS_PAGES[0]), "## Part 5") + section(
        pages.text(LIMITS_PAGES[1]), "|", "## Part 6"
    )
    return limit_table(text, CODE, "pp.21-22 Schedule 3 Part 5")


def minimum_hours(pages: Pages) -> dict[str, dict]:
    """Service -> minimum hours on an Operating day (Schedule 3 Part 7, Cl.21)."""
    source = "p.22 Schedule 3 Part 7"
    found = MINIMUM_HOURS.findall(section(pages.text(22), "## Part 7"))
    if not found:
        raise ValueError(f"{source}: no 'not less than N hours' line")
    return {code: term(parse_amount(hours, source), source) for code, hours in found}


def ddr_parts(pages: Pages) -> dict[str, dict]:
    """Service -> Daily Drilling Report part required before payment (Schedule 5, Cl.37)."""
    source = f"p.{DDR_PAGE} Schedule 5"
    parts = {}
    for cells in rows_starting_with(pages.text(DDR_PAGE), CODE):
        match = DDR_PART.search(cells[-1])
        if not match:
            raise ValueError(f"{source} {cells[0]}: {cells[-1]!r} names no report part")
        parts[cells[0]] = term(match.group(1), source)
    return parts


def lost_in_hole(pages: Pages) -> dict:
    """Read replacement values in USD (Sch.6) and in SAR with the exchange rate (Sch.2D).

    Cl.31A p.35: Schedule 2D governs; Schedule 6 is the USD value as the contract was let.
    """
    sar_text = pages.text(SAR_VALUES_PAGE)
    source_2d = f"p.{SAR_VALUES_PAGE} Schedule 2D"
    exchange = month_table(section(sar_text, "Rate of exchange"), source_2d)
    return {
        "usd_values": rate_table(
            pages.text(LOST_IN_HOLE_PAGE), CODE, f"p.{LOST_IN_HOLE_PAGE} Schedule 6"
        ),
        "sar_values": rate_table(section(sar_text, "| Code", "Rate of exchange"), CODE, source_2d),
        "halalas_per_usd": term(exchange, source_2d),
    }


def report_terms(pages: Pages) -> dict[str, dict]:
    """Service -> the words the Daily Drilling Report uses for it (Appendix G, Cl.19A)."""
    source = f"p.{APPENDIX_G_PAGE} Appendix G"
    return {
        cells[0]: term(cells[-1], source)
        for cells in rows_starting_with(pages.text(APPENDIX_G_PAGE), CODE)
    }


def instruments(pages: Pages) -> list[dict]:
    """Every supplement and amendment, checked against the Schedule of Variations (p.37)."""
    schedule = schedule_of_variations(pages, VARIATIONS_PAGE)
    parsed = [parse_instrument(pages, page, CODE) for page in INSTRUMENT_PAGES]
    return check_against_schedule(parsed, schedule, VARIATIONS_PAGE)
