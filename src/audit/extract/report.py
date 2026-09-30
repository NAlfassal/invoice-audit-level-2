"""Write output/contract_verification.md and group the values the invoices did not confirm.

Input: per contract, the extracted dict and its check results. Output: the markdown report
and a one-line count per group. Every unverified value is put in exactly one group by the
section it sits in: the eye check (only a person reading the scan can confirm it), the
Phase 3 pricing calibration or Phase 4 record linking (invoices or records will confirm it
once those rules are modelled), quote-checked prose (words, matched to the OCR text), or
not used by any invoice line.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterator
from pathlib import Path

EYE, P3, P4, QUOTED, UNUSED = (
    "eye check",
    "Phase 3 calibration",
    "Phase 4 linking",
    "quote-checked prose",
    "not used by any invoice line",
)
# Section prefix -> group, first match wins. Instrument dates and term ends cannot be seen in
# billed rates; instrument rates, monthly rates and discounts can, once P3 prices by date.
GROUPS = [
    (".issued", EYE),
    (".term_end", EYE),
    ("instruments", P3),
    ("daily_limits", EYE),
    ("exclusions", EYE),
    ("surveyed_items", EYE),
    ("once_per_well", EYE),
    ("record_series", P4),
    ("ddr_parts", P4),
    ("report_terms", P4),
    ("lost_in_hole", P4),
    ("daywork", UNUSED),
    ("provisional_sums", UNUSED),
    ("preliminaries", UNUSED),
]
CALIBRATION_REPORT_SHARE = 0.9  # calibration rows below this agreement are listed


def terms_in(node: object, path: str = "") -> Iterator[tuple[str, dict]]:
    """Every (path, term) in a contract dict; a term is a dict with value, source, verified."""
    if isinstance(node, dict):
        if {"value", "source", "verified"} <= node.keys():
            yield path, node
            return
        for key, child in node.items():
            yield from terms_in(child, f"{path}.{key}" if path else key)
    elif isinstance(node, list):
        for index, child in enumerate(node):
            yield from terms_in(child, f"{path}[{index}]")


def group_of(path: str, entry: dict) -> str:
    """Return the group an unverified value belongs to."""
    if path.startswith("terms."):
        return EYE if _holds_a_number(entry["value"]) else QUOTED
    for prefix, group in GROUPS:
        if prefix in path if prefix.startswith(".") else path.startswith(prefix):
            return group
    return P3


def _holds_a_number(value: object) -> bool:
    """Numbers and dates need a look at the scan; words were already matched to the OCR text."""
    if isinstance(value, list):
        return False
    if isinstance(value, str):
        return value[:1].isdigit()
    return True


def number_count(entry: dict) -> int:
    """How many numbers a value holds for the eye check: a month table counts its open months."""
    if isinstance(entry["value"], dict):
        return len(entry["value"]) - len(entry.get("confirmed_months", []))
    return 1


def open_values(contract: dict) -> list[tuple[str, str, dict]]:
    """(group, path, term) for every value not yet verified."""
    return [
        (group_of(path, entry), path, entry)
        for path, entry in terms_in(contract)
        if not entry["verified"]
    ]


def write_report(results: list[tuple[str, dict, dict]], path: Path) -> str:
    """Write the verification report; return the counts line for the log."""
    lines = ["# Contract verification (Phase 2)", ""]
    totals: Counter[str] = Counter()
    for name, contract, checks in results:
        all_terms = list(terms_in(contract))
        verified = sum(entry["verified"] for _, entry in all_terms)
        opened = open_values(contract)
        counts = Counter()
        for group, _, entry in opened:
            counts[group] += number_count(entry)
        totals.update(counts)
        lines += _contract_section(name, len(all_terms), verified, counts, checks, opened)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return ", ".join(f"{group}: {count}" for group, count in sorted(totals.items()))


def _contract_section(
    name: str, total: int, verified: int, counts: Counter, checks: dict, opened: list
) -> list[str]:
    lines = [f"## {name}", ""]
    lines.append(f"- values extracted: {total}; verified by the invoices: {verified}")
    lines.append(f"- codes billed but missing from Schedule 1: {checks['missing_codes'] or 'none'}")
    lines.append(f"- OCR corrections applied: {len(checks['corrections'])}")
    for header in checks["headers"]:
        lines.append(f"- {header}")
    for group, count in sorted(counts.items()):
        lines.append(f"- open, {group}: {count} numbers")
    lines += [
        "",
        "### OCR corrections",
        "",
        "| page | OCR text | corrected | reason |",
        "|---|---|---|---|",
    ]
    for fix in checks["corrections"]:
        ocr = fix.get("ocr_text", "(rows appended)").strip("| ")
        corrected = fix.get("corrected", "see file").strip("| ")
        lines.append(f"| {fix['page']} | `{ocr}` | `{corrected}` | {fix['reason']} |")
    lines += [
        "",
        "### Calibration below 90 % agreement",
        "",
        "| value | reproduced | lines |",
        "|---|---|---|",
    ]
    for row in checks["calibration"]:
        if row["matched"] < CALIBRATION_REPORT_SHARE * row["lines"]:
            lines.append(f"| {row['value']} | {row['matched']} | {row['lines']} |")
    lines += ["", "### Eye check and second OCR engine", "", "| value | evidence |", "|---|---|"]
    for value_path, evidence in checks.get("eye_checks", []):
        lines.append(f"| `{value_path}` | {evidence} |")
    lines += [
        "",
        "### Open values",
        "",
        "| group | value | extracted | source |",
        "|---|---|---|---|",
    ]
    for group, path, entry in sorted(opened, key=lambda item: (item[0], item[1])):
        shown = entry["value"] if not isinstance(entry["value"], dict) else "(month table)"
        lines.append(f"| {group} | `{path}` | {shown} | {entry['source']} |")
    lines.append("")
    return lines
