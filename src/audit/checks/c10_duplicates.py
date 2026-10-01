"""Guideline check 10: nothing is billed twice, within an invoice or against an earlier one.

Reads invoice lines and headers; returns one finding per later copy (expected 0). The
earlier copy stands and is named in the finding's evidence, so both copies are reported in
one row. "Later" = later submission date, then invoice number, then line number.

Keys:
- Civil Cl.44 p.8: same item, work area (site) and date; quantity is not part of the key
  (Cl.44 p.8).
- Civil, same record: one record evidences one measurement (Cl.44 + Cl.46), so a second
  line for the same item on the same record_ref bills it again, e.g. one weekly dewatering
  log billed as a full week on several applications (D07).
- Drilling Cl.29 p.7: no service is charged twice for the same well and day, save PD-210,
  which may be charged more than once a day for different depth intervals (Cl.23). The key
  is therefore well, service date, service code and depth interval.

`exact_copies` names the later copies of a line repeated in full (same key, quantity and
record or report). They are removed before the daily limits are counted (c09), so a copy
keeps its category, duplicate_charge, and does not use up a limit.
"""

from __future__ import annotations

from functools import cache

import pandas as pd

from audit.checks import CONFIDENCE, Finding
from audit.io import AuditData, to_cents

CHECK_ID = "c10"
DISCOUNT_CODE = "DS-900"
DRILLING_CLAUSE = "p.7 Cl.29"


CIVIL_COPY_KEY = ["item_code", "site", "work_date", "quantity", "record_ref"]
DRILLING_COPY_KEY = ["well_name", "service_date", "service_code", "quantity", "report_ref"]


def run(data: AuditData, rejected: frozenset[str] = frozenset()) -> list[Finding]:
    """Return one finding per later copy of a civil or drilling charge."""
    return _civil(data) + _drilling(data)


@cache
def exact_copies(data: AuditData) -> frozenset[str]:
    """Return the line_refs of later copies of a line repeated in full, in both contracts."""
    civil = in_submission_order(
        data.civil_lines, data.civil_apps, "application_no", "application_date"
    )
    services = data.drill_lines[data.drill_lines["service_code"] != DISCOUNT_CODE]
    drilling = in_submission_order(services, data.drill_invoices, "invoice_no", "invoice_date")
    drilling["_interval"] = interval(drilling)
    copies = set()
    for ordered, key in ((civil, CIVIL_COPY_KEY), (drilling, DRILLING_COPY_KEY + ["_interval"])):
        repeated = ordered.duplicated(subset=key, keep="first")
        copies.update(ordered.loc[repeated, "line_ref"])
    return frozenset(copies)


def interval(lines: pd.DataFrame) -> pd.Series:
    """Return each line's depth interval as text; lines without depths share one value."""
    return lines["depth_from_m"].astype(str) + "-" + lines["depth_to_m"].astype(str)


def in_submission_order(
    lines: pd.DataFrame, headers: pd.DataFrame, id_col: str, date_col: str
) -> pd.DataFrame:
    """Sort lines by their invoice's submission date, invoice number, then line number."""
    ordered = lines.join(headers.set_index(id_col)[[date_col]], on=id_col)
    ordered["_line_no"] = ordered["line_no"].astype(int)
    return ordered.sort_values([date_col, id_col, "_line_no"], kind="stable")


def later_copies(
    ordered: pd.DataFrame,
    key: list[str],
    id_col: str,
    clause: str,
    confidence: float,
    label: str,
) -> list[Finding]:
    """Return one finding for every line after the first in each group sharing `key`."""
    findings = []
    for _, group in ordered.groupby(key, sort=False, dropna=False):
        if len(group) < 2:
            continue
        first_ref = group.iloc[0]["line_ref"]
        for line in group.iloc[1:].itertuples(index=False):
            findings.append(
                Finding(
                    getattr(line, id_col),
                    line.line_ref,
                    CHECK_ID,
                    "duplicate_charge",
                    -to_cents(line.amount),
                    clause,
                    f"{label}; first billed on {first_ref}",
                    confidence,
                )
            )
    return findings


def _civil(data: AuditData) -> list[Finding]:
    ordered = in_submission_order(
        data.civil_lines, data.civil_apps, "application_no", "application_date"
    )
    findings = later_copies(
        ordered,
        ["item_code", "site", "work_date"],
        "application_no",
        "p.8 Cl.44",
        CONFIDENCE["duplicate"],
        "same item, work area and date",
    )
    # A line already disallowed under Cl.44 is not counted again as a record re-use.
    already = {finding.line_ref for finding in findings}
    with_record = ordered[
        (ordered["record_ref"].str.strip() != "") & ~ordered["line_ref"].isin(already)
    ]
    findings += later_copies(
        with_record,
        ["record_ref", "item_code"],
        "application_no",
        "p.8 Cl.44, Cl.46",
        CONFIDENCE["duplicate_record"],
        "same item billed again on the same record",
    )
    return findings


def _drilling(data: AuditData) -> list[Finding]:
    services = data.drill_lines[data.drill_lines["service_code"] != DISCOUNT_CODE]
    ordered = in_submission_order(services, data.drill_invoices, "invoice_no", "invoice_date")
    # Depths are None on most lines; as text, "no depth" groups like any other value.
    ordered["_interval"] = interval(ordered)
    return later_copies(
        ordered,
        ["well_name", "service_date", "service_code", "_interval"],
        "invoice_no",
        DRILLING_CLAUSE,
        CONFIDENCE["duplicate"],
        "same well, date, service and depth interval",
    )
