"""Check the extracted contract values against the invoices (Phase 2 calibration).

Input: the contract dicts built by extract.civil / extract.drilling and the invoice files.
Output: the same dicts with `verified` / `evidence` set, and a report of what each check
found. Checks:
- completeness: every code billed on an invoice line exists in Schedule 1;
- rate calibration: for every line in its item's base period (before any instrument names
  the item), the billed rate is rebuilt from the base rate and the factors the contract's
  clauses say apply. A value is verified when it reproduces the billed rate exactly on at
  least MIN_MATCHES lines; a misread digit reproduces none;
- header rules: retention (civil), VAT and the DS-900 discount (drilling) against every
  invoice header.
Values the invoices cannot confirm are listed for the eye check (see eye_check_list).
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date
from decimal import ROUND_DOWN, ROUND_HALF_EVEN, ROUND_HALF_UP, Decimal

import pandas as pd

MIN_MATCHES = 3  # exact reproductions needed before a value counts as verified
CENT = Decimal("0.01")
HUNDRED = Decimal(100)
WEEKDAYS = {
    "Monday": 0,
    "Tuesday": 1,
    "Wednesday": 2,
    "Thursday": 3,
    "Friday": 4,
    "Saturday": 5,
    "Sunday": 6,
}
DISCOUNT_CODE = "DS-900"
NOT_CHARGEABLE = "not chargeable"


@dataclass
class Tally:
    """Per value: the term dict, lines that reproduced the billed rate, and lines that did not."""

    terms: dict[str, dict] = field(default_factory=dict)
    matched: dict[str, int] = field(default_factory=lambda: defaultdict(int))
    missed: dict[str, int] = field(default_factory=lambda: defaultdict(int))

    def record(self, used: dict[str, dict], reproduced: bool) -> None:
        """Count one line against every value it used."""
        for path, entry in used.items():
            self.terms[path] = entry
            if reproduced:
                self.matched[path] += 1
            else:
                self.missed[path] += 1

    def mark(self) -> list[dict]:
        """Set verified / evidence on every counted value; return one report row per value.

        A month table (index, exchange rate) is verified month by month: it is verified as a
        whole only when every month the invoices use reproduces at least MIN_MATCHES lines.
        """
        rows = []
        month_tables: dict[int, tuple[dict, list[str], list[str]]] = {}
        for path in sorted(self.terms):
            matched, missed = self.matched[path], self.missed[path]
            entry = self.terms[path]
            rows.append({"value": path, "matched": matched, "lines": matched + missed})
            if isinstance(entry["value"], dict):
                _, confirmed, unconfirmed = month_tables.setdefault(id(entry), (entry, [], []))
                month = path.rsplit(".", 1)[1]
                (confirmed if matched >= MIN_MATCHES else unconfirmed).append(month)
            elif matched >= MIN_MATCHES:
                entry["verified"] = True
                entry["evidence"] = (
                    f"calibration: reproduces the billed rate on {matched} of "
                    f"{matched + missed} lines"
                )
        for entry, confirmed, unconfirmed in month_tables.values():
            entry["confirmed_months"] = confirmed
            entry["verified"] = not unconfirmed
            entry["evidence"] = f"calibration: {len(confirmed)} months reproduce billed rates" + (
                f"; not confirmed: {', '.join(unconfirmed)}" if unconfirmed else ""
            )
        return rows


def value(entry: dict) -> Decimal:
    """Return a term's value as Decimal."""
    return Decimal(entry["value"])


def month_of(day: date) -> str:
    """'2025-03' for a date in March 2025."""
    return f"{day.year}-{day.month:02d}"


def first_change(instruments: list[dict]) -> dict[str, date]:
    """Item -> earliest date any instrument changes its rate or discount (ends the base period)."""
    earliest: dict[str, date] = {}

    def note(item: str, day: str) -> None:
        start = date.fromisoformat(day)
        earliest[item] = min(start, earliest.get(item, start))

    for instrument in instruments:
        for item, entry in instrument["rates"].items():
            note(item, entry["effective"])
        for item in instrument["monthly_rates"]:
            note(item, instrument["effective"]["value"])
        if instrument["discount"]:
            for item in instrument["discount"]["items"]:
                note(item, instrument["discount"]["start"])
    return earliest


