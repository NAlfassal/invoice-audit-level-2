"""Loading the four invoice files: row counts, date parsing, exact Decimal money."""

from collections.abc import Callable
from datetime import date
from decimal import Decimal

import pandas as pd
import pytest

from audit import io


@pytest.fixture(scope="module")
def civil_apps() -> pd.DataFrame:
    return io.load_civil_applications()


@pytest.fixture(scope="module")
def civil_lines() -> pd.DataFrame:
    return io.load_civil_lines()


@pytest.fixture(scope="module")
def drill_invoices() -> pd.DataFrame:
    return io.load_drilling_invoices()


@pytest.fixture(scope="module")
def drill_lines() -> pd.DataFrame:
    return io.load_drilling_lines()


def test_row_counts(
    civil_apps: pd.DataFrame,
    civil_lines: pd.DataFrame,
    drill_invoices: pd.DataFrame,
    drill_lines: pd.DataFrame,
) -> None:
    assert len(civil_apps) == 900
    assert len(civil_lines) == 7_746
    assert len(drill_invoices) == 1_906
    assert len(drill_lines) == 91_244


def test_template_covers_every_invoice(
    civil_apps: pd.DataFrame, drill_invoices: pd.DataFrame
) -> None:
    template = io.load_template()
    assert len(template) == 2_806
    assert set(template["invoice_id"]) == (
        set(civil_apps["application_no"]) | set(drill_invoices["invoice_no"])
    )


def test_pa00001_header(civil_apps: pd.DataFrame) -> None:
    row = civil_apps.set_index("application_no").loc["PA-00001"]
    assert row["application_total"] == Decimal("265123.89")
    assert row["retention"] == Decimal("13256.19")  # Cl.45 p.8: 5% of the total, rounded down
    assert row["period_to"] == date(2025, 10, 4)


def test_civil_line_types(civil_lines: pd.DataFrame) -> None:
    row = civil_lines.set_index("line_ref").loc["PA-00001-03"]  # the A.11.020 golden line
    assert row["work_date"] == date(2025, 9, 22)
    assert row["rate_applied"] == Decimal("21.42")
    assert row["quantity"] * row["rate_applied"] == row["amount"] == Decimal("1992.06")


def test_drilling_header_dates(drill_invoices: pd.DataFrame) -> None:
    row = drill_invoices.set_index("invoice_no").loc["MDS-00001"]
    assert (row["period_start"], row["period_end"], row["invoice_date"]) == (
        date(2025, 1, 1),
        date(2025, 1, 4),
        date(2025, 1, 27),
    )
    assert row["net_amount"] + row["vat_amount"] == row["invoice_total"] == Decimal("114793.41")


def test_ds900_lines_have_no_date(drill_lines: pd.DataFrame) -> None:
    ds900 = drill_lines[drill_lines["service_code"] == "DS-900"]
    assert len(ds900) == 63
    assert ds900["service_date"].isna().all()
    assert (ds900["amount"] < 0).all()
    # Every other line is dated.
    assert drill_lines.loc[drill_lines["service_code"] != "DS-900", "service_date"].notna().all()


def test_money_is_decimal_never_float(civil_lines: pd.DataFrame, drill_lines: pd.DataFrame) -> None:
    for df, cols in [
        (civil_lines, ["rate_applied", "amount"]),
        (drill_lines, ["unit_rate", "amount"]),
    ]:
        for col in cols:
            assert all(isinstance(v, Decimal) for v in df[col])


@pytest.mark.parametrize("text, expected", [("2025-09-25", date(2025, 9, 25)), ("", None)])
def test_parse_iso_date(text: str, expected: date | None) -> None:
    assert io.parse_iso_date(text) == expected


@pytest.mark.parametrize(
    "text, expected",
    [
        ("09/01/2025", date(2025, 1, 9)),  # CT-00001: day first
        ("31/12/2025", date(2025, 12, 31)),
    ],
)
def test_parse_record_date(text: str, expected: date | None) -> None:
    assert io.parse_record_date(text) == expected


@pytest.mark.parametrize(
    "text, expected",
    [("01-Jan-2025", date(2025, 1, 1)), ("25-Feb-2026", date(2026, 2, 25)), ("", None)],
)
def test_parse_dmon_date(text: str, expected: date | None) -> None:
    assert io.parse_dmon_date(text) == expected


def test_to_cents() -> None:
    assert io.to_cents(Decimal("265123.89")) == 26512389
    assert io.to_cents(Decimal("-0.05")) == -5
    with pytest.raises(ValueError):
        io.to_cents(Decimal("1.005"))  # must be rounded the contract's way first


@pytest.mark.parametrize(
    "parser, bad",
    [
        (io.parse_iso_date, "25/09/2025"),
        (io.parse_record_date, "2025-01-09"),
        (io.parse_dmon_date, "01-JAN-2025"),
        (io.parse_dmon_date, "31-Feb-2025"),
        (io.parse_decimal, "1,200.00"),
        (io.parse_decimal, "12.4e3"),
    ],
)
def test_bad_values_raise(parser: Callable[[str], object], bad: str) -> None:
    with pytest.raises(ValueError):
        parser(bad)
