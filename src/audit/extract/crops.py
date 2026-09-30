"""Cut page crops for the eye check: each crop shows the scan behind a group of numbers.

Input: the contract PDFs, the extracted JSON and the eye-check list (report.open_values).
Output: extracted/ocr/crops/NN_<name>.png and crops/README.md, which lists for every crop the
JSON values and their extracted figures to compare with the image. Regions are given as
fractions of the page height, read off the rendered pages; two small strips from different
pages may share one image. Stops if any eye-check value is not covered by a crop.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

import pypdfium2 as pdfium
from PIL import Image

from audit.config import OCR_DIR, InputPaths
from audit.contract import load_contract
from audit.extract.report import EYE, open_values

CROPS_DIR = OCR_DIR / "crops"
RENDER_SCALE = 1.6  # enough to read digits; grayscale keeps the committed files small
GAP = 12  # pixels of white between two stacked strips

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class Crop:
    """One image: page regions (page, top, bottom as fractions) and the JSON paths it shows."""

    name: str
    contract: str
    regions: tuple[tuple[int, float, float], ...]
    paths: tuple[str, ...]


CROPS = (
    Crop("civil_cl7_night_hours", "civil", ((3, 0.60, 0.70),), ("terms.night_hours",)),
    Crop("civil_cl41_window", "civil", ((8, 0.17, 0.28),), ("terms.window_days",)),
    Crop(
        "civil_sch4_limits_exclusions_surveyed",
        "civil",
        ((26, 0.06, 0.62),),
        ("daily_limits.", "exclusions.", "surveyed_items"),
    ),
    Crop(
        "civil_part7_6A_27A_33A_45A",
        "civil",
        ((32, 0.20, 0.92),),
        (
            "terms.chargeable_hour_deduction",
            "terms.night_uplift_max_zone_factor",
            "terms.ground_datum_after",
            "terms.survey_tolerance_pct",
            "terms.retention_release_share",
        ),
    ),
    Crop("civil_cl47A_five_days", "civil", ((33, 0.08, 0.20),), ("terms.week_min_days",)),
    Crop(
        "civil_term_dates",
        "civil",
        ((38, 0.38, 0.46),),
        ("terms.commencement", "terms.completion_as_let", "terms.completion"),
    ),
    Crop("civil_supplement_1_issued", "civil", ((39, 0.07, 0.13),), ("instruments[0].",)),
    Crop("civil_amendment_1_issued_extension", "civil", ((40, 0.07, 0.29),), ("instruments[1].",)),
    Crop("civil_supplement_2_issued", "civil", ((41, 0.07, 0.13),), ("instruments[2].",)),
    Crop("civil_amendment_2_issued_extension", "civil", ((42, 0.07, 0.30),), ("instruments[3].",)),
    Crop("civil_amendment_3_issued", "civil", ((43, 0.07, 0.13),), ("instruments[4].",)),
    Crop(
        "drilling_cl31_depreciation",
        "drilling",
        ((7, 0.52, 0.63),),
        ("terms.lost_in_hole_depreciation",),
    ),
    Crop("drilling_cl33_window", "drilling", ((8, 0.17, 0.25),), ("terms.window_days",)),
    Crop("drilling_sch3_limits_page_21", "drilling", ((21, 0.51, 0.92),), ("daily_limits.",)),
    Crop(
        "drilling_sch3_limits_page_22_once_per_well",
        "drilling",
        ((22, 0.06, 0.34),),
        ("daily_limits.", "once_per_well"),
    ),
    Crop(
        "drilling_21A_25A",
        "drilling",
        ((35, 0.46, 0.62),),
        ("terms.chargeable_hour_deduction", "terms.metres_tolerance_pct"),
    ),
    Crop(
        "drilling_term_dates",
        "drilling",
        ((37, 0.38, 0.44),),
        ("terms.commencement", "terms.expiry_as_let", "terms.expiry"),
    ),
    Crop(
        "drilling_supplements_1_2_issued",
        "drilling",
        ((38, 0.07, 0.13), (40, 0.07, 0.13)),
        ("instruments[0].", "instruments[2]."),
    ),
    Crop(
        "drilling_amendment_1_issued_extension",
        "drilling",
        ((39, 0.07, 0.28),),
        ("instruments[1].",),
    ),
    Crop(
        "drilling_amendment_2_issued_extension",
        "drilling",
        ((41, 0.07, 0.28),),
        ("instruments[3].",),
    ),
    Crop("drilling_amendment_3_issued", "drilling", ((42, 0.07, 0.13),), ("instruments[4].",)),
)


def eye_check_paths(contract: str) -> dict[str, dict]:
    """Path -> term for every value of the contract on the eye-check list."""
    return {
        path: entry for group, path, entry in open_values(load_contract(contract)) if group == EYE
    }


def assign(crops: tuple[Crop, ...]) -> dict[str, list[tuple[str, dict]]]:
    """Crop name -> the eye-check values it shows; stop if a value has no crop."""
    shown: dict[str, list[tuple[str, dict]]] = {crop.name: [] for crop in crops}
    for contract in ("civil", "drilling"):
        for path, entry in eye_check_paths(contract).items():
            owner = next(
                (
                    crop
                    for crop in crops
                    if crop.contract == contract
                    and any(path.startswith(prefix) for prefix in crop.paths)
                    and _on_crop_page(crop, entry)
                ),
                None,
            )
            if owner is None:
                raise ValueError(f"{contract} {path} ({entry['source']}) is in no crop")
            shown[owner.name].append((path, entry))
    return shown


def crop_shows(crop: Crop, path: str, entry: dict) -> bool:
    """Tell whether a crop shows a value: its path matches and its source page is on the crop."""
    return any(path.startswith(prefix) for prefix in crop.paths) and _on_crop_page(crop, entry)


def _on_crop_page(crop: Crop, entry: dict) -> bool:
    """Tell whether the value's source page is one of the crop's pages ('pp.21-22': both)."""
    pages = {page for page, _, _ in crop.regions}
    source = entry["source"].split()[0].lstrip("p.")
    first, _, last = source.partition("-")
    span = range(int(first), int(last or first) + 1)
    return bool(pages & set(span))


def render_crop(pdf: pdfium.PdfDocument, crop: Crop) -> Image.Image:
    """Cut the crop's regions from the rendered pages and stack them top to bottom."""
    strips = []
    for page, top, bottom in crop.regions:
        image = pdf[page - 1].render(scale=RENDER_SCALE).to_pil().convert("L")
        width, height = image.size
        strips.append(image.crop((0, int(height * top), width, int(height * bottom))))
    width = max(strip.width for strip in strips)
    height = sum(strip.height for strip in strips) + GAP * (len(strips) - 1)
    sheet = Image.new("L", (width, height), color=255)
    offset = 0
    for strip in strips:
        sheet.paste(strip, (0, offset))
        offset += strip.height + GAP
    return sheet


