"""Synthetic error injection, Phase 6.

Input: the loaded invoices (`io.AuditData`) and a pool of clean invoice ids (no finding on
the real data). Output: a copy of the data in which a sample of the pool carries exactly one
planted error each, and the labels (invoice_id, category, true_expected_total_cents). The
other pool invoices are the negatives. After a change, the line amount, the subtotal,
retention / DS-900 / VAT and the total are recomputed as a contractor's system would, so
only the intended check can catch the error (arithmetic errors are the one exception: a line
amount is broken on purpose). A fixed seed makes every set reproducible.
"""

from __future__ import annotations

import random
from collections.abc import Callable
from dataclasses import dataclass, replace
from datetime import date, timedelta
from decimal import Decimal

import pandas as pd

from audit.contract import (
    NO_DISCOUNT,
    civil_retention,
    civil_total,
    drilling_totals,
    load_contract,
    rate_history,
    retroactive_instruments,
    round_civil,
    round_drilling,
    term,
)
from audit.io import AuditData, to_cents
from audit.linker import (
    civil_payable_quantity,
    civil_reading,
    record_for,
    report_for,
    report_quantity,
)
from audit.pricing import LinePrice, civil, drilling

PER_CATEGORY = 10  # positives per category and set: 120 of about 1,280 invoices (~9%)
DISCOUNT_CODE = "DS-900"
BROKEN_BY = Decimal("10.00")  # added to a line amount to plant an arithmetic error
OVER_RECORD = Decimal("1.10")  # quantity planted 10% above the record (beyond Cl.33A 2%)
MISSING_REPORT = "DDR-000-19000101"
CATEGORIES = (
    "superseded_rate",
    "rate_buildup",
    "discount_misapplied",
    "quantity_over_record",
    "missing_record",
    "duplicate_charge",
    "outside_term",
    "invoice_window",
    "wrong_contract_ref",
    "limit_exceeded",
    "retro_adjustment",
    "arithmetic",
)


@dataclass
class Frames:
    """Mutable copies of the four invoice tables of one evaluation set."""

    civil_apps: pd.DataFrame
    civil_lines: pd.DataFrame
    drill_invoices: pd.DataFrame
    drill_lines: pd.DataFrame


@dataclass(frozen=True)
class Label:
    """One planted error: the invoice, its category and the total the contract supports."""

    invoice_id: str
    category: str
    true_expected_total_cents: int


# ---- totals, as a contractor's system builds them ----------------------------------------


def civil_restate(frames: Frames, app_id: str) -> Decimal:
    """Recompute an application's total, retention and net from its lines; return the total."""
    lines = frames.civil_lines[frames.civil_lines["application_no"] == app_id]
    total = civil_total(lines["amount"])
    row = frames.civil_apps["application_no"] == app_id
    retention = civil_retention(total)
    frames.civil_apps.loc[row, "application_total"] = total
    frames.civil_apps.loc[row, "retention"] = retention
    frames.civil_apps.loc[row, "net_payable"] = total - retention
    return total


def drilling_restate(frames: Frames, invoice_id: str) -> Decimal:
    """Recompute an invoice's DS-900 line, net, VAT and total; return the total."""
    lines = frames.drill_lines
    own = lines["invoice_no"] == invoice_id
    services = lines.loc[own & (lines["service_code"] != DISCOUNT_CODE), "amount"]
    totals = drilling_totals(services)
    discount = own & (lines["service_code"] == DISCOUNT_CODE)
    lines.loc[discount, "amount"] = totals.discount
    lines.loc[discount, "unit_rate"] = totals.discount
    row = frames.drill_invoices["invoice_no"] == invoice_id
    frames.drill_invoices.loc[row, "net_amount"] = totals.net
    frames.drill_invoices.loc[row, "vat_amount"] = totals.vat
    frames.drill_invoices.loc[row, "invoice_total"] = totals.total
    return totals.total


def expected_without(frames: Frames, invoice_id: str, line_ref: str) -> Decimal:
    """Return the invoice total the contract supports once one line is set to zero."""
    if invoice_id.startswith("PA-"):
        lines = frames.civil_lines
        kept = lines[(lines["application_no"] == invoice_id) & (lines["line_ref"] != line_ref)]
        return civil_total(kept["amount"])
    lines = frames.drill_lines
    kept = lines[
        (lines["invoice_no"] == invoice_id)
        & (lines["line_ref"] != line_ref)
        & (lines["service_code"] != DISCOUNT_CODE)
    ]
    return drilling_totals(kept["amount"]).total


