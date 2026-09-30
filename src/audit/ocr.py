"""OCR the two scanned contracts into one markdown file per page.

Input: the contract PDFs under DATA_DIR. Output: extracted/ocr/<contract>/page_XX.md.
Docling runs with the settings measured in scripts/compare_ocr.py (OCR on, auto engine =
RapidOCR, TableFormer ACCURATE). Each page is converted in its own Python process: Docling's
memory grows with every conversion and crashed after two pages on a 16 GB machine, while a
fresh process per page keeps the peak at one page. Pages already written are skipped, so an
interrupted run resumes; the output is committed, so the audit never needs the OCR models.
"""

from __future__ import annotations

import logging
import subprocess
import sys
import time
from pathlib import Path

import pypdfium2 as pdfium

from audit.config import OCR_DIR, InputPaths, input_paths

PAGE_FILE = "page_{:02d}.md"
STDERR_TAIL = 2000  # characters of a failed child's stderr kept in the error message

log = logging.getLogger(__name__)


def contract_pdfs(paths: InputPaths) -> dict[str, Path]:
    """Return the contract PDFs keyed by output folder name."""
    return {"civil": paths.civil_contract_pdf, "drilling": paths.drilling_contract_pdf}


def page_count(pdf: Path) -> int:
    """Return the number of pages in a PDF."""
    document = pdfium.PdfDocument(str(pdf))
    try:
        return len(document)
    finally:
        document.close()


def page_path(out_dir: Path, page: int) -> Path:
    """Where the markdown for one page is written."""
    return out_dir / PAGE_FILE.format(page)


def convert_page(pdf: Path, page: int, target: Path) -> None:
    """OCR one page with the measured Docling settings and write it as markdown."""
    from docling.datamodel.base_models import InputFormat
    from docling.datamodel.pipeline_options import PdfPipelineOptions, TableFormerMode
    from docling.document_converter import DocumentConverter, PdfFormatOption

    options = PdfPipelineOptions(do_ocr=True, do_table_structure=True)
    options.table_structure_options.mode = TableFormerMode.ACCURATE
    converter = DocumentConverter(
        format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=options)}
    )
    markdown = converter.convert(str(pdf), page_range=(page, page)).document.export_to_markdown()
    # Write to a temporary file first so a crash never leaves half a page behind.
    partial = target.with_suffix(".part")
    partial.write_text(markdown + "\n", encoding="utf-8")
    partial.replace(target)


def run(paths: InputPaths | None = None) -> None:
    """OCR every page of both contracts that has no output yet, one process per page."""
    paths = paths or input_paths()
    for name, pdf in contract_pdfs(paths).items():
        out_dir = OCR_DIR / name
        out_dir.mkdir(parents=True, exist_ok=True)
        pages = range(1, page_count(pdf) + 1)
        missing = [page for page in pages if not page_path(out_dir, page).exists()]
        if not missing:
            log.info("ocr: %s already extracted (%d pages), skipped", name, len(pages))
            continue
        for page in missing:
            started = time.perf_counter()
            target = page_path(out_dir, page)
            command = [sys.executable, "-m", "audit.ocr", str(pdf), str(page), str(target)]
            completed = subprocess.run(command, capture_output=True, text=True, check=False)
            if completed.returncode != 0 or not target.exists():
                raise RuntimeError(
                    f"ocr: {pdf.name} page {page} failed (exit {completed.returncode}):\n"
                    f"{completed.stderr[-STDERR_TAIL:]}"
                )
            seconds = time.perf_counter() - started
            log.info("ocr: %s page %d/%d (%.0f s)", name, page, len(pages), seconds)


if __name__ == "__main__":
    # Child process entry point used by run(): python -m audit.ocr <pdf> <page> <target>
    convert_page(Path(sys.argv[1]), int(sys.argv[2]), Path(sys.argv[3]))
