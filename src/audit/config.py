"""Every path the project uses, in one place (CLAUDE.md §0).

Inputs are read from DATA_DIR (default ./data) and TEMPLATE_PATH (default
./data/submission_template.csv). Both can be set as environment variables or in a
`.env` file at the project root; a real environment variable wins over `.env`.
Nothing under DATA_DIR is ever written.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, fields
from pathlib import Path

# src/audit/config.py -> project root is two levels above the package folder.
PROJECT_ROOT = Path(__file__).resolve().parents[2]

# Project-side locations (code writes here, never into DATA_DIR).
EXTRACTED_DIR = PROJECT_ROOT / "extracted"
OCR_DIR = EXTRACTED_DIR / "ocr"
CONTRACTS_DIR = EXTRACTED_DIR / "contracts"
MAPPINGS_DIR = EXTRACTED_DIR / "mappings"
OUTPUT_DIR = PROJECT_ROOT / "output"
SUBMISSION_PATH = PROJECT_ROOT / "submission.csv"


class ConfigError(RuntimeError):
    """An input the pipeline needs is missing or misconfigured."""


@dataclass(frozen=True)
class InputPaths:
    """Every input file or folder, resolved from DATA_DIR and TEMPLATE_PATH."""

    data_dir: Path
    template: Path
    # Civil works, CW-2025-0417-CIV
    civil_contract_pdf: Path
    civil_guidelines: Path
    civil_applications: Path
    civil_application_lines: Path
    civil_records_dir: Path
    # Directional drilling, DDS-2025-118
    drilling_contract_pdf: Path
    drilling_guidelines: Path
    drilling_invoices: Path
    drilling_invoice_lines: Path
    drilling_records_dir: Path


def _read_dotenv(path: Path) -> dict[str, str]:
    """Minimal KEY=VALUE reader for .env (no extra dependency needed for two settings)."""
    values: dict[str, str] = {}
    if not path.is_file():
        return values
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def _setting(name: str, default: Path) -> Path:
    """Env var, else .env, else the default.

    Relative values are taken from the project root, so the pipeline behaves the same
    whatever folder it is started from (DECISION_LOG D04).
    """
    value = os.environ.get(name) or _read_dotenv(PROJECT_ROOT / ".env").get(name)
    path = Path(value) if value else default
    return (path if path.is_absolute() else PROJECT_ROOT / path).resolve()


def input_paths(check: bool = True) -> InputPaths:
    """Resolve every input path; with check=True, fail listing everything that is missing."""
    data_dir = _setting("DATA_DIR", Path("data"))
    template = _setting("TEMPLATE_PATH", Path("data") / "submission_template.csv")
    civil = data_dir / "civilwork"
    drill = data_dir / "drilling_services"
    paths = InputPaths(
        data_dir=data_dir,
        template=template,
        civil_contract_pdf=civil / "contract" / "CW-2025-0417-CIV.pdf",
        civil_guidelines=civil / "guidelines" / "INVOICE_AUDIT_GUIDELINES.md",
        civil_applications=civil / "invoices" / "applications.csv",
        civil_application_lines=civil / "invoices" / "application_lines.csv",
        civil_records_dir=civil / "records",
        drilling_contract_pdf=drill / "contract" / "DDS-2025-118.pdf",
        drilling_guidelines=drill / "guidelines" / "INVOICE_AUDIT_GUIDELINES.md",
        drilling_invoices=drill / "invoices" / "invoices.csv",
        drilling_invoice_lines=drill / "invoices" / "invoice_lines.csv",
        drilling_records_dir=drill / "records",
    )
    if check:
        _check(paths)
    return paths


def _check(paths: InputPaths) -> None:
    """Raise ConfigError naming every input file or folder that is missing."""
    missing = []
    for f in fields(paths):
        path: Path = getattr(paths, f.name)
        is_dir = f.name.endswith("_dir")
        ok = path.is_dir() if is_dir else path.is_file()
        if ok and is_dir and f.name != "data_dir" and not any(path.glob("*.txt")):
            ok = False  # a records folder with no .txt files is as good as missing
        if not ok:
            missing.append(f"  - {f.name}: {path}")
    if missing:
        raise ConfigError(
            "Input data not found:\n"
            + "\n".join(missing)
            + "\n\nCopy civilwork/, drilling_services/ and submission_template.csv from "
            "https://github.com/majedzahrani3/invoice-auditing-level-2 into ./data, or set "
            "DATA_DIR and TEMPLATE_PATH (environment or .env, see .env.example)."
        )