def set_line(frames: Frames, line_ref: str, **values: object) -> None:
    """Change fields of one line and recompute its amount as quantity x rate."""
    civil_line = line_ref.startswith("PA-")
    lines = frames.civil_lines if civil_line else frames.drill_lines
    row = lines["line_ref"] == line_ref
    for column, value in values.items():
        lines.loc[row, column] = value
    if "amount" in values:
        return
    rate_col = "rate_applied" if civil_line else "unit_rate"
    quantity, rate = lines.loc[row, "quantity"].iloc[0], lines.loc[row, rate_col].iloc[0]
    rounding = round_civil if civil_line else round_drilling
    lines.loc[row, "amount"] = rounding(quantity * rate)


def restate(frames: Frames, invoice_id: str) -> Decimal:
    """Recompute an invoice's totals from its lines; return the new billed total."""
    if invoice_id.startswith("PA-"):
        return civil_restate(frames, invoice_id)
    return drilling_restate(frames, invoice_id)


def billed_total(frames: Frames, invoice_id: str) -> Decimal:
    """Return an invoice's judged total as it stands in the set."""
    if invoice_id.startswith("PA-"):
        apps = frames.civil_apps
        return apps.loc[apps["application_no"] == invoice_id, "application_total"].iloc[0]
    invoices = frames.drill_invoices
    return invoices.loc[invoices["invoice_no"] == invoice_id, "invoice_total"].iloc[0]


# ---- planters: each returns the true expected total, or None if the invoice does not fit --

Planter = Callable[["Context", str], Decimal | None]


@dataclass
class Context:
    """What the planters read: the original data, its prices, and the set being built."""

    data: AuditData
    frames: Frames
    civil_prices: dict[str, LinePrice]
    drill_prices: dict[str, LinePrice]
    rng: random.Random


def lines_of(ctx: Context, invoice_id: str) -> pd.DataFrame:
    """Return an invoice's lines in the set, DS-900 excluded, in a shuffled but fixed order."""
    if invoice_id.startswith("PA-"):
        lines = ctx.frames.civil_lines[ctx.frames.civil_lines["application_no"] == invoice_id]
    else:
        lines = ctx.frames.drill_lines[
            (ctx.frames.drill_lines["invoice_no"] == invoice_id)
            & (ctx.frames.drill_lines["service_code"] != DISCOUNT_CODE)
        ]
    order = list(range(len(lines)))
    ctx.rng.shuffle(order)
    return lines.iloc[order]


def price_of(ctx: Context, line_ref: str) -> LinePrice | None:
    """Return the engine price of an original line, single-part lines only."""
    prices = ctx.civil_prices if line_ref.startswith("PA-") else ctx.drill_prices
    price = prices.get(line_ref)
    return price if price is not None and len(price.parts) == 1 else None


def reprice(ctx: Context, line: object, price: LinePrice, **change: object) -> LinePrice | None:
    """Price a line with another base rate, discount or factors."""
    base, discount = change.get("base", price.base), change.get("discount", price.discount)
    if line.line_ref.startswith("PA-"):
        return civil.repriced(line, price, base, discount)
    well_class = ctx.data.drill_invoices.set_index("invoice_no").loc[line.invoice_no, "well_class"]
    return drilling.repriced(line, well_class, base, discount)


def plant_rate(ctx: Context, invoice_id: str, new_price: LinePrice, line: object) -> Decimal:
    """Bill a line at a new price; return the original total (the contract price)."""
    original = billed_total(ctx.frames, invoice_id)
    rate_col = "rate_applied" if invoice_id.startswith("PA-") else "unit_rate"
    set_line(ctx.frames, line.line_ref, **{rate_col: new_price.rate})
    restate(ctx.frames, invoice_id)
    return original


def superseded_rate(ctx: Context, invoice_id: str) -> Decimal | None:
    """Bill a line at the rate an instrument replaced (guideline 7)."""
    code_col = "item_code" if invoice_id.startswith("PA-") else "service_code"
    contract = "civil" if invoice_id.startswith("PA-") else "drilling"
    for line in lines_of(ctx, invoice_id).itertuples(index=False):
        price = price_of(ctx, line.line_ref)
        if price is None or not price.base.reference:
            continue
        older = [
            r
            for r in rate_history(contract, getattr(line, code_col))
            if r.value != price.base.value
        ]
        for rate in older[:1]:
            again = reprice(ctx, line, price, base=rate)
            if again is not None and again.rate != price.rate:
                return plant_rate(ctx, invoice_id, again, line)
    return None


