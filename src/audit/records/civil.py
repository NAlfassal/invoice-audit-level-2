"""Civil site records: parse the 2,169 record files into one table.

Input: civilwork/records/*.txt (read-only). Each record has a title, `Ticket`, `Job`, `Area`,
`Date` (DD/MM/YYYY) or, for a weekly log, `Week beginning` and `Days on`, an optional
`Ground`, one free-text work line and two signatures (Cl.47 p.8, Cl.47A p.33). Output: a
DataFrame with one row per record: ticket, series, area, date, week_beginning, days_on,
ground, work_text, foreman, engineer_rep. The work line is matched to an item by
`records.phrases`.
"""

from __future__ import annotations

import re
from datetime import date, timedelta
from functools import cache
from pathlib import Path

import pandas as pd

from audit.io import parse_record_date
from audit.records import signature

FIELD = re.compile(r"^(?P<name>[A-Z][^:\n]*):[ \t]*(?P<value>.*)$", re.MULTILINE)
FOREMAN = "Signed (foreman)"
ENGINEER = "Countersigned (Engineer's representative)"
WEEK_DAYS = 7
COLUMNS = [
    "ticket",
    "series",
    "area",
    "date",
    "week_beginning",
    "days_on",
    "ground",
    "work_text",
    "foreman",
    "engineer_rep",
]


def fields_of(text: str) -> dict[str, str]:
    """Return the `Name: value` fields of a record, values stripped."""
    return {m["name"]: m["value"].strip() for m in FIELD.finditer(text)}


def work_line(text: str, path: Path) -> str:
    """Return the free-text work line: the first line after the header block's blank line."""
    lines = text.splitlines()
    try:
        start = lines.index("")
    except ValueError as exc:
        raise ValueError(f"{path}: no blank line after the record header") from exc
    for line in lines[start + 1 :]:
        if line.strip():
            return line.strip()
    raise ValueError(f"{path}: no work line")


def parse_date(value: str | None, path: Path, name: str) -> date | None:
    """Parse a DD/MM/YYYY record date; stop with the file name if it cannot be read."""
    if not value:
        return None
    parsed = parse_record_date(value)
    if parsed is None:
        raise ValueError(f"{path}: {name} {value!r} is not DD/MM/YYYY")
    return parsed


def parse_record(path: Path) -> dict:
    """Parse one civil record file into a row of the records table."""
    text = path.read_text(encoding="utf-8")
    fields = fields_of(text)
    ticket = fields.get("Ticket", "")
    if ticket != path.stem:
        raise ValueError(f"{path}: Ticket {ticket!r} does not match the file name")
    days_on = fields.get("Days on", "")
    return {
        "ticket": ticket,
        "series": ticket.split("-")[0],
        "area": fields.get("Area", ""),
        "date": parse_date(fields.get("Date"), path, "Date"),
        "week_beginning": parse_date(fields.get("Week beginning"), path, "Week beginning"),
        "days_on": len([day for day in days_on.split(",") if day.strip()]) if days_on else None,
        "ground": fields.get("Ground", "").split(" ")[0],
        "work_text": work_line(text, path),
        "foreman": signature(fields.get(FOREMAN)),
        "engineer_rep": signature(fields.get(ENGINEER)),
    }


@cache
def load_records(records_dir: Path) -> pd.DataFrame:
    """Parse every civil record in a folder; return one row per record, indexed by ticket."""
    rows = [parse_record(path) for path in sorted(records_dir.glob("*.txt"))]
    table = pd.DataFrame(rows, columns=COLUMNS).astype({"days_on": "Int64"})
    return table.set_index("ticket", drop=False)


def covers(record: pd.Series, work_date: date) -> bool:
    """Tell whether a record is for the work date: its date, or a day of its week."""
    if record["week_beginning"] is not None:
        start = record["week_beginning"]
        return start <= work_date < start + timedelta(days=WEEK_DAYS)
    return record["date"] == work_date
