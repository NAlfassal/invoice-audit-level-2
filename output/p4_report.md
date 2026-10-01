# Phase 4 report: records, linking and the record-based checks

> Final count after P6/P7 (signature fix, eye check): 214 of 2,806 invoices flagged, civil 92
> (10.2%), drilling 122 (6.4%). The figures below are the P4 state (211); see docs/REPORT.md.

Pipeline state after P4: `uv run python -m audit audit`, 242 findings, 211 of 2,806 invoices
flagged. Two runs give identical files; 120 tests pass; ruff is clean.

## Flag share (the brief: 5-8% of invoices are wrong)

| contract | invoices | flagged | share | expected_total = billed_total |
|---|---|---|---|---|
| civil | 900 | 92 | 10.2% | 830 (92.2%) |
| drilling | 1,906 | 119 | 6.2% | 1,797 (94.3%) |
| total | 2,806 | 211 | 7.5% | 2,627 (93.6%) |

The civil share is above the 5-8% range. The categories behind it: rate_buildup 41,
duplicate_charge 18, invoice_window 6, missing_record 6, wrong_unit 4. The threshold is
unchanged (P(error) >= 1/6); the civil rate_buildup lines are isolated (P3 calibration: 99.3%
of civil lines at the billed rate; no item has more than 5 differences).

## Flagged invoices by category (the finding with the largest money impact)

| error_category | civil | drilling |
|---|---|---|
| arithmetic | 3 | 6 |
| discount_misapplied | 2 | 9 |
| duplicate_charge | 18 | 3 |
| invoice_window | 6 | 9 |
| limit_exceeded | 3 | 11 |
| missing_record | 6 | 5 |
| outside_term | 2 | 3 |
| quantity_over_record | 0 | 24 |
| rate_buildup | 41 | 40 |
| retro_adjustment | 3 | 1 |
| superseded_rate | 2 | 5 |
| wrong_contract_ref | 2 | 3 |
| wrong_unit | 4 | 0 |

## Findings by check (every finding, in guideline order)

| check | category | status | civil | drilling |
|---|---|---|---|---|
| c01 | invoice_window | error | 3 | 0 |
| c01 | wrong_contract_ref | error | 2 | 3 |
| c02 | outside_term | error | 2 | 3 |
| c03 | invoice_window | error | 6 | 9 |
| c04 | missing_record | error | 8 | 5 |
| c05 | quantity_over_record | error | 2 | 24 |
| c06 | wrong_unit | error | 4 | 0 |
| c07 | retro_adjustment | error | 4 | 1 |
| c07 | superseded_rate | error | 2 | 10 |
| c08 | discount_misapplied | error | 3 | 7 |
| c08 | rate_buildup | error | 47 | 40 |
| c09 | limit_exceeded | error | 3 | 18 |
| c10 | duplicate_charge | error | 20 | 3 |
| c11 | arithmetic | error | 4 | 6 |
| c11 | discount_misapplied | error | 0 | 3 |

## Linking

| | lines | linked to a record of the same area / well and day |
|---|---|---|
| civil (Schedule 5 items) | 2,197 | 2,189 (99.6%) |
| drilling (service lines) | 91,181 | 91,173 (99.99%) |

- Civil: all 2,169 records match exactly one of 26 work-line templates; each template
  belongs to one item (extracted/mappings/civil_phrases.json). Ambiguous links: 0.
  No LLM call was needed, so the phrase-mapping prompt (prompts/v1_phrase_mapping.md) was not
  run.
- Drilling: all 8,151 reports parsed; services mapped through Appendix G and Schedule 8
  (extracted/mappings/drilling_terms.json).
- Unlinked lines are missing_record: civil 8 (P1 cases), drilling 8 (a report of another
  well or day; 6 of them are already rejected by c02 or c03).
- No record or report lacks a signature (unsigned_record: 0).

## Record quantities against the billed quantities

- Drilling: the billed quantity equals the report on almost every line (e.g. DD-101 8,151 of
  8,151; DD-120 4,601 of 4,606; PD-210 intervals 2,390 of 2,390). 24 lines are billed above
  the report (c05), 3 lines lack the report part they need (c04), 8 lost-in-hole charges
  are not the Schedule 2D value less depreciation (46 of 54 agree; c08), 3 MB-701 lines are
  not on the first day on the well (c09).
- Civil: 2 lines above the record (PA-00312-04, 4 against a survey of 3; PA-00243-03, 10 h
  against 10 recorded, 9 chargeable). 25 joint-survey lines are 0.13-1.68% above the survey
  and are payable as measured (Cl.33A). 140 lines are billed below the record (not
  errors: guideline 5 and Cl.46 limit payment to the record). No DX or PT ground class differs from its line up to 2025-09-27. No weekly log
  shows fewer than five days.

## Pricing (from P3, unchanged by P4)

Lines at the billed rate: civil 7,693 of 7,746 (99.3%), drilling 91,073 of 91,122 (99.9%).
Invoices whose priced lines all agree: civil 853 of 900, drilling 1,857 of 1,906.
Details: output/calibration.md.

## Crops to check by eye

Values the invoices cannot confirm, with the invoices each affects. Crops not listed are
confirmed by the data (e.g. 12 depreciation: 46 of 54 lost-in-hole charges; 16 Cl.21A:
5,542 hour lines) or affect no invoice (01, 05, 07-10, 18-20).

| crop | values | invoices affected |
|---|---|---|
| 11 civil p.43 | Amendment 3 issued 2026-05-12 | PA-00006, PA-00023, PA-00380 (carriers); the civil settlement of 60,508.18 |
| 21 drilling p.42 | Amendment 3 issued 2026-08-17 | MDS-01625 (carrier); the drilling settlement of 309,965.52 |
| 14 drilling p.21 | daily limits (22 values) | MDS-00767, MDS-00799, MDS-01265, MDS-01341, MDS-01373, MDS-01646, MDS-01751 |
| 03 civil p.26 | daily limits, A.14.020 exclusion (2 days), surveyed items | PA-00243, PA-00801, PA-00845; surveyed list: PA-00312 and the 25 lines within 2% |
| 04 civil p.32 | 45A one half; 33A 2% | PA-00678 (release 4,034,571.73); PA-00312 and the 25 lines within 2% |
| 02 civil p.8 | Cl.41 21 days | PA-00125, PA-00613, PA-00699, PA-00708 |
| 13 drilling p.8 | Cl.33 30 days | MDS-00038, MDS-00199, MDS-00537, MDS-00645, MDS-00828, MDS-01258 |
| 06 civil p.38, 17 drilling p.37 | term dates | PA-00375, PA-00678; MDS-01619, MDS-01798, MDS-01860 |
| 15 drilling p.22 | once-per-well list | MDS-00320, MDS-01438, MDS-01887 (the list itself agrees with the data: DD-140, LW-430 and MB-702 are billed once on each of 214 wells) |

Not in any crop: Schedule 3 Part 3 "not chargeable" on a Standby day (p.20-21), which
rejects HC-640 on MDS-00626, MDS-01183, MDS-01424, MDS-01620.

## Open points (DECISION_LOG)

D24 (6-hour minimum with Cl.21A, 0 lines), D28 (PD-210 nominated sections, not checkable),
D29 (civil standby limits P2, P9, H15, not checkable), and the AN readings D05, D19, D22,
D25, D26, D27.

## Known limits of P4

- A line billed above its record is paid at the recorded quantity and the billed rate
  (c05). If the rate is also wrong, the later rate finding does not re-price the line
  (guideline order).
- Where c05 and c09 both reduce a drilling line (e.g. MW-330 billed 2 days), the earlier
  check's correction is used.
