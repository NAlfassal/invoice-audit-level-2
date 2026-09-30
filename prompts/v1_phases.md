
 
Paste one phase at a time into Claude Code, opened in the project folder `invoice_audit_level2/`,
with `CLAUDE.md` at its root. Inputs are read from the exercise repo via `DATA_DIR` (CLAUDE.md §0).
Claude Code never runs git or creates repositories; version control and uploading are done by hand.
 
Do not start the next phase until the current one's acceptance criteria are met and you
have reviewed the summary. When you change a prompt, save the new version as a new file
(`v2_phases.md`, …) whose first line says what changed and why.
 
Time budget (16 h cap). Original: P0 0.5 · P1 1.5 · P2 3.5 · P3 3 · P4 3 · P5 1.5 · P6 1.5 · P7 1.5.
Revised: about 8 working hours remain for P3, P4, P6 and P7.
P5 is folded in: retro adjustment and discounts go to P3; daily caps, once-only items and
minimum charges go to P4. Both parts are required, not optional.
 
---
 
## P0 — Kick-off and setup (0.5 h)
 
```
Read CLAUDE.md fully. Then read the original brief invoice-auditing-level-2-main/README.md and,
from DATA_DIR (./data, read-only), both */guidelines/INVOICE_AUDIT_GUIDELINES.md files.
 
Then:
1. Restate the task, the scoring and the five deliverables in ≤12 bullets so I can confirm you
   understood. Flag anything in CLAUDE.md that contradicts the README or the guidelines.
2. Create the target structure from CLAUDE.md §6 in THIS folder (empty modules with docstrings
   are fine). Do not create or initialise any repository. src/audit/config.py resolves DATA_DIR
   from the environment (default ./data) and TEMPLATE_PATH (default ./data/submission_template.csv), fails
   with a clear message if either or any expected input file is missing, and exposes every
   input path.
3. Set up uv + pyproject.toml with pinned versions: pandas, docling,
   pytest. No Makefile (Windows): add src/audit/cli.py + __main__.py so that
   `uv run python -m audit ocr|audit|eval|all` runs each stage, and `uv run pytest` runs tests.
4. Write src/audit/io.py: load the four CSVs from DATA_DIR, parse every date format listed in CLAUDE.md §5
   into datetime.date, money columns into Decimal. Add tests that the row counts are
   900 / 7,746 / 1,906 / 91,244 and that PA-00001 application_total == Decimal("265123.89").
5. Create docs/DECISION_LOG.md (template: Assumption / Ambiguity /
   Reading chosen / Why / Impact).
 
Stop and report. Do not start Phase 1.
```
 
---
 
## P1 — Contract-independent checks + first submission (1.5 h)
 
```
Goal: a complete, valid submission.csv using only checks that need no rate extraction.
Use the verified facts in CLAUDE.md §5 only.
 
Implement in src/audit/checks/ (each returns findings rows per CLAUDE.md §7):
- c01_contract: contract_ref and issuer match the contract (exact string).
- c02_term: every work/service date inside the extended term (civil ≤ 2026-09-30,
  drilling ≤ 2026-12-31, both ≥ commencement).
- c03_window: civil — submitted on/after period_to and within 21 days of it; every line's
  work_date inside [period_from, period_to]. Drilling — within 30 days of period_end,
  not before it; service dates inside the period.
- c04_record_presence (civil only for now): Schedule 5 items with blank record_ref, or a
  record_ref whose series prefix does not match the item (e.g. a PR ref on D.41.010),
  or a record file that does not exist.
- c10_duplicates: same (item, date, site, quantity) or same record_ref+item billed twice,
  within an invoice or across invoices. Report both copies; the later invoice is the error.
- c11_arithmetic: quantity × rate = amount per line; Σ lines = subtotal; civil retention
  = floor(5% of total to the halala) and net = total − retention; drilling
  VAT = 15% of net (half-even) and total = net + VAT. Include DS-900 discount lines.
 
Then src/audit/decide.py (first version): one row per invoice, flagged if any finding,
category = largest money impact, expected_total = billed ± deltas we can compute
(else billed), confidence per CLAUDE.md §7. Write submission.csv at the project root
(the deliverable) and output/findings.csv. Validate: 2,806 rows, same order as the template, integer cents.
 
Report: count of flags per check and per contract, total flagged vs the 140–225 prior,
and 3 example findings per check with the raw evidence. List anything surprising.
Stop. Do not start Phase 2.
```
 
