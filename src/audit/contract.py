"""Contract terms from extracted/contracts/*.json, and the contracts' totalling rules.

Input: civil.json and drilling.json written by the extract stage (every value with its
source). Output: typed terms (`Term`) and the invoice-level arithmetic each contract lays
down: civil retention (Cl.45), drilling discount, VAT and total (Cl.36-40). Rounding modes
are the contracts' own: civil half up (Cl.28), drilling half to even at each step (Cl.17).
It also answers the date questions of pricing: the rate and discount in force on a work date
(`rate_at`, `discount_at`) and the Contract Year of a date (`contract_year`, Cl.3A).
No contract value is typed in this module.
"""

from __future__ import annotations

import json
import re
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date
from decimal import ROUND_DOWN, ROUND_HALF_EVEN, ROUND_HALF_UP, Decimal
from functools import cache

from audit.config import CONTRACTS_DIR

CENT = Decimal("0.01")
HUNDRED = Decimal(100)
ISO_DATE = re.compile(r"\d{4}-\d{2}-\d{2}")
PLAIN_NUMBER = re.compile(r"-?\d+(\.\d+)?")


@dataclass(frozen=True)
class Term:
    """A contract value with the page and clause it was read from."""

    value: object
    source: str
    verified: bool


@cache
def load_contract(name: str) -> dict:
    """Return the extracted contract ("civil" or "drilling"); stop if extract has not run."""
    path = CONTRACTS_DIR / f"{name}.json"
    if not path.exists():
        raise FileNotFoundError(f"{path} is missing: run `python -m audit extract` first")
    return json.loads(path.read_text(encoding="utf-8"))


def _typed(raw: object) -> object:
    """Convert a JSON value to date, Decimal or text (money is stored as text, never float)."""
    if isinstance(raw, str) and ISO_DATE.fullmatch(raw):
        return date.fromisoformat(raw)
    if isinstance(raw, str) and PLAIN_NUMBER.fullmatch(raw):
        return Decimal(raw)
    return raw


def term(name: str, key: str) -> Term:
    """Return a clause-level term (e.g. "window_days", "completion") of one contract."""
    entry = load_contract(name)["terms"][key]
    return Term(_typed(entry["value"]), entry["source"], entry["verified"])


def record_series() -> dict[str, Term]:
    """Return civil item -> record series required before payment (Schedule 5, Cl.46)."""
    series = load_contract("civil")["record_series"]
    return {
        item: Term(entry["value"], entry["source"], entry["verified"])
        for item, entry in series.items()
    }


# ---- rounding -------------------------------------------------------------------------


def round_civil(amount: Decimal) -> Decimal:
    """Round to the nearest halala, a half halala upward (civil Cl.28)."""
    return amount.quantize(CENT, ROUND_HALF_UP)


def round_drilling(amount: Decimal) -> Decimal:
    """Round to the cent, a result exactly half way to the even cent (drilling Cl.17)."""
    return amount.quantize(CENT, ROUND_HALF_EVEN)


def civil_retention(total: Decimal) -> Decimal:
    """Return the retention on an application total, rounded down to the halala (Cl.45)."""
    percent = term("civil", "retention_pct").value
    return (total * percent / HUNDRED).quantize(CENT, ROUND_DOWN)


# ---- invoice totals as the contract builds them ---------------------------------------


def civil_total(line_amounts: Iterable[Decimal]) -> Decimal:
    """Return the application total: the sum of its line amounts, before retention (Cl.43)."""
    return sum(line_amounts, Decimal(0))


@dataclass(frozen=True)
class DrillingTotals:
    """An invoice's totals built the contract's way (Cl.36-40)."""

    services: Decimal
    discount: Decimal  # DS-900, <= 0
    net: Decimal
    vat: Decimal
    total: Decimal


def vat_rate() -> Decimal:
    """Return VAT as a fraction of the net amount (Cl.39)."""
    return term("drilling", "vat_pct").value / HUNDRED


def drilling_discount(services: Decimal) -> Decimal:
    """Return the DS-900 discount on a services total, as a negative charge (Cl.38)."""
    excess = services - term("drilling", "discount_threshold").value
    if excess <= 0:
        return Decimal("0.00")
    percent = term("drilling", "discount_pct").value
    return -round_drilling(excess * percent / HUNDRED)


def drilling_totals(service_amounts: Iterable[Decimal]) -> DrillingTotals:
    """Build an invoice's totals: net = services + DS-900; VAT on net; total (Cl.36-40)."""
    services = sum(service_amounts, Decimal(0))
    discount = drilling_discount(services)
    net = services + discount
    vat = round_drilling(net * vat_rate())
    return DrillingTotals(services, discount, net, vat, net + vat)


# ---- rates, discounts and Contract Years in force on a date -----------------------------


@dataclass(frozen=True)
class RateOn:
    """A rate in force on a work date, with the schedule or instrument that set it."""

    value: Decimal
    source: str  # page and clause, e.g. "p.43 Amendment No. 3"
    reference: str  # instrument reference, "" for the Schedule 1 rate
    month: str = ""  # published month of a monthly rate, e.g. "2026-04"


