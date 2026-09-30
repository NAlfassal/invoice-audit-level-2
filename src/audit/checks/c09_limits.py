"""Guideline check 9: limits hold (caps, exclusion windows, once-only items, minimum charges).

Reads invoice lines and headers and the limits in the contract JSON; returns
`limit_exceeded` findings. Lines already rejected by an earlier check are not measured, so
they neither use up a cap nor exclude another item (Cl.31: "no more than that quantity is
measurable"). Where several lines share a cap, the quantity is kept in the order submitted
(submission date, invoice number, line number) and the later lines lose the excess.

Civil: daily limits per item, work area and day (Cl.31 p.6, Sch.4 Pt4 p.25); an excluded item
within the stated days after its excluding item on the same work area (Cl.32 p.6, Sch.4 Pt5
p.26, P19 p.13); traffic management on a work area and day with surfacing (P21 p.13).
Drilling: daily limits per well and day (Cl.22 p.6, Sch.3 Pt5 pp.21-22); once-per-well
services (Cl.27 p.7, Sch.3 Pt6 p.22); the DD-120 minimum hours (Cl.21 p.6, Sch.3 Pt7 p.22,
P10); services not chargeable on a Standby day (Cl.20, Sch.3 Pt3) and services charged only
on one (Sch.3 Pt4 p.21); charges for a run or a well on the day Cl.26-27 p.7 names, from
the Daily Drilling Reports.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable, Iterator
from decimal import Decimal

import pandas as pd

from audit import linker
from audit.checks import CONFIDENCE, Finding
from audit.checks.c10_duplicates import exact_copies
from audit.contract import load_contract, round_civil, round_drilling, term
from audit.io import AuditData, to_cents

CHECK_ID = "c09"
CATEGORY = "limit_exceeded"
DISCOUNT_CODE = "DS-900"
STANDBY = "Standby"
OPERATING = "Operating"
NOT_CHARGEABLE = "not chargeable"

Cap = Callable[[object], tuple[Decimal, dict] | None]


def run(data: AuditData, rejected: frozenset[str] = frozenset()) -> list[Finding]:
    """Return every limit finding of both contracts (see module docstring)."""
    rejected = rejected | exact_copies(data)
    civil = measured(
        data.civil_lines, data.civil_apps, "application_no", "application_date", rejected
    )
    services = data.drill_lines[data.drill_lines["service_code"] != DISCOUNT_CODE]
    drill = measured(services, data.drill_invoices, "invoice_no", "invoice_date", rejected)
    found = (
        civil_daily_limits(civil)
        + civil_exclusions(civil)
        + traffic_with_surfacing(civil)
        + drilling_daily_limits(drill)
        + once_per_well(drill)
        + minimum_hours(drill)
        + standby_rules(drill)
        + run_and_well_days(data, drill)
    )
    return first_per_line(found)


def first_per_line(findings: list[Finding]) -> list[Finding]:
    """Keep the first limit finding on each line: a line is judged once per check."""
    seen: set[str] = set()
    kept = []
    for found in findings:
        if found.line_ref and found.line_ref in seen:
            continue
        seen.add(found.line_ref)
        kept.append(found)
    return kept


# ---- shared helpers ----------------------------------------------------------------------


def measured(
    lines: pd.DataFrame, headers: pd.DataFrame, id_col: str, date_col: str, rejected: frozenset[str]
) -> pd.DataFrame:
    """Return the lines not rejected, with their submission date, in the order submitted.

    `rejected` also holds the exact copies c10 disallows, so a copy does not use up a limit.
    """
    kept = lines[~lines["line_ref"].isin(rejected)]
    dated = kept.merge(headers[[id_col, date_col]], on=id_col, how="left", validate="many_to_one")
    dated = dated.rename(columns={date_col: "submitted"})
    dated["line_number"] = dated["line_no"].astype(int)
    return dated.sort_values(["submitted", id_col, "line_number"], kind="stable")


def confidence_of(entry: dict) -> float:
    """Return the limit confidence, capped while the limit value is not verified (§7)."""
    return CONFIDENCE["limit" if entry.get("verified") else "limit_unverified"]


def over_cap(
    lines: pd.DataFrame, keys: list[str], cap_of: Cap
) -> Iterator[tuple[object, Decimal, dict]]:
    """Yield (line, quantity kept, limit entry) for each line that runs past its group's cap."""
    used: dict[tuple, Decimal] = defaultdict(Decimal)
    for line in lines.itertuples(index=False):
        found = cap_of(line)
        if found is None:
            continue
        cap, entry = found
        key = tuple(getattr(line, column) for column in keys)
        kept = max(Decimal(0), min(line.quantity, cap - used[key]))
        used[key] += line.quantity
        if kept < line.quantity:
            yield line, kept, entry