---
 
## P2 — Contract extraction (3.5 h) — the highest-risk phase
 
```
Goal: extracted/contracts/civil.json and drilling.json containing every term needed to
price a line, each value with "source" (page + clause/table) and "verified": true|false.
 
1. src/audit/ocr.py: run Docling (default pipeline; OCR auto-selects RapidOCR; TableFormer
   accurate) on both PDFs from DATA_DIR, page by page → extracted/ocr/<contract>/page_XX.md,
   tables kept as markdown tables. One-time step (~40 s/page on CPU): skip pages already done,
   and commit the output so later phases and the evaluator never re-run OCR.
   Known from compare_ocr.py: all 60 Schedule 1 codes read; one Schedule 4 band row
   ("A.12.010 4,001 to 16,000 m3 96%") not read in order — check it by eye.
2. Parse every table listed in CLAUDE.md §5 into JSON from the markdown tables (use the
   column headers to pick each value; civil codes [A-E].dd.ddd, drilling codes XX-ddd): Schedule 1 rates,
   zone/ground factors, uplifts, bands, daily caps, exclusions, joint-survey list, indexed
   rates + index table, USD items + exchange rule, daywork, provisional sums, preliminaries,
   VAT/retention/rounding rules, every instrument with its per-item effective dates,
   discounts, term extensions, Clause 31A retro settlement, standby rules, depth bands,
   lost-in-hole values, Appendix G terms.
3. Verify every number with three checks (no second OCR engine):
   a. Completeness — every item_code / service_code in the invoice lines exists in the JSON.
      A missing code = an OCR miss. Fix by reading the page crop.
   b. Calibration — compare each base rate with the most common billed rate on lines with
      no factors (civil Z1, no ground class, no night work, before 2025-05-01; drilling first
      months). Agreement = verified. Disagreement = OCR error OR an unmodelled rule. Known
      examples of rules, not OCR errors: B.23.020 38.40 → billed 144.00 (= ×3.75, a USD item,
      Schedule 2B); D.41.030 89.40 → 89.76 (indexed item, Schedule 2A). Explain every one.
   c. Eye check — numbers the invoices cannot confirm (instrument dates, percentages, caps,
      band limits, term dates, windows) are checked by me against a page crop. Save crops to
      extracted/ocr/crops/ and list them for me.
4. Record in DECISION_LOG: the OCR choice with the compare_ocr.py numbers (CLAUDE.md §6),
   and every clause you had to interpret (e.g. what "monthly rate" means, how
   retro settlement is billed, what application_total includes).
5. Note every place the guidelines and the contract differ.
 
Acceptance: every value has a source; every invoice code present; every calibration
disagreement explained; the facts already verified in CLAUDE.md §5 reproduced exactly.
Report and stop.
```
 
---
 
## P3 — Pricing engine + calibration (3 h)
 
```
Goal: for every line, the contract rate on its work date, built up in the contract's order,
and a calibration report showing that the engine reproduces the clean majority.
 
1. src/audit/contract.py: rate_at(item, date) applying instruments in order issued, with
   per-item effective dates; discount_at(item, date); in_term(date).
2. src/audit/pricing/civil.py: base → zone (not Series E) → ground (listed items) → night /
   rest-day uplift (listed items; rest day = Fri/Sat) → bands per Contract Year → rebate →
   discount → round once. Indexed (2A) and USD (2B) items per their clauses.
   pricing/drilling.py: rates, depth bands, standby, factors, discounts; half-even rounding
   at each step. Unit tests: the two golden lines in CLAUDE.md §5 and one per rule.
3. src/audit/calibrate.py → output/calibration.md: % of lines where expected == billed,
   broken down by item × period. Any item or period with low agreement = a rule we got
   wrong; investigate before trusting it. Iterate until agreement is high and the residual
   mismatches look like isolated errors, not whole groups.
4. Add check c07_rate (superseded / wrong rate) and c08_buildup (factor, uplift, discount,
   rounding) using the engine; only confident when calibration for that item is high.
5. Re-run decide.py and regenerate submission.csv.
 
Retro settlement (Amendment 3): the difference is one adjustment on the first invoice submitted
on or after the issue date, and on no other (civil Cl.31A p.32, drilling Cl.36A p.35).

Report: agreement % overall and per contract, the groups that still disagree and why,
new DECISION_LOG entries, change in flag count. Stop.
```

