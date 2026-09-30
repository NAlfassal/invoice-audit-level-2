"""Turn findings into one verdict per invoice: submission.csv plus output/findings.csv.

Guideline check 12 ("the outcome is written down"): findings.csv keeps every finding's
clause, evidence and money effect; the submission carries the verdict per invoice.

- A finding counts when its confidence >= FLAG_THRESHOLD (checks.FLAG_THRESHOLD). The cost
  is 5 x FN + 1 x FP, so flagging pays whenever P(error) > 1/6 (CLAUDE.md §2). A finding
  below it is a query: kept in findings.csv with status "query", never flagged.
- error_category: the counting finding with the largest money impact; ties go to the higher
  confidence, then to the earlier category in the vocabulary.
- expected_total: the invoice rebuilt the contract's way from corrected line amounts, in
  guideline order: a line any counting finding rejects is 0; otherwise the correction of
  the earliest check on it applies (a later check does not re-price it, CLAUDE.md §4).
  Unflagged invoices keep the billed total.
- confidence: flagged -> the strongest counting finding (P(invoice wrong)); unflagged ->
  CLEAN_CONFIDENCE, P(invoice right) (DECISION_LOG D01; tuned in Phase 6).
"""

from __future__ import annotations

import csv
from collections import defaultdict
from dataclasses import asdict, fields
from decimal import Decimal
from pathlib import Path

import pandas as pd

from audit import calibrate, config, io
from audit.checks import CATEGORIES, Finding, counts, run_all, unmeasured_lines
from audit.contract import civil_total, drilling_totals

CLEAN_CONFIDENCE = 0.90
DISCOUNT_CODE = "DS-900"
CIVIL_PREFIX = "PA-"
SUBMISSION_COLUMNS = [
    "invoice_id",
    "flagged",
    "error_category",
    "expected_total_cents",
    "billed_total_cents",
    "confidence",
]


def run(paths: config.InputPaths) -> str:
    """Run every check, write and validate the submission and findings; return a summary."""
    data = io.load_all(paths)
    findings = run_all(data)
    submission = decide(data, findings)
    validate(submission, io.load_template(paths))
    write_findings(findings, config.OUTPUT_DIR / "findings.csv")
    calibrate.write_report(data, config.OUTPUT_DIR / "calibration.md", unmeasured_lines(data))
    submission.to_csv(config.SUBMISSION_PATH, index=False, lineterminator="\n")
    flagged = int(submission["flagged"].sum())
    return (
        f"audit: {len(findings)} findings, {flagged} of {len(submission)} invoices flagged "
        f"-> {config.SUBMISSION_PATH.name}, output/findings.csv, output/calibration.md"
    )


def decide(data: io.AuditData, findings: list[Finding]) -> pd.DataFrame:
    """Return one submission row per template invoice id, in template order."""
    counting: dict[str, list[Finding]] = defaultdict(list)
    for finding in findings:
        if counts(finding):
            counting[finding.invoice_id].append(finding)

    billed = billed_totals(data)
    rows = []
    for invoice_id in io.load_template(data.paths)["invoice_id"]:
        own = counting.get(invoice_id, [])
        billed_cents = io.to_cents(billed[invoice_id])
        if own:
            expected = expected_total(data, invoice_id, own)
            confidence = max(finding.confidence for finding in own)
            category = main_finding(own).category
            rows.append((invoice_id, 1, category, io.to_cents(expected), billed_cents, confidence))
        else:
            rows.append((invoice_id, 0, "", billed_cents, billed_cents, CLEAN_CONFIDENCE))
    submission = pd.DataFrame(rows, columns=SUBMISSION_COLUMNS)
    submission["confidence"] = submission["confidence"].map(lambda value: f"{value:.2f}")
    return submission


def main_finding(own: list[Finding]) -> Finding:
    """Return the finding that names the category: largest money impact, then confidence."""
    return max(
        own,
        key=lambda finding: (
            abs(finding.delta_minor_units),
            finding.confidence,
            -CATEGORIES.index(finding.category),
        ),
    )


def billed_totals(data: io.AuditData) -> dict[str, Decimal]:
    """Return the judged billed figure per invoice: application_total or invoice_total."""
    civil = data.civil_apps.set_index("application_no")["application_total"]
    drilling = data.drill_invoices.set_index("invoice_no")["invoice_total"]
    return civil.to_dict() | drilling.to_dict()


def corrected_amounts(lines: pd.DataFrame, own: list[Finding]) -> list[Decimal]:
    """Return the line amounts after corrections, applied in guideline order.

    `own` is in check order (run_all). A line any finding sets to zero is zero; otherwise the
    earliest check's correction stands and later ones do not re-price the line.
    """
    corrections: dict[str, Decimal] = {}
    for finding in own:
        if not finding.line_ref:
            continue
        fixed = lines.loc[finding.line_ref, "amount"] + Decimal(finding.delta_minor_units) / 100
        if finding.line_ref not in corrections or fixed == 0:
            corrections[finding.line_ref] = fixed
    return [corrections.get(ref, amount) for ref, amount in lines["amount"].items()]


def expected_total(data: io.AuditData, invoice_id: str, own: list[Finding]) -> Decimal:
    """Rebuild the invoice total from corrected lines.

    Civil: sum of lines (Cl.43). Drilling: services -> DS-900 (Cl.38) -> net -> VAT (Cl.39)
    -> total (Cl.40), so zeroing a line also moves the discount and the VAT.
    """
    if invoice_id.startswith(CIVIL_PREFIX):
        lines = data.civil_lines[data.civil_lines["application_no"] == invoice_id]
        return civil_total(corrected_amounts(lines.set_index("line_ref"), own))
    drill_lines = data.drill_lines
    lines = drill_lines[
        (drill_lines["invoice_no"] == invoice_id) & (drill_lines["service_code"] != DISCOUNT_CODE)
    ]
    return drilling_totals(corrected_amounts(lines.set_index("line_ref"), own)).total


def validate(submission: pd.DataFrame, template: pd.DataFrame) -> None:
    """Stop with a clear message rather than write a malformed deliverable."""
    problems = []
    if list(submission.columns) != list(template.columns):
        problems.append(f"columns {list(submission.columns)} != template {list(template.columns)}")
    if list(submission["invoice_id"]) != list(template["invoice_id"]):
        problems.append("invoice ids or their order differ from the template")
    if not submission["flagged"].isin([0, 1]).all():
        problems.append("flagged is not 0/1")
    for column in ("expected_total_cents", "billed_total_cents"):
        if not all(isinstance(value, int) for value in submission[column]):
            problems.append(f"{column} is not integer minor units")
    flagged = submission["flagged"] == 1
    if not submission.loc[flagged, "error_category"].isin(CATEGORIES).all():
        problems.append("flagged row with a category outside the vocabulary")
    if (submission.loc[~flagged, "error_category"] != "").any():
        problems.append("unflagged row with a category")
    if problems:
        raise ValueError("submission invalid: " + "; ".join(problems))


def write_findings(findings: list[Finding], path: Path) -> None:
    """Write every finding, by invoice and in guideline order, with its status.

    status is "error" for a finding that counts towards the flag and "query" for one kept
    for review below the threshold.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    names = [field.name for field in fields(Finding)] + ["status"]
    ordered = sorted(findings, key=lambda f: (f.invoice_id, f.check_id, f.line_ref))
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=names, lineterminator="\n")
        writer.writeheader()
        for finding in ordered:
            status = "error" if counts(finding) else "query"
            writer.writerow(asdict(finding) | {"status": status})