def finding(
    line: object, id_col: str, expected: Decimal, clause: str, evidence: str, confidence: float
) -> Finding:
    """Build a limit finding for one line, from its expected amount."""
    return Finding(
        getattr(line, id_col),
        line.line_ref,
        CHECK_ID,
        CATEGORY,
        to_cents(expected - line.amount),
        clause,
        evidence,
        confidence,
    )


# ---- civil -------------------------------------------------------------------------------


def civil_daily_limits(lines: pd.DataFrame) -> list[Finding]:
    """Cap each item per work area per day; the excess is not payable (Cl.31, Sch.4 Pt4)."""
    limits = load_contract("civil")["daily_limits"]

    def cap_of(line: object) -> tuple[Decimal, dict] | None:
        entry = limits.get(line.item_code)
        if entry is None or entry["unit"] != line.unit:
            return None  # a line in another unit is rejected by c06, not capped here
        return Decimal(entry["value"]), entry

    findings = []
    for line, kept, entry in over_cap(lines, ["item_code", "site", "work_date"], cap_of):
        expected = round_civil(kept * line.rate_applied)
        evidence = (
            f"{line.item_code} on {line.site} {line.work_date}: "
            f"limit {entry['value']} {entry['unit']} "
            f"a day, {kept} of {line.quantity} within it"
        )
        clause = f"p.6 Cl.31; {entry['source']}"
        findings.append(
            finding(line, "application_no", expected, clause, evidence, confidence_of(entry))
        )
    return findings


def civil_exclusions(lines: pd.DataFrame) -> list[Finding]:
    """Reject an excluded item measured within the stated days of its excluding item (Cl.32).

    Sch.4 Pt5 p.26: "not measurable within the stated period following measurement of the
    item in the second column on the same work area". The same day counts as inside the
    window (D27); no source settles it, so a same-day finding carries a moderate confidence.
    """
    findings = []
    for excluded, entry in load_contract("civil")["exclusions"].items():
        days = int(entry["value"])
        excluding = lines[lines["item_code"] == entry["excluded_by"]]
        clause = f"p.6 Cl.32; {entry['source']}; p.13 P19"
        for line in lines[lines["item_code"] == excluded].itertuples(index=False):
            same_area = excluding[excluding["site"] == line.site]
            gaps = [(line.work_date - day).days for day in same_area["work_date"]]
            inside = [gap for gap in gaps if 0 <= gap <= days]
            if not inside:
                continue
            gap = min(inside)
            if gap == 0:
                when, confidence = "the same day as", CONFIDENCE["exclusion_same_day"]
            else:
                when, confidence = f"{gap} day(s) after", confidence_of(entry)
            evidence = f"{excluded} measured {when} {entry['excluded_by']} on {line.site}"
            findings.append(
                finding(line, "application_no", Decimal("0.00"), clause, evidence, confidence)
            )
    return findings


