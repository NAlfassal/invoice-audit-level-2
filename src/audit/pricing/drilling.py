"""Drilling pricing: the contract rate and amount of every invoice line.

Input: drilling invoice lines and headers (`io.AuditData`) and
extracted/contracts/drilling.json. Output: one `LinePrice` per service line. The build-up
follows Cl.18 p.6 in its order: base rate (Schedule 1 or the instrument in force; PD-210 from
the Schedule 2 depth band; Sch.2C services indexed first), hole-section factor, well-class
factor, standby percentage, discount. Every step is rounded to the cent, half to even
(Cl.17). DS-900 (Cl.38) is an invoice-level charge and is not priced here.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import date
from decimal import Decimal
from functools import cache

import pandas as pd

from audit.contract import (
    NO_DISCOUNT,
    DiscountOn,
    RateOn,
    contract_year,
    discount_at,
    load_contract,
    rate_at,
    round_drilling,
    term,
)
from audit.io import AuditData
from audit.pricing import HUNDRED, LinePrice, Part, bands_from, cumulative_splits

CONTRACT = "drilling"
DISCOUNT_CODE = "DS-900"
FOOTAGE_CODE = "PD-210"
STANDBY = "Standby"
NOT_CHARGEABLE = "not chargeable"
FULL_RATE = Decimal(100)


class NotPriceable(ValueError):
    """The contract gives no rate for this line (e.g. a service not chargeable on Standby)."""


@dataclass(frozen=True)
class Context:
    """What a drilling line's rate depends on besides the base rate and discount."""

    code: str
    service_date: date
    hole_section: str
    standby: bool
    well_class: str


def context_of(line: object, well_class: str) -> Context:
    """Read the pricing context from one invoice line and its invoice's well class."""
    return Context(
        code=line.service_code,
        service_date=line.service_date,
        hole_section=line.hole_section,
        standby=line.day_status == STANDBY,
        well_class=well_class,
    )


def indexed_rate(code: str, rate: Decimal, service_date: date) -> Decimal:
    """Index a Sch.2C service rate for the month of the service, rounded half to even.

    Cl.17A p.35: base rate x index of the month / base index. Other services keep their rate.
    """
    indexed = load_contract(CONTRACT)["indexed"]
    if code not in indexed["items"]:
        return rate
    month = f"{service_date.year}-{service_date.month:02d}"
    if month not in indexed["index"]["value"]:
        raise NotPriceable(f"{code}: no Rig Services Index for {month}")
    index = Decimal(indexed["index"]["value"][month])
    return round_drilling(rate * index / term(CONTRACT, "index_base").value)


def standby_percent(context: Context) -> Decimal:
    """Return the Schedule 3 Part 3 percentage charged on a Standby day (Cl.20 p.6).

    Services charged per well or for a loss, and DD-121 (charged only on a Standby day, in
    place of DD-120), are charged in full (Sch.3 Pts 3-4 pp.20-21).
    """
    contract = load_contract(CONTRACT)
    entry = contract["standby"].get(context.code)
    if entry is None:
        in_full = (
            set(contract["once_per_well"]["value"])
            | set(contract["lost_in_hole"]["usd_values"])
            | set(term(CONTRACT, "standby_only_items").value)
        )
        if context.code in in_full:
            return FULL_RATE
        raise NotPriceable(f"{context.code}: no Schedule 3 Part 3 standby percentage")
    if entry["value"] == NOT_CHARGEABLE:
        raise NotPriceable(f"{context.code}: not chargeable on a Standby day (Cl.20)")
    return Decimal(entry["value"])


@dataclass(frozen=True)
class Factors:
    """The Cl.18 steps of a service rate: section and class factors, standby % (1 / 100 if none)."""

    section: Decimal
    well_class: Decimal
    standby_percent: Decimal