### P3 plan as approved

1. `contract.rate_at` / `discount_at`: the latest instrument issued on or before the submission date
   whose per-item effective date is on or before the work date (Cl.31A p.32, Cl.36A p.35, D16).
   Monthly rates (civil D.41.020, E.54.010; drilling HC-601, DD-120) carry the last published month
   forward until replaced. DD-120 = 416.00 from 2026-02-01 (D12). Test: one line before and one after
   each instrument, and one on an invoice submitted on the issue date.
2. Civil build-up (Cl.27–28 p.6; 26A, 29A, 27A p.32; P11 p.12): base (USD or indexed, half to even),
   zone, ground, night or rest-day uplift, band %, discount (5% or 8%, D13); round once, half up.
   Tests: the two golden lines in §5 and one per rule.
3. Civil bands (Sch.4 Pt3 pp.24–25, D14, D19): cumulative per item per Contract Year, in the order
   work date, application number, line number; a line crossing a band is split, each part at its own
   rounded rate (Cl.28). Resolves the 32 lines of D08.
4. Drilling build-up (Cl.17–18 p.6; 17A, 17B p.35; Sch.2, Sch.3): base (PD-210 depth band, or indexed),
   section factor (not on Standby), class factor (not on PD-210, D21), standby %, discount (4% or 7%);
   half to even at each step. PD-210
   Contract Year % stays at 100% (the highest well total in a year is 3,355 m).
5. Calibration → `output/calibration.md`: share of lines where the expected rate equals the billed rate,
   per item × rate period. A low group sends the reading back to the clause, not to the rule. After the
   run, also report per contract the invoices where expected_total = billed_total (target 92–95%) and
   the differing lines by item and cause; below 92%, or many differences on one item: stop and report.
6. Checks: `c06` wrong_unit (civil Cl.26, drilling Cl.35; 4 civil lines, 0 drilling); `c07`
   superseded_rate; `c08` rate_buildup and discount_misapplied. Confidence 0.90 where the item's
   calibration is ≥ 90%, else 0.60.
7. Retro settlement (Cl.31A, Cl.36A): lines of Amendment 3 items with work date ≥ effective date on
   invoices submitted before the issue date; difference per line = (new − old built-up rate) × quantity,
   same build-up and rounding; one adjustment per contract. Carrier (D16, D18): drilling MDS-01625
   (17-Aug-2026, adjustment 0.00) flagged with high confidence; civil PA-00006, PA-00023, PA-00380 (all
   2026-05-12) flagged at 0.33 each. "Taken early": a line on an invoice submitted before the issue date
   billed at the new rate. `expected_total` excludes the adjustment (D17), delta 0.
   Cl.45A (p.32): the first application after 2026-09-30 releases half of all earlier retention, rounded
   down. PA-00678 (2026-10-28) shows retention_released 0.00; earlier retention 8,069,143.47, so
   4,034,571.73 is due → retro_adjustment finding, delta 0 (D17).
8. `c09_limits` (P5, required): civil daily limits per item × work area × day (Cl.31, Sch.4 Pt4);
   A.14.020 within 2 days after A.14.010 (Cl.32, Sch.4 Pt5, P19); E.51.020 not measurable for a work
   area on a day when D.41.020, D.41.030, D.41.050, D.43.010 or D.43.020 is measured there (P21 p.13;
   0 of 104 lines at present); drilling daily limits per well × day
   (Cl.22, Sch.3 Pt5); once per well (Cl.27, Sch.3 Pt6); DD-120 minimum 6 h per Operating day (Cl.21,
   P10); Standby "not chargeable" services and DD-121 on Standby only (Cl.20–21, Sch.3 Pt3–4).
   Excess quantity → 0, category limit_exceeded.