def rate_buildup(ctx: Context, invoice_id: str) -> Decimal | None:
    """Bill a line with a wrong zone, ground, section or class factor (guideline 8)."""
    wanted = ("zone", "ground") if invoice_id.startswith("PA-") else ("section", "class")
    for line in lines_of(ctx, invoice_id).itertuples(index=False):
        price = price_of(ctx, line.line_ref)
        if price is None:
            continue
        if invoice_id.startswith("PA-"):
            options = civil.variants(line, price)
        else:
            klass = ctx.data.drill_invoices.set_index("invoice_no").loc[invoice_id, "well_class"]
            options = drilling.variants(line, klass, price)
        for name, other in options:
            if name.startswith(wanted) and other.rate != price.rate:
                return plant_rate(ctx, invoice_id, other, line)
    return None


def discount_misapplied(ctx: Context, invoice_id: str) -> Decimal | None:
    """Bill a discounted line without its discount (guideline 8)."""
    for line in lines_of(ctx, invoice_id).itertuples(index=False):
        price = price_of(ctx, line.line_ref)
        if price is None or not price.discount.percent:
            continue
        again = reprice(ctx, line, price, discount=NO_DISCOUNT)
        if again is not None and again.rate != price.rate:
            return plant_rate(ctx, invoice_id, again, line)
    return None


def retro_adjustment(ctx: Context, invoice_id: str) -> Decimal | None:
    """Bill a retroactive rate before its instrument's issue ("taken early", Cl.31A/36A)."""
    contract = "civil" if invoice_id.startswith("PA-") else "drilling"
    code_col, date_col = (
        ("item_code", "work_date") if contract == "civil" else ("service_code", "service_date")
    )
    submitted = submission_date(ctx, invoice_id)
    for instrument in retroactive_instruments(contract):
        issued = pd.Timestamp(instrument["issued"]["value"]).date()
        if submitted >= issued:
            continue
        for line in lines_of(ctx, invoice_id).itertuples(index=False):
            price = price_of(ctx, line.line_ref)
            entry = instrument["rates"].get(getattr(line, code_col))
            if price is None or entry is None:
                continue
            if getattr(line, date_col) < pd.Timestamp(entry["effective"]).date():
                continue
            new_rate = replace(
                price.base,
                value=Decimal(entry["value"]),
                reference=instrument["reference"],
                month="",
            )
            again = reprice(ctx, line, price, base=new_rate)
            if again is not None and again.rate != price.rate:
                return plant_rate(ctx, invoice_id, again, line)
    return None


def quantity_over_record(ctx: Context, invoice_id: str) -> Decimal | None:
    """Bill a line 10% (at least one unit) above its record (guideline 5)."""
    banded = set(load_contract("civil")["bands"])
    for line in lines_of(ctx, invoice_id).itertuples(index=False):
        if invoice_id.startswith("PA-"):
            record = record_for(ctx.data, line.record_ref.strip())
            if record is None or line.item_code in banded:
                continue
            supported = civil_payable_quantity(record, civil_reading(record))
        else:
            report = report_for(ctx.data, line.report_ref)
            supported = None if report is None else report_quantity(line.service_code, report)
        if supported is None or supported == 0 or line.quantity != supported:
            continue
        original = billed_total(ctx.frames, invoice_id)
        more = max((supported * OVER_RECORD).to_integral_value(), supported + 1)
        set_line(ctx.frames, line.line_ref, quantity=more)
        restate(ctx.frames, invoice_id)
        return original
    return None


def banded(line: object) -> bool:
    """Tell whether a line counts towards quantity bands (civil Sch.4 Pt3, PD-210 metres).

    Removing such a line from the count moves the bands of later lines on other invoices
    (D19); planting on it would add false flags that come from the injection, not the audit.
    """
    code = getattr(line, "item_code", None) or line.service_code
    return code in load_contract("civil")["bands"] or code == "PD-210"


def missing_record(ctx: Context, invoice_id: str) -> Decimal | None:
    """Blank a Schedule 5 record reference, or cite a report that does not exist (guideline 4)."""
    for line in lines_of(ctx, invoice_id).itertuples(index=False):
        if banded(line):
            continue
        if invoice_id.startswith("PA-"):
            if not line.record_ref.strip():
                continue
            set_line(ctx.frames, line.line_ref, record_ref="", amount=line.amount)
        else:
            set_line(ctx.frames, line.line_ref, report_ref=MISSING_REPORT, amount=line.amount)
        return expected_without(ctx.frames, invoice_id, line.line_ref)
    return None