def factors_of(context: Context) -> Factors:
    """Return the factors the contract gives a service line.

    Cl.17B p.35: no section factor on a Standby day and no class factor on PD-210 (D21).
    """
    contract = load_contract(CONTRACT)
    section, well_class, standby = Decimal(1), Decimal(1), FULL_RATE
    sections = contract["section_factors"]
    if context.code in sections["items"]["value"] and not context.standby:
        section = Decimal(sections["factors"][context.hole_section]["value"])
    classes = contract["class_factors"]
    if context.code in classes["items"]["value"] and context.code != FOOTAGE_CODE:
        well_class = Decimal(classes["factors"][context.well_class]["value"])
    if context.standby:
        standby = standby_percent(context)
    return Factors(section, well_class, standby)


def built_up_rate(
    base: Decimal, year_percent: Decimal, factors: Factors, discount: DiscountOn
) -> Decimal:
    """Build a service rate in Cl.18 order, rounding half to even at each step (Cl.17).

    The Contract Year percentage applies to PD-210 only (Sch.2 Pt2 p.17). The discount is
    the last factor (drilling S2 §2.2 p.40, A2 §2.3 p.41). A factor of 1 leaves the rate
    unchanged, so every step is applied.
    """
    rate = round_drilling(base * year_percent / HUNDRED)
    rate = round_drilling(rate * factors.section)
    rate = round_drilling(rate * factors.well_class)
    rate = round_drilling(rate * factors.standby_percent / HUNDRED)
    return round_drilling(rate * (HUNDRED - discount.percent) / HUNDRED)


def depth_bands(depth_from: Decimal, depth_to: Decimal) -> list[tuple[Decimal, RateOn]]:
    """Split a PD-210 interval at the Schedule 2 depth bands; return (metres, band rate).

    Cl.23 p.6: metres in each band are charged at that band's rate; a boundary depth
    belongs to the shallower band.
    """
    parts = []
    for band in load_contract(CONTRACT)["depth_bands"]:
        lower = Decimal(band["over_m"])
        upper = depth_to if band["to_m"] is None else Decimal(band["to_m"])
        metres = min(depth_to, upper) - max(depth_from, lower)
        if metres > 0:
            parts.append((metres, RateOn(Decimal(band["value"]), band["source"], "")))
    return parts


def year_splits(
    lines: pd.DataFrame, unmeasured: frozenset[str]
) -> dict[str, list[tuple[Decimal, Decimal]]]:
    """Return line_ref -> (metres, Contract Year %) parts for every PD-210 line.

    Sch.2 Pt2 p.17: metres already drilled on the well count from zero at the start of each
    Contract Year (Cl.3A p.35), payable lines only, in order of service date, invoice number
    and line number.
    """
    bands = bands_from(load_contract(CONTRACT)["contract_year_bands"], "to_m")
    footage = lines[lines["service_code"] == FOOTAGE_CODE].copy()
    footage["line_number"] = footage["line_no"].astype(int)
    footage = footage.sort_values(["service_date", "invoice_no", "line_number"], kind="stable")
    return cumulative_splits(
        footage,
        lambda line: (line.well_name, contract_year(CONTRACT, line.service_date)),
        lambda line: bands,
        unmeasured,
    )


def priced_footage(
    line: object, context: Context, year_split: list[tuple[Decimal, Decimal]]
) -> LinePrice:
    """Price a PD-210 line: each depth band part at its band rate (Cl.23)."""
    year_percent = year_split[0][1]  # a well's yearly footage stays within one band here
    if len(year_split) > 1:
        raise NotPriceable(f"{line.line_ref}: crosses a Contract Year footage band")
    parts = []
    base = None
    for metres, band_rate in depth_bands(line.depth_from_m, line.depth_to_m):
        base = base or band_rate
        rate = built_up_rate(band_rate.value, year_percent, factors_of(context), NO_DISCOUNT)
        parts.append(Part(metres, year_percent, rate))
    if not parts:
        raise NotPriceable(f"{line.line_ref}: no depth interval")
    if len(parts) == 1:
        # One band: the billed metres are priced as stated; metres against the depths are a
        # Phase 4 check (Cl.23, Cl.25A).
        parts = [Part(line.quantity, year_percent, parts[0].rate)]
    amount = round_drilling(sum((part.quantity * part.rate for part in parts), Decimal(0)))
    return LinePrice(line.line_ref, base, NO_DISCOUNT, tuple(parts), amount)


