"""Guideline check 7: the rate is the one in force on the work date.

Reads the priced lines (`pricing`), the price differences (`pricing.compare`) and the invoice
headers. Returns:
- `superseded_rate` per line billed at a rate the instruments do not give for its work date;
- `retro_adjustment` per line billed at the retroactive Amendment 3 rate on an invoice
  submitted before its issue ("taken early", Cl.31A p.32 / Cl.36A p.35);
- `retro_adjustment` per invoice that should carry the single Amendment 3 settlement and
  does not (the first invoice submitted on or after the issue date, D16, D18, D25), and per
  other invoice that carries one;
- `retro_adjustment` on the civil application that should release half the retention
  (Cl.45A p.32) and does not.
Settlement and release findings carry delta 0: the judged total is the measured total (D17).
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import date
from decimal import ROUND_DOWN, Decimal

import pandas as pd

from audit.calibrate import item_agreement
from audit.checks import CONFIDENCE, RATE_CALIBRATED, Finding, unmeasured_lines
from audit.contract import instrument_rate, retroactive_instruments, term
from audit.io import AuditData, to_cents
from audit.pricing import HUNDRED, LinePrice, civil, drilling
from audit.pricing.compare import Difference, differences

CHECK_ID = "c07"
CENT = Decimal("0.01")
CATEGORIES = frozenset({"superseded_rate", "retro_adjustment"})
VARIATIONS_PAGE = {
    "civil": "p.38 Schedule of Variations",
    "drilling": "p.37 Schedule of Variations",
}
RETRO_CLAUSE = {"civil": "p.32 Cl.31A", "drilling": "p.35 Cl.36A"}
BUILDUP_CLAUSE = {"civil": "p.6 Cl.27-28", "drilling": "p.6 Cl.17-18"}


def run(data: AuditData, rejected: frozenset[str] = frozenset()) -> list[Finding]:
    """Return rate, retro-settlement and retention-release findings (see module docstring)."""
    findings = price_findings(data, rejected, CATEGORIES, CHECK_ID)
    for contract in ("civil", "drilling"):
        findings += settlement_findings(data, contract, rejected)
    return findings + retention_release_findings(data.civil_apps)


# ---- line findings shared with c08 ------------------------------------------------------


def clause_of(diff: Difference) -> str:
    """Return the clause a price difference relies on."""
    if diff.category == "superseded_rate":
        return f"{VARIATIONS_PAGE[diff.contract]}; {diff.expected.base.source}"
    if diff.category == "retro_adjustment":
        return RETRO_CLAUSE[diff.contract]
    if diff.category == "discount_misapplied":
        return diff.expected.discount.source or VARIATIONS_PAGE[diff.contract]
    return BUILDUP_CLAUSE[diff.contract]


def rate_confidence(data: AuditData, diff: Difference) -> float:
    """Return 0.90 when the engine reproduces the item on enough lines, else 0.60 (§8.1)."""
    share = item_agreement(data, unmeasured_lines(data)).get((diff.contract, diff.code), 0.0)
    return CONFIDENCE["rate_calibrated" if share >= RATE_CALIBRATED else "rate_uncalibrated"]


def price_findings(
    data: AuditData, rejected: frozenset[str], categories: frozenset[str], check_id: str
) -> list[Finding]:
    """Turn the price differences of the given categories into findings, skipping rejected lines."""
    findings = []
    for diff in differences(data, unmeasured_lines(data)):
        if diff.category not in categories or diff.line_ref in rejected:
            continue
        evidence = (
            f"{diff.code}: billed {diff.billed_rate} ({diff.billed_amount}); contract "
            f"{diff.expected.rate} ({diff.expected.amount}); {diff.reason}"
        )
        findings.append(
            Finding(
                diff.invoice_id,
                diff.line_ref,
                check_id,
                diff.category,
                to_cents(diff.delta),
                clause_of(diff),
                evidence,
                rate_confidence(data, diff),
            )
        )
    return findings


def tie_confidence(tied: int) -> float:
    """Return the carrier confidence shared by invoices tied as "first" (D18, D25): 1/n, 2 dp."""
    return min(CONFIDENCE["retro_carrier"], round(1 / tied, 2))


# ---- Amendment 3 settlement (Cl.31A civil, Cl.36A drilling) -----------------------------


def submission_dates(data: AuditData, contract: str) -> pd.Series:
    """Return invoice id -> submission date for one contract."""
    if contract == "civil":
        return data.civil_apps.set_index("application_no")["application_date"]
    return data.drill_invoices.set_index("invoice_no")["invoice_date"]


def adjustments(data: AuditData, contract: str) -> pd.Series:
    """Return invoice id -> the adjustment the invoice carries."""
    headers = data.civil_apps if contract == "civil" else data.drill_invoices
    id_col = "application_no" if contract == "civil" else "invoice_no"
    return headers.set_index(id_col)["adjustment"]


def repricer(
    data: AuditData, contract: str
) -> Callable[[object, LinePrice, object], LinePrice | None]:
    """Return a function that prices a line again at another rate, keeping its discount."""
    if contract == "civil":
        return lambda line, price, rate: civil.repriced(line, price, rate, price.discount)
    well_class = data.drill_invoices.set_index("invoice_no")["well_class"]
    return lambda line, price, rate: drilling.repriced(
        line, well_class[line.invoice_no], rate, price.discount
    )


def amount_owed(
    data: AuditData, contract: str, instrument: dict, rejected: frozenset[str]
) -> tuple[Decimal, int]:
    """Return the settlement due under a retroactive instrument, and the lines it covers.

    Cl.31A / Cl.36A: work on or after the substituted rate's effective date, on invoices
    submitted before the date of issue, was valued at the rate then in force; the difference
    is the substituted rate's amount minus the amount at the rate in force when submitted.
    Lines another check rejected are not payable and carry no difference.
    """
    issued = date.fromisoformat(instrument["issued"]["value"])
    submitted = submission_dates(data, contract)
    if contract == "civil":
        lines, prices, id_col, code_col, date_col = (
            data.civil_lines,
            civil.price_lines(data, unmeasured_lines(data)),
            "application_no",
            "item_code",
            "work_date",
        )
    else:
        lines, prices, id_col, code_col, date_col = (
            data.drill_lines,
            drilling.price_lines(data, unmeasured_lines(data)),
            "invoice_no",
            "service_code",
            "service_date",
        )
    reprice = repricer(data, contract)
    owed, covered = Decimal(0), 0
    for line in lines[lines[code_col].isin(instrument["rates"])].itertuples(index=False):
        if submitted[getattr(line, id_col)] >= issued or line.line_ref in rejected:
            continue
        new_rate = instrument_rate(instrument, getattr(line, code_col), getattr(line, date_col))
        price = prices.get(line.line_ref)
        if new_rate is None or price is None:
            continue
        again = reprice(line, price, new_rate)
        if again is not None:
            owed += again.amount - price.amount
            covered += 1
    return owed, covered


def settlement_findings(data: AuditData, contract: str, rejected: frozenset[str]) -> list[Finding]:
    """Check that the single settlement sits on the first invoice on or after the issue date.

    "First" is by submission date (D16). Invoices tied on that date share the finding: each
    is flagged at 1/n of the confidence (D18, D25). An adjustment on any other invoice is a
    finding of its own ("and on no other").
    """
    submitted = submission_dates(data, contract)
    carried = adjustments(data, contract)
    findings = []
    for instrument in retroactive_instruments(contract):
        issued = date.fromisoformat(instrument["issued"]["value"])
        owed, covered = amount_owed(data, contract, instrument, rejected)
        on_or_after = submitted[submitted >= issued]
        first = on_or_after[on_or_after == on_or_after.min()].index.sort_values()
        clause = f"{RETRO_CLAUSE[contract]}; {instrument['issued']['source']}"
        confidence = tie_confidence(len(first))
        for invoice_id in first:
            if carried[invoice_id] == owed:
                continue
            evidence = (
                f"{instrument['reference']} issued {issued}: settlement of {owed} on {covered} "
                f"lines due on the first invoice submitted on or after the issue date; "
                f"{invoice_id} ({submitted[invoice_id]}) carries {carried[invoice_id]}"
            )
            if len(first) > 1:
                evidence += (
                    f"; {len(first)} invoices tie on {submitted[invoice_id]}: {', '.join(first)}"
                )
            findings.append(
                Finding(
                    invoice_id, "", CHECK_ID, "retro_adjustment", 0, clause, evidence, confidence
                )
            )
        others = carried[(carried != 0) & ~carried.index.isin(first)]
        for invoice_id, amount in others.items():
            evidence = (
                f"adjustment {amount} on an invoice other than the first on or after {issued}"
            )
            findings.append(
                Finding(
                    invoice_id,
                    "",
                    CHECK_ID,
                    "retro_adjustment",
                    0,
                    clause,
                    evidence,
                    CONFIDENCE["retro_carrier"],
                )
            )
    return findings


# ---- retention release (civil Cl.45A) ----------------------------------------------------


def retention_release_findings(apps: pd.DataFrame) -> list[Finding]:
    """Check the release of half the retention on the first application after completion.

    Cl.45A p.32: "On the first Application for Payment submitted after the Date for
    Completion as extended, one half of the retention held on all earlier Applications is
    released, rounded down to the halala."
    """
    completion = term("civil", "completion")
    share = term("civil", "retention_release_share").value
    after = apps[apps["application_date"] > completion.value]
    if after.empty:
        return []
    first_date = after["application_date"].min()
    earlier = apps[apps["application_date"] < first_date]
    due = (earlier["retention"].sum() * share / HUNDRED).quantize(CENT, ROUND_DOWN)
    first = after[after["application_date"] == first_date].sort_values("application_no")
    findings = []
    for app in first.itertuples(index=False):
        if app.retention_released == due:
            continue
        evidence = (
            f"first application after completion ({completion.value}): release of {due} due "
            f"({share}% of {earlier['retention'].sum()} held on {len(earlier)} earlier "
            f"applications); {app.application_no} releases {app.retention_released}"
        )
        findings.append(
            Finding(
                app.application_no,
                "",
                CHECK_ID,
                "retro_adjustment",
                0,
                "p.32 Cl.45A",
                evidence,
                tie_confidence(len(first)),
            )
        )
    return findings
