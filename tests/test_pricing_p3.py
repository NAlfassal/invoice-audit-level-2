"""Phase 3: pricing rules checked by hand on the scans and the invoices."""

from datetime import date
from decimal import Decimal

import pandas as pd
import pytest

from audit import calibrate, contract, decide
from audit.checks import FLAG_THRESHOLD, Finding, c09_limits
from audit.io import AuditData
from audit.pricing import Band, band_parts, civil, drilling
from audit.pricing.compare import differences

D = Decimal
LATE = date(2026, 12, 31)  # a submission date after every instrument's issue


@pytest.fixture(scope="module")
def submission(data: AuditData, findings: list[Finding]) -> pd.DataFrame:
    return decide.decide(data, findings).set_index("invoice_id")


def _line(data: AuditData, line_ref: str) -> tuple:
    lines = data.civil_lines if line_ref.startswith("PA") else data.drill_lines
    return next(lines[lines["line_ref"] == line_ref].itertuples(index=False))


# ---- rates, discounts and Contract Years in force --------------------------------------


@pytest.mark.parametrize(
    "work_date, expected",
    [
        (date(2025, 4, 30), D("4120.00")),  # Schedule 1, before Supplement 1 (p.39)
        (date(2025, 5, 1), D("4385.00")),  # Supplement 1 from its effective date
        (date(2025, 9, 30), D("4385.00")),  # Amendment 1 effective 2025-09-28 but item 2025-10-01
        (date(2025, 10, 1), D("4450.00")),  # Amendment 1 per-item effective date (p.40)
    ],
)
def test_rate_at_follows_per_item_effective_dates(work_date: date, expected: Decimal) -> None:
    assert contract.rate_at("civil", "B.23.010", work_date, LATE).value == expected


def test_rate_at_counts_only_instruments_issued_by_submission() -> None:
    # Amendment 3 (issued 2026-05-12) substitutes A.14.010 from 2025-11-01 (Cl.31A, D16).
    before = contract.rate_at("civil", "A.14.010", date(2026, 1, 10), date(2026, 5, 11))
    on_issue = contract.rate_at("civil", "A.14.010", date(2026, 1, 10), date(2026, 5, 12))
    assert (before.value, on_issue.value) == (D("53.20"), D("56.80"))


def test_monthly_rate_carries_forward() -> None:
    # Supplement 1 §1.2 p.39: after the last month stated, the last published rate applies.
    october = contract.rate_at("civil", "D.41.020", date(2025, 10, 15), LATE)
    assert (october.value, october.month) == (D("220.50"), "2025-09")


def test_dd120_amendment3_governs_monthly_rates() -> None:
    # D12: Amendment 3 (issued later) sets 416.00 from 2026-02-01 over Supplement 2's months.
    assert contract.rate_at("drilling", "DD-120", date(2026, 5, 3), LATE).value == D("416.00")
    before_issue = contract.rate_at("drilling", "DD-120", date(2026, 5, 3), date(2026, 8, 16))
    assert before_issue.value == D("411.50")


@pytest.mark.parametrize(
    "work_date, percent",
    [(date(2025, 11, 30), 0), (date(2025, 12, 1), 5), (date(2026, 4, 1), 8)],
)
def test_civil_discount_replaces_not_adds(work_date: date, percent: int) -> None:
    assert contract.discount_at("civil", "C.32.010", work_date, LATE).percent == percent  # D13


@pytest.mark.parametrize(
    "name, day, year",
    [
        ("civil", date(2026, 1, 4), 1),
        ("civil", date(2026, 1, 5), 2),  # Cl.3A: first anniversary of 2025-01-05
        ("drilling", date(2025, 12, 31), 1),
        ("drilling", date(2026, 1, 1), 2),
    ],
)
def test_contract_year_starts_on_anniversary(name: str, day: date, year: int) -> None:
    assert contract.contract_year(name, day) == year


# ---- bands -------------------------------------------------------------------------------


