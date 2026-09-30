"""Stage commands: `uv run python -m audit ocr|audit|eval|all`.

ocr   scanned contracts -> extracted/ocr (once; output is committed, so later runs skip it)
audit invoices + extracted contract terms -> output/findings.csv and submission.csv
eval  synthetic error injection -> output/eval.md (code lives in eval/ at the project root)
all   ocr, audit, eval in that order; runs offline, no API key needed
"""

from __future__ import annotations

import argparse
import logging
import runpy
import sys
from collections.abc import Callable

from audit import config


def run_ocr() -> None:
    """OCR the contracts; pages already extracted are skipped."""
    paths = config.input_paths()  # fail early and clearly if the PDFs are missing
    from audit import ocr  # imported here: Docling is heavy and only this stage needs it

    ocr.run(paths)


def run_extract() -> None:
    """Build and check the contract JSON from the committed OCR pages."""
    paths = config.input_paths()
    from audit import extract

    extract.run(paths)


def run_crops() -> None:
    """Cut the page crops for the eye check (a review aid; not part of `all`)."""
    paths = config.input_paths()
    from audit.extract.crops import make_crops

    make_crops(paths)


def run_audit() -> None:
    """Run the checks and write findings.csv and submission.csv."""
    paths = config.input_paths()
    from audit import decide

    print(decide.run(paths))


def run_eval() -> None:
    """Score the pipeline on injected errors."""
    config.input_paths()
    # eval/ sits outside the package (it is tooling, not the auditor), so load it by path.
    evaluate = runpy.run_path(str(config.PROJECT_ROOT / "eval" / "evaluate.py"))
    evaluate["main"]()


STAGES: dict[str, list[Callable[[], None]]] = {
    "ocr": [run_ocr],
    "extract": [run_extract],
    "crops": [run_crops],
    "audit": [run_audit],
    "eval": [run_eval],
    "all": [run_ocr, run_extract, run_audit, run_eval],
}


def main(argv: list[str] | None = None) -> int:
    """Run the stage named on the command line; exit code 2 when an input is missing."""
    parser = argparse.ArgumentParser(
        prog="python -m audit",
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("stage", choices=list(STAGES))
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    try:
        for step in STAGES[args.stage]:
            step()
    except config.ConfigError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    return 0