9. Moved to P4 (need the records): lost-in-hole values (Cl.31, 31A), metres against the report (Cl.24–25, 25A).
10. `findings.csv`: column `counts` becomes `status` (error / query). ruff D401 enabled; docstrings updated.

Main functions: `contract.rate_at`, `contract.discount_at`, `contract.contract_year`;
`pricing.civil.base_rate`, `band_parts`, `built_up_rate`, `price_lines`; `pricing.drilling.built_up_rate`,
`price_lines`; `calibrate.agreement`; `checks.c07_rate.retro_adjustment`; `run(data)` in c06–c09.
 
---
 
## P4 — Records parsing + linking (3 h)
 
```
Goal: every line linked to its record and its priced item, and quantities checked.
 
1. records/civil.py: regex parser → table (ticket, type, area, date, ground, week/days-on,
   work_text, quantity, unit_normalised, foreman, engineer_rep). Normalise units
   ("square metres"→m2, "cube"/"m3"→m3, "m"→lm, hours, weeks, "no.").
   records/drilling.py: parse parts A–E into structured fields (crew counts by role, tools
   in hole, depths, hours, gyro count, sources, lost tool code, signatures).
2. Build extracted/mappings/civil_phrases.json: unique work_text patterns → item code.
   Use regex/keywords first; for the remainder, write a versioned LLM prompt
   (prompts/v1_0x_phrase_mapping.md), show me the proposed mapping for review, then commit it.
   Drilling: mappings from Appendix G (extracted in P2), with Part E overriding for LH codes.
   Where a phrase fits two items → "ambiguous", never resolved on price (guideline 6).
3. linker.py: line ↔ record by ref, then verify date, area/well, item, signatures.
4. Checks: c04 full (record exists, right type, right date/area, both signatures, required
   DDR part present, weekly ≥5 days), c05_quantity (billed ≤ recorded; payable = recorded),
   c06_identification (billed item consistent with the record's item).
5. Validate on the known examples: CT-00001↔PA-00233-13, and the 9 first records of each
   civil type. Investigate MO/PS "billed one hour less" — find the clause.

Rules moved here from P3 (need the records; decided 2026-09-30):
- Hourly quantities: civil Cl.6A (record hours − 1); drilling Cl.21A per report day (D23).
  DD-120 6-hour minimum with 21A: open (D24), check report days with ≤ 7 circulating hours.
- Tolerances: civil 33A (joint survey, 2%); drilling 25A (metres, 1%); metres against the report
  (Cl.24–25); lost-in-hole value (Cl.31, 31A, Sch.2D, P12).
- Once-only by run or day on the well: DD-111 last day of each BHA run carrying a motor, LW-420 first
  day of each run carrying a source (Cl.26); MB-701, DD-140 first day, LW-430, MB-702 last day on the
  well, LW-430 only where LWD was run (Cl.27).
- Civil: S4 (classification not recorded on the day → G2), P13 (trench depth decides A.12.020/030/040),
  standby limits P2, P9, H15, S20 (E.51.010 only for the hours recorded).
- Drilling: no charge on rig-move days (P4), failed tool only on days in the hole (P6), crew change
  counted once (P7), hours in whole hours (R4), PD-210 only on nominated sections (Cl.23).

Civil record work lines follow a small set of fixed phrase templates (about 26), for example
'N square metres of sub-base in and compacted' for D.41.010. Each template belongs to one item
only. The one exception found is PA-00170-04, which cites PT-00189, a record that belongs to
PA-00238-09. So the P4 mapping from record text to item can be a fixed table that you build
once by reading the templates, stored with its evidence, with no LLM call at runtime. Check
this on all 2,169 records before relying on it.
 
Report: link rate, ambiguous count, new findings per check, examples. Stop.
```
 
---
 
## P5 — Limits and adjustments (folded into P3 and P4 — kept here for reference)
 