def priced_service(
    line: object,
    context: Context,
    base: RateOn,
    discount: DiscountOn,
    factors: Factors | None = None,
    index_date: date | None = None,
) -> LinePrice:
    """Price a service line at a given base rate and discount.

    `factors` and `index_date` replace the contract's factors and index month when given
    (used to diagnose a billed rate).
    """
    base_rate = indexed_rate(context.code, base.value, index_date or context.service_date)
    rate = built_up_rate(base_rate, FULL_RATE, factors or factors_of(context), discount)
    part = Part(line.quantity, FULL_RATE, rate)
    return LinePrice(line.line_ref, base, discount, (part,), round_drilling(line.quantity * rate))


def is_rated(code: str) -> bool:
    """Tell whether Schedule 1 states a rate for the code (LH-7xx are priced under Cl.31)."""
    value = load_contract(CONTRACT)["items"][code]["rate"]["value"]
    return value[:1].isdigit()


@cache
def price_lines(data: AuditData, unmeasured: frozenset[str] = frozenset()) -> dict[str, LinePrice]:
    """Price every drilling service line the contract can price; return line_ref -> LinePrice.

    `unmeasured` holds the lines that are not payable; their metres do not count towards the
    Contract Year footage bands.

    Lines left out: DS-900, lost in hole (Phase 4), and lines the contract gives no rate for
    (NotPriceable, e.g. a service not chargeable on Standby, checked by c09).
    """
    invoices = data.drill_invoices
    submitted = dict(zip(invoices["invoice_no"], invoices["invoice_date"], strict=True))
    well_class = dict(zip(invoices["invoice_no"], invoices["well_class"], strict=True))
    splits = year_splits(data.drill_lines, unmeasured)
    prices = {}
    for line in data.drill_lines.itertuples(index=False):
        if line.service_code == DISCOUNT_CODE:
            continue
        # PD-210 is rated from Schedule 2 (its Schedule 1 entry names no rate).
        if line.service_code != FOOTAGE_CODE and not is_rated(line.service_code):
            continue
        context = context_of(line, well_class[line.invoice_no])
        try:
            if line.service_code == FOOTAGE_CODE:
                price = priced_footage(line, context, splits[line.line_ref])
            else:
                on = submitted[line.invoice_no]
                base = rate_at(CONTRACT, context.code, context.service_date, on)
                discount = discount_at(CONTRACT, context.code, context.service_date, on)
                price = priced_service(line, context, base, discount)
        except NotPriceable:
            continue
        prices[line.line_ref] = price
    return prices


def repriced(line: object, well_class: str, base: RateOn, discount: DiscountOn) -> LinePrice | None:
    """Price a service line at another base rate or discount; None if it cannot be priced."""
    try:
        return priced_service(line, context_of(line, well_class), base, discount)
    except NotPriceable:
        return None


