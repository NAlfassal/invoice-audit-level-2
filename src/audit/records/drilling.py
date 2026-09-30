"""Daily Drilling Reports: parse the 8,151 report files into one table.

Input: drilling_services/records/*.txt (read-only). One report per well per day (Cl.15 p.5,
Sch.5 p.24) with numbered parts: A operations (every day), B BHA run, C gyro surveys,
D radioactive source, E lost in hole; signed by the Company Representative and the lead
directional driller. Output: a DataFrame with one row per report, indexed by its `Report:`
number (the reference invoice lines quote, Cl.19A p.35). Crew and tools stay in the rig's
own words; `records.drilling_terms` maps them to service codes (Appendix G p.36).
"""

from __future__ import annotations

import re
from decimal import Decimal
from functools import cache
from pathlib import Path

import pandas as pd

from audit.io import parse_dmon_date
from audit.records import signature

FIELD = re.compile(r"^(?P<name>[A-Z][^:\n]*):[ \t]*(?P<value>.*)$", re.MULTILINE)
PART = re.compile(r"^PART (?P<part>[A-E]) ", re.MULTILINE)
CREW_ENTRY = re.compile(r"^(?P<count>\d+) (?P<term>.+)$")
REPRESENTATIVE = "Signed (Company Representative)"
DRILLER = "Signed (lead directional driller)"
NUMBER_FIELDS = {
    "depth_start": "Depth start (m MD)",
    "depth_end": "Depth end (m MD)",
    "circulating_hours": "Circulating hours",
    "gyro_surveys": "Gyro surveys",
    "pressure_points": "Pressure points",
    "wiper_trips": "Wiper trips",
    "back_reaming_hours": "Back-reaming hours",
    "clean_out_runs": "Clean-out runs",
    "bha_run": "BHA run",
    "run": "Run",
    "metres_logged": "Metres logged",
    "metres_reamed": "Metres reamed",
    "lost_hours": "Circulating hours accumulated on the well",
}


def number(fields: dict[str, str], name: str, path: Path) -> Decimal | None:
    """Return a numeric field as Decimal (None when absent); stop if it is not a number."""
    value = fields.get(name)
    if value is None:
        return None
    try:
        return Decimal(value)
    except ArithmeticError as exc:
        raise ValueError(f"{path}: {name} {value!r} is not a number") from exc


def day(fields: dict[str, str], name: str, path: Path) -> object:
    """Return a DD-Mon-YYYY field as a date (None when absent); stop if unreadable."""
    value = fields.get(name)
    if not value:
        return None
    parsed = parse_dmon_date(value)
    if parsed is None:
        raise ValueError(f"{path}: {name} {value!r} is not DD-Mon-YYYY")
    return parsed


def terms(value: str | None) -> tuple[str, ...]:
    """Split a comma-separated list of rig words ("MWD collar, drilling jars")."""
    return tuple(part.strip() for part in (value or "").split(",") if part.strip())


def crew(value: str | None, path: Path) -> dict[str, int]:
    """Read "2 directional hands, 1 night man" into {term: count}."""
    counts = {}
    for entry in terms(value):
        match = CREW_ENTRY.match(entry)
        if match is None:
            raise ValueError(f"{path}: crew entry {entry!r} is not '<count> <role>'")
        counts[match["term"]] = int(match["count"])
    return counts


def parse_report(path: Path) -> dict:
    """Parse one Daily Drilling Report into a row of the reports table."""
    text = path.read_text(encoding="utf-8")
    fields = {m["name"]: m["value"].strip() for m in FIELD.finditer(text)}
    row = {
        "report": fields.get("Report", ""),
        "file": path.name,
        "well": fields.get("Well", ""),
        "date": day(fields, "Date", path),
        "hole_section": fields.get("Hole section", ""),
        "status": fields.get("Status", ""),
        "in_hole": terms(fields.get("In the hole")),
        "crew": crew(fields.get("Crew on tour"), path),
        "run_first_day": day(fields, "Run first day", path),
        "run_last_day": day(fields, "Run last day", path),
        "run_tools": terms(fields.get("Tools in run")),
        "source_carried": fields.get("Radioactive source carried", ""),
        "parts": "".join(PART.findall(text)),
        "lost_tool": fields.get("Lost in hole tool", ""),
        "representative": signature(fields.get(REPRESENTATIVE)),
        "driller": signature(fields.get(DRILLER)),
    }
    for column, name in NUMBER_FIELDS.items():
        row[column] = number(fields, name, path)
    if not row["report"]:
        raise ValueError(f"{path}: no Report number")
    return row


@cache
def load_reports(records_dir: Path) -> pd.DataFrame:
    """Parse every report in a folder; return one row per report, indexed by report number."""
    rows = [parse_report(path) for path in sorted(records_dir.glob("*.txt"))]
    table = pd.DataFrame(rows)
    duplicated = table["report"][table["report"].duplicated()]
    if not duplicated.empty:
        raise ValueError(f"{records_dir}: report numbers used twice: {sorted(duplicated)[:5]}")
    return table.set_index("report", drop=False)
