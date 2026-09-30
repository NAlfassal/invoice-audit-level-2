"""Guideline check 8: adjustments are applied in the contract's order and rounded its way.

Reads the price differences (`pricing.compare`), the civil records and the Daily Drilling
Reports (`linker`); returns:
- one finding per line whose billed rate the build-up does not give: `discount_misapplied`
  when another discount reproduces it (civil S2 / A2 pp.41-42, drilling S2 / A2 pp.40-41),
  `rate_buildup` otherwise, including a line not split at a band limit (civil Cl.27-28 p.6
  and Sch.4 Pt3 p.24; drilling Cl.17-18 p.6);
- `rate_buildup` where a civil line's ground class differs from its DX or PT record, for
  the Schedule 3 items and work up to 27 September 2025 (Cl.5 p.3; after that Cl.27A p.32
  sets G2 whatever the record says);
- `rate_buildup` where a lost-in-hole charge is not the Schedule 2D value less depreciation
  (Cl.31 p.7, Cl.31A p.35).
"""

from __future__ import annotations

from dataclasses import replace
from decimal import Decimal

from audit import linker
from audit.checks import CONFIDENCE, Finding, unmeasured_lines
from audit.checks.c07_rate import price_findings
from audit.contract import load_contract, round_drilling, term
from audit.io import AuditData, to_cents
from audit.pricing import civil, drilling

CHECK_ID = "c08"
CATEGORIES = frozenset({"rate_buildup", "discount_misapplied"})
GROUND_CLAUSE = "p.3 Cl.5; p.23 Schedule 3; p.32 Cl.27A"
LOST_CLAUSE = "p.7 Cl.31; p.35 Cl.31A; p.19 Schedule 2D"


def run(data: AuditData, rejected: frozenset[str] = frozenset()) -> list[Finding]:
    """Return build-up, discount, recorded-ground and lost-in-hole differences."""
    return (
        price_findings(data, rejected, CATEGORIES, CHECK_ID)
        + ground_findings(data, rejected)
        + lost_in_hole_findings(data, rejected)
    )


def build_up_finding(
    invoice_id: str, line: object, expected: Decimal, clause: str, evidence: str
) -> Finding:
    """Build a rate_buildup finding from a line's expected amount."""
    return Finding(
        invoice_id,
        line.line_ref,
        CHECK_ID,
        "rate_buildup",
        to_cents(expected - line.amount),
        clause,
        evidence,
        CONFIDENCE["rate_calibrated"],
    )


def ground_findings(data: AuditData, rejected: frozenset[str]) -> list[Finding]:
    """Price a line at its record's ground class where the invoice states another one."""
    ground_items = set(load_contract("civil")["ground"]["items"]["value"])
    datum_after = term("civil", "ground_datum_after").value
    prices = civil.price_lines(data, unmeasured_lines(data))
    findings = []
    for line in data.civil_lines.itertuples(index=False):
        if line.item_code not in ground_items or line.work_date > datum_after:
            continue
        record = linker.record_for(data, line.record_ref.strip())
        if record is None or not record["ground"] or line.line_ref in rejected:
            continue
        billed_class = line.ground_class.split(" ")[0] if line.ground_class else ""
        if billed_class == record["ground"] or line.line_ref not in prices:
            continue
        price = prices[line.line_ref]
        context = replace(civil.context_of(line), ground_class=record["ground"])
        split = [(part.quantity, part.percent) for part in price.parts]
        expected = civil.priced(line.line_ref, context, price.base, price.discount, split)
        evidence = (
            f"{line.item_code} billed at ground {billed_class or 'none'}; {record.name} records "
            f"{record['ground']}: rate {expected.rate}, amount {expected.amount}"
        )
        findings.append(
            build_up_finding(line.application_no, line, expected.amount, GROUND_CLAUSE, evidence)
        )
    return findings


def lost_in_hole_findings(data: AuditData, rejected: frozenset[str]) -> list[Finding]:
    """Check each lost-in-hole charge against its Schedule 2D value and the Part E hours."""
    codes = set(load_contract("drilling")["lost_in_hole"]["sar_values"])
    lines = data.drill_lines[data.drill_lines["service_code"].isin(codes)]
    findings = []
    for line in lines.itertuples(index=False):
        report = linker.report_for(data, line.report_ref)
        if report is None or line.line_ref in rejected or report["lost_hours"] is None:
            continue
        value = drilling.lost_in_hole_value(
            line.service_code, line.service_date, report["lost_hours"]
        )
        if line.unit_rate == value:
            continue
        expected = round_drilling(line.quantity * value)
        evidence = (
            f"{line.service_code} billed {line.unit_rate}; Schedule 2D value for "
            f"{line.service_date:%Y-%m} less depreciation for {report['lost_hours']} h is {value}"
        )
        findings.append(build_up_finding(line.invoice_no, line, expected, LOST_CLAUSE, evidence))
    return findings