def traffic_with_surfacing(lines: pd.DataFrame) -> list[Finding]:
    """Reject traffic management on a work area and day with surfacing measured (P21 p.13)."""
    traffic = term("civil", "traffic_management_item")
    surfacing = term("civil", "surfacing_items")
    surfacing_lines = lines[lines["item_code"].isin(surfacing.value)]
    surfaced = set(zip(surfacing_lines["site"], surfacing_lines["work_date"], strict=True))
    findings = []
    for line in lines[lines["item_code"] == traffic.value].itertuples(index=False):
        if (line.site, line.work_date) in surfaced:
            evidence = (
                f"{traffic.value} on {line.site} {line.work_date}, a day with surfacing measured"
            )
            findings.append(
                finding(
                    line,
                    "application_no",
                    Decimal("0.00"),
                    surfacing.source,
                    evidence,
                    CONFIDENCE["limit"],
                )
            )
    return findings


# ---- drilling ----------------------------------------------------------------------------


def drilling_daily_limits(lines: pd.DataFrame) -> list[Finding]:
    """Cap each service per well per day (Cl.22 p.6, Sch.3 Pt5)."""
    limits = load_contract("drilling")["daily_limits"]

    def cap_of(line: object) -> tuple[Decimal, dict] | None:
        entry = limits.get(line.service_code)
        return None if entry is None else (Decimal(entry["value"]), entry)

    findings = []
    for line, kept, entry in over_cap(lines, ["service_code", "well_name", "service_date"], cap_of):
        expected = round_drilling(kept * line.unit_rate)
        evidence = (
            f"{line.service_code} on {line.well_name} {line.service_date}: "
            f"limit {entry['value']} a day, {kept} of {line.quantity} within it"
        )
        findings.append(
            finding(
                line,
                "invoice_no",
                expected,
                f"p.6 Cl.22; {entry['source']}",
                evidence,
                confidence_of(entry),
            )
        )
    return findings


def once_per_well(lines: pd.DataFrame) -> list[Finding]:
    """Allow a once-per-well service once on each well (Cl.27 p.7, Sch.3 Pt6 p.22)."""
    entry = load_contract("drilling")["once_per_well"]
    codes = set(entry["value"])

    def cap_of(line: object) -> tuple[Decimal, dict] | None:
        return (Decimal(1), entry) if line.service_code in codes else None

    findings = []
    for line, kept, _ in over_cap(lines, ["service_code", "well_name"], cap_of):
        expected = round_drilling(kept * line.unit_rate)
        evidence = (
            f"{line.service_code} is charged once per well; already charged on {line.well_name}"
        )
        findings.append(
            finding(
                line,
                "invoice_no",
                expected,
                f"p.7 Cl.27; {entry['source']}",
                evidence,
                confidence_of(entry),
            )
        )
    return findings


def minimum_hours(lines: pd.DataFrame) -> list[Finding]:
    """Raise an hourly charge below its minimum on an Operating day (Cl.21 p.6, P10)."""
    findings = []
    for code, entry in load_contract("drilling")["minimum_hours"].items():
        minimum = Decimal(entry["value"])
        short = lines[(lines["service_code"] == code) & (lines["day_status"] == OPERATING)]
        for line in short[short["quantity"] < minimum].itertuples(index=False):
            expected = round_drilling(minimum * line.unit_rate)
            evidence = f"{code} billed {line.quantity} h on an Operating day; minimum {minimum} h"
            findings.append(
                finding(
                    line,
                    "invoice_no",
                    expected,
                    f"p.6 Cl.21; {entry['source']}",
                    evidence,
                    confidence_of(entry),
                )
            )
    return findings


