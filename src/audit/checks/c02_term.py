"""Guideline check 2: the contract was live on the work dates, as extended by every instrument.

Reads invoice lines; returns one finding per line dated outside the term. Work outside the
term is not payable, so the line is expected 0. DS-900 discount lines carry no date and are
not dated work, so they are not tested.
"""

from __future__ import annotations

import pandas as pd

from audit.checks import CONFIDENCE, Finding
from audit.contract import Term, term
from audit.io import AuditData, to_cents


def run(data: AuditData, rejected: frozenset[str] = frozenset()) -> list[Finding]:
    """Every dated line within its contract's term as extended (civil.json / drilling.json)."""
    civil = lines_outside_term(
        data.civil_lines,
        "application_no",
        "work_date",
        term("civil", "commencement"),
        term("civil", "completion"),
    )
    drilling = lines_outside_term(
        data.drill_lines,
        "invoice_no",
        "service_date",
        term("drilling", "commencement"),
        term("drilling", "expiry"),
    )
    return civil + drilling


def lines_outside_term(
    lines: pd.DataFrame, id_col: str, date_col: str, start: Term, end: Term
) -> list[Finding]:
    """One finding per line whose work date falls before `start` or after `end`."""
    findings = []
    for line in lines.itertuples(index=False):
        work_date = getattr(line, date_col)
        if work_date is None or start.value <= work_date <= end.value:
            continue
        bound = start if work_date < start.value else end
        findings.append(
            Finding(
                getattr(line, id_col),
                line.line_ref,
                "c02",
                "outside_term",
                -to_cents(line.amount),
                bound.source,
                f"work date {work_date} outside term {start.value}..{end.value}",
                CONFIDENCE["term_window_ref"],
            )
        )
    return findings
