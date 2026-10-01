"""Calibration: how often the pricing engine reproduces the billed rate.

Input: the priced lines of both contracts and the price differences (`pricing.compare`).
Output: agreement per item x rate period, per item and per invoice, and
output/calibration.md. Between 92% and 95% of invoices are correct, so a reading of the
contract that reprices a whole group of lines is a misreading, not a group of errors; the
per-item share also sets the confidence of the rate findings (c07, c08).
"""

from __future__ import annotations

from collections import Counter
from functools import cache
from pathlib import Path

import pandas as pd

from audit.io import AuditData
from audit.pricing import civil, drilling
from audit.pricing.compare import differences

TABLE_COLUMNS = ["contract", "invoice_id", "line_ref", "code", "period", "rate_ok", "amount_ok"]


def contract_rows(
    contract: str, lines: pd.DataFrame, prices: dict, fields: tuple[str, str, str]
) -> list[tuple]:
    """Return one agreement row per priced line of one contract."""
    invoice_col, code_col, rate_col = fields
    rows = []
    for line in lines.itertuples(index=False):
        price = prices.get(line.line_ref)
        if price is None:
            continue
        rows.append(
            (
                contract,
                getattr(line, invoice_col),
                line.line_ref,
                getattr(line, code_col),
                price.period,
                price.rate == getattr(line, rate_col),
                price.amount == line.amount,
            )
        )
    return rows


@cache
def line_agreement(data: AuditData, unmeasured: frozenset[str] = frozenset()) -> pd.DataFrame:
    """Return one row per priced line: its rate period and whether rate and amount agree."""
    rows = contract_rows(
        "civil",
        data.civil_lines,
        civil.price_lines(data, unmeasured),
        ("application_no", "item_code", "rate_applied"),
    ) + contract_rows(
        "drilling",
        data.drill_lines,
        drilling.price_lines(data, unmeasured),
        ("invoice_no", "service_code", "unit_rate"),
    )
    return pd.DataFrame(rows, columns=TABLE_COLUMNS)


@cache
def item_agreement(
    data: AuditData, unmeasured: frozenset[str] = frozenset()
) -> dict[tuple[str, str], float]:
    """Return (contract, code) -> share of priced lines whose billed rate is reproduced."""
    table = line_agreement(data, unmeasured)
    shares = table.groupby(["contract", "code"])["rate_ok"].mean()
    return {key: float(share) for key, share in shares.items()}


def group_table(table: pd.DataFrame, keys: list[str]) -> pd.DataFrame:
    """Count lines and agreements per group, with the rate agreement in per cent."""
    grouped = table.groupby(keys).agg(
        lines=("rate_ok", "size"), rate_ok=("rate_ok", "sum"), amount_ok=("amount_ok", "sum")
    )
    grouped["rate_pct"] = (100 * grouped["rate_ok"] / grouped["lines"]).round(1)
    return grouped.reset_index()


def invoice_table(data: AuditData, unmeasured: frozenset[str]) -> pd.DataFrame:
    """Return per contract: invoices, and invoices whose priced lines all agree with the engine."""
    diff_invoices = {diff.invoice_id for diff in differences(data, unmeasured)}
    rows = []
    for contract, ids in (
        ("civil", data.civil_apps["application_no"]),
        ("drilling", data.drill_invoices["invoice_no"]),
    ):
        agree = sum(invoice_id not in diff_invoices for invoice_id in ids)
        rows.append((contract, len(ids), agree, round(100 * agree / len(ids), 1)))
    return pd.DataFrame(rows, columns=["contract", "invoices", "all_lines_agree", "pct"])


def markdown(table: pd.DataFrame) -> str:
    """Render a table as GitHub markdown without the pandas index."""
    header = "| " + " | ".join(table.columns) + " |"
    rule = "|" + "---|" * len(table.columns)
    body = [
        "| " + " | ".join(str(value) for value in row) + " |"
        for row in table.itertuples(index=False)
    ]
    return "\n".join([header, rule, *body])


def write_report(data: AuditData, path: Path, unmeasured: frozenset[str]) -> None:
    """Write output/calibration.md: agreement per contract, item and period, and the causes."""
    table = line_agreement(data, unmeasured)
    causes = Counter((diff.contract, diff.category) for diff in differences(data, unmeasured))
    cause_table = pd.DataFrame(
        [(contract, category, count) for (contract, category), count in sorted(causes.items())],
        columns=["contract", "category", "lines"],
    )
    periods = group_table(table, ["contract", "code", "period"])
    below = periods[periods["rate_ok"] < periods["lines"]]
    sections = [
        "# Calibration (Phase 3)",
        "Share of priced lines whose billed rate and amount the pricing engine reproduces "
        "(the brief: 92-95% of invoices are correct). A rate period is the instrument "
        "(and month) and discount in force.",
        "## Per contract",
        markdown(group_table(table, ["contract"])),
        "## Invoices whose priced lines all agree",
        markdown(invoice_table(data, unmeasured)),
        "## Differences by cause",
        markdown(cause_table),
        "## Item x period groups with a difference",
        markdown(below),
        "## All items x periods",
        markdown(periods),
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n\n".join(sections) + "\n", encoding="utf-8")
