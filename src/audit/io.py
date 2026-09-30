"""Load the invoice CSVs with dates as datetime.date and money as Decimal.

Input: the four invoice files, the submission template and the civil record file names,
all under DATA_DIR. Output: pandas DataFrames (and `AuditData`, everything loaded once).
Every file is read as text first, so pandas never guesses a type and no float touches money;
then each date or number column is parsed strictly. A value that does not match its format
raises with the file, column and value, rather than silently becoming NaN. Blank cells become
None (the 63 DS-900 discount lines have no service_date; most lines have no depth).
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from pathlib import Path

import pandas as pd

from audit.config import InputPaths, input_paths

# Month names are mapped by hand: strptime("%b") depends on the OS locale.
MONTHS = {
    name: number
    for number, name in enumerate(
        ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
        start=1,
    )
}
ISO_DATE = re.compile(r"(\d{4})-(\d{2})-(\d{2})")  # civil invoices: 2025-09-25
RECORD_DATE = re.compile(r"(\d{2})/(\d{2})/(\d{4})")  # civil records: 09/01/2025
DRILLING_DATE = re.compile(r"(\d{2})-([A-Z][a-z]{2})-(\d{4})")  # drilling: 01-Jan-2025
PLAIN_NUMBER = re.compile(r"-?\d+(\.\d+)?")
CENT = Decimal("0.01")

Parser = Callable[[str], object]


def _parse_date(
    text: str, pattern: re.Pattern[str], build: Callable[..., date], fmt: str
) -> date | None:
    """Blank -> None; a full match of `pattern` -> date; anything else raises."""
    text = (text or "").strip()
    if not text:
        return None
    match = pattern.fullmatch(text)
    if not match:
        raise ValueError(f"date {text!r} is not {fmt}")
    return build(*match.groups())


def parse_iso_date(text: str) -> date | None:
    """YYYY-MM-DD (civil invoice files)."""
    return _parse_date(text, ISO_DATE, lambda y, m, d: date(int(y), int(m), int(d)), "YYYY-MM-DD")


def parse_record_date(text: str) -> date | None:
    """DD/MM/YYYY (civil site records); day first, so 09/01/2025 is 9 January 2025."""
    return _parse_date(
        text, RECORD_DATE, lambda d, m, y: date(int(y), int(m), int(d)), "DD/MM/YYYY"
    )


def parse_dmon_date(text: str) -> date | None:
    """DD-Mon-YYYY (drilling invoice files and daily reports)."""

    def build(day: str, month: str, year: str) -> date:
        if month not in MONTHS:
            raise ValueError(f"unknown month {month!r}")
        return date(int(year), MONTHS[month], int(day))

    return _parse_date(text, DRILLING_DATE, build, "DD-Mon-YYYY")


def parse_decimal(text: str) -> Decimal | None:
    """Plain decimal text ('265123.89', '-1200.00', '792') -> Decimal, exactly as printed."""
    text = (text or "").strip()
    if not text:
        return None
    if not PLAIN_NUMBER.fullmatch(text):
        raise ValueError(f"number {text!r} is not a plain decimal")
    try:
        return Decimal(text)
    except InvalidOperation as exc:  # pragma: no cover - the regex already guards this
        raise ValueError(f"number {text!r} is not a plain decimal") from exc


# Column -> parser for each file. Columns not listed stay as text.
CIVIL_APPLICATIONS: dict[str, Parser] = {
    "period_from": parse_iso_date,
    "period_to": parse_iso_date,
    "application_date": parse_iso_date,
    "application_total": parse_decimal,
    "retention": parse_decimal,
    "net_payable": parse_decimal,
    "adjustment": parse_decimal,
    "retention_released": parse_decimal,
}
CIVIL_LINES: dict[str, Parser] = {
    "work_date": parse_iso_date,
    "quantity": parse_decimal,
    "rate_applied": parse_decimal,
    "amount": parse_decimal,
}
DRILLING_INVOICES: dict[str, Parser] = {
    "period_start": parse_dmon_date,
    "period_end": parse_dmon_date,
    "invoice_date": parse_dmon_date,
    "net_amount": parse_decimal,
    "vat_amount": parse_decimal,
    "invoice_total": parse_decimal,
    "adjustment": parse_decimal,
}
DRILLING_LINES: dict[str, Parser] = {
    "service_date": parse_dmon_date,
    "depth_from_m": parse_decimal,
    "depth_to_m": parse_decimal,
    "quantity": parse_decimal,
    "unit_rate": parse_decimal,
    "amount": parse_decimal,
}


def load_csv(path: Path, parsers: dict[str, Parser]) -> pd.DataFrame:
    """Read a CSV as text and parse the listed columns; raise naming file, column and value."""
    # keep_default_na=False keeps blanks as "" (not NaN) so the parsers decide what blank means.
    frame = pd.read_csv(path, dtype=str, keep_default_na=False, encoding="utf-8")
    missing = set(parsers) - set(frame.columns)
    if missing:
        raise ValueError(f"{path.name}: expected columns missing: {sorted(missing)}")
    for column, parse in parsers.items():
        try:
            values = [parse(value) for value in frame[column]]
        except ValueError as exc:
            raise ValueError(f"{path.name}, column {column}: {exc}") from exc
        frame[column] = pd.Series(values, index=frame.index, dtype=object)
    return frame


def load_civil_applications(paths: InputPaths | None = None) -> pd.DataFrame:
    """Civil application headers (900 rows), keyed by application_no."""
    return load_csv((paths or input_paths()).civil_applications, CIVIL_APPLICATIONS)


def load_civil_lines(paths: InputPaths | None = None) -> pd.DataFrame:
    """Civil application lines (7,746 rows)."""
    return load_csv((paths or input_paths()).civil_application_lines, CIVIL_LINES)


def load_drilling_invoices(paths: InputPaths | None = None) -> pd.DataFrame:
    """Drilling invoice headers (1,906 rows), keyed by invoice_no."""
    return load_csv((paths or input_paths()).drilling_invoices, DRILLING_INVOICES)


def load_drilling_lines(paths: InputPaths | None = None) -> pd.DataFrame:
    """Drilling invoice lines (91,244 rows), including the DS-900 discount lines."""
    return load_csv((paths or input_paths()).drilling_invoice_lines, DRILLING_LINES)


def load_template(paths: InputPaths | None = None) -> pd.DataFrame:
    """Load the submission template: invoice ids in the required order."""
    return pd.read_csv((paths or input_paths()).template, dtype=str, keep_default_na=False)


@dataclass(frozen=True, eq=False)
class AuditData:
    """Everything the checks read, loaded once.

    Compared and hashed by identity, so results computed from one load can be cached.
    """

    paths: InputPaths
    civil_apps: pd.DataFrame
    civil_lines: pd.DataFrame
    drill_invoices: pd.DataFrame
    drill_lines: pd.DataFrame
    civil_record_ids: frozenset[str]  # file stems in civilwork/records, e.g. "CT-00001"


def load_all(paths: InputPaths | None = None) -> AuditData:
    """Load every invoice file and the civil record file names."""
    paths = paths or input_paths()
    return AuditData(
        paths=paths,
        civil_apps=load_civil_applications(paths),
        civil_lines=load_civil_lines(paths),
        drill_invoices=load_drilling_invoices(paths),
        drill_lines=load_drilling_lines(paths),
        civil_record_ids=frozenset(p.stem for p in paths.civil_records_dir.glob("*.txt")),
    )


def to_cents(amount: Decimal) -> int:
    """Money in integer minor units (CLAUDE.md §4).

    The amount must already be rounded to 2 dp the contract's way, so the rounding mode
    here never changes a value; it only converts the type.
    """
    if amount != amount.quantize(CENT):
        raise ValueError(f"{amount} is not rounded to 2 dp")
    return int((amount * 100).to_integral_value(ROUND_HALF_UP))