```
Implement c09_limits: daily caps per item per work area (Clause 31), exclusion windows
(Clause 32), once-only items, minimum charges, bands per Contract Year, drilling limits
from Schedule 3. Implement retro settlement (civil Clause 31A, drilling Clause 36A): for Amendment 3 in both
contracts, compute the difference owed for work between the effective date and the issue
date, and check it appears on the first application/invoice submitted on or after the issue
date (civil Cl.31A p.32, drilling Cl.36A p.35) — missing = retro_adjustment omitted; appearing
earlier = taken early.
Re-run everything, regenerate submission.csv. Report and stop.
```
 
---
 
## P6 — Decision, confidence, evaluation (1.5 h)
 
```
Follow CLAUDE.md §8 exactly.
 
1. eval/inject.py (fixed seeds A and B): build two evaluation sets from invoices with zero
   findings. Each: ~7% positives with exactly one planted error, ~15 per category listed in
   §8.2, and the rest untouched negatives. Recompute line amount, subtotal, retention/VAT and
   total after every planted change so only the intended check can catch it. Write
   eval/labels_A.csv and eval/labels_B.csv (invoice_id, category, true_expected_total_cents).
2. eval/evaluate.py: run the full pipeline on a set and report per category and overall:
   TP, FP, FN, TN, precision, recall, F1, cost (5×FN + FP), category accuracy, amount
   accuracy, and the confidence-band table (stated vs measured precision).
3. Tune on set A only: confidences per category and the flag threshold (start ~0.17).
   Then run set B once and write those numbers to output/eval.md. Do not tune on B.
4. Final decide.py on the real data: combine findings per invoice, pick the category by
   money impact, recompute expected_total with all corrections, apply the threshold, and
   check the flag count against 140–225. Explain any big deviation before changing anything.
5. Produce a list of 30 real flagged invoices (stratified by category) for my manual review.
 
Report the set-B table, the real flag count, and which categories are weakest. Stop.
```
 
---
 
## P7 — Documentation and packaging (1.5 h)
 
```
1. README.md for this project: near the top, a Mermaid flowchart of the pipeline (inputs →
   stages → outputs, and the calibration loop back to extraction). Start from this draft and
   update it to match the final code:
 
       flowchart LR
         PDF[contracts PDF] --> OCR[ocr: Docling] --> CJ[contract JSON]
         CSV[invoices CSV] --> P1[checks without contract]
         TXT[site records TXT] --> REC[parse records] --> MAP[mapping JSON]
         CJ --> PR[pricing + calibration]
         CSV --> PR
         CJ --> LIM[limits + retro adjustments]
         MAP --> LNK[record linking]
         CSV --> LNK
         P1 --> F[findings.csv]
         PR --> F
         LNK --> F
         LIM --> F
         F --> DEC[decide] --> SUB[submission.csv]
         PR -. reprices clean lines? re-check reading .-> OCR
 
   Then: what this is; data source and setup — "clone
   https://github.com/majedzahrani3/invoice-auditing-level-2, copy civilwork/,
   drilling_services/ and submission_template.csv into ./data (or set DATA_DIR and
   TEMPLATE_PATH)"; how to run (uv sync --locked; uv run python -m audit all); where outputs go; runtime;
   the one-command reproduction;
   and AI disclosure (Claude Code for implementation, Claude chat for planning/data
   exploration; prompts in prompts/).
2. docs/REPORT.md (≤2 pages): approach (including why contract-independent checks came
   first: a valid submission early, and data lessons before the high-risk extraction), calibration results, eval results, flag stats,
   and error analysis grouped by 3–4 FAILURE TYPES (e.g. OCR/extraction, item linking,
   ambiguous clause reading, unmodelled rule), each with one concrete example, plus what we
   could not determine.
3. docs/DECISION_LOG.md: tighten to one page.
4. Clean-copy test: copy this project folder to a new location (excluding .venv, output/ and
   submission.csv),
   point DATA_DIR at the exercise repo → uv sync → uv run python -m audit all → identical submission.csv
   (compare its hash with the committed root submission.csv). No git, no cloning.
5. Final validation of submission.csv against the template.
If the 16 h cap was reached earlier, add "What I would do next" to REPORT.md.