def duplicate_charge(ctx: Context, invoice_id: str) -> Decimal | None:
    """Bill one line twice on the same invoice (guideline 10)."""
    civil_invoice = invoice_id.startswith("PA-")
    limited = set(load_contract("civil" if civil_invoice else "drilling")["daily_limits"])
    for line in lines_of(ctx, invoice_id).itertuples(index=False):
        code = line.item_code if civil_invoice else line.service_code
        if civil_invoice and code in limited:
            continue  # a copy of a capped item would also break the cap (c09 runs first)
        original = billed_total(ctx.frames, invoice_id)
        lines = ctx.frames.civil_lines if civil_invoice else ctx.frames.drill_lines
        id_col = "application_no" if civil_invoice else "invoice_no"
        copy = lines[lines["line_ref"] == line.line_ref].copy()
        last = int(lines.loc[lines[id_col] == invoice_id, "line_no"].astype(int).max()) + 1
        copy["line_no"] = str(last)
        copy["line_ref"] = (
            f"{invoice_id}-{last:03d}" if not civil_invoice else f"{invoice_id}-{last:02d}"
        )
        frame = pd.concat([lines, copy], ignore_index=True)
        if civil_invoice:
            ctx.frames.civil_lines = frame
        else:
            ctx.frames.drill_lines = frame
        restate(ctx.frames, invoice_id)
        return original
    return None


def outside_term(ctx: Context, invoice_id: str) -> Decimal | None:
    """Date one line before the Commencement Date (guideline 2)."""
    contract = "civil" if invoice_id.startswith("PA-") else "drilling"
    date_col = "work_date" if contract == "civil" else "service_date"
    start = term(contract, "commencement").value
    for line in lines_of(ctx, invoice_id).itertuples(index=False):
        if banded(line):
            continue
        set_line(
            ctx.frames,
            line.line_ref,
            **{date_col: start - timedelta(days=3), "amount": line.amount},
        )
        return expected_without(ctx.frames, invoice_id, line.line_ref)
    return None


def invoice_window(ctx: Context, invoice_id: str) -> Decimal | None:
    """Submit the invoice after its window (guideline 3); the work is still payable (D05)."""
    contract = "civil" if invoice_id.startswith("PA-") else "drilling"
    days = int(term(contract, "window_days").value)
    period_end = period_end_of(ctx, invoice_id)
    late = period_end + timedelta(days=days + 5)
    if issued_between(contract, submission_date(ctx, invoice_id), late):
        return None  # a later date would bring a new instrument into force (D16)
    if contract == "civil":
        apps = ctx.frames.civil_apps
        row = apps["application_no"] == invoice_id
        apps.loc[row, "application_date"] = late
    else:
        invoices = ctx.frames.drill_invoices
        row = invoices["invoice_no"] == invoice_id
        invoices.loc[row, "invoice_date"] = late
    return billed_total(ctx.frames, invoice_id)


def wrong_contract_ref(ctx: Context, invoice_id: str) -> Decimal | None:
    """Quote a contract reference with two digits swapped (guideline 1)."""
    contract = "civil" if invoice_id.startswith("PA-") else "drilling"
    ref = str(term(contract, "contract_ref").value)
    wrong = ref[:-2] + ref[-1] + ref[-2] if ref[-1].isdigit() else ref.replace("0417", "0471")
    headers = ctx.frames.civil_apps if contract == "civil" else ctx.frames.drill_invoices
    id_col = "application_no" if contract == "civil" else "invoice_no"
    headers.loc[headers[id_col] == invoice_id, "contract_ref"] = wrong
    return billed_total(ctx.frames, invoice_id)


def limit_exceeded(ctx: Context, invoice_id: str) -> Decimal | None:
    """Bill a capped civil item above its daily limit, without a record to contradict it."""
    if not invoice_id.startswith("PA-"):
        return None
    contract = load_contract("civil")
    limits, banded = contract["daily_limits"], set(contract["bands"])
    all_lines = ctx.data.civil_lines
    for line in lines_of(ctx, invoice_id).itertuples(index=False):
        entry = limits.get(line.item_code)
        if entry is None or line.item_code in banded or line.record_ref.strip():
            continue
        same_day = all_lines[
            (all_lines["item_code"] == line.item_code)
            & (all_lines["site"] == line.site)
            & (all_lines["work_date"] == line.work_date)
        ]
        if len(same_day) != 1:
            continue
        cap = Decimal(entry["value"])
        more = cap + max(Decimal(1), (cap / 10).to_integral_value())
        set_line(ctx.frames, line.line_ref, quantity=more)
        restate(ctx.frames, invoice_id)
        lines = ctx.frames.civil_lines[ctx.frames.civil_lines["application_no"] == invoice_id]
        capped = round_civil(cap * line.rate_applied)
        return (
            civil_total(lines["amount"])
            - lines.loc[lines["line_ref"] == line.line_ref, "amount"].iloc[0]
            + capped
        )
    return None


