"""Guideline check 6: each line is identified against a priced item.

Reads invoice lines, Schedule 1 of each contract and the civil records (`linker`); returns
one finding per line whose code Schedule 1 does not list or whose record evidences another
item (`unidentified_item`), or whose unit is not the one Schedule 1 states (`wrong_unit`).
Civil Cl.26 p.6: "a quantity presented in a unit other than that stated shall be rejected
in its entirety rather than converted"; drilling Cl.35 p.8: "in the unit Schedule 1 gives
for the service, and in no other". All three are expected 0. A civil record is read with
the reviewed template table; each template belongs to one item, so no link is ambiguous
(D20). A drilling report names tools and crew in the rig's words, which c05 reads.
"""

from __future__ import annotations

import pandas as pd

from audit import linker
from audit.checks import CONFIDENCE, Finding
from audit.contract import load_contract
from audit.io import AuditData, to_cents

CHECK_ID = "c06"
DISCOUNT_CODE = "DS-900"
UNIT_CLAUSE = {"civil": "p.6 Cl.26", "drilling": "p.8 Cl.35"}
RECORD_CLAUSE = "p.33 Cl.47A; p.27 Schedule 5"


def run(data: AuditData, rejected: frozenset[str] = frozenset()) -> list[Finding]:
    """Return lines with an unknown code, a record of another item, or a wrong unit."""
    civil = identify("civil", data.civil_lines, "application_no", "item_code")
    services = data.drill_lines[data.drill_lines["service_code"] != DISCOUNT_CODE]
    drilling = identify("drilling", services, "invoice_no", "service_code")
    return civil + record_items(data, rejected) + drilling


def finding(invoice_id: str, line: object, category: str, clause: str, evidence: str) -> Finding:
    """Build a finding that rejects a line in full."""
    return Finding(
        invoice_id,
        line.line_ref,
        CHECK_ID,
        category,
        -to_cents(line.amount),
        clause,
        evidence,
        CONFIDENCE["wrong_unit"],
    )


def identify(contract: str, lines: pd.DataFrame, id_col: str, code_col: str) -> list[Finding]:
    """Return one finding per line whose code or unit does not match Schedule 1."""
    items = load_contract(contract)["items"]
    findings = []
    for line in lines.itertuples(index=False):
        code = getattr(line, code_col)
        if code not in items:
            category, clause = "unidentified_item", f"{contract} Schedule 1"
            evidence = f"code {code} is not in Schedule 1"
        elif line.unit != items[code]["unit"]:
            category = "wrong_unit"
            clause = f"{UNIT_CLAUSE[contract]}; {items[code]['rate']['source']}"
            evidence = f"{code} billed in {line.unit!r}; Schedule 1 unit is {items[code]['unit']!r}"
        else:
            continue
        findings.append(finding(getattr(line, id_col), line, category, clause, evidence))
    return findings


def record_items(data: AuditData, rejected: frozenset[str]) -> list[Finding]:
    """Return civil lines whose record's work line evidences another item."""
    findings = []
    for line in data.civil_lines.itertuples(index=False):
        record = linker.record_for(data, line.record_ref.strip())
        if record is None or line.line_ref in rejected:
            continue
        reading = linker.civil_reading(record)
        if reading.item == line.item_code:
            continue
        evidence = (
            f"{line.item_code} cites {record.name} ({record['work_text']!r}), "
            f"which evidences {reading.item}"
        )
        findings.append(
            finding(line.application_no, line, "unidentified_item", RECORD_CLAUSE, evidence)
        )
    return findings
