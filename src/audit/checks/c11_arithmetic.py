"""Guideline check 11: the arithmetic reconciles.

Reads invoice lines and headers; returns findings for line amounts, totals, retention (civil)
and the discount, VAT and total (drilling). Retention and net payable do not change the
judged civil figure (application_total), so their findings carry delta 0.
"""

from __future__ import annotations

from collections.abc import Iterable
from decimal import Decimal

import pandas as pd

from audit.checks import CONFIDENCE, Finding, unmeasured_lines
from audit.contract import civil_retention, drilling_discount, round_drilling, vat_rate
from audit.io import AuditData, to_cents
from audit.pricing import civil

CHECK_ID = "c11"
DISCOUNT_CODE = "DS-900"


def run(data: AuditData, rejected: frozenset[str] = frozenset()) -> list[Finding]:
    """Return civil and drilling line and header arithmetic findings."""
    prices = civil.price_lines(data, unmeasured_lines(data))
    split_lines = {ref for ref, price in prices.items() if len(price.parts) > 1}
    return (
        civil_lines(data.civil_lines, frozenset(split_lines))
        + civil_headers(data.civil_apps, data.civil_lines)
        + drilling_lines(data.drill_lines)
        + drilling_headers(data.drill_invoices, data.drill_lines)
    )


def _finding(
    invoice_id: str,
    line_ref: str,
    category: str,
    delta: Decimal,
    clause: str,
    evidence: str,
    confidence: float = CONFIDENCE["arithmetic"],
) -> Finding:
    return Finding(
        invoice_id, line_ref, CHECK_ID, category, to_cents(delta), clause, evidence, confidence
    )


def _total(amounts: Iterable[Decimal]) -> Decimal:
    return sum(amounts, Decimal(0))


def civil_lines(lines: pd.DataFrame, split_lines: frozenset[str]) -> list[Finding]:
    """Check each line amount against quantity x rate (Cl.42), except band-split lines.

    Cl.28 p.6 and Sch.4 Pt3 p.24: a quantity crossing a band is split and each part priced
    at its own rate, so a band-split line is not quantity x rate; the pricing engine judges
    it (c08). Any other line whose amount is not quantity x rate is an arithmetic error
    (DECISION_LOG D08).
    """
    findings = []
    for line in lines.itertuples(index=False):
        if line.line_ref in split_lines:
            continue
        product = line.quantity * line.rate_applied  # integer x 2 dp: exact, no rounding
        if line.amount == product:
            continue
        findings.append(
            _finding(
                line.application_no,
                line.line_ref,
                "arithmetic",
                product - line.amount,
                "p.8 Cl.42; p.6 Cl.28",
                f"{line.quantity} x {line.rate_applied} = {product}, billed {line.amount}",
            )
        )
    return findings


def civil_headers(apps: pd.DataFrame, lines: pd.DataFrame) -> list[Finding]:
    """Total = sum of lines (Cl.43); retention 5% rounded down (Cl.45); net = total - retention."""
    line_sums = lines.groupby("application_no")["amount"].agg(_total)
    findings = []
    for app in apps.itertuples(index=False):
        app_id, total = app.application_no, app.application_total
        if total != line_sums[app_id]:
            findings.append(
                _finding(
                    app_id,
                    "",
                    "arithmetic",
                    line_sums[app_id] - total,
                    "p.8 Cl.43",
                    f"lines sum to {line_sums[app_id]}, application_total {total}",
                )
            )
        retention = civil_retention(total)
        if app.retention != retention:
            findings.append(
                _finding(
                    app_id,
                    "",
                    "retention_vat",
                    Decimal(0),
                    "p.8 Cl.45",
                    f"retention {app.retention}, 5% rounded down is {retention}",
                )
            )
        findings += _civil_net(app)
    return findings


def _civil_net(app: tuple) -> list[Finding]:
    # adjustment and retention_released are 0.00 on every application. If one is not, its
    # sign convention is unknown, so the net check is replaced by a query.
    if app.adjustment or app.retention_released:
        evidence = (
            f"adjustment {app.adjustment}, retention_released {app.retention_released}: "
            "not modelled"
        )
        return [
            _finding(
                app.application_no,
                "",
                "retention_vat",
                Decimal(0),
                "p.8 Cl.45",
                evidence,
                CONFIDENCE["query"],
            )
        ]
    expected_net = app.application_total - app.retention
    if app.net_payable == expected_net:
        return []
    return [
        _finding(
            app.application_no,
            "",
            "retention_vat",
            Decimal(0),
            "p.8 Cl.45",
            f"net_payable {app.net_payable} != total - retention {expected_net}",
        )
    ]


def drilling_lines(lines: pd.DataFrame) -> list[Finding]:
    """Line amount = quantity x rate (Cl.34 p.8), rounded under Cl.17."""
    findings = []
    for line in lines.itertuples(index=False):
        product = round_drilling(line.quantity * line.unit_rate)
        if line.amount != product:
            findings.append(
                _finding(
                    line.invoice_no,
                    line.line_ref,
                    "arithmetic",
                    product - line.amount,
                    "p.8 Cl.34, Cl.36",
                    f"{line.quantity} x {line.unit_rate} = {product}, billed {line.amount}",
                )
            )
    return findings


def drilling_headers(invoices: pd.DataFrame, lines: pd.DataFrame) -> list[Finding]:
    """DS-900 discount (Cl.38), net (Cl.36), VAT (Cl.39) and total (Cl.40)."""
    is_discount = lines["service_code"] == DISCOUNT_CODE
    services = lines[~is_discount].groupby("invoice_no")["amount"].agg(_total)
    discounts = lines[is_discount].groupby("invoice_no")["amount"].agg(_total)
    charges = lines.groupby("invoice_no")["amount"].agg(_total)
    findings = []
    for inv in invoices.itertuples(index=False):
        inv_id = inv.invoice_no
        billed_discount = discounts.get(inv_id, Decimal("0.00"))
        expected_discount = drilling_discount(services[inv_id])
        if billed_discount != expected_discount:
            findings.append(
                _finding(
                    inv_id,
                    "",
                    "discount_misapplied",
                    expected_discount - billed_discount,
                    "p.8 Cl.38",
                    f"services {services[inv_id]}: DS-900 should be {expected_discount}, "
                    f"billed {billed_discount}",
                )
            )
        if inv.net_amount != charges[inv_id]:
            findings.append(
                _finding(
                    inv_id,
                    "",
                    "arithmetic",
                    charges[inv_id] - inv.net_amount,
                    "p.8 Cl.36",
                    f"charges sum to {charges[inv_id]}, net_amount {inv.net_amount}",
                )
            )
        vat = round_drilling(inv.net_amount * vat_rate())
        if inv.vat_amount != vat:
            findings.append(
                _finding(
                    inv_id,
                    "",
                    "retention_vat",
                    vat - inv.vat_amount,
                    "p.8 Cl.39",
                    f"VAT {inv.vat_amount}, 15% of net is {vat}",
                )
            )
        net_plus_vat = inv.net_amount + inv.vat_amount
        if inv.invoice_total != net_plus_vat:
            findings.append(
                _finding(
                    inv_id,
                    "",
                    "arithmetic",
                    net_plus_vat - inv.invoice_total,
                    "p.8 Cl.40",
                    f"net {inv.net_amount} + VAT {inv.vat_amount} = {net_plus_vat}, "
                    f"total {inv.invoice_total}",
                )
            )
    return findings
