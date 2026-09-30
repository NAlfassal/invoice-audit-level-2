"""Contract extraction stage: OCR pages -> extracted/contracts/{civil,drilling}.json.

Input: extracted/ocr/<contract>/page_XX.md, extracted/contracts/ocr_corrections.json and
<contract>_clauses.json, and the invoice files (for the checks). Output: the two contract
JSON files, every value with source / verified / evidence, and
output/contract_verification.md. Values the invoices cannot confirm are grouped by where
they will be confirmed: the eye check, the Phase 3 pricing calibration, or Phase 4 linking.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from audit import io
from audit.config import CONTRACTS_DIR, OUTPUT_DIR, InputPaths
from audit.extract import verify
from audit.extract.civil import civil_contract
from audit.extract.clauses import load_clause_terms
from audit.extract.drilling import drilling_contract
from audit.extract.ocr_text import load_pages
from audit.extract.report import EYE, open_values, terms_in, write_report

log = logging.getLogger(__name__)
JSON_FILE = "{contract}.json"
EYE_CHECKS_FILE = CONTRACTS_DIR / "eye_checks.json"


def run(paths: InputPaths) -> None:
    """Extract both contracts, check them against the invoices and write JSON and report."""
    data = io.load_all(paths)
    results = [extract_civil(data), extract_drilling(data)]
    for contract, extracted, checks in results:
        checks["eye_checks"] = apply_eye_checks(contract, extracted)
        write_json(extracted, CONTRACTS_DIR / JSON_FILE.format(contract=contract))
    report = OUTPUT_DIR / "contract_verification.md"
    counts = write_report(results, report)
    log.info("extract: civil.json, drilling.json, %s (%s)", report.name, counts)


def extract_civil(data: io.AuditData) -> tuple[str, dict, dict]:
    """Civil JSON with calibration applied, and the check results for the report."""
    pages = load_pages("civil")
    contract = civil_contract(pages)
    contract["terms"] = load_clause_terms(pages)
    checks = {
        "missing_codes": verify.missing_codes(
            contract["items"], set(data.civil_lines["item_code"])
        ),
        "calibration": verify.calibrate_civil(contract, contract["terms"], data.civil_lines),
        "headers": [
            verify.check_reference(
                contract["terms"], data.civil_apps, "contract_ref", "subcontractor"
            ),
            verify.check_retention(contract["terms"], data.civil_apps),
            verify.check_record_series(contract, data.civil_lines),
        ],
        "corrections": pages.applied,
    }
    return "civil", contract, checks


def extract_drilling(data: io.AuditData) -> tuple[str, dict, dict]:
    """Drilling JSON with calibration applied, and the check results for the report."""
    pages = load_pages("drilling")
    contract = drilling_contract(pages)
    contract["terms"] = load_clause_terms(pages)
    billed = set(data.drill_lines["service_code"]) - {verify.DISCOUNT_CODE}
    checks = {
        "missing_codes": verify.missing_codes(contract["items"], billed),
        "calibration": verify.calibrate_drilling(
            contract, contract["terms"], data.drill_lines, data.drill_invoices
        ),
        "headers": [
            verify.check_reference(
                contract["terms"], data.drill_invoices, "contract_ref", "contractor"
            ),
            verify.check_vat_and_discount(contract["terms"], data.drill_invoices, data.drill_lines),
        ],
        "corrections": pages.applied,
    }
    return "drilling", contract, checks


def apply_eye_checks(name: str, contract: dict) -> list[tuple[str, str]]:
    """Mark the values confirmed by an eye check or a second OCR engine as verified.

    Input: extracted/contracts/eye_checks.json, by crop number (the order in
    extract.crops.CROPS) or by value path. Returns (path, evidence) for the report.
    """
    from audit.extract.crops import CROPS, crop_shows

    checks = json.loads(EYE_CHECKS_FILE.read_text(encoding="utf-8"))["checks"]
    # A crop confirms only the values it was cut for (the eye-check list), not every value
    # of the same instrument or table.
    on_list = {path for group, path, _ in open_values(contract) if group == EYE}
    marked = []
    for path, entry in terms_in(contract):
        for check in checks:
            if "crop" in check:
                crop = CROPS[int(check["crop"]) - 1]
                applies = (
                    crop.contract == name and path in on_list and crop_shows(crop, path, entry)
                )
            else:
                applies = check["contract"] == name and check["path"] == path
            if applies and not entry["verified"]:
                entry["verified"] = True
                entry["evidence"] = check["evidence"]
                marked.append((path, check["evidence"]))
    return marked


def write_json(contract: dict, path: Path) -> None:
    """Write the contract JSON; key order is fixed by the builders, so output is stable."""
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(contract, indent=1, ensure_ascii=False)
    path.write_text(text + "\n", encoding="utf-8")
