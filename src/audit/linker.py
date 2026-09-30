"""Invoice line <-> site record <-> contract item (Phase 4).

Input: the loaded invoices (`io.AuditData`), the parsed records (`records.civil`,
`records.drilling`) and the two reviewed mappings in extracted/mappings/. Output: for each
line, its record, whether the record is for that line's work area (or well) and day, and
the quantity the record supports for the billed item. Every template maps to one item, so
no link is ambiguous (D20 would apply if one were).
"""

from __future__ import annotations

import json
from decimal import Decimal
from functools import cache

import pandas as pd

from audit.config import MAPPINGS_DIR
from audit.contract import term
from audit.io import AuditData
from audit.records import civil as civil_records
from audit.records import drilling as drilling_records
from audit.records.phrases import Reading, read_work_line

SERVICES_FILE = MAPPINGS_DIR / "drilling_terms.json"
HOUR = "hour"
OPERATING = "Operating"


# ---- civil -------------------------------------------------------------------------------


@cache
def civil_records_of(data: AuditData) -> pd.DataFrame:
    """Return the parsed civil records, indexed by ticket."""
    return civil_records.load_records(data.paths.civil_records_dir)


def record_for(data: AuditData, record_ref: str) -> pd.Series | None:
    """Return the civil record a line cites, or None if there is no such file."""
    records = civil_records_of(data)
    return records.loc[record_ref] if record_ref in records.index else None


def civil_mismatch(line: object, record: pd.Series) -> str | None:
    """Describe how a record is not for its line's work area and day, or return None."""
    if record["area"] != line.site:
        return f"{record['ticket']} is for {record['area']}, the line for {line.site}"
    if not civil_records.covers(record, line.work_date):
        when = record["week_beginning"] or record["date"]
        return f"{record['ticket']} is dated {when}, the line {line.work_date}"
    return None


def civil_reading(record: pd.Series) -> Reading:
    """Return the item and quantity a civil record states; stop if no template matches."""
    reading = read_work_line(record["series"], record["work_text"])
    if reading is None:
        raise ValueError(f"{record['ticket']}: work line {record['work_text']!r} fits no template")
    return reading


def civil_payable_quantity(record: pd.Series, reading: Reading) -> Decimal:
    """Return the quantity a civil record makes payable for the item it states.

    Cl.6A p.32: an item measured by the hour is measured at the hours attended minus one.
    Cl.47A p.33: a weekly record is measurable only with work on at least five days.
    """
    quantity = reading.quantity
    if reading.unit == HOUR:
        quantity -= term("civil", "chargeable_hour_deduction").value
    days_on = record["days_on"]
    if not pd.isna(days_on) and days_on < term("civil", "week_min_days").value:
        return Decimal(0)
    return max(quantity, Decimal(0))


# ---- drilling ----------------------------------------------------------------------------


@cache
def reports_of(data: AuditData) -> pd.DataFrame:
    """Return the parsed Daily Drilling Reports, indexed by report number."""
    return drilling_records.load_reports(data.paths.drilling_records_dir)


@cache
def services() -> dict[str, dict]:
    """Load the reviewed service -> report mapping (extracted/mappings/drilling_terms.json)."""
    if not SERVICES_FILE.exists():
        raise FileNotFoundError(f"{SERVICES_FILE} is missing: the drilling mapping is committed")
    return json.loads(SERVICES_FILE.read_text(encoding="utf-8"))["services"]


def report_for(data: AuditData, report_ref: str) -> pd.Series | None:
    """Return the report a line cites, or None if there is no such report."""
    reports = reports_of(data)
    return reports.loc[report_ref] if report_ref in reports.index else None


def drilling_mismatch(line: object, report: pd.Series) -> str | None:
    """Describe how a report is not for its line's well and day, or return None."""
    if report["well"] != line.well_name or report["date"] != line.service_date:
        return (
            f"{report['report']} is for {report['well']} on {report['date']}, the line for "
            f"{line.well_name} on {line.service_date}"
        )
    return None


def metres_drilled(report: pd.Series) -> Decimal:
    """Return the metres drilled on the report's day, from its measured depths (Cl.23)."""
    return report["depth_end"] - report["depth_start"]


def report_quantity(code: str, report: pd.Series) -> Decimal | None:
    """Return the quantity the report supports for a daily service, or None if not daily.

    Schedule 8 pp.27-28 states what each charge is for: persons on the rig (Cl.22), a day
    with the tool in the hole (Cl.28), hours less the first (Cl.21A, D23), counts (Cl.30),
    metres drilled with the tool in the hole on an Operating day (Cl.24-25).
    """
    service = services().get(code, {})
    basis = service.get("basis")
    if basis == "crew":
        return Decimal(report["crew"].get(service["term"], 0))
    if basis == "day_in_hole":
        return Decimal(1) if service["term"] in report["in_hole"] else Decimal(0)
    if basis == "hours":
        deduction = term("drilling", "chargeable_hour_deduction").value
        return max(report[service["field"]] - deduction, Decimal(0))
    if basis == "count":
        return report[service["field"]]
    if basis == "metres_with_tool":
        in_hole = service["term"] in report["in_hole"] and report["status"] == OPERATING
        return metres_drilled(report) if in_hole else Decimal(0)
    return None
