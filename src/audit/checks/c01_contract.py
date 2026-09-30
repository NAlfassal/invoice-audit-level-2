"""Guideline check 1: the invoice belongs to this contract (reference, issuer and period).

Reads invoice headers (and, for the civil period, line work dates); returns findings.
A wrong reference or a misstated period does not change what the work is worth, so these
findings carry delta 0 (DECISION_LOG D05).
"""

from __future__ import annotations

from audit.checks import CONFIDENCE, Finding
from audit.contract import term
from audit.io import AuditData


def run(data: AuditData, rejected: frozenset[str] = frozenset()) -> list[Finding]:
    """Check the reference and issuer on both contracts, and the civil stated period (Cl.40)."""
    return _civil(data) + _drilling(data)


def reference_and_issuer(
    invoice_id: str, contract_ref: str, issuer: str, contract: str
) -> list[Finding]:
    """Exact match on the contract reference and the issuer; a near-miss is another contract.

    The agreement (p.1) prints party names in capitals, so the issuer is compared without case.
    """
    findings = []
    for field, billed in (("contract_ref", contract_ref), ("issuer", issuer)):
        expected = term(contract, field)
        if billed.casefold() != str(expected.value).casefold():
            findings.append(
                Finding(
                    invoice_id,
                    "",
                    "c01",
                    "wrong_contract_ref",
                    0,
                    expected.source,
                    f"{field} {billed!r}, contract is {expected.value!r}",
                    CONFIDENCE["term_window_ref"],
                )
            )
    return findings


def _civil(data: AuditData) -> list[Finding]:
    findings: list[Finding] = []
    work_days = data.civil_lines.groupby("application_no")["work_date"].agg(["min", "max"])
    for app in data.civil_apps.itertuples(index=False):
        findings += reference_and_issuer(
            app.application_no, app.contract_ref, app.subcontractor, "civil"
        )
        first = work_days.loc[app.application_no, "min"]
        last = work_days.loc[app.application_no, "max"]
        # Cl.40 p.8: the stated period is the first and last day any included item was executed.
        if (app.period_from, app.period_to) != (first, last):
            findings.append(
                Finding(
                    app.application_no,
                    "",
                    "c01",
                    "invoice_window",
                    0,
                    "p.8 Cl.40",
                    f"stated period {app.period_from}..{app.period_to}, "
                    f"work executed {first}..{last}",
                    CONFIDENCE["period_statement"],
                )
            )
    return findings


def _drilling(data: AuditData) -> list[Finding]:
    findings: list[Finding] = []
    for inv in data.drill_invoices.itertuples(index=False):
        findings += reference_and_issuer(
            inv.invoice_no, inv.contract_ref, inv.contractor, "drilling"
        )
    return findings