def instruments_in_force(name: str, submitted: date) -> list[dict]:
    """Return the instruments issued on or before the submission date, in the order issued.

    Cl.31A p.32 / Cl.36A p.35: an invoice submitted before an instrument's date of issue was
    correct at the rate then in force; one submitted on or after it applies it (D16).
    """
    issued = [
        instrument
        for instrument in load_contract(name)["instruments"]
        if date.fromisoformat(instrument["issued"]["value"]) <= submitted
    ]
    return sorted(issued, key=lambda instrument: instrument["issued"]["value"])


def schedule_rate(name: str, item: str) -> RateOn:
    """Return the Schedule 1 rate of an item; stop if Schedule 1 prices it otherwise."""
    entry = load_contract(name)["items"][item]["rate"]
    if not PLAIN_NUMBER.fullmatch(entry["value"]):
        raise ValueError(f"{name}.json items.{item}: Schedule 1 gives no rate ({entry['value']})")
    return RateOn(Decimal(entry["value"]), entry["source"], "")


def rate_at(name: str, item: str, work_date: date, submitted: date) -> RateOn:
    """Return the rate in force for an item on its work date.

    Schedule of Variations (civil p.38, drilling p.37): instruments are read in the order
    issued, and each governs work on or after its effective date; the later one governs, the
    earlier governs work before the later one's effective date. Only instruments issued on or
    before the submission date count (D16).
    """
    rate = schedule_rate(name, item)
    for instrument in instruments_in_force(name, submitted):
        found = instrument_rate(instrument, item, work_date)
        if found is not None:
            rate = found
    return rate


def instrument_rate(instrument: dict, item: str, work_date: date) -> RateOn | None:
    """Return the rate one instrument sets for an item on a work date, or None.

    A monthly rate is the one published for the month of the work; after the last month
    stated, the last published rate applies until superseded (e.g. civil p.39 §1.2).
    """
    reference = instrument["reference"]
    if item in instrument["rates"]:
        entry = instrument["rates"][item]
        if work_date < date.fromisoformat(entry["effective"]):
            return None
        return RateOn(Decimal(entry["value"]), entry["source"], reference)
    if item in instrument["monthly_rates"]:
        entry = instrument["monthly_rates"][item]
        work_month = f"{work_date.year}-{work_date.month:02d}"
        published = sorted(month for month in entry["value"] if month <= work_month)
        if not published:
            return None
        month = published[-1]
        return RateOn(Decimal(entry["value"][month]), entry["source"], reference, month)
    return None


def rate_history(name: str, item: str) -> list[RateOn]:
    """Return every rate the contract has stated for an item: Schedule 1, then each instrument.

    Schedule 1 is left out when it gives no number (e.g. PD-210, priced from Schedule 2).
    """
    entry = load_contract(name)["items"][item]["rate"]
    history = [schedule_rate(name, item)] if PLAIN_NUMBER.fullmatch(entry["value"]) else []
    for instrument in load_contract(name)["instruments"]:
        reference = instrument["reference"]
        if item in instrument["rates"]:
            entry = instrument["rates"][item]
            history.append(RateOn(Decimal(entry["value"]), entry["source"], reference))
        if item in instrument["monthly_rates"]:
            entry = instrument["monthly_rates"][item]
            for month, value in sorted(entry["value"].items()):
                history.append(RateOn(Decimal(value), entry["source"], reference, month))
    return history


@dataclass(frozen=True)
class DiscountOn:
    """A discount percentage in force on a work date, with its instrument."""

    percent: Decimal
    source: str
    reference: str


NO_DISCOUNT = DiscountOn(Decimal(0), "", "")


def discount_at(name: str, item: str, work_date: date, submitted: date) -> DiscountOn:
    """Return the discount in force for an item on its work date (0 when none).

    Civil S2 / A2 (pp.41-42), drilling S2 / A2 (pp.40-41): a later discount on the same item
    replaces the earlier one from its start date; work before the first start carries none.
    """
    found = NO_DISCOUNT
    for instrument in instruments_in_force(name, submitted):
        entry = instrument["discount"]
        if entry is None or item not in entry["items"]:
            continue
        if work_date >= date.fromisoformat(entry["start"]):
            found = DiscountOn(Decimal(entry["value"]), entry["source"], instrument["reference"])
    return found


def discount_history(name: str, item: str) -> list[DiscountOn]:
    """Return every discount the contract states for an item, with no discount first."""
    history = [NO_DISCOUNT]
    for instrument in load_contract(name)["instruments"]:
        entry = instrument["discount"]
        if entry is not None and item in entry["items"]:
            history.append(
                DiscountOn(Decimal(entry["value"]), entry["source"], instrument["reference"])
            )
    return history


def contract_year(name: str, day: date) -> int:
    """Return the Contract Year (1, 2, ...) a date falls in.

    Cl.3A (civil p.32, drilling p.35): the first Contract Year runs from the Commencement
    Date; each following one starts on an anniversary of it. An extension of the term does
    not start a new one.
    """
    start = term(name, "commencement").value
    years = day.year - start.year
    if (day.month, day.day) < (start.month, start.day):
        years -= 1
    return years + 1


def retroactive_instruments(name: str) -> list[dict]:
    """Return the instruments that take effect before their date of issue (Cl.31A / Cl.36A)."""
    return [
        instrument
        for instrument in load_contract(name)["instruments"]
        if instrument["effective"]["value"] < instrument["issued"]["value"]
    ]
