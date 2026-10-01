"""Phase 1 checks: golden cases found by hand in the data and on the scans (p.8)."""

from collections import Counter
from datetime import date
from decimal import Decimal

import pandas as pd
import pytest

from audit import contract, decide, io
from audit.checks import FLAG_THRESHOLD, Finding, c03_window, c10_duplicates
from audit.io import AuditData


def _hits(
    findings: list[Finding],
    check_id: str,
    category: str | None = None,
    prefix: str | None = None,
    counting: bool = True,
) -> list[Finding]:
    return [
        f
        for f in findings
        if f.check_id == check_id
        and (category is None or f.category == category)
        and (prefix is None or f.invoice_id.startswith(prefix))
        and (not counting or f.confidence >= FLAG_THRESHOLD)
    ]


# ---- contract rules ------------------------------------------------------------------


def test_civil_retention_rounds_down() -> None:
    assert contract.civil_retention(Decimal("265123.89")) == Decimal("13256.19")  # Cl.45


def test_drilling_discount_cl38() -> None:
    assert contract.drilling_discount(Decimal("250000.00")) == Decimal("0.00")
    assert contract.drilling_discount(Decimal("1307552.40")) == Decimal("-42302.10")


def test_drilling_totals_half_even() -> None:
    # 0.15 x 0.10 = 0.015 -> 0.02 (half to even: 1 is odd, rounds up to 2)
    t = contract.drilling_totals([Decimal("0.10")])
    assert (t.net, t.vat, t.total) == (Decimal("0.10"), Decimal("0.02"), Decimal("0.12"))


# ---- c03 window boundaries (Cl.41 civil, Cl.33 drilling) -------------------------------


@pytest.mark.parametrize(
    "submitted, flagged",
    [
        (date(2025, 3, 31), True),  # before the last day of the period
        (date(2025, 4, 1), False),  # on the last day: allowed
        (date(2025, 4, 22), False),  # day 21
        (date(2025, 4, 23), True),  # day 22
    ],
)
def test_civil_window_boundaries(submitted: date, flagged: bool) -> None:
    headers = pd.DataFrame(
        {"application_no": ["X"], "period_to": [date(2025, 4, 1)], "application_date": [submitted]}
    )
    hits = c03_window.late_or_early(
        headers, "application_no", "period_to", "application_date", 21, "p.8 Cl.41"
    )
    assert bool(hits) == flagged


def test_window_counts(findings: list[Finding]) -> None:
    submission = [f for f in _hits(findings, "c03") if not f.line_ref]
    early = Counter(f.invoice_id[:2] for f in submission if "before" in f.evidence)
    late = Counter(f.invoice_id[:2] for f in submission if "after" in f.evidence)
    assert (early["PA"], late["PA"]) == (1, 3)
    assert (early["MD"], late["MD"]) == (3, 3)


# ---- other checks ----------------------------------------------------------------------


def test_contract_ref_variants(findings: list[Finding]) -> None:
    refs = {f.invoice_id for f in _hits(findings, "c01", "wrong_contract_ref")}
    assert len([r for r in refs if r.startswith("PA")]) == 2
    assert len([r for r in refs if r.startswith("MDS")]) == 3


def test_outside_term_lines(findings: list[Finding]) -> None:
    lines = {f.line_ref for f in _hits(findings, "c02")}
    assert {
        "PA-00375-07",
        "PA-00678-10",
        "MDS-01619-045",
        "MDS-01798-045",
        "MDS-01860-039",
    } == lines


def test_missing_records(findings: list[Finding]) -> None:
    lines = {f.line_ref for f in _hits(findings, "c04")}
    assert "PA-00170-04" in lines  # JS item citing a PT record
    assert "PA-00609-01" in lines  # CT-00126 does not exist
    assert "PA-00111-13" in lines  # blank ref on A.12.030
    assert "PA-00233-13" not in lines  # CT-00001, the known good link


def test_cl44_duplicate_is_later_line(data: AuditData, findings: list[Finding]) -> None:
    dup = [f for f in c10_duplicates.run(data) if f.clause == "p.8 Cl.44"]
    assert [f.line_ref for f in dup] == ["PA-00111-12"]
    assert dup[0].evidence.endswith("PA-00111-03")
    # Guideline order: c04 rejects the line first (no JS record), so the
    # later c10 finding on it is not kept.
    on_line = [f.check_id for f in findings if f.line_ref == "PA-00111-12"]
    assert on_line == ["c04"]


def test_pd210_depth_splits_are_not_duplicates(data: AuditData) -> None:
    # c10 alone: 3 exact copies; PD-210 depth-band splits of one day are not duplicates.
    drilling = [f for f in c10_duplicates.run(data) if f.invoice_id.startswith("MDS")]
    assert len(drilling) == 3


def test_lines_below_quantity_x_rate(findings: list[Finding]) -> None:
    # 32 civil lines bill less than quantity x rate (Cl.28 p.6; Sch.4 Pt3 p.24): 29 are band
    # splits the pricing engine reproduces (no c11 finding); the 3 on items without bands are
    # arithmetic errors.
    below = _hits(findings, "c11", "arithmetic", "PA")
    lines = {f.line_ref for f in below if f.line_ref}
    assert lines == {"PA-00610-02", "PA-00659-03", "PA-00672-02"}


def test_drilling_header_arithmetic(findings: list[Finding]) -> None:
    disc = {f.invoice_id for f in _hits(findings, "c11", "discount_misapplied")}
    assert disc == {"MDS-00072", "MDS-00282", "MDS-01049"}
    totals = {f.invoice_id for f in _hits(findings, "c11", "arithmetic", "MDS") if not f.line_ref}
    assert totals == {"MDS-00551", "MDS-00916", "MDS-01317"}


# ---- decide ----------------------------------------------------------------------------


@pytest.fixture(scope="module")
def submission(data: AuditData, findings: list[Finding]) -> pd.DataFrame:
    return decide.decide(data, findings).set_index("invoice_id")


def test_submission_valid(data: AuditData, findings: list[Finding]) -> None:
    decide.validate(decide.decide(data, findings), io.load_template())


@pytest.mark.parametrize(
    "invoice_id, expected",
    [
        ("PA-00043", 23142526),  # total restated as the sum of its lines (Cl.43)
        ("MDS-00551", 23051504),  # total restated as net + VAT (Cl.40)
        ("MDS-00072", 145503784),  # DS-900 added, VAT recomputed (Cl.38-39)
        ("PA-00125", 2506853),  # early submission: the work is still worth what was billed
    ],
)
def test_expected_totals(submission: pd.DataFrame, invoice_id: str, expected: int) -> None:
    assert submission.loc[invoice_id, "expected_total_cents"] == expected
    assert submission.loc[invoice_id, "flagged"] == 1


def test_unflagged_rows_keep_billed_total(submission: pd.DataFrame) -> None:
    clean = submission[submission["flagged"] == 0]
    assert (clean["expected_total_cents"] == clean["billed_total_cents"]).all()
    assert (clean["error_category"] == "").all()
