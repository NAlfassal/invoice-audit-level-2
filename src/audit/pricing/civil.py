"""Civil pricing: the contract rate and amount of every application line.

Input: civil application lines and headers (`io.AuditData`) and extracted/contracts/civil.json.
Output: one `LinePrice` per line. The build-up follows Cl.27 p.6 in its order: base rate
(Schedule 1 or the instrument in force, converted from USD or indexed first), zone factor,
ground factor, night or rest-day uplift, band percentage, discount; the rate is rounded once,
half up (Cl.28). A line crossing a band limit is split, each part at its own rounded rate.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import date
from decimal import ROUND_HALF_EVEN, Decimal
from functools import cache

import pandas as pd

from audit.contract import (
    DiscountOn,
    RateOn,
    contract_year,
    discount_at,
    load_contract,
    rate_at,
    round_civil,
    term,
)
from audit.io import AuditData
from audit.pricing import HUNDRED, Band, LinePrice, Part, bands_from, cumulative_splits

CONTRACT = "civil"
CENT = Decimal("0.01")
FULL_RATE = Decimal(100)
WEEKDAYS = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")


class NotPriceable(ValueError):
    """The contract gives no rate for this line (e.g. an exchange rate for an unlisted month)."""


@dataclass(frozen=True)
class Context:
    """What a civil line's rate depends on besides the base rate, discount and band."""

    item: str
    work_date: date
    zone: str  # "Z2"
    ground_class: str  # "G5", or "" when none recorded
    night_work: bool


def context_of(line: object) -> Context:
    """Read the pricing context from one application line."""
    return Context(
        item=line.item_code,
        work_date=line.work_date,
        zone=line.site_zone.split()[0],
        ground_class=line.ground_class.split()[0] if line.ground_class else "",
        night_work=line.night_work == "Y",
    )


def converted_rate(item: str, rate: Decimal, work_date: date) -> Decimal:
    """Convert a USD (Sch.2B) or indexed (Sch.2A) base rate to SAR, rounded half to even.

    Cl.26A / Cl.29A p.32: the rate of the calendar month of the work; the conversion comes
    before any factor. Other items keep their rate unchanged.
    """
    contract = load_contract(CONTRACT)
    month = f"{work_date.year}-{work_date.month:02d}"
    if item in contract["usd"]["items"]:
        table = contract["usd"]["halalas_per_usd"]["value"]
        divisor = HUNDRED  # the table is in halalas per USD
    elif item in contract["indexed"]["items"]:
        table = contract["indexed"]["index"]["value"]
        divisor = term(CONTRACT, "index_base").value
    else:
        return rate
    if month not in table:
        raise NotPriceable(f"{item}: no Schedule 2A/2B figure for {month}")
    return (rate * Decimal(table[month]) / divisor).quantize(CENT, ROUND_HALF_EVEN)


def zone_factor(context: Context) -> Decimal:
    """Return the Schedule 2 zone factor; Series E carries none (Sch.2 p.20, Cl.29)."""
    if context.item[0] not in term(CONTRACT, "zone_factor_series").value:
        return Decimal(1)
    return Decimal(load_contract(CONTRACT)["zone_factors"][context.zone]["value"])


def ground_factor(context: Context) -> Decimal:
    """Return the Schedule 3 ground factor for the listed items (p.23).

    Cl.27A p.32: work after 27 September 2025 takes the datum class G2 whatever was recorded.
    Spec. S4 p.10: a classification not recorded on the day is taken to be G2.
    """
    ground = load_contract(CONTRACT)["ground"]
    if context.item not in ground["items"]["value"]:
        return Decimal(1)
    datum = term(CONTRACT, "ground_datum_class").value
    after = term(CONTRACT, "ground_datum_after").value
    ground_class = context.ground_class or datum
    if context.work_date > after:
        ground_class = datum
    return Decimal(ground["factors"][ground_class]["value"])


def uplift_factor(context: Context, zone: Decimal) -> Decimal:
    """Return 1 + the night or rest-day uplift that applies (Sch.4 Pts 1-2 p.24).

    Cl.8 p.3 / P11 p.12: night work on a rest day takes the rest-day uplift alone. Cl.27A p.32:
    no night uplift on an item priced at a zone factor above 1.1.
    """
    contract = load_contract(CONTRACT)
    rest_days = term(CONTRACT, "rest_days").value
    on_rest_day = WEEKDAYS[context.work_date.weekday()] in rest_days
    if on_rest_day and context.item in contract["rest_day_uplift"]:
        return 1 + Decimal(contract["rest_day_uplift"][context.item]["value"]) / HUNDRED
    night_allowed = zone <= term(CONTRACT, "night_uplift_max_zone_factor").value
    if context.night_work and night_allowed and context.item in contract["night_uplift"]:
        return 1 + Decimal(contract["night_uplift"][context.item]["value"]) / HUNDRED
    return Decimal(1)


@dataclass(frozen=True)
class Factors:
    """The Cl.27 factors of a line (1 where none applies)."""

    zone: Decimal
    ground: Decimal
    uplift: Decimal


def factors_of(context: Context) -> Factors:
    """Return the zone, ground and uplift factors the contract gives a line."""
    zone = zone_factor(context)
    return Factors(zone, ground_factor(context), uplift_factor(context, zone))


