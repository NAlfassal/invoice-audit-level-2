"""Audit checks: one module per guideline check (c01 ... c11).

Every check takes the loaded data (`io.AuditData`) and the lines already rejected by an
earlier check, and returns `Finding` rows; none prints or decides. `run_all`
runs them in guideline order, so a line an earlier check rejects is not judged again by a
later one (guideline order). Guideline check 12, "the outcome is written down", is `decide.py`.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from functools import cache

from audit.io import AuditData, to_cents

# Fixed error_category vocabulary (the brief asks for consistent categories). A flagged
# invoice takes the category of its finding with the largest money impact.
CATEGORIES = (
    "wrong_contract_ref",
    "outside_term",
    "invoice_window",
    "missing_record",
    "unsigned_record",
    "quantity_over_record",
    "unidentified_item",
    "superseded_rate",
    "rate_buildup",
    "discount_misapplied",
    "retro_adjustment",
    "limit_exceeded",
    "duplicate_charge",
    "arithmetic",
    "retention_vat",
    "wrong_unit",  # Cl.26 p.6: a quantity in a unit other than Schedule 1's is rejected in full
)

# Starting confidences, checked on eval set A in Phase 6. Defined here only.
CONFIDENCE = {
    "arithmetic": 0.95,
    "duplicate": 0.95,  # civil Cl.44 key; drilling same well, date, service, interval
    "duplicate_record": 0.85,  # one record billed on several lines (DECISION_LOG D07)
    "missing_record": 0.85,
    "unsigned": 0.85,  # Cl.47 civil / Cl.15 drilling: both signatures required
    "quantity_over_record": 0.85,
    "term_window_ref": 0.90,
    "period_statement": 0.50,  # stated period is not the first/last work day (Cl.40)
    "query": 0.05,  # kept in findings.csv for review, deliberately below the flag threshold
    "wrong_unit": 0.90,  # civil Cl.26 / drilling Cl.35: read from the line and Schedule 1
    "rate_calibrated": 0.90,  # the item's rate is reproduced on >= RATE_CALIBRATED of lines
    "rate_uncalibrated": 0.60,  # below that share, or a contract value not yet verified
    "retro_carrier": 0.90,  # divided by the number of invoices tied as "first" (D18, D25)
    "limit": 0.85,
    "limit_unverified": 0.60,  # the limit value awaits the eye check (capped while unverified)
    "exclusion_same_day": 0.60,  # Cl.32 window read to include the same day (D27)
}

# A finding counts towards the flag when its confidence reaches this value: the cost is
# 5 x FN + 1 x FP, so flagging pays whenever P(error) > 1/6 (the brief's cost: 5 x FN + 1 x FP).
FLAG_THRESHOLD = 0.17
# Share of an item's lines the engine must reproduce before its rate findings are confident.
RATE_CALIBRATED = 0.90


@dataclass(frozen=True)
class Finding:
    """One audit finding on an invoice or one of its lines."""

    invoice_id: str
    line_ref: str  # "" for an invoice-level finding
    check_id: str  # e.g. "c05"
    category: str  # one of CATEGORIES
    delta_minor_units: int  # expected minus billed, in cents/halalas (negative = overbilled)
    clause: str  # the contract clause relied on, e.g. "p.8 Cl.41"
    evidence: str  # what was seen: record file, billed vs expected
    confidence: float  # P(this finding is a real error), 0..1

    def __post_init__(self) -> None:
        if self.category not in CATEGORIES:
            raise ValueError(f"{self.invoice_id}: unknown category {self.category!r}")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"{self.invoice_id}: confidence {self.confidence} outside 0..1")


def counts(finding: Finding) -> bool:
    """Tell whether a finding counts towards the flag (confidence at or above the threshold)."""
    return finding.confidence >= FLAG_THRESHOLD


def line_amounts(data: AuditData) -> dict[str, Decimal]:
    """Return line_ref -> billed amount for every civil and drilling line."""
    civil = zip(data.civil_lines["line_ref"], data.civil_lines["amount"], strict=True)
    drilling = zip(data.drill_lines["line_ref"], data.drill_lines["amount"], strict=True)
    return dict(civil) | dict(drilling)


def rejects(finding: Finding, amounts: dict[str, Decimal]) -> bool:
    """Tell whether a counting finding sets its line to zero (the line is rejected)."""
    if not finding.line_ref or not counts(finding):
        return False
    return finding.delta_minor_units == -to_cents(amounts[finding.line_ref])


@cache
def unmeasured_lines(data: AuditData) -> frozenset[str]:
    """Return the lines a check rejects in full before pricing, and the duplicates c10 disallows.

    These lines are not payable, so they do not count towards the quantity bands (Sch.4 Pt3
    "the quantity measured"; D19): out of term (c02), outside the stated period (c03), no
    record (c04), wrong unit (c06), and later copies (c10).
    """
    from audit.checks import c02_term, c03_window, c04_record, c06_identification, c10_duplicates

    amounts = line_amounts(data)
    lines = set()
    for check in (c02_term, c03_window, c04_record, c06_identification, c10_duplicates):
        lines.update(f.line_ref for f in check.run(data) if rejects(f, amounts))
    return frozenset(lines)


def run_all(data: AuditData) -> list[Finding]:
    """Run every implemented check in guideline order (c01 ... c11).

    A line rejected by an earlier check is passed to the later ones, and any later finding on
    it is dropped: the line is not re-priced or re-judged (guideline order).
    """
    from audit.checks import (
        c01_contract,
        c02_term,
        c03_window,
        c04_record,
        c05_quantity,
        c06_identification,
        c07_rate,
        c08_buildup,
        c09_limits,
        c10_duplicates,
        c11_arithmetic,
    )

    checks = (
        c01_contract,
        c02_term,
        c03_window,
        c04_record,
        c05_quantity,
        c06_identification,
        c07_rate,
        c08_buildup,
        c09_limits,
        c10_duplicates,
        c11_arithmetic,
    )
    amounts = line_amounts(data)
    findings: list[Finding] = []
    rejected: set[str] = set()
    for check in checks:
        found = [f for f in check.run(data, frozenset(rejected)) if f.line_ref not in rejected]
        findings.extend(found)
        rejected.update(f.line_ref for f in found if rejects(f, amounts))
    return findings
