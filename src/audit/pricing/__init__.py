"""Pricing engine: the contract rate and amount of every invoice line (Phase 3).

`civil.price_lines` and `drilling.price_lines` read the loaded invoices (`io.AuditData`) and
the extracted contract terms, and return one `LinePrice` per line they can price. This
module holds what both contracts share: the priced-line record and the split of a quantity
across cumulative bands (civil Sch.4 Pt3, drilling Sch.2 Pt2).
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable, Hashable, Sequence
from dataclasses import dataclass
from decimal import Decimal

import pandas as pd

from audit.contract import DiscountOn, RateOn

HUNDRED = Decimal(100)


@dataclass(frozen=True)
class Band:
    """One cumulative band: the quantity it ends at (None = open) and its percentage."""

    upper: Decimal | None
    percent: Decimal


@dataclass(frozen=True)
class Part:
    """One part of a line priced at a single rate (a line crossing a band has several)."""

    quantity: Decimal
    percent: Decimal  # band percentage of the rate (100 when no band applies)
    rate: Decimal  # built-up rate, rounded the contract's way


@dataclass(frozen=True)
class LinePrice:
    """The contract price of one invoice line, with the values it was built from."""

    line_ref: str
    base: RateOn  # rate in force on the work date (Schedule 1 or an instrument)
    discount: DiscountOn
    parts: tuple[Part, ...]
    amount: Decimal

    @property
    def rate(self) -> Decimal:
        """Return the rate of the first part: the rate an invoice line states."""
        return self.parts[0].rate

    @property
    def period(self) -> str:
        """Return the rate period label: the instrument (and month) and discount in force."""
        label = schedule_label(self.base)
        if self.base.month:
            label += f" {self.base.month}"
        if self.discount.percent:
            label += f", discount {self.discount.percent}%"
        return label


def schedule_label(rate: RateOn) -> str:
    """Name where a rate comes from: the instrument, else the schedule in its source."""
    if rate.reference:
        return rate.reference
    # A schedule rate's source reads "p.<page> <schedule>", e.g. "p.17 Schedule 2".
    return rate.source.split(" ", 1)[1]


def band_parts(
    bands: Sequence[Band], done: Decimal, quantity: Decimal
) -> list[tuple[Decimal, Decimal]]:
    """Split a quantity across cumulative bands; return (quantity, percent) per part.

    `done` is the quantity already counted in the year before this line. A quantity that
    crosses a band limit is divided at the limit, each part at its band's percentage (civil
    Sch.4 Pt3 p.24, drilling Sch.2 Pt2 p.17).
    """
    start, end = done, done + quantity
    parts = []
    lower = Decimal(0)
    for band in bands:
        upper = end if band.upper is None else band.upper
        overlap = min(end, upper) - max(start, lower)
        if overlap > 0:
            parts.append((overlap, band.percent))
        if band.upper is None:
            break
        lower = band.upper
    return parts


def bands_from(entries: Sequence[dict], upper_key: str) -> tuple[Band, ...]:
    """Build bands from their contract JSON entries (upper limit and percentage)."""
    return tuple(
        Band(
            None if entry[upper_key] is None else Decimal(entry[upper_key]), Decimal(entry["value"])
        )
        for entry in entries
    )


def cumulative_splits(
    ordered: pd.DataFrame,
    group_of: Callable[[object], Hashable],
    bands_of: Callable[[object], Sequence[Band]],
    unmeasured: frozenset[str],
) -> dict[str, list[tuple[Decimal, Decimal]]]:
    """Split each line across cumulative bands counted per group, in the order given.

    Only payable lines add to the count ("the quantity measured", Sch.4 Pt3 p.24; D19): a
    line in `unmeasured` is split at the count reached, but its quantity is not counted.
    """
    done: dict[Hashable, Decimal] = defaultdict(Decimal)
    splits = {}
    for line in ordered.itertuples(index=False):
        group = group_of(line)
        splits[line.line_ref] = band_parts(bands_of(line), done[group], line.quantity)
        if line.line_ref not in unmeasured:
            done[group] += line.quantity
    return splits
