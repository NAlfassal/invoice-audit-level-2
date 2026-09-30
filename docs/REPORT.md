# Report

## Approach
 
Every figure on an invoice is checked against the contract, and every quantity against its
site record. Guideline checks 1-11 run in order (c01 ... c11); check 12, writing the outcome
down, is `output/findings.csv`. A line rejected by an earlier check is not re-priced by a
later one, and the expected total is rebuilt from the corrected lines the contract's way
(civil: round once, half up, retention rounded down; drilling: half to even at each step,
DS-900 and VAT).
 
The checks that do not need the rate schedules were built first (reference, term, window,
record presence, duplicates, arithmetic); they use a few dates and periods read from the
contract. They gave a valid submission early and showed which patterns look wrong but are
not: a civil line split across two quantity bands, and PD-210 billed twice on one day for two
depth intervals. The rate schedules were then extracted with their page and clause and
verified three ways: against the invoices, by a manual check against the scanned page, and by
a second OCR engine. Rules come from clauses; a pattern in the billed data only sent the
reading back to the contract.
 
## Results
 
| | civil | drilling | total |
| --- | --- | --- | --- |
| invoices | 900 | 1,906 | 2,806 |
| flagged | 92 (10.2%) | 122 (6.4%) | 214 (7.6%) |
| lines at the billed rate (pricing engine) | 7,693 / 7,746 (99.3%) | 91,073 / 91,122 (99.9%) | |
| lines linked to their record / report | 2,189 / 2,197 | 91,173 / 91,181 | |
 
Civil is above the 5-8% range in the brief; the flag threshold (P(error) >= 1/6) was not
moved to reach it.
 
**Flagged by category**
 
| category | civil | drilling |
| --- | --- | --- |
| rate_buildup | 41 | 40 |
| quantity_over_record | 0 | 24 |
| duplicate_charge | 18 | 3 |
| limit_exceeded | 3 | 11 |
| invoice_window | 5 | 9 |
| discount_misapplied | 2 | 9 |
| arithmetic | 3 | 6 |
| missing_record | 6 | 5 |
| superseded_rate | 2 | 5 |
| wrong_contract_ref | 2 | 3 |
| outside_term | 2 | 3 |
| unsigned_record | 1 | 3 |
| retro_adjustment | 3 | 1 |
| wrong_unit | 4 | 0 |
 
**Evaluation on planted errors (set B, `output/eval.md`)**
 
| planted errors | clean invoices | detected | false flags | right category | right expected total |
| --- | --- | --- | --- | --- | --- |
| 120 | 1,176 | 120 | 0 | 120 | 120 |
 
The planted errors follow the same rules the checks implement, so this shows each check works
as built; it does not measure accuracy on the real invoices.
 
**Confidence.** Flagged invoices carry 0.85-0.95 when the rule and its values are verified,
0.60 for a reading no source settles (A.14.020 on the same day, D27), and 0.33 for each of
three applications tied as the first after Amendment 3 (D25). Unflagged invoices carry 0.90.
 
## Error analysis by failure type
 
1. **OCR misreads of numbers.** Docling reversed percentage signs in Schedule 4 Part 3
   (civil p.24: "%96" for 96%) and read a decimal point as a colon (drilling p.41 MB-701
   "19,237:00"). Any such value would reprice a whole item. Found by the calibration (a
   misread digit reproduces no billed rate) and the manual check against the scan; eight
   corrections are listed in `extracted/contracts/ocr_corrections.json`.
2. **Two parts of the contract that read differently.** Schedule 2 and Schedule 3 Part 2 call
   PD-210 class-rated; Cl.17B (p.35) says the class factor is not applied to it. The
   Schedule reading would have made 939 PD-210 lines on 248 invoices wrong. The clause that
   names the item, the invoice form in Appendix B and the invoices agree with Cl.17B (D21).
   Likewise the Amendment 3 pages say "after" where Cl.31A / Cl.36A say "on or after"; the
   clause governs, which moves the drilling settlement to MDS-01625 (D16).
3. **Interaction between rules.** Checks that each hold alone can give a wrong category
   together. An exact duplicate drilling line first showed as a daily-limit breach because
   the limit check (c09) runs before the duplicate check (c10); exact copies are now removed
   before limits are counted. Band quantities first counted rejected lines while the limits
   did not; both now count payable lines only (D19).
4. **Reading the site records.** A record can be valid in form and still not evidence the
   line: PA-00170-04 cites PT-00189, the pressure test of another line. A signature line of
   underscores was first read as a name; four records (DX-00089 and three daily reports) are
   now unsigned_record. Records are matched to their line by series, area or well, and day,
   not by reference alone.
## What we could not determine
 
- **PD-210 nominated sections** (Cl.23): the definition on p.29 limits a performance-drilled
  section to 12-1/4" or 8-1/2", and all 2,390 PD-210 lines are on those sections (0
  findings). Which wells the call-off nominated is not in the data (D28).
- **Civil standby limits** P2, P9, H15: the records do not give times of day, flood watches
  or safety suspensions; not checked (D29).
- **Which of three applications dated 2026-05-12 was first** after Amendment 3 (D25), and
  whether the Cl.21 six-hour minimum applies before or after the Cl.21A deduction (D24, no
  line affected).
- **Recall on error types that were not planted** is not measured.