def test_band_parts_split_at_limit() -> None:
    bands = (Band(D(3500), D(100)), Band(D(14500), D(95)), Band(None, D(92)))
    assert band_parts(bands, D(3293), D(258)) == [(D(207), D(100)), (D(51), D(95))]
    assert band_parts(bands, D(0), D(10)) == [(D(10), D(100))]
    assert band_parts(bands, D(20000), D(5)) == [(D(5), D(92))]


def test_band_split_line_reproduced(data: AuditData) -> None:
    # PA-00076-08 D.41.040: 207 at 100% (34.56) + 51 at 95% (32.83) = 8828.25 (Cl.28).
    price = civil.price_lines(data)["PA-00076-08"]
    assert [(p.quantity, p.percent, p.rate) for p in price.parts] == [
        (D(207), D(100), D("34.56")),
        (D(51), D(95), D("32.83")),
    ]
    assert price.amount == D("8828.25")


# ---- civil build-up ----------------------------------------------------------------------


@pytest.mark.parametrize(
    "line_ref, rate",
    [
        ("PA-00001-03", D("21.42")),  # 12.40 x 1.06 (Z2) x 1.63 (G5), rounded once
        ("PA-00001-04", D("412.34")),  # 389.00 x 1.06
        ("PA-00006-14", D("69.07")),  # A3 56.80 x 1.28 (Z4) x 95% band, on the issue date
        ("PA-00380-02", D("61.78")),  # A3 56.80 x 1.145 (Z3) x 95% band
    ],
)
def test_civil_golden_rates(data: AuditData, line_ref: str, rate: Decimal) -> None:
    assert civil.price_lines(data)[line_ref].rate == rate


def test_usd_rate_converted_half_even(data: AuditData) -> None:
    # Cl.26A: B.23.020 is 38.40 USD, converted at the month's rate before any factor.
    line = data.civil_lines[data.civil_lines["item_code"] == "B.23.020"].iloc[0]
    month = f"{line.work_date.year}-{line.work_date.month:02d}"
    table = contract.load_contract("civil")["usd"]["halalas_per_usd"]["value"]
    expected = (D("38.40") * D(table[month]) / 100).quantize(D("0.01"), "ROUND_HALF_EVEN")
    assert civil.converted_rate("B.23.020", D("38.40"), line.work_date) == expected


def test_no_night_uplift_above_zone_limit() -> None:
    # Cl.27A p.32: no night uplift on an item priced at a zone factor above 1.1 (Z3, Z4).
    night = civil.Context("A.12.030", date(2025, 3, 4), "Z4", "G2", True)
    assert civil.factors_of(night).uplift == 1
    day_z1 = civil.Context("A.12.030", date(2025, 3, 4), "Z1", "G2", True)
    assert civil.factors_of(day_z1).uplift == D("1.18")


def test_ground_datum_after_extension() -> None:
    # Cl.27A p.32: work after 2025-09-27 takes G2 whatever was recorded.
    before = civil.Context("A.12.010", date(2025, 9, 27), "Z1", "G5", False)
    after = civil.Context("A.12.010", date(2025, 9, 28), "Z1", "G5", False)
    assert (civil.ground_factor(before), civil.ground_factor(after)) == (D("1.63"), D(1))


# ---- drilling build-up -------------------------------------------------------------------


def test_drilling_amendment3_rate_with_discount(data: AuditData) -> None:
    # MDS-01625 (17-Aug-2026, the issue date): DD-101 1954.00 x 0.93 (A2 7%) = 1817.22.
    lines = data.drill_lines
    ref = lines[(lines["invoice_no"] == "MDS-01625") & (lines["service_code"] == "DD-101")]
    assert drilling.price_lines(data)[ref["line_ref"].iloc[0]].rate == D("1817.22")


def test_pd210_has_no_class_factor(data: AuditData) -> None:
    # Cl.17B / D21: an HPHT well's PD-210 is priced at the plain Schedule 2 band rate.
    invoices = data.drill_invoices
    hpht = set(invoices.loc[invoices["well_class"] == "HPHT", "invoice_no"])
    lines = data.drill_lines
    footage = lines[(lines["service_code"] == "PD-210") & lines["invoice_no"].isin(hpht)]
    rates = {drilling.price_lines(data)[ref].rate for ref in footage["line_ref"]}
    assert rates <= {D("42.35"), D("58.15"), D("76.45"), D("98.70")}