def standby_rules(lines: pd.DataFrame) -> list[Finding]:
    """Reject services not chargeable on a Standby day, and Standby-only services on others.

    Cl.20 p.6: "A service Schedule 3 Part 3 marks as not chargeable is not charged on a
    Standby day in any quantity." Sch.3 Pt4 p.21: DD-121 is charged only on a Standby day.
    """
    standby = load_contract("drilling")["standby"]
    standby_only = term("drilling", "standby_only_items")
    findings = []
    for line in lines.itertuples(index=False):
        entry = standby.get(line.service_code)
        if line.day_status == STANDBY and entry is not None and entry["value"] == NOT_CHARGEABLE:
            evidence = f"{line.service_code} charged on a Standby day; Sch.3 Pt3: not chargeable"
            findings.append(
                finding(
                    line,
                    "invoice_no",
                    Decimal("0.00"),
                    f"p.6 Cl.20; {entry['source']}",
                    evidence,
                    confidence_of(entry),
                )
            )
        elif line.day_status != STANDBY and line.service_code in standby_only.value:
            evidence = (
                f"{line.service_code} charged on a day recorded as {line.day_status}; "
                "charged only on a Standby day"
            )
            findings.append(
                finding(
                    line,
                    "invoice_no",
                    Decimal("0.00"),
                    standby_only.source,
                    evidence,
                    CONFIDENCE["limit"],
                )
            )
    return findings


# ---- charges on a named day of the run or the well (Cl.26-27) ---------------------------

LWD_PREFIX = "LW-"  # Series 400, Logging While Drilling (Schedule 1 p.15)


def lwd_wells(data: AuditData) -> set[str]:
    """Return the wells on which a report records a logging-while-drilling tool in the hole."""
    services = linker.services()
    lwd_terms = {
        service["term"]
        for code, service in services.items()
        if code.startswith(LWD_PREFIX) and service.get("basis") == "metres_with_tool"
    }
    reports = linker.reports_of(data)
    logged = reports[reports["in_hole"].map(lambda tools: bool(lwd_terms & set(tools)))]
    return set(logged["well"])


def day_problem(
    code: str, service: dict, report: pd.Series, well_days: tuple, lwd: set[str]
) -> str | None:
    """Return why a run or well charge is not on the day Cl.26-27 names, or None."""
    basis, first_day, last_day = service.get("basis"), well_days[0], well_days[1]
    if basis == "run_last_day":
        if report["date"] != report["run_last_day"]:
            ends = report["run_last_day"]
            return f"{code} charged on {report['date']}; run {report['run']} ends {ends}"
        if service["term"] not in report["run_tools"]:
            return f"{code} charged for run {report['run']}, which carries no {service['term']}"
    if basis == "run_first_day" and report["date"] != report["run_first_day"]:
        starts = report["run_first_day"]
        return f"{code} charged on {report['date']}; run {report['run']} starts {starts}"
    if basis == "well_first_day" and report["date"] != first_day:
        return f"{code} charged on {report['date']}; first day on the well is {first_day}"
    if basis == "well_last_day":
        if report["date"] != last_day:
            return f"{code} charged on {report['date']}; last day on the well is {last_day}"
        if code.startswith(LWD_PREFIX) and report["well"] not in lwd:
            return f"{code} charged on a well where no logging while drilling was run"
    return None


def run_and_well_days(data: AuditData, lines: pd.DataFrame) -> list[Finding]:
    """Reject run and well charges not on the day the contract names (Cl.26-27 p.7)."""
    services = linker.services()
    bases = {"run_last_day", "run_first_day", "well_first_day", "well_last_day"}
    reports = linker.reports_of(data)
    well_days = reports.groupby("well")["date"].agg(["min", "max"])
    lwd = lwd_wells(data)
    findings = []
    for line in lines.itertuples(index=False):
        service = services.get(line.service_code, {})
        report = linker.report_for(data, line.report_ref)
        if service.get("basis") not in bases or report is None:
            continue
        days = tuple(well_days.loc[report["well"]])
        problem = day_problem(line.service_code, service, report, days, lwd)
        if problem:
            findings.append(
                finding(
                    line,
                    "invoice_no",
                    Decimal("0.00"),
                    service["source"],
                    problem,
                    CONFIDENCE["limit"],
                )
            )
    return findings