def built_up_rate(
    base: Decimal, factors: Factors, band_percent: Decimal, discount: DiscountOn
) -> Decimal:
    """Build a line's rate: base, zone, ground, uplift, band %, discount; round once half up.

    Cl.27-28 p.6; the discount is the final factor, after any rebate and before rounding
    (S2 §2.2 p.41, A2 §2.3 p.42).
    """
    rate = base * factors.zone * factors.ground * factors.uplift
    rate = rate * band_percent / HUNDRED
    rate = rate * (HUNDRED - discount.percent) / HUNDRED
    return round_civil(rate)


def priced(
    line_ref: str,
    context: Context,
    base: RateOn,
    discount: DiscountOn,
    split: list[tuple[Decimal, Decimal]],
    factors: Factors | None = None,
) -> LinePrice:
    """Price every part of a line and add up the amount (Cl.28: each part at its own rate).

    `factors` replaces the contract's factors when given (used to diagnose a billed rate).
    """
    factors = factors or factors_of(context)
    base_rate = converted_rate(context.item, base.value, context.work_date)
    parts = tuple(
        Part(quantity, percent, built_up_rate(base_rate, factors, percent, discount))
        for quantity, percent in split
    )
    amount = round_civil(sum((part.quantity * part.rate for part in parts), Decimal(0)))
    return LinePrice(line_ref, base, discount, parts, amount)


def band_table() -> dict[str, tuple[Band, ...]]:
    """Return item -> Schedule 4 Part 3 bands (pp.24-25)."""
    return {
        item: bands_from(entries, "to_qty")
        for item, entries in load_contract(CONTRACT)["bands"].items()
    }


def band_splits(
    lines: pd.DataFrame, unmeasured: frozenset[str]
) -> dict[str, list[tuple[Decimal, Decimal]]]:
    """Return line_ref -> (quantity, band %) parts for every line of a banded item.

    Sch.4 Pt3 p.24: quantities count per item from zero at the start of each Contract Year
    (Cl.3A), payable lines only (D19), in Cl.30 order: work date, application number, line
    number.
    """
    bands = band_table()
    banded = lines[lines["item_code"].isin(bands)].copy()
    banded["line_number"] = banded["line_no"].astype(int)
    banded = banded.sort_values(["work_date", "application_no", "line_number"], kind="stable")
    return cumulative_splits(
        banded,
        lambda line: (line.item_code, contract_year(CONTRACT, line.work_date)),
        lambda line: bands[line.item_code],
        unmeasured,
    )


@cache
def price_lines(data: AuditData, unmeasured: frozenset[str] = frozenset()) -> dict[str, LinePrice]:
    """Price every civil line the contract can price; return line_ref -> LinePrice.

    A line is priced at the rate in force on its work date for its application's
    submission date (D16). `unmeasured` holds the lines that are not payable, which do not
    count towards the bands (D19). Lines the contract cannot price (NotPriceable) are left
    out.
    """
    submitted = dict(
        zip(data.civil_apps["application_no"], data.civil_apps["application_date"], strict=True)
    )
    splits = band_splits(data.civil_lines, unmeasured)
    prices = {}
    for line in data.civil_lines.itertuples(index=False):
        context = context_of(line)
        on = submitted[line.application_no]
        base = rate_at(CONTRACT, line.item_code, line.work_date, on)
        discount = discount_at(CONTRACT, line.item_code, line.work_date, on)
        split = splits.get(line.line_ref, [(line.quantity, FULL_RATE)])
        try:
            prices[line.line_ref] = priced(line.line_ref, context, base, discount, split)
        except NotPriceable:
            continue
    return prices


def repriced(line: object, price: LinePrice, base: RateOn, discount: DiscountOn) -> LinePrice:
    """Price a line again with another base rate or discount, keeping its band parts."""
    split = [(part.quantity, part.percent) for part in price.parts]
    return priced(line.line_ref, context_of(line), base, discount, split)


def factor_options(context: Context) -> list[tuple[str, Factors]]:
    """Return the other factor sets the contract states for a line, one factor changed at a time.

    Used only to name the factor a wrong billed rate was built with: every other zone and
    ground factor of the item, its uplifts, and no uplift.
    """
    contract = load_contract(CONTRACT)
    actual = factors_of(context)
    options = []
    if context.item[0] in term(CONTRACT, "zone_factor_series").value:
        for zone, entry in contract["zone_factors"].items():
            options.append((f"zone {zone}", replace(actual, zone=Decimal(entry["value"]))))
    if context.item in contract["ground"]["items"]["value"]:
        for ground, entry in contract["ground"]["factors"].items():
            options.append((f"ground {ground}", replace(actual, ground=Decimal(entry["value"]))))
    for kind in ("night_uplift", "rest_day_uplift"):
        if context.item in contract[kind]:
            percent = Decimal(contract[kind][context.item]["value"])
            name = kind.replace("_", " ").replace("rest day", "rest-day")
            options.append((f"{name} {percent}%", replace(actual, uplift=1 + percent / HUNDRED)))
    options.append(("no uplift", replace(actual, uplift=Decimal(1))))
    return [(name, factors) for name, factors in options if factors != actual]


def variants(line: object, price: LinePrice) -> list[tuple[str, LinePrice]]:
    """Price a line with one build-up step changed at a time; return (what changed, price)."""
    context = context_of(line)
    split = [(part.quantity, part.percent) for part in price.parts]
    found = []
    if len(split) > 1 or split[0][1] != FULL_RATE:
        unbanded = [(line.quantity, FULL_RATE)]
        found.append(
            (
                "band rebate not applied",
                priced(line.line_ref, context, price.base, price.discount, unbanded),
            )
        )
    for name, factors in factor_options(context):
        found.append(
            (name, priced(line.line_ref, context, price.base, price.discount, split, factors))
        )
    return found