def missing_codes(items: dict[str, dict], billed_codes: set[str]) -> list[str]:
    """Codes billed on an invoice line but absent from Schedule 1 (an OCR miss if not empty)."""
    return sorted(billed_codes - set(items))


# ---- civil --------------------------------------------------------------------------------


def civil_rate(contract: dict, terms: dict, line: object) -> tuple[Decimal, dict[str, dict]]:
    """Return the base-period rate the contract gives a civil line, and the values used.

    Cl.27 p.6: base -> zone (Sch.2, Series A-D only) -> ground (Sch.3 listed items) -> night
    uplift -> rest-day uplift, rounded once half up (Cl.28). Cl.26A / Cl.29A: USD and indexed
    base rates are converted first and rounded half to even. Cl.27A: no night uplift where
    the zone factor exceeds 1.1; ground taken as G2 for work after 27 September 2025.
    P11: night and rest day together -> the rest-day uplift alone.
    """
    item, used = line.item_code, {}
    month = month_of(line.work_date)
    if item in contract["usd"]["items"]:
        usd_entry = contract["usd"]["items"][item]
        exchange = contract["usd"]["halalas_per_usd"]
        rate = value(usd_entry) * Decimal(exchange["value"][month]) / HUNDRED
        rate = rate.quantize(CENT, ROUND_HALF_EVEN)
        used |= {f"usd.items.{item}": usd_entry, f"usd.halalas_per_usd.{month}": exchange}
    elif item in contract["indexed"]["items"]:
        base_entry = contract["indexed"]["items"][item]
        index = contract["indexed"]["index"]
        rate = value(base_entry) * Decimal(index["value"][month]) / value(terms["index_base"])
        rate = rate.quantize(CENT, ROUND_HALF_EVEN)
        used |= {
            f"indexed.items.{item}": base_entry,
            f"indexed.index.{month}": index,
            "terms.index_base": terms["index_base"],
        }
    else:
        base_entry = contract["items"][item]["rate"]
        rate = value(base_entry)
        used[f"items.{item}.rate"] = base_entry

    zone_factor = Decimal(1)
    if item[0] in terms["zone_factor_series"]["value"]:
        zone = line.site_zone.split()[0]
        zone_entry = contract["zone_factors"][zone]
        zone_factor = value(zone_entry)
        used[f"zone_factors.{zone}"] = zone_entry
    rate *= zone_factor

    ground_items = contract["ground"]["items"]["value"]
    if item in ground_items and line.ground_class:
        after = date.fromisoformat(terms["ground_datum_after"]["value"])
        ground = terms["ground_datum_class"]["value"]
        if line.work_date <= after:
            ground = line.ground_class.split()[0]
        ground_entry = contract["ground"]["factors"][ground]
        rate *= value(ground_entry)
        used[f"ground.factors.{ground}"] = ground_entry

    rest_days = {WEEKDAYS[name] for name in terms["rest_days"]["value"]}
    on_rest_day = line.work_date.weekday() in rest_days and item in contract["rest_day_uplift"]
    night_allowed = zone_factor <= value(terms["night_uplift_max_zone_factor"])
    at_night = line.night_work == "Y" and item in contract["night_uplift"] and night_allowed
    if on_rest_day:
        uplift = contract["rest_day_uplift"][item]
        rate *= 1 + value(uplift) / HUNDRED
        used[f"rest_day_uplift.{item}"] = uplift
    elif at_night:
        uplift = contract["night_uplift"][item]
        rate *= 1 + value(uplift) / HUNDRED
        used[f"night_uplift.{item}"] = uplift
    return rate.quantize(CENT, ROUND_HALF_UP), used