def arithmetic(ctx: Context, invoice_id: str) -> Decimal | None:
    """Break one line amount (quantity x rate no longer holds); totals follow the lines."""
    for line in lines_of(ctx, invoice_id).itertuples(index=False):
        original = billed_total(ctx.frames, invoice_id)
        set_line(ctx.frames, line.line_ref, amount=line.amount + BROKEN_BY)
        restate(ctx.frames, invoice_id)
        return original
    return None


PLANTERS: dict[str, Planter] = {
    "superseded_rate": superseded_rate,
    "rate_buildup": rate_buildup,
    "discount_misapplied": discount_misapplied,
    "quantity_over_record": quantity_over_record,
    "missing_record": missing_record,
    "duplicate_charge": duplicate_charge,
    "outside_term": outside_term,
    "invoice_window": invoice_window,
    "wrong_contract_ref": wrong_contract_ref,
    "limit_exceeded": limit_exceeded,
    "retro_adjustment": retro_adjustment,
    "arithmetic": arithmetic,
}


def period_end_of(ctx: Context, invoice_id: str) -> date:
    """Return the last day of the period an invoice states."""
    if invoice_id.startswith("PA-"):
        apps = ctx.frames.civil_apps
        return apps.loc[apps["application_no"] == invoice_id, "period_to"].iloc[0]
    invoices = ctx.frames.drill_invoices
    return invoices.loc[invoices["invoice_no"] == invoice_id, "period_end"].iloc[0]


def issued_between(contract: str, start: date, end: date) -> bool:
    """Tell whether any instrument of the contract is issued after `start`, up to `end`."""
    for instrument in load_contract(contract)["instruments"]:
        issued = date.fromisoformat(instrument["issued"]["value"])
        if start < issued <= end:
            return True
    return False


def submission_date(ctx: Context, invoice_id: str) -> date:
    """Return an invoice's submission date in the set."""
    if invoice_id.startswith("PA-"):
        apps = ctx.frames.civil_apps
        return apps.loc[apps["application_no"] == invoice_id, "application_date"].iloc[0]
    invoices = ctx.frames.drill_invoices
    return invoices.loc[invoices["invoice_no"] == invoice_id, "invoice_date"].iloc[0]


def build_set(
    data: AuditData,
    pool: list[str],
    seed: int,
    civil_prices: dict[str, LinePrice],
    drill_prices: dict[str, LinePrice],
) -> tuple[AuditData, list[Label], list[str]]:
    """Plant PER_CATEGORY errors per category in a pool of clean invoices.

    Returns the modified data, the labels, and the invoice ids of the set (positives and
    negatives). Categories alternate between the contracts where both can carry them.
    """
    rng = random.Random(seed)
    frames = Frames(
        data.civil_apps.copy(),
        data.civil_lines.copy(),
        data.drill_invoices.copy(),
        data.drill_lines.copy(),
    )
    ctx = Context(data, frames, civil_prices, drill_prices, rng)
    candidates = sorted(pool)
    rng.shuffle(candidates)
    labels: list[Label] = []
    used: set[str] = set()
    for category in CATEGORIES:
        planted = 0
        for invoice_id in candidates:
            if planted == PER_CATEGORY:
                break
            wants_civil = planted % 2 == 0 or category == "limit_exceeded"
            if invoice_id in used or invoice_id.startswith("PA-") != wants_civil:
                continue
            expected = PLANTERS[category](ctx, invoice_id)
            if expected is None:
                continue
            used.add(invoice_id)
            labels.append(Label(invoice_id, category, to_cents(expected)))
            planted += 1
    modified = replace(
        data,
        civil_apps=frames.civil_apps,
        civil_lines=frames.civil_lines,
        drill_invoices=frames.drill_invoices,
        drill_lines=frames.drill_lines,
    )
    return modified, labels, sorted(pool)