def make_crops(paths: InputPaths) -> None:
    """Write every crop image and the index a reviewer reads them with."""
    shown = assign(CROPS)
    pdfs = {
        "civil": pdfium.PdfDocument(str(paths.civil_contract_pdf)),
        "drilling": pdfium.PdfDocument(str(paths.drilling_contract_pdf)),
    }
    CROPS_DIR.mkdir(parents=True, exist_ok=True)
    index = ["# Eye-check crops", "", "Compare each value with the image; note any difference."]
    for number, crop in enumerate(CROPS, start=1):
        file_name = f"{number:02d}_{crop.name}.png"
        render_crop(pdfs[crop.contract], crop).save(CROPS_DIR / file_name, optimize=True)
        pages = ", ".join(f"p.{page}" for page, _, _ in crop.regions)
        index += ["", f"## {number:02d}. {crop.contract} {pages}: `{file_name}`", ""]
        index += ["| value | extracted | source |", "|---|---|---|"]
        for path, entry in shown[crop.name]:
            index.append(f"| `{path}` | {entry['value']} | {entry['source']} |")
    (CROPS_DIR / "README.md").write_text("\n".join(index) + "\n", encoding="utf-8")
    total = sum(len(values) for values in shown.values())
    log.info("crops: %d images, %d values, in %s", len(CROPS), total, CROPS_DIR)
