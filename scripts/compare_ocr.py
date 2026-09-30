"""Compare Docling and Tesseract on five pages of the civil contract CW-2025-0417-CIV.

Pages 17-19 (Schedule 1, one rate per row) are scored against the invoices.
Pages 24 (Schedule 4) and 40 (Amendment 1) have several number columns per row and are scored
against rows checked by eye on the scans, to test whether each engine keeps columns in order.

For each engine it reports:
  - how many of the 60 item codes billed in the invoices it found on the page,
  - how many extracted base rates equal the most common billed rate on clean lines
    (zone Z1, no ground class, no night work, work before 2025-05-01),
  - the mismatches, and the run time.
Then it lists every code where the two engines read a different number.

Usage (from the project folder):
    pip install docling pytesseract pypdfium2 pandas
    python compare_ocr.py   (data in ./data)
Tesseract must be installed on the system for the Tesseract part (brew/apt install tesseract).
"""
import argparse, re, time
from pathlib import Path

import pandas as pd

RATE_PAGES = (17, 19)                     # Schedule 1: one rate per row
RANGES = [(17, 19), (24, 24), (40, 40)]   # + Schedule 4 and Amendment 1 (several number columns)

# Rows checked by eye against the scans (pages 24 and 40). A row counts as read correctly
# only if one line holds the code and every value, in this left-to-right order.
TRUTH = [
    # p.24 Part 1, night working uplift
    ("A.12.020", "18%"), ("A.12.030", "18%"), ("A.14.010", "18%"), ("B.21.020", "22%"),
    ("B.21.030", "22%"), ("C.31.010", "18%"), ("D.41.020", "25%"), ("D.41.030", "25%"),
    ("D.43.010", "25%"), ("A.12.040", "18%"), ("B.21.040", "22%"), ("C.31.030", "18%"),
    ("D.43.020", "25%"),
    # p.24 Part 2, rest-day uplift
    ("B.21.020", "35%"), ("B.21.030", "35%"), ("D.41.030", "35%"), ("B.21.040", "35%"),
    # p.24 Part 3, banded quantities
    ("A.12.010", "1 to 4,000", "m3", "100%"), ("A.12.010", "4,001 to 16,000", "m3", "96%"),
    ("A.12.010", "above 16,000", "m3", "93%"), ("A.12.020", "1 to 1,500", "m3", "100%"),
    # p.40 Amendment 1, substituted rates: old rate, new rate, effective date
    ("E.54.010", "week", "876.00", "948.00", "2025-10-01"),
    ("B.23.010", "tonne", "4,385.00", "4,450.00", "2025-10-01"),
]


def row_ok(text, fields):
    norm = lambda s: re.sub(r"\s+", " ", s)
    for line in text.splitlines():
        line = norm(line)
        pos = 0
        for f in fields:
            i = line.find(norm(f), pos)
            if i < 0:
                break
            pos = i + len(f)
        else:
            return True
    return False
ROW = re.compile(r"([A-E]\.\d{2}\.\d{3}).*?([\d,]+\.\d{2})\s*\|?\s*[.:a-z]?\s*$")


def rates_from_text(text):
    text = text.split("\f")[0]  # rates only from the Schedule 1 part (see run_*)
    out = {}
    for line in text.splitlines():
        m = ROW.search(line.strip())
        if m:
            out[m.group(1)] = float(m.group(2).replace(",", ""))
    return out


def run_docling(pdf, engine):
    from docling.datamodel.base_models import InputFormat
    from docling.datamodel.pipeline_options import PdfPipelineOptions
    from docling.document_converter import DocumentConverter, PdfFormatOption

    opts = PdfPipelineOptions(do_ocr=True, do_table_structure=True)
    if engine == "tesseract":
        from docling.datamodel.pipeline_options import TesseractCliOcrOptions
        opts.ocr_options = TesseractCliOcrOptions(force_full_page_ocr=True)
    conv = DocumentConverter(format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=opts)})
    parts = []
    for r in RANGES:
        res = conv.convert(str(pdf), page_range=r)
        parts.append(res.document.export_to_markdown())
    md = "\f".join(parts)
    Path(f"docling_{engine}.md").write_text(md, encoding="utf-8")
    return md


