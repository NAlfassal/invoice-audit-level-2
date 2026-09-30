"""Guideline check 3: the invoice was raised inside its window, after its period closed.

Reads invoice headers and lines; returns findings. An early or late submission does not
change what the work is worth (delta 0, DECISION_LOG D05); a line dated outside the stated
period is not payable in this invoice (expected 0).
"""

from __future__ import annotations

from datetime import timedelta

import pandas as pd

from audit.checks import CONFIDENCE, Finding
from audit.contract import term
from audit.io import AuditData, to_cents

CHECK_ID = "c03"
CATEGORY = "invoice_window"


def run(data: AuditData, rejected: frozenset[str] = frozenset()) -> list[Finding]:
    """Submission date against the period end; line dates against the stated period."""
    civil_days, drilling_days = term("civil", "window_days"), term("drilling", "window_days")
    findings = late_or_early(
        data.civil_apps,
        "application_no",
        "period_to",
        "application_date",
        civil_days.value,
        civil_days.source,
    )
    findings += late_or_early(
        data.drill_invoices,
        "invoice_no",
        "period_end",
        "invoice_date",
        drilling_days.value,
        drilling_days.source,
    )
    # Cl.41 p.8 (civil): no item in an application whose period excludes its work day.
    findings += lines_outside_period(
        data.civil_apps,
        data.civil_lines,
        "application_no",
        ("period_from", "period_to"),
        "work_date",
        "p.8 Cl.41",
    )
    # Cl.32 p.8 (drilling): every charge is for a day within the period the invoice states.
    findings += lines_outside_period(
        data.drill_invoices,
        data.drill_lines,
        "invoice_no",
        ("period_start", "period_end"),
        "service_date",
        "p.8 Cl.32",
    )
    return findings


def late_or_early(
    headers: pd.DataFrame, id_col: str, end_col: str, date_col: str, days: int, source: str
) -> list[Finding]:
    """Invoices submitted before the period end or more than `days` after it.

    Civil Cl.41 and drilling Cl.33 (p.8): not before the last day of the period, and within
    21 / 30 days after it. Submitting on the last day itself is allowed.
    """
    findings = []
    for header in headers.itertuples(index=False):
        period_end, submitted = getattr(header, end_col), getattr(header, date_col)
        if submitted < period_end:
            gap = (period_end - submitted).days
            evidence = f"submitted {submitted}, {gap} days before period end {period_end}"
        elif submitted > period_end + timedelta(days=days):
            gap = (submitted - period_end).days
            evidence = (
                f"submitted {submitted}, {gap} days after period end {period_end} (limit {days})"
            )
        else:
            continue
        findings.append(
            Finding(
                getattr(header, id_col),
                "",
                CHECK_ID,
                CATEGORY,
                0,
                source,
                evidence,
                CONFIDENCE["term_window_ref"],
            )
        )
    return findings


def lines_outside_period(
    headers: pd.DataFrame,
    lines: pd.DataFrame,
    id_col: str,
    period_cols: tuple[str, str],
    date_col: str,
    source: str,
) -> list[Finding]:
    """Lines whose work date lies outside their invoice's stated period (expected 0)."""
    start_col, end_col = period_cols
    periods = headers.set_index(id_col)[[start_col, end_col]]
    findings = []
    for line in lines.join(periods, on=id_col).itertuples(index=False):
        work_date = getattr(line, date_col)
        start, end = getattr(line, start_col), getattr(line, end_col)
        if work_date is None or start <= work_date <= end:
            continue
        findings.append(
            Finding(
                getattr(line, id_col),
                line.line_ref,
                CHECK_ID,
                CATEGORY,
                -to_cents(line.amount),
                source,
                f"work date {work_date} outside stated period {start}..{end}",
                CONFIDENCE["term_window_ref"],
            )
        )
    return findings