def calibrate_civil(contract: dict, terms: dict, lines: pd.DataFrame) -> list[dict]:
    """Rebuild every base-period civil line's rate and mark the values that reproduce it."""
    tally = Tally()
    changes = first_change(contract["instruments"])
    for line in lines.itertuples(index=False):
        change = changes.get(line.item_code)
        if change is not None and line.work_date >= change:
            continue
        rate, used = civil_rate(contract, terms, line)
        tally.record(used, rate == line.rate_applied)
    return tally.mark()


def check_retention(terms: dict, apps: pd.DataFrame) -> str:
    """Cl.45: retention = 5% of the total rounded down, on every application header."""
    percent = value(terms["retention_pct"])
    agree = sum(
        (total * percent / HUNDRED).quantize(CENT, ROUND_DOWN) == retention
        for total, retention in zip(apps["application_total"], apps["retention"], strict=True)
    )
    evidence = f"header check: retention reproduced on {agree} of {len(apps)} applications"
    for key in ("retention_pct", "retention_rounding"):
        if agree >= MIN_MATCHES:
            terms[key]["verified"], terms[key]["evidence"] = True, evidence
    return evidence


def check_reference(terms: dict, headers: pd.DataFrame, ref_column: str, issuer_column: str) -> str:
    """Contract reference and issuer: verified when the invoice headers carry them."""
    parts = []
    for key, column in (("contract_ref", ref_column), ("issuer", issuer_column)):
        expected = str(terms[key]["value"]).casefold()
        agree = int((headers[column].str.casefold() == expected).sum())
        if agree >= MIN_MATCHES:
            terms[key]["verified"] = True
            terms[key]["evidence"] = f"data: {agree} of {len(headers)} invoice headers"
        parts.append(f"{key} on {agree} of {len(headers)} headers")
    return "reference check: " + ", ".join(parts)


def check_record_series(contract: dict, lines: pd.DataFrame) -> str:
    """Schedule 5: a series is verified when lines for its item quote refs of that series."""
    verified = 0
    for item, entry in contract["record_series"].items():
        refs = lines.loc[lines["item_code"] == item, "record_ref"]
        agree = int(refs.str.startswith(entry["value"] + "-").sum())
        if agree >= MIN_MATCHES:
            entry["verified"] = True
            entry["evidence"] = f"data: {agree} of {len(refs)} lines quote a {entry['value']} ref"
            verified += 1
    return f"record series: {verified} of {len(contract['record_series'])} confirmed by line refs"


# ---- drilling -----------------------------------------------------------------------------


def _half_even(amount: Decimal) -> Decimal:
    return amount.quantize(CENT, ROUND_HALF_EVEN)


def drilling_rate(
    contract: dict, terms: dict, line: object, well_class: str
) -> tuple[Decimal | None, dict[str, dict]]:
    """Return the base-period rate the contract gives a drilling line, and the values used.

    Cl.18 p.6: Schedule 1 rate (PD-210: Schedule 2 depth band) -> hole-section factor
    (section-rated) -> well-class factor (class-rated) -> standby %, each step rounded half to
    even (Cl.17). Cl.17A: indexed services are converted first. Cl.17B: no section factor on
    Standby, no class factor on PD-210. None when the contract gives no rate to rebuild.
    """
    code, used = line.service_code, {}
    if code == "PD-210":
        band = depth_band(contract["depth_bands"], line.depth_to_m)
        rate = value(band)
        used[f"depth_bands.{band['band']}"] = band
    elif code in contract["indexed"]["items"]:
        base_entry = contract["indexed"]["items"][code]
        index = contract["indexed"]["index"]
        month = month_of(line.service_date)
        if month not in index["value"]:
            return None, {}  # a month the index does not cover (work after the term)
        rate = _half_even(
            value(base_entry) * Decimal(index["value"][month]) / value(terms["index_base"])
        )
        used |= {
            f"indexed.items.{code}": base_entry,
            f"indexed.index.{month}": index,
            "terms.index_base": terms["index_base"],
        }
    else:
        base_entry = contract["items"][code]["rate"]
        if not base_entry["value"][0].isdigit():
            return None, {}  # e.g. lost in hole: priced under Cl.31, not a rate
        rate = value(base_entry)
        used[f"items.{code}.rate"] = base_entry

    standby = line.day_status == "Standby"
    sections = contract["section_factors"]
    if code in sections["items"]["value"] and not standby:
        factor = sections["factors"][line.hole_section]
        rate = _half_even(rate * value(factor))
        used[f"section_factors.{line.hole_section}"] = factor
    classes = contract["class_factors"]
    if code in classes["items"]["value"] and code != "PD-210":
        factor = classes["factors"][well_class]
        rate = _half_even(rate * value(factor))
        used[f"class_factors.{well_class}"] = factor
    if standby:
        entry = contract["standby"].get(code)
        if entry is None or entry["value"] == NOT_CHARGEABLE:
            return None, {}  # not chargeable on Standby: a P3 check, not a rate to rebuild
        rate = _half_even(rate * value(entry) / HUNDRED)
        used[f"standby.{code}"] = entry
    return rate, used


