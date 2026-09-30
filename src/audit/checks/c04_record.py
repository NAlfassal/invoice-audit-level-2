"""Guideline check 4: every line has its record for that day or run, signed as required.

Reads invoice lines and the parsed records (`linker`); returns one finding per line whose
record does not evidence it. The line is expected 0: civil Cl.46 p.8, an item "is not
payable in any valuation until that record has been delivered"; drilling Cl.37 p.8 and
Sch.5 p.24, "a part that applies and is absent is a record not delivered".

- Civil (Schedule 5 items): record_ref blank, of the wrong series, not on file, or for
  another work area or day (`missing_record`); a record without both signatures, foreman and
  Engineer's representative (Cl.47 p.8, `unsigned_record`).
- Drilling (every service line; DS-900 has no report): the cited report missing or for
  another well or day (`missing_record`); the report part Schedule 5 requires absent
  (`missing_record`); a report without both signatures (Cl.15 p.5, `unsigned_record`).
"""

from __future__ import annotations

import pandas as pd

from audit import linker
from audit.checks import CONFIDENCE, Finding
from audit.contract import Term, record_series
from audit.io import AuditData, to_cents

CHECK_ID = "c04"
DISCOUNT_CODE = "DS-900"
CIVIL_CLAUSE = "p.8 Cl.46"
CIVIL_SIGNATURES = "p.8 Cl.47"
DRILLING_CLAUSE = "p.8 Cl.37; p.24 Schedule 5"
DRILLING_SIGNATURES = "p.5 Cl.15"


def run(data: AuditData, rejected: frozenset[str] = frozenset()) -> list[Finding]:
    """Return the civil and drilling lines whose record does not evidence them."""
    return civil_findings(data) + drilling_findings(data)


def reject(invoice_id: str, line: object, category: str, clause: str, evidence: str) -> Finding:
    """Build a finding that sets a line to zero for want of its record."""
    confidence = CONFIDENCE["missing_record" if category == "missing_record" else "unsigned"]
    return Finding(
        invoice_id,
        line.line_ref,
        CHECK_ID,
        category,
        -to_cents(line.amount),
        clause,
        evidence,
        confidence,
    )


# ---- civil -------------------------------------------------------------------------------


def record_problem(
    item_code: str, record_ref: str, required: Term, record_ids: frozenset[str]
) -> str | None:
    """Return why a Schedule 5 item's record_ref does not evidence it, or None if it does."""
    series = required.value
    ref = record_ref.strip()
    if not ref:
        return f"{item_code} requires a {series} record; record_ref is blank"
    if not ref.startswith(series + "-"):
        return f"{item_code} requires a {series} record; line cites {ref}"
    if ref not in record_ids:
        return f"{item_code} cites {ref}, which is not in civilwork/records"
    return None


def unsigned(record: pd.Series, names: dict[str, str]) -> str | None:
    """Return which required signature a record lacks, or None when both are there."""
    missing = [label for column, label in names.items() if not record[column]]
    return f"{record.name} is not signed by the {' and the '.join(missing)}" if missing else None


def civil_findings(data: AuditData) -> list[Finding]:
    """Check each Schedule 5 civil line against the record it cites."""
    findings = []
    required = record_series()
    lines = data.civil_lines[data.civil_lines["item_code"].isin(required)]
    signers = {"foreman": "foreman", "engineer_rep": "Engineer's representative"}
    for line in lines.itertuples(index=False):
        series = required[line.item_code]
        clause = f"{series.source}; {CIVIL_CLAUSE}"
        problem = record_problem(line.item_code, line.record_ref, series, data.civil_record_ids)
        record = None if problem else linker.record_for(data, line.record_ref.strip())
        if record is not None:
            problem = linker.civil_mismatch(line, record)
        if problem:
            findings.append(reject(line.application_no, line, "missing_record", clause, problem))
            continue
        missing = unsigned(record, signers)
        if missing:
            findings.append(
                reject(line.application_no, line, "unsigned_record", CIVIL_SIGNATURES, missing)
            )
    return findings


# ---- drilling ----------------------------------------------------------------------------


def drilling_findings(data: AuditData) -> list[Finding]:
    """Check each drilling service line against the Daily Drilling Report it cites."""
    findings = []
    services = linker.services()
    signers = {"representative": "Company Representative", "driller": "lead directional driller"}
    lines = data.drill_lines[data.drill_lines["service_code"] != DISCOUNT_CODE]
    for line in lines.itertuples(index=False):
        report = linker.report_for(data, line.report_ref)
        if report is None:
            problem = f"{line.report_ref} is not among the Daily Drilling Reports"
        else:
            problem = linker.drilling_mismatch(line, report)
        part = services.get(line.service_code, {}).get("report_part")
        if problem is None and part and part not in report["parts"]:
            problem = (
                f"{line.service_code} needs Part {part}; "
                f"{line.report_ref} has parts {report['parts']}"
            )
        if problem:
            findings.append(
                reject(line.invoice_no, line, "missing_record", DRILLING_CLAUSE, problem)
            )
            continue
        missing = unsigned(report, signers)
        if missing:
            findings.append(
                reject(line.invoice_no, line, "unsigned_record", DRILLING_SIGNATURES, missing)
            )
    return findings