def test_no_section_factor_on_standby() -> None:
    context = drilling.Context("RM-511", date(2025, 3, 1), '26"', True, "Standard")
    factors = drilling.factors_of(context)
    assert (factors.section, factors.standby_percent) == (D(1), D(50))


# ---- calibration against the billed rates -------------------------------------------------


def test_engine_reproduces_the_clean_majority(data: AuditData) -> None:
    table = calibrate.line_agreement(data)
    share = table.groupby("contract")["rate_ok"].mean()
    assert share["civil"] >= 0.99 and share["drilling"] >= 0.99


def test_every_difference_has_a_category(data: AuditData) -> None:
    allowed = {"superseded_rate", "retro_adjustment", "discount_misapplied", "rate_buildup"}
    assert {diff.category for diff in differences(data)} <= allowed


# ---- retro settlement and retention release (Cl.31A, Cl.36A, Cl.45A) -------------------


def test_retro_carrier_drilling(submission: pd.DataFrame) -> None:
    # D16: MDS-01625 is the first invoice on or after 2026-08-17 and carries no adjustment.
    assert submission.loc["MDS-01625", "flagged"] == 1
    for invoice_id in ("MDS-01585", "MDS-01631"):
        assert submission.loc[invoice_id, "error_category"] != "retro_adjustment"


def test_retro_carriers_civil_tie(findings: list[Finding]) -> None:
    # D25: three applications on 2026-05-12, each at 1/3; PA-00443 is not a carrier.
    retro = {
        f.invoice_id: f.confidence
        for f in findings
        if f.category == "retro_adjustment"
        and not f.line_ref
        and f.clause.startswith("p.32 Cl.31A")
    }
    assert retro == {"PA-00006": 0.33, "PA-00023": 0.33, "PA-00380": 0.33}


def test_retention_release_omitted(findings: list[Finding]) -> None:
    release = [f for f in findings if f.clause == "p.32 Cl.45A"]
    assert [f.invoice_id for f in release] == ["PA-00678"]
    assert "release of 4034571.73 due" in release[0].evidence
    assert release[0].delta_minor_units == 0  # D17: outside the judged total


# ---- units and limits --------------------------------------------------------------------


def test_wrong_unit_lines(findings: list[Finding]) -> None:
    lines = {f.line_ref for f in findings if f.category == "wrong_unit"}
    assert lines == {"PA-00052-02", "PA-00406-03", "PA-00833-07", "PA-00892-06"}


def test_same_day_exclusion_is_flagged_moderately(data: AuditData) -> None:
    # D27: a same-day A.14.020 is inside the Cl.32 window, at confidence 0.60.
    found = [f for f in c09_limits.run(data) if "same day" in f.evidence]
    assert [f.line_ref for f in found] == ["PA-00801-05"]
    assert found[0].confidence == 0.60 and found[0].confidence >= FLAG_THRESHOLD


def test_exact_copies_stay_duplicates(findings: list[Finding]) -> None:
    # An exact copy is removed before the daily limits are counted: its category is c10's.
    copies = {"MDS-00476-051", "MDS-00580-046", "MDS-01654-078"}
    kept = {f.line_ref: f.category for f in findings if f.line_ref in copies}
    assert kept == dict.fromkeys(copies, "duplicate_charge")


def test_bands_count_payable_lines_only(data: AuditData) -> None:
    # D19 (b): a line not payable is split at the count reached but not counted.
    from audit.checks import unmeasured_lines

    unpaid = unmeasured_lines(data)
    assert "PA-00609-01" in unpaid  # D.41.010, no valid record
    a = civil.price_lines(data)
    b = civil.price_lines(data, unpaid)
    assert all(a[ref].parts == b[ref].parts for ref in a)  # thresholds passed before it