def run_tesseract(pdf):
    import pypdfium2 as pdfium
    import pytesseract

    doc = pdfium.PdfDocument(str(pdf))
    parts = []
    for a, b in RANGES:
        pages = [pytesseract.image_to_string(doc[i].render(scale=300 / 72).to_pil(), config="--psm 6")
                 for i in range(a - 1, b)]
        parts.append("\n".join(pages))
    txt = "\f".join(parts)
    Path("tesseract.txt").write_text(txt, encoding="utf-8")
    return txt


def score(name, text, codes, billed, seconds):
    rates = rates_from_text(text)
    found = codes & set(rates)
    ok, bad = 0, []
    for code, b in billed.items():
        if code in rates:
            if abs(rates[code] - b) < 0.005:
                ok += 1
            else:
                bad.append((code, rates[code], b))
    print(f"\n=== {name}  ({seconds:.0f}s)")
    print(f"codes found: {len(found)}/{len(codes)}   missing: {sorted(codes - set(rates))}")
    print(f"base rate == billed on clean lines: {ok}   different: {len(bad)}")
    for code, r, b in bad:
        print(f"   {code}: read {r:,.2f}  billed {b:,.2f}  ratio {b / r:.4f}")
    rest = text.split("\f", 1)[1] if "\f" in text else ""
    miss = [t for t in TRUTH if not row_ok(rest, t)]
    print(f"multi-column rows (p.24, p.40) read with every value in order: "
          f"{len(TRUTH) - len(miss)}/{len(TRUTH)}")
    for t in miss:
        print("   not found:", " | ".join(t))


def main():
    ap = argparse.ArgumentParser()
    # default: the data/ folder next to this script, so it works from any working directory
    ap.add_argument("--data", default=str(Path(__file__).resolve().parent / "data"))
    ap.add_argument("--skip-tesseract", action="store_true")
    a = ap.parse_args()
    data = Path(a.data)
    for f in ("civilwork/contract/CW-2025-0417-CIV.pdf", "civilwork/invoices/application_lines.csv"):
        if not (data / f).exists():
            raise SystemExit(f"Missing input: {data / f}\nCheck that data/ holds civilwork/ and drilling_services/.")
    print(f"Reading data from: {data}")
    pdf = data / "civilwork/contract/CW-2025-0417-CIV.pdf"
    lines = pd.read_csv(data / "civilwork/invoices/application_lines.csv")
    codes = set(lines.item_code)
    clean = lines[(lines.site_zone == "Z1 Compound") & lines.ground_class.isna()
                  & (lines.night_work == "N") & (lines.work_date < "2025-05-01")]
    billed = clean.groupby("item_code").rate_applied.agg(lambda s: s.mode().iloc[0]).to_dict()

    results = {}
    for name, fn in [("Docling (auto OCR)", lambda: run_docling(pdf, "auto")),
                     ("Docling (Tesseract OCR)", lambda: run_docling(pdf, "tesseract")),
                     ("Tesseract only", lambda: run_tesseract(pdf))]:
        if name == "Tesseract only" and a.skip_tesseract:
            continue
        t = time.time()
        try:
            results[name] = fn()
        except Exception as e:  # keep going so one failure does not hide the others
            print(f"\n=== {name}: FAILED — {type(e).__name__}: {e}")
            continue
        score(name, results[name], codes, billed, time.time() - t)

    names = list(results)
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            x, y = rates_from_text(results[names[i]]), rates_from_text(results[names[j]])
            diff = sorted(c for c in set(x) & set(y) if abs(x[c] - y[c]) >= 0.005)
            print(f"\n{names[i]} vs {names[j]}: {len(diff)} codes read differently {diff}")


if __name__ == "__main__":
    main()