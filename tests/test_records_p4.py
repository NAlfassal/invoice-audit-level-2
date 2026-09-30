"""Phase 4: record parsing, linking and the record-based checks, on cases read by hand."""

from datetime import date
from decimal import Decimal

import pytest

from audit import linker
from audit.checks import Finding
from audit.io import AuditData
from audit.pricing import drilling

D = Decimal


def _on(findings: list[Finding], line_ref: str) -> list[tuple[str, str]]:
    return [(f.check_id, f.category) for f in findings if f.line_ref == line_ref]


# ---- civil records -----------------------------------------------------------------------


def test_civil_record_golden(data: AuditData) -> None:
    # CT-00001 "792 square metres of sub-base in and compacted" <-> PA-00233-13 D.41.010.
    record = linker.record_for(data, "CT-00001")
    reading = linker.civil_reading(record)
    assert (reading.item, reading.quantity, reading.unit) == ("D.41.010", D(792), "m2")
    assert (record["area"], record["date"]) == ("S-01 Platform North", date(2025, 1, 9))
    assert record["foreman"] and record["engineer_rep"]


def test_every_record_matches_one_template(data: AuditData) -> None:
    records = linker.civil_records_of(data)
    assert len(records) == 2169
    for record in records.itertuples(index=False):
        assert linker.read_work_line(record.series, record.work_text) is not None


def test_first_nine_records_of_each_type_agree_with_their_lines(data: AuditData) -> None:
    records = linker.civil_records_of(data)
    lines = data.civil_lines.set_index("record_ref", drop=False)
    for series, group in records.groupby("series"):
        for record in group.head(9).itertuples(index=False):
            reading = linker.civil_reading(records.loc[record.ticket])
            for line in lines[lines.index == record.ticket].itertuples(index=False):
                assert line.item_code == reading.item, (series, record.ticket)


def test_weekly_log_and_chargeable_hours(data: AuditData) -> None:
    week = linker.record_for(data, "DW-00004")
    assert week["days_on"] == 7 and week["week_beginning"] == date(2025, 2, 10)
    hours = linker.record_for(data, "MO-00001")  # 6 hours standing -> 5 chargeable (Cl.6A)
    assert linker.civil_payable_quantity(hours, linker.civil_reading(hours)) == D(5)


# ---- drilling reports --------------------------------------------------------------------


def test_report_quantities(data: AuditData) -> None:
    report = linker.report_for(data, "DDR-011-20260225")
    assert report["parts"] == "ABC" and report["status"] == "Operating"
    assert linker.report_quantity("DD-101", report) == D(2)  # 2 directional hands
    assert linker.report_quantity("HC-620", report) == D(1)  # drilling jars in the hole
    assert linker.report_quantity("RM-511", report) == D(0)  # no hole opener
    assert linker.report_quantity("DD-120", report) == D(14)  # 15 hours less the first


def test_lost_in_hole_depreciation() -> None:
    # Appendix F p.34: 412 hours -> 16% depreciation (complete 25-hour steps).
    full = drilling.lost_in_hole_value("LH-713", date(2025, 1, 15), D(0))
    assert drilling.lost_in_hole_value("LH-713", date(2025, 1, 15), D(412)) == (
        full * D("0.84")
    ).quantize(D("0.01"))
    capped = drilling.lost_in_hole_value("LH-713", date(2025, 1, 15), D(5000))
    assert capped == (full / 2).quantize(D("0.01"))  # at most 50%


# ---- record-based findings -----------------------------------------------------------------


@pytest.mark.parametrize(
    "line_ref, expected",
    [
        ("MDS-00128-026", ("c04", "missing_record")),  # report of the day before
        ("MDS-00876-062", ("c04", "missing_record")),  # LW-420 without Part D
        ("MDS-00954-021", ("c04", "missing_record")),  # DD-130 without Part C
        ("PA-00312-04", ("c05", "quantity_over_record")),  # 4 billed, survey 3 (> 2%)
        ("PA-00243-03", ("c05", "quantity_over_record")),  # 10 h billed, 10 recorded -> 9
        ("MDS-01604-055", ("c05", "quantity_over_record")),  # DD-120 20 h, report 16 -> 15
        ("MDS-00062-021", ("c05", "quantity_over_record")),  # LW-410 171 m, report 125 m
        ("MDS-00639-027", ("c08", "rate_buildup")),  # lost in hole without depreciation
        ("MDS-00320-016", ("c09", "limit_exceeded")),  # MB-701 after the first day
    ],
)
def test_record_findings(findings: list[Finding], line_ref: str, expected: tuple[str, str]) -> None:
    assert expected in _on(findings, line_ref)


def test_survey_tolerance_not_flagged(findings: list[Finding]) -> None:
    # Cl.33A: PA-00022-04 billed 588 against a survey of 580 (1.38%) is payable as measured.
    assert _on(findings, "PA-00022-04") == []


def test_line_below_record_not_flagged(findings: list[Finding]) -> None:
    assert _on(findings, "PA-00003-07") == []  # 527 billed, 546 recorded (D30)


def test_signature_without_letters_is_missing() -> None:
    from audit.records import signature

    assert signature("____________________") == ""
    assert signature("  ") == "" and signature(None) == ""
    assert signature("K. Doyle") == "K. Doyle"


@pytest.mark.parametrize(
    "line_ref",
    ["PA-00613-01"],  # DX-00089: Engineer's representative line is underscores (Cl.47)
)
def test_unsigned_civil_record(findings: list[Finding], line_ref: str) -> None:
    assert ("c04", "unsigned_record") in _on(findings, line_ref)


@pytest.mark.parametrize("invoice_id", ["MDS-00842", "MDS-00340", "MDS-00901"])
def test_unsigned_reports(findings: list[Finding], invoice_id: str) -> None:
    # Both signature lines of the cited report are underscores (Cl.15 p.5).
    hits = [f for f in findings if f.invoice_id == invoice_id and f.category == "unsigned_record"]
    assert hits
