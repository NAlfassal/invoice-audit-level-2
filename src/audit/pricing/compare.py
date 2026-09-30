"""Compare billed rates with the contract rates and name the cause of each difference.

Input: the priced lines of both contracts (`civil.price_lines`, `drilling.price_lines`) and
the invoice lines. Output: one `Difference` per line whose billed rate or amount the contract
does not support. The cause is found by pricing the line again with the other rates and
discounts the contract has stated for the item: a match with an older or later rate is
`superseded_rate`, a match with the retroactive instrument's rate on an invoice submitted
before its issue is `retro_adjustment` (taken early, Cl.31A / Cl.36A), a match with another
discount is `discount_misapplied`; anything else is `rate_buildup`.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from functools import cache

from audit.contract import (
    DiscountOn,
    RateOn,
    discount_history,
    rate_history,
    retroactive_instruments,
)
from audit.io import AuditData
from audit.pricing import LinePrice, civil, drilling, schedule_label

Reprice = Callable[[RateOn, DiscountOn], LinePrice | None]
Variants = Callable[[], list[tuple[str, LinePrice]]]


@dataclass(frozen=True)
class Difference:
    """A line whose billed rate or amount differs from the contract price."""

    contract: str
    invoice_id: str
    line_ref: str
    code: str
    billed_rate: Decimal
    billed_amount: Decimal
    expected: LinePrice
    category: str
    reason: str

    @property
    def delta(self) -> Decimal:
        """Return expected minus billed amount (negative = overbilled)."""
        return self.expected.amount - self.billed_amount


def label(rate: RateOn) -> str:
    """Name the schedule or instrument (and month) a rate comes from."""
    return f"{schedule_label(rate)} {rate.month}".strip()


def taken_early(contract: str, rate: RateOn, work_date: date, submitted: date) -> bool:
    """Tell whether a rate is a retroactive instrument's, billed before that instrument's issue.

    Cl.31A p.32 / Cl.36A p.35: an invoice submitted before the date of issue is correct at the
    rate then in force; the difference belongs on the settling invoice.
    """
    for instrument in retroactive_instruments(contract):
        if rate.reference != instrument["reference"]:
            continue
        issued = date.fromisoformat(instrument["issued"]["value"])
        effective = date.fromisoformat(instrument["effective"]["value"])
        return submitted < issued and work_date >= effective
    return False


def cause(
    contract: str,
    code: str,
    billed_rate: Decimal,
    price: LinePrice,
    reprice: Reprice,
    variants: Variants,
    work_date: date,
    submitted: date,
) -> tuple[str, str]:
    """Return the category and reason for a billed rate the contract does not give.

    The other stated rates are tried first (guideline 7), then the other discounts
    (guideline 8), then both together; a rate none of them reproduces is a build-up error,
    and the build-up step it used is named when changing one step reproduces it.
    """
    rates = [rate for rate in rate_history(contract, code) if rate != price.base]
    discounts = [d for d in discount_history(contract, code) if d != price.discount]
    in_force = f"{label(price.base)} {price.base.value}"
    for rate in rates:
        other = reprice(rate, price.discount)
        if other is None or other.rate != billed_rate:
            continue
        if taken_early(contract, rate, work_date, submitted):
            return "retro_adjustment", (
                f"billed at the {label(rate)} rate {rate.value} before its issue; "
                f"in force when submitted: {in_force} (Cl.31A/36A)"
            )
        return (
            "superseded_rate",
            f"billed at the {label(rate)} rate {rate.value}; in force: {in_force}",
        )
    for discount in discounts:
        other = reprice(price.base, discount)
        if other is not None and other.rate == billed_rate:
            return "discount_misapplied", (
                f"billed with a {discount.percent}% discount; in force: {price.discount.percent}%"
            )
    for rate in rates:
        for discount in discounts:
            other = reprice(rate, discount)
            if other is not None and other.rate == billed_rate:
                return "superseded_rate", (
                    f"billed at the {label(rate)} rate {rate.value} with a {discount.percent}% "
                    f"discount; in force: {in_force}, {price.discount.percent}%"
                )
    contract_rate = f"contract {price.rate} ({price.period})"
    for name, other in variants():
        if other.rate == billed_rate:
            return "rate_buildup", f"billed rate matches the build-up with {name}; {contract_rate}"
    return (
        "rate_buildup",
        f"billed rate {billed_rate} not reproduced by one changed step; {contract_rate}",
    )


def band_reason(price: LinePrice) -> str:
    """Describe the band parts of a line the invoice did not split as the contract does."""
    parts = ", ".join(f"{part.quantity} at {part.percent}% = {part.rate}" for part in price.parts)
    return f"band split (Sch.4 Pt3): {parts}"


def difference(
    contract: str,
    line: object,
    fields: tuple[str, str, str, str],
    price: LinePrice,
    reprice: Reprice,
    variants: Variants,
    submitted: date,
) -> Difference | None:
    """Compare one line with its contract price; return the difference, or None if it agrees.

    `fields` names the line's invoice id, code, rate and work-date columns.
    """
    invoice_col, code_col, rate_col, date_col = fields
    billed_rate, billed_amount = getattr(line, rate_col), line.amount
    code, work_date = getattr(line, code_col), getattr(line, date_col)
    if price.rate == billed_rate:
        if len(price.parts) == 1 or price.amount == billed_amount:
            return None  # an amount that is not quantity x rate is an arithmetic finding (c11)
        category, reason = "rate_buildup", band_reason(price)
    else:
        category, reason = cause(
            contract, code, billed_rate, price, reprice, variants, work_date, submitted
        )
    return Difference(
        contract,
        getattr(line, invoice_col),
        line.line_ref,
        code,
        billed_rate,
        billed_amount,
        price,
        category,
        reason,
    )


def civil_differences(data: AuditData, unmeasured: frozenset[str]) -> list[Difference]:
    """Return every civil line whose billed rate or band split the contract does not support."""
    prices = civil.price_lines(data, unmeasured)
    apps = data.civil_apps
    submitted = dict(zip(apps["application_no"], apps["application_date"], strict=True))
    fields = ("application_no", "item_code", "rate_applied", "work_date")
    found = []
    for line in data.civil_lines.itertuples(index=False):
        price = prices.get(line.line_ref)
        if price is None:
            continue

        def reprice(
            rate: RateOn, discount: DiscountOn, line: object = line, price: LinePrice = price
        ) -> LinePrice:
            return civil.repriced(line, price, rate, discount)

        def variants(line: object = line, price: LinePrice = price) -> list[tuple[str, LinePrice]]:
            return civil.variants(line, price)

        on = submitted[line.application_no]
        diff = difference("civil", line, fields, price, reprice, variants, on)
        if diff is not None:
            found.append(diff)
    return found


def drilling_differences(data: AuditData, unmeasured: frozenset[str]) -> list[Difference]:
    """Return every drilling line whose billed rate the contract does not support."""
    prices = drilling.price_lines(data, unmeasured)
    invoices = data.drill_invoices
    submitted = dict(zip(invoices["invoice_no"], invoices["invoice_date"], strict=True))
    well_class = dict(zip(invoices["invoice_no"], invoices["well_class"], strict=True))
    fields = ("invoice_no", "service_code", "unit_rate", "service_date")
    found = []
    for line in data.drill_lines.itertuples(index=False):
        price = prices.get(line.line_ref)
        if price is None:
            continue
        klass = well_class[line.invoice_no]

        def reprice(
            rate: RateOn, discount: DiscountOn, line: object = line, klass: str = klass
        ) -> LinePrice | None:
            if line.service_code == drilling.FOOTAGE_CODE:
                return None  # Schedule 2 depth bands are not changed by any instrument
            return drilling.repriced(line, klass, rate, discount)

        def variants(
            line: object = line, klass: str = klass, price: LinePrice = price
        ) -> list[tuple[str, LinePrice]]:
            return drilling.variants(line, klass, price)

        on = submitted[line.invoice_no]
        diff = difference("drilling", line, fields, price, reprice, variants, on)
        if diff is not None:
            found.append(diff)
    return found


@cache
def differences(
    data: AuditData, unmeasured: frozenset[str] = frozenset()
) -> tuple[Difference, ...]:
    """Return the price differences of both contracts, civil first, in line order.

    `unmeasured` holds the lines that are not payable (they do not count towards bands).
    """
    return tuple(civil_differences(data, unmeasured) + drilling_differences(data, unmeasured))