def first_of_month(day: date, step: int) -> date:
    """Return the first day of the month `step` months after (or before) the day's month."""
    index = day.year * 12 + day.month - 1 + step
    return date(index // 12, index % 12 + 1, 1)


def factor_options(context: Context) -> list[tuple[str, Factors]]:
    """Return the other factor sets the contract states for a line, one step changed at a time.

    Used only to name the step a wrong billed rate was built with: each section and class
    factor, the standby percentage applied or not.
    """
    contract = load_contract(CONTRACT)
    actual = factors_of(context)
    options = [
        (f"section {name}", replace(actual, section=Decimal(entry["value"])))
        for name, entry in contract["section_factors"]["factors"].items()
    ]
    options += [
        (f"class {name}", replace(actual, well_class=Decimal(entry["value"])))
        for name, entry in contract["class_factors"]["factors"].items()
    ]
    options.append(("no section factor", replace(actual, section=Decimal(1))))
    options.append(("no standby percentage", replace(actual, standby_percent=FULL_RATE)))
    entry = contract["standby"].get(context.code)
    if entry is not None and entry["value"] != NOT_CHARGEABLE:
        options.append(
            ("standby percentage", replace(actual, standby_percent=Decimal(entry["value"])))
        )
    return [(name, factors) for name, factors in options if factors != actual]


def variants(line: object, well_class: str, price: LinePrice) -> list[tuple[str, LinePrice]]:
    """Price a service line with one build-up step changed at a time; return (change, price)."""
    context = context_of(line, well_class)
    if line.service_code == FOOTAGE_CODE:
        return footage_variants(line, context, price)
    found = []
    for name, factors in factor_options(context):
        try:
            found.append((name, priced_service(line, context, price.base, price.discount, factors)))
        except NotPriceable:
            continue
    for step, label in ((-1, "previous"), (1, "next")):
        month = first_of_month(line.service_date, step)
        try:
            other = priced_service(line, context, price.base, price.discount, index_date=month)
        except NotPriceable:
            continue
        found.append((f"index of the {label} month", other))
    return found


def footage_variants(
    line: object, context: Context, price: LinePrice
) -> list[tuple[str, LinePrice]]:
    """Price a PD-210 line at each other depth band, and with the well-class factor applied.

    Used only to name what a wrong billed footage rate used (Cl.23; Cl.17B, D21).
    """
    contract = load_contract(CONTRACT)
    percent = price.parts[0].percent
    plain = factors_of(context)
    options = [
        (f"depth {band['band']} rate {band['value']}", Decimal(band["value"]), plain)
        for band in contract["depth_bands"]
    ]
    class_factor = Decimal(contract["class_factors"]["factors"][context.well_class]["value"])
    base_rate = price.base.value
    options.append(
        (
            f"well-class factor {class_factor} applied",
            base_rate,
            replace(plain, well_class=class_factor),
        )
    )
    found = []
    for name, rate, factors in options:
        built = built_up_rate(rate, percent, factors, NO_DISCOUNT)
        part = Part(line.quantity, percent, built)
        amount = round_drilling(line.quantity * built)
        found.append((name, LinePrice(line.line_ref, price.base, NO_DISCOUNT, (part,), amount)))
    return found


def lost_in_hole_value(code: str, loss_date: date, hours: Decimal) -> Decimal:
    """Return the charge for a tool lost in the hole.

    Cl.31A p.35: the Schedule 2D SAR value converted at that Schedule's rate for the month of
    the loss, rounded half to even; Sch.2D governs over Schedule 6. Cl.31 p.7: less 1% for
    each complete 25 circulating hours on the well (P12: including the day of the loss), to
    at most 50%, rounded under Cl.17.
    """
    lost = load_contract(CONTRACT)["lost_in_hole"]
    month = f"{loss_date.year}-{loss_date.month:02d}"
    rates = lost["halalas_per_usd"]["value"]
    if month not in rates:
        raise NotPriceable(f"{code}: no Schedule 2D exchange rate for {month}")
    usd = round_drilling(
        Decimal(lost["sar_values"][code]["value"]) * HUNDRED / Decimal(rates[month])
    )
    step_hours = term(CONTRACT, "lost_in_hole_depreciation_hours").value
    step_pct = term(CONTRACT, "lost_in_hole_depreciation_pct").value
    cap_pct = term(CONTRACT, "lost_in_hole_depreciation_max_pct").value
    depreciation = min(cap_pct, (hours // step_hours) * step_pct)
    return round_drilling(usd * (HUNDRED - depreciation) / HUNDRED)
