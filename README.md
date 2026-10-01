# Invoice Audit — Level 2
 
Audits 2,806 invoices against two amended contracts — 900 civil-works applications under
CW-2025-0417-CIV and 1,906 drilling invoices under DDS-2025-118 — and writes
`submission.csv`: for each invoice, whether it is wrong, the error category, the total the
contract supports, the billed total and a confidence.
 
```mermaid
flowchart LR
  PDF[contract PDFs] --> OCR[ocr: Docling, once] --> TXT[extracted/ocr pages]
  TXT --> EXT[extract: tables + quote-checked clauses] --> CJ[contract JSON]
  COR[ocr_corrections.json, eye_checks.json] --> EXT
  CSV[invoice CSVs] --> CHK
  REC[site records, daily reports] --> LNK[records + linker]
  MAP[mappings JSON: 26 templates, Appendix G] --> LNK
  CJ --> PR[pricing engine]
  PR --> CAL[calibration.md]
  CJ --> CHK[checks c01-c11 in guideline order]
  PR --> CHK
  LNK --> CHK
  CHK --> F[findings.csv] --> DEC[decide] --> SUB[submission.csv]
  SUB --> EV[eval: injected errors, sets A and B] --> EVM[eval.md]
  CAL -. a whole group repriced? re-read the clause .-> EXT
```
 
## What it does
 
1. **OCR** (`ocr`): the scanned contracts are read once with Docling (RapidOCR); the page
   text is committed in `extracted/ocr/`, so later runs and the evaluator do not need the
   OCR models.
2. **Extraction** (`extract`): every rate, factor, date and percentage is written to
   `extracted/contracts/{civil,drilling}.json` with its page and clause. Values are verified
   against the invoices (calibration), by a manual check against the scanned page, or by a
   second OCR engine (`output/contract_verification.md`).
3. **Audit** (`audit`): records are parsed and linked to lines, each line the contract prices
   is priced by its build-up, and guideline checks 1-11 run in order (c01 ... c11). A line
   rejected by an earlier check is not re-priced by a later one. `decide` turns the findings
   into one verdict per invoice.
4. **Evaluation** (`eval`): errors are planted in clean invoices (set A for tuning, set B for
   the result) and the pipeline is scored on them.
The civil record wording is mapped to items with a fixed table
of 26 templates (`extracted/mappings/civil_phrases.json`): all 2,169 records match exactly one
template, so the phrase-mapping prompt (`prompts/v1_phrase_mapping.md`) was not needed and
was not used. Drilling report words are mapped through the contract's Appendix G and
Schedule 8 (`extracted/mappings/drilling_terms.json`).
 
## Setup and run
 
The exercise data (both contracts, the invoices, the site records and daily reports, and the
submission template) is included in `./data`. The pipeline only reads this folder.
 
### With uv
 
1. Install uv, if it is not installed:
```text
   # Linux / macOS
   curl -LsSf https://astral.sh/uv/install.sh | sh
 
   # Windows (PowerShell)
   powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```
 
   Open a new terminal afterwards so that `uv` is on the PATH.
2. From the project folder, install the exact versions pinned in `uv.lock` (Python 3.11; uv
   downloads it if it is missing):
 
```text
   uv sync --locked
```
 
3. Run:
```text
   uv run python -m audit all      # ocr (skips committed pages), extract, audit, eval; no network needed
   uv run python -m audit audit    # checks only -> output/findings.csv, submission.csv
   uv run python -m audit eval     # injected errors -> output/eval.md
   uv run pytest                   # 125 tests
```
 
### Without uv
 
1. With Python 3.11 installed, from the project folder:
```text
   python -m venv .venv
   .venv\Scripts\Activate.ps1      # Windows PowerShell (or .venv\Scripts\activate in cmd)
   source .venv/bin/activate        # Linux / macOS
   pip install -r requirements.txt
   pip install -e . --no-deps
```
 
 
2. Run:
```text
   python -m audit all              # ocr (skips committed pages), extract, audit, eval; no network needed
   python -m audit audit            # checks only -> output/findings.csv, submission.csv
   python -m audit eval             # injected errors -> output/eval.md
```
 
### Reading the contracts again
 
To read the contracts again from the scans, delete `extracted/ocr/civil/` and
`extracted/ocr/drilling/`, then run `all` (with or without uv). This takes about an hour on a
CPU, and Docling downloads its models on the first run.
If the new OCR text differs from the committed text, the extract stage stops at the first
correction it cannot find; update extracted/contracts/ocr_corrections.json for that page.
 
## Outputs
 
| file | content |
| --- | --- |
| `submission.csv` | the deliverable: 2,806 rows in template order, money in minor units |
| `output/findings.csv` | every finding: check, category, money effect, clause, evidence, confidence, status |
| `output/calibration.md` | share of lines whose billed rate the pricing engine reproduces, per item and rate period |
| `output/eval.md` | set B result (and set A, the tuning record) |
| `output/contract_verification.md` | how each extracted value was verified |
| `docs/REPORT.md`, `docs/DECISION_LOG.md` | results, error analysis, and the readings chosen where the text left a choice |
 
## AI disclosure
 
AI assistance was used for data exploration, planning and implementation, under the author's
direction and review. The prompts are in `prompts/`.