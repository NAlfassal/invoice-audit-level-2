"""Phase 2: OCR corrections are enforced; the contract JSON reproduces values checked on scans."""

from datetime import date
from decimal import Decimal

import pytest

from audit import io
from audit.contract import load_contract, term
from audit.extract import ocr_text
from audit.extract.clauses import load_clause_terms
from audit.extract.report import terms_in
from audit.extract.verify import civil_rate, depth_band

# ---- OCR text safety -------------------------------------------------------------------


def test_correction_that_does_not_match_stops_extraction() -> None:
    pages = ocr_text.Pages(
        "civil", corrections=[{"page": 25, "ocr_text": "%60", "corrected": "90%"}]
    )
    with pytest.raises(ValueError, match="not found"):
        pages.text(25)


def test_correction_is_applied_and_recorded() -> None:
    pages = ocr_text.load_pages("civil")
    assert "%06" not in pages.text(25) and "90%" in pages.text(25)
    assert any(fix["page"] == 25 for fix in pages.applied)


@pytest.mark.parametrize("bad", ["%06", "%00%", "96", "9 6%x"])
def test_reversed_or_broken_percent_is_rejected(bad: str) -> None:
    with pytest.raises(ValueError):
        ocr_text.parse_percent(bad, "test")


@pytest.mark.parametrize("bad", ["19,237:00", "1.2.3", "abc"])
def test_broken_amount_is_rejected(bad: str) -> None:
    with pytest.raises(ValueError):
        ocr_text.parse_amount(bad, "test")


def test_month_table_splits_fused_cells() -> None:
    text = "| Month | Index Month | Index |\n| 2025-04 | 101.802026-04 | 111.50 |"
    values = ocr_text.month_table(text, "test", expected=2)
    assert values == {"2025-04": Decimal("101.80"), "2026-04": Decimal("111.50")}


def test_every_clause_quote_is_on_its_page() -> None:
    for contract in ("civil", "drilling"):
        assert load_clause_terms(ocr_text.load_pages(contract))


# ---- the JSON reproduces the facts checked on the scans -----------------------------------


def _values(section: dict) -> dict:
    return {key: entry["value"] for key, entry in section.items()}


def test_every_value_has_a_source() -> None:
    for contract in ("civil", "drilling"):
        for path, entry in terms_in(load_contract(contract)):
            assert entry["source"], path


def test_civil_factors() -> None:
    civil = load_contract("civil")
    assert _values(civil["zone_factors"]) == {"Z1": "1", "Z2": "1.06", "Z3": "1.145", "Z4": "1.28"}
    assert _values(civil["ground"]["factors"]) == {
        "G1": "0.94",
        "G2": "1",
        "G3": "1.12",
        "G4": "1.375",
        "G5": "1.63",
    }
    assert len(civil["ground"]["items"]["value"]) == 15


def test_civil_schedule_5() -> None:
    series = _values(load_contract("civil")["record_series"])
    assert len(series) == 17
    assert series["A.16.010"] == "DW" and series["E.51.030"] == "PS"


def test_civil_instruments() -> None:
    instruments = load_contract("civil")["instruments"]
    dates = [(i["issued"]["value"], i["effective"]["value"]) for i in instruments]
    assert dates == [
        ("2025-03-24", "2025-05-01"),
        ("2025-08-18", "2025-09-28"),
        ("2025-11-12", "2025-12-01"),
        ("2026-02-16", "2026-04-01"),
        ("2026-05-12", "2025-11-01"),
    ]
    amendment_1 = instruments[1]["rates"]
    assert amendment_1["E.54.010"]["value"] == "948.00"
    assert amendment_1["B.23.010"]["effective"] == "2025-10-01"
    assert [i["discount"]["value"] for i in instruments if i["discount"]] == ["5", "8"]
    assert term("civil", "completion").value == date(2026, 9, 30)


def test_drilling_instruments_and_discount() -> None:
    drilling = load_contract("drilling")
    dates = [(i["issued"]["value"], i["effective"]["value"]) for i in drilling["instruments"]]
    assert dates[-1] == ("2026-08-17", "2026-02-01")  # Amendment 3, retroactive
    assert term("drilling", "expiry").value == date(2026, 12, 31)
    assert term("drilling", "discount_pct").value == Decimal("4")
    assert term("drilling", "discount_threshold").value == Decimal("250000.00")


@pytest.mark.parametrize(
    "line_ref, billed",
    [("PA-00001-03", Decimal("21.42")), ("PA-00001-04", Decimal("412.34"))],
)
def test_golden_civil_lines(line_ref: str, billed: Decimal) -> None:
    # A.11.020: 12.40 x 1.06 (Z2) x 1.63 (G5) = 21.4247 -> 21.42; B.21.030: 389.00 x 1.06.
    civil = load_contract("civil")
    line = io.load_civil_lines().set_index("line_ref").loc[line_ref]
    rate, _ = civil_rate(civil, civil["terms"], line)
    assert rate == billed == line["rate_applied"]


@pytest.mark.parametrize(
    "depth, band", [(Decimal(1500), "Band 1"), (Decimal(1501), "Band 2"), (Decimal(9000), "Band 4")]
)
def test_depth_band_boundary_belongs_to_shallower_band(depth: Decimal, band: str) -> None:
    assert depth_band(load_contract("drilling")["depth_bands"], depth)["band"] == band


def test_every_eye_check_value_has_a_crop() -> None:
    from audit.extract.crops import CROPS, assign

    # All 68 values listed for the eye check are confirmed, by the eye check or a second OCR
    # engine (extracted/contracts/eye_checks.json); none is left open. assign() stops if an
    # open value has no crop.
    assert sum(len(values) for values in assign(CROPS).values()) == 0
