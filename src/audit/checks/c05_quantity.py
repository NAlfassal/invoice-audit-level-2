"""Guideline check 5: the quantities are the recorded ones.

Reads invoice lines and their records (`linker`); returns `quantity_over_record` for each
line billed above what its record supports. The payable quantity is the recorded one, so
the expected amount is that quantity at the billed rate (a wrong rate is c07/c08's). A line
billed below its record is not an error. Lines without a valid record are c04's.

- Civil: the quantity the record's work line states (`records.phrases`), less the first
  hour for an hourly item (Cl.6A p.32); a week with fewer than five days is not measurable
  (Cl.47A p.33). A joint-survey item up to 2% above the survey is payable as measured,
  above that at the surveyed quantity (Cl.33A p.32).
- Drilling: persons, days in the hole, hours less the first (Cl.21A, D23), counts and metres
  from the Daily Drilling Report (Cl.22-30, Schedule 8). Metres up to 1% above the report
  are payable as charged (Cl.25A p.35). PD-210 metres are the interval charged, which must
  lie inside the day's depths (Cl.23 p.6).
"""

from __future__ import annotations

from collections.abc import Callable
from decimal import Decimal

from audit import linker
from audit.checks import CONFIDENCE, Finding
from audit.contract import load_contract, round_civil, round_drilling, term
from audit.io import AuditData, to_cents
from audit.pricing import HUNDRED

CHECK_ID = "c05"
CATEGORY = "quantity_over_record"
DISCOUNT_CODE = "DS-900"
FOOTAGE_CODE = "PD-210"
METRE_BASES = {"metres_with_tool", "metres_drilled"}
OPERATING = "Operating"


def run(data: AuditData, rejected: frozenset[str] = frozenset()) -> list[Finding]:
    """Return the lines of both contracts billed above their record."""
    return civil_findings(data, rejected) + drilling_findings(data, rejected)


def within(billed: Decimal, recorded: Decimal, tolerance_pct: Decimal) -> bool:
    """Tell whether a billed quantity is at most `tolerance_pct` per cent above the record."""
    return billed <= recorded * (HUNDRED + tolerance_pct) / HUNDRED


def over(
    invoice_id: str,
    line: object,
    payable: Decimal,
    rate: Decimal,
    rounding: Callable[[Decimal], Decimal],
    clause: str,
    evidence: str,
) -> Finding:
    """Build a finding that pays a line at its recorded quantity."""
    expected = rounding(payable * rate)
    return Finding(
        invoice_id,
        line.line_ref,
        CHECK_ID,
        CATEGORY,
        to_cents(expected - line.amount),
        clause,
        evidence,
        CONFIDENCE["quantity_over_record"],
    )


def civil_findings(data: AuditData, rejected: frozenset[str]) -> list[Finding]:
    """Compare each civil line that cites a record with the quantity the record supports."""
    surveyed = set(load_contract("civil")["surveyed_items"]["value"])
    tolerance = term("civil", "survey_tolerance_pct").value
    findings = []
    for line in data.civil_lines.itertuples(index=False):
        record = linker.record_for(data, line.record_ref.strip())
        if record is None or line.line_ref in rejected:
            continue
        reading = linker.civil_reading(record)
        if reading.item != line.item_code:
            continue  # a record of another item is c06's
        payable = linker.civil_payable_quantity(record, reading)
        if line.quantity <= payable:
            continue
        if line.item_code in surveyed and within(line.quantity, payable, tolerance):
            continue  # Cl.33A: within the survey tolerance, payable as measured
        evidence = (
            f"{line.item_code} billed {line.quantity} {line.unit}; "
            f"{record.name} supports {payable} "
            f"({record['work_text']!r})"
        )
        clause = "p.8 Cl.46; p.32 Cl.6A, Cl.33A, Cl.47A"
        findings.append(
            over(
                line.application_no, line, payable, line.rate_applied, round_civil, clause, evidence
            )
        )
    return findings


def with_minimum(code: str, report: object, supported: Decimal | None) -> Decimal | None:
    """Raise report hours to the Cl.21 minimum on an Operating day with the tool in the hole.

    Cl.21 p.6 and P10 p.11: at least 6 hours on each such day. The minimum is applied to the
    chargeable hours, after the Cl.21A deduction (D24, reading (a); no billed line is below
    7 hours).
    """
    contract = load_contract("drilling")
    minimum = contract["minimum_hours"].get(code)
    if supported is None or minimum is None:
        return supported
    tool = contract["report_terms"][code]["value"]
    if report["status"] != OPERATING or tool not in report["in_hole"]:
        return supported
    return max(supported, Decimal(minimum["value"]))


def drilling_findings(data: AuditData, rejected: frozenset[str]) -> list[Finding]:
    """Compare each daily drilling charge with the quantity its report supports."""
    tolerance = term("drilling", "metres_tolerance_pct").value
    services = linker.services()
    findings = []
    lines = data.drill_lines[data.drill_lines["service_code"] != DISCOUNT_CODE]
    for line in lines.itertuples(index=False):
        report = linker.report_for(data, line.report_ref)
        if report is None or line.line_ref in rejected:
            continue
        basis = services.get(line.service_code, {}).get("basis")
        if line.service_code == FOOTAGE_CODE:
            inside = (
                report["depth_start"] <= line.depth_from_m
                and line.depth_to_m <= report["depth_end"]
            )
            supported = line.depth_to_m - line.depth_from_m if inside else Decimal(0)
        else:
            supported = linker.report_quantity(line.service_code, report)
            supported = with_minimum(line.service_code, report, supported)
        if supported is None or line.quantity <= supported:
            continue
        if basis in METRE_BASES and within(line.quantity, supported, tolerance):
            continue  # Cl.25A: up to 1% above the report is payable as charged
        evidence = (
            f"{line.service_code} billed {line.quantity} {line.unit}; "
            f"{line.report_ref} supports {supported}"
        )
        clause = f"{services[line.service_code]['source']}"
        findings.append(
            over(line.invoice_no, line, supported, line.unit_rate, round_drilling, clause, evidence)
        )
    return findings