def depth_band(bands: list[dict], depth_to: Decimal) -> dict:
    """Return the Schedule 2 band whose range holds the interval's deeper end.

    Cl.23: a boundary depth belongs to the shallower band.
    """
    for band in bands:
        lower, upper = Decimal(band["over_m"]), band["to_m"]
        if depth_to > lower and (upper is None or depth_to <= Decimal(upper)):
            return band
    raise ValueError(f"no Schedule 2 depth band holds {depth_to} m")


def calibrate_drilling(
    contract: dict, terms: dict, lines: pd.DataFrame, invoices: pd.DataFrame
) -> list[dict]:
    """Rebuild every base-period drilling line's rate and mark the values that reproduce it."""
    tally = Tally()
    changes = first_change(contract["instruments"])
    well_class = dict(zip(invoices["invoice_no"], invoices["well_class"], strict=True))
    for line in lines.itertuples(index=False):
        if line.service_code == DISCOUNT_CODE:
            continue
        change = changes.get(line.service_code)
        if change is not None and line.service_date >= change:
            continue
        rate, used = drilling_rate(contract, terms, line, well_class[line.invoice_no])
        if rate is not None:
            tally.record(used, rate == line.unit_rate)
    return tally.mark()


def check_vat_and_discount(terms: dict, invoices: pd.DataFrame, lines: pd.DataFrame) -> str:
    """Cl.38 and Cl.39: DS-900 and VAT reproduced on the invoice headers."""
    vat_pct = value(terms["vat_pct"])
    vat_agree = sum(
        _half_even(net * vat_pct / HUNDRED) == vat
        for net, vat in zip(invoices["net_amount"], invoices["vat_amount"], strict=True)
    )
    is_discount = lines["service_code"] == DISCOUNT_CODE
    services = lines[~is_discount].groupby("invoice_no")["amount"].sum()
    billed = lines[is_discount].groupby("invoice_no")["amount"].sum()
    threshold, pct = value(terms["discount_threshold"]), value(terms["discount_pct"])
    discount_agree = 0
    for invoice_no, total in services.items():
        expected = -_half_even((total - threshold) * pct / HUNDRED) if total > threshold else 0
        discount_agree += expected == billed.get(invoice_no, 0)
    vat_evidence = f"header check: VAT reproduced on {vat_agree} of {len(invoices)} invoices"
    discount_evidence = (
        f"header check: DS-900 reproduced on {discount_agree} of {len(services)} invoices"
    )
    for key, evidence, agree in (
        ("vat_pct", vat_evidence, vat_agree),
        ("rounding", vat_evidence, vat_agree),
        ("discount_threshold", discount_evidence, discount_agree),
        ("discount_pct", discount_evidence, discount_agree),
    ):
        if agree >= MIN_MATCHES:
            terms[key]["verified"], terms[key]["evidence"] = True, evidence
    return f"{vat_evidence}; {discount_evidence}"
