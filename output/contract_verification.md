# Contract verification (Phase 2)

## civil

- values extracted: 245; verified by the invoices: 133
- codes billed but missing from Schedule 1: none
- OCR corrections applied: 3
- reference check: contract_ref on 898 of 900 headers, issuer on 900 of 900 headers
- header check: retention reproduced on 900 of 900 applications
- record series: 17 of 17 confirmed by line refs
- open, Phase 3 calibration: 65 numbers
- open, not used by any invoice line: 48 numbers
- open, quote-checked prose: 11 numbers

### OCR corrections

| page | OCR text | corrected | reason |
|---|---|---|---|
| 24 | `%96` | `96%` | Schedule 4 Part 3, A.12.010 band 4,001 to 16,000: digits and % sign reversed by OCR; the scan reads 96% |
| 25 | `%06` | `90%` | Schedule 4 Part 3, A.13.010 band above 20,000: reversed by OCR; the scan reads 90% |
| 25 | `%16` | `91%` | Schedule 4 Part 3, A.14.010 band above 8,000: reversed by OCR; the scan reads 91% |

### Calibration below 90 % agreement

| value | reproduced | lines |
|---|---|---|
| ground.factors.G2 | 977 | 1100 |
| ground.factors.G3 | 152 | 169 |
| ground.factors.G4 | 161 | 185 |
| ground.factors.G5 | 146 | 169 |
| items.A.12.010.rate | 38 | 144 |
| items.A.12.020.rate | 16 | 100 |
| items.A.13.010.rate | 47 | 126 |
| items.A.14.010.rate | 12 | 53 |
| items.B.22.010.rate | 8 | 145 |
| items.B.23.010.rate | 8 | 21 |
| items.D.41.010.rate | 21 | 139 |
| items.D.41.040.rate | 20 | 126 |
| night_uplift.A.12.020 | 0 | 5 |
| night_uplift.A.14.010 | 0 | 2 |
| usd.halalas_per_usd.2026-10 | 0 | 1 |
| zone_factors.Z2 | 1309 | 1473 |
| zone_factors.Z3 | 1524 | 1701 |
| zone_factors.Z4 | 1341 | 1549 |

### Eye check and second OCR engine

| value | evidence |
|---|---|
| `daily_limits.A.11.010` | eye check, crop 03 |
| `daily_limits.A.12.010` | eye check, crop 03 |
| `daily_limits.B.21.020` | eye check, crop 03 |
| `daily_limits.C.32.010` | eye check, crop 03 |
| `daily_limits.D.41.030` | eye check, crop 03 |
| `daily_limits.E.51.020` | eye check, crop 03 |
| `daily_limits.A.13.030` | eye check, crop 03 |
| `daily_limits.C.32.030` | eye check, crop 03 |
| `daily_limits.E.53.010` | eye check, crop 03 |
| `exclusions.A.14.020` | eye check, crop 03 |
| `surveyed_items` | eye check, crop 03 |
| `instruments[0].issued` | eye check, crop 07 |
| `instruments[1].issued` | eye check, crop 08 |
| `instruments[1].term_end` | eye check, crop 08 |
| `instruments[2].issued` | eye check, crop 09 |
| `instruments[3].issued` | eye check, crop 10 |
| `instruments[3].term_end` | eye check, crop 10 |
| `instruments[4].issued` | second OCR engine, crop 11 |
| `terms.commencement` | second OCR engine, crop 06 |
| `terms.completion_as_let` | second OCR engine, crop 06 |
| `terms.completion` | second OCR engine, crop 06 |
| `terms.window_days` | second OCR engine, crop 02 |
| `terms.night_hours` | eye check, crop 01 |
| `terms.night_uplift_max_zone_factor` | second OCR engine, crop 04 |
| `terms.ground_datum_after` | second OCR engine, crop 04 |
| `terms.chargeable_hour_deduction` | second OCR engine, crop 04 |
| `terms.survey_tolerance_pct` | second OCR engine, crop 04 |
| `terms.retention_release_share` | second OCR engine, crop 04 |
| `terms.week_min_days` | eye check, crop 05 |

### Open values

| group | value | extracted | source |
|---|---|---|---|
| Phase 3 calibration | `bands.A.12.010[0]` | 100 | pp.24-25 Schedule 4 Part 3 |
| Phase 3 calibration | `bands.A.12.010[1]` | 96 | pp.24-25 Schedule 4 Part 3 |
| Phase 3 calibration | `bands.A.12.010[2]` | 93 | pp.24-25 Schedule 4 Part 3 |
| Phase 3 calibration | `bands.A.12.020[0]` | 100 | pp.24-25 Schedule 4 Part 3 |
| Phase 3 calibration | `bands.A.12.020[1]` | 97 | pp.24-25 Schedule 4 Part 3 |
| Phase 3 calibration | `bands.A.12.020[2]` | 94 | pp.24-25 Schedule 4 Part 3 |
| Phase 3 calibration | `bands.A.13.010[0]` | 100 | pp.24-25 Schedule 4 Part 3 |
| Phase 3 calibration | `bands.A.13.010[1]` | 94 | pp.24-25 Schedule 4 Part 3 |
| Phase 3 calibration | `bands.A.13.010[2]` | 90 | pp.24-25 Schedule 4 Part 3 |
| Phase 3 calibration | `bands.A.14.010[0]` | 100 | pp.24-25 Schedule 4 Part 3 |
| Phase 3 calibration | `bands.A.14.010[1]` | 95 | pp.24-25 Schedule 4 Part 3 |
| Phase 3 calibration | `bands.A.14.010[2]` | 91 | pp.24-25 Schedule 4 Part 3 |
| Phase 3 calibration | `bands.B.22.010[0]` | 100 | pp.24-25 Schedule 4 Part 3 |
| Phase 3 calibration | `bands.B.22.010[1]` | 96 | pp.24-25 Schedule 4 Part 3 |
| Phase 3 calibration | `bands.B.22.010[2]` | 93 | pp.24-25 Schedule 4 Part 3 |
| Phase 3 calibration | `bands.B.23.010[0]` | 100 | pp.24-25 Schedule 4 Part 3 |
| Phase 3 calibration | `bands.B.23.010[1]` | 97 | pp.24-25 Schedule 4 Part 3 |
| Phase 3 calibration | `bands.B.23.010[2]` | 94 | pp.24-25 Schedule 4 Part 3 |
| Phase 3 calibration | `bands.D.41.010[0]` | 100 | pp.24-25 Schedule 4 Part 3 |
| Phase 3 calibration | `bands.D.41.010[1]` | 95 | pp.24-25 Schedule 4 Part 3 |
| Phase 3 calibration | `bands.D.41.010[2]` | 92 | pp.24-25 Schedule 4 Part 3 |
| Phase 3 calibration | `bands.D.41.040[0]` | 100 | pp.24-25 Schedule 4 Part 3 |
| Phase 3 calibration | `bands.D.41.040[1]` | 95 | pp.24-25 Schedule 4 Part 3 |
| Phase 3 calibration | `bands.D.41.040[2]` | 92 | pp.24-25 Schedule 4 Part 3 |
| Phase 3 calibration | `ground.items` | ['A.11.020', 'A.12.010', 'A.12.020', 'A.12.030', 'A.12.040', 'A.12.050', 'A.14.020', 'A.15.010', 'A.15.020', 'C.31.010', 'C.31.020', 'C.31.030', 'C.32.010', 'C.32.030', 'C.33.010'] | p.23 Schedule 3 |
| Phase 3 calibration | `instruments[0].effective` | 2025-05-01 | p.39 Supplement No. 1 |
| Phase 3 calibration | `instruments[0].monthly_rates.D.41.020` | (month table) | p.39 Supplement No. 1 |
| Phase 3 calibration | `instruments[0].rates.A.16.010` | 1524.00 | p.39 Supplement No. 1 |
| Phase 3 calibration | `instruments[0].rates.B.21.020` | 431.50 | p.39 Supplement No. 1 |
| Phase 3 calibration | `instruments[0].rates.B.23.010` | 4385.00 | p.39 Supplement No. 1 |
| Phase 3 calibration | `instruments[1].effective` | 2025-09-28 | p.40 Amendment No. 1 |
| Phase 3 calibration | `instruments[1].rates.B.23.010` | 4450.00 | p.40 Amendment No. 1 |
| Phase 3 calibration | `instruments[1].rates.E.54.010` | 948.00 | p.40 Amendment No. 1 |
| Phase 3 calibration | `instruments[2].discount` | 5 | p.41 Supplement No. 2 |
| Phase 3 calibration | `instruments[2].effective` | 2025-12-01 | p.41 Supplement No. 2 |
| Phase 3 calibration | `instruments[2].rates.D.41.020` | 228.00 | p.41 Supplement No. 2 |
| Phase 3 calibration | `instruments[3].discount` | 8 | p.42 Amendment No.2 |
| Phase 3 calibration | `instruments[3].effective` | 2026-04-01 | p.42 Amendment No.2 |
| Phase 3 calibration | `instruments[3].monthly_rates.E.54.010` | (month table) | p.42 Amendment No.2 |
| Phase 3 calibration | `instruments[4].effective` | 2025-11-01 | p.43 Amendment No. 3 |
| Phase 3 calibration | `instruments[4].rates.A.14.010` | 56.80 | p.43 Amendment No. 3 |
| Phase 3 calibration | `instruments[4].rates.C.32.010` | 1984.00 | p.43 Amendment No. 3 |
| Phase 3 calibration | `items.B.23.020.rate` | 38.40 | p.18 Schedule 1 |
| Phase 3 calibration | `items.B.25.010.rate` | 219.00 | p.18 Schedule 1 |
| Phase 3 calibration | `items.C.31.010.rate` | 86.20 | p.18 Schedule 1 |
| Phase 3 calibration | `items.C.32.040.rate` | 423.00 | p.18 Schedule 1 |
| Phase 3 calibration | `items.D.41.030.rate` | 89.40 | p.18 Schedule 1 |
| Phase 3 calibration | `night_uplift.A.12.020` | 18 | p.24 Schedule 4 Part 1 |
| Phase 3 calibration | `night_uplift.A.14.010` | 18 | p.24 Schedule 4 Part 1 |
| Phase 3 calibration | `night_uplift.B.21.020` | 22 | p.24 Schedule 4 Part 1 |
| Phase 3 calibration | `night_uplift.C.31.010` | 18 | p.24 Schedule 4 Part 1 |
| Phase 3 calibration | `night_uplift.D.41.020` | 25 | p.24 Schedule 4 Part 1 |
| Phase 3 calibration | `usd.halalas_per_usd` | (month table) | p.22 Schedule 2B |
| not used by any invoice line | `daywork.additions.Labour, to cover supervision and overheads` | 68 | pp.28-29 Schedule 6 |
| not used by any invoice line | `daywork.additions.Materials, to cover handling and overheads` | 14 | pp.28-29 Schedule 6 |
| not used by any invoice line | `daywork.additions.Plant, to cover fuel, maintenance and overheads` | 22 | pp.28-29 Schedule 6 |
| not used by any invoice line | `daywork.additions.Subcontracted daywork` | 10 | pp.28-29 Schedule 6 |
| not used by any invoice line | `daywork.rates.Articulated dump truck, 25 tonne, with operator` | 212.00 | pp.28-29 Schedule 6 |
| not used by any invoice line | `daywork.rates.Banksman` | 46.90 | pp.28-29 Schedule 6 |
| not used by any invoice line | `daywork.rates.Carpenter, formwork` | 73.10 | pp.28-29 Schedule 6 |
| not used by any invoice line | `daywork.rates.Concrete pump, boom, with operator` | 398.00 | pp.28-29 Schedule 6 |
| not used by any invoice line | `daywork.rates.Dewatering pump, 100 mm, with hoses` | 1240.00 | pp.28-29 Schedule 6 |
| not used by any invoice line | `daywork.rates.Foreman` | 96.50 | pp.28-29 Schedule 6 |
| not used by any invoice line | `daywork.rates.Ganger` | 78.50 | pp.28-29 Schedule 6 |
| not used by any invoice line | `daywork.rates.General operative` | 43.60 | pp.28-29 Schedule 6 |
| not used by any invoice line | `daywork.rates.Mobile crane, 50 tonne, with operator` | 472.00 | pp.28-29 Schedule 6 |
| not used by any invoice line | `daywork.rates.Pipelayer` | 66.30 | pp.28-29 Schedule 6 |
| not used by any invoice line | `daywork.rates.Plate compactor` | 34.00 | pp.28-29 Schedule 6 |
| not used by any invoice line | `daywork.rates.Semi-skilled operative` | 51.80 | pp.28-29 Schedule 6 |
| not used by any invoice line | `daywork.rates.Site dumper, 6 tonne, with operator` | 98.00 | pp.28-29 Schedule 6 |
| not used by any invoice line | `daywork.rates.Site engineer` | 118.00 | pp.28-29 Schedule 6 |
| not used by any invoice line | `daywork.rates.Skilled operative` | 64.20 | pp.28-29 Schedule 6 |
| not used by any invoice line | `daywork.rates.Steel fixer` | 71.40 | pp.28-29 Schedule 6 |
| not used by any invoice line | `daywork.rates.Tipper lorry, 8 wheel, with driver` | 156.00 | pp.28-29 Schedule 6 |
| not used by any invoice line | `daywork.rates.Tracked excavator, 13 tonne, with operator` | 188.00 | pp.28-29 Schedule 6 |
| not used by any invoice line | `daywork.rates.Tracked excavator, 21 tonne, with operator` | 246.00 | pp.28-29 Schedule 6 |
| not used by any invoice line | `daywork.rates.Vibrating roller, 12 tonne, with operator` | 138.00 | pp.28-29 Schedule 6 |
| not used by any invoice line | `daywork.rates.Wellpoint system, 30 m run` | 3860.00 | pp.28-29 Schedule 6 |
| not used by any invoice line | `daywork.rates.Wheeled loader, 12 tonne, with operator` | 174.00 | pp.28-29 Schedule 6 |
| not used by any invoice line | `preliminaries.PR.01` | 486000.00 | p.31 Schedule 8 |
| not used by any invoice line | `preliminaries.PR.02` | 14200.00 | p.31 Schedule 8 |
| not used by any invoice line | `preliminaries.PR.03` | 218.00 | p.31 Schedule 8 |
| not used by any invoice line | `preliminaries.PR.04` | 38500.00 | p.31 Schedule 8 |
| not used by any invoice line | `preliminaries.PR.05` | 164000.00 | p.31 Schedule 8 |
| not used by any invoice line | `preliminaries.PR.06` | 92000.00 | p.31 Schedule 8 |
| not used by any invoice line | `preliminaries.PR.07` | 78000.00 | p.31 Schedule 8 |
| not used by any invoice line | `preliminaries.PR.08` | 9800.00 | p.31 Schedule 8 |
| not used by any invoice line | `preliminaries.PR.09` | 2400.00 | p.31 Schedule 8 |
| not used by any invoice line | `preliminaries.PR.10` | 6700.00 | p.31 Schedule 8 |
| not used by any invoice line | `preliminaries.PR.11` | 1900.00 | p.31 Schedule 8 |
| not used by any invoice line | `preliminaries.PR.12` | 142000.00 | p.31 Schedule 8 |
| not used by any invoice line | `preliminaries.PR.13` | 88000.00 | p.31 Schedule 8 |
| not used by any invoice line | `preliminaries.PR.14` | 214000.00 | p.31 Schedule 8 |
| not used by any invoice line | `provisional_sums.PC.01` | 142000.00 | p.30 Schedule 7 |
| not used by any invoice line | `provisional_sums.PC.02` | 88500.00 | p.30 Schedule 7 |
| not used by any invoice line | `provisional_sums.PC.03` | 515000.00 | p.30 Schedule 7 |
| not used by any invoice line | `provisional_sums.PS.01` | 420000.00 | p.30 Schedule 7 |
| not used by any invoice line | `provisional_sums.PS.02` | 185000.00 | p.30 Schedule 7 |
| not used by any invoice line | `provisional_sums.PS.03` | 96000.00 | p.30 Schedule 7 |
| not used by any invoice line | `provisional_sums.PS.04` | 310000.00 | p.30 Schedule 7 |
| not used by any invoice line | `provisional_sums.PS.05` | 268000.00 | p.30 Schedule 7 |
| quote-checked prose | `terms.bands_counted_from` | start_of_contract_year | p.24 Schedule 4 Part 3 (substitutes Cl.30) |
| quote-checked prose | `terms.concurrent_uplifts` | rest_day_only | p.13 P11 |
| quote-checked prose | `terms.contract_year` | from_commencement_anniversary | p.32 Cl.3A |
| quote-checked prose | `terms.conversion_rounding` | half_even | p.32 Cl.26A, Cl.29A |
| quote-checked prose | `terms.ground_datum_class` | G2 | p.32 Cl.27A |
| quote-checked prose | `terms.rate_rounding` | half_up_once | p.6 Cl.28 |
| quote-checked prose | `terms.rest_days` | ['Friday', 'Saturday'] | p.3 Cl.8 |
| quote-checked prose | `terms.retro_settlement` | first_application_on_or_after_issue | p.32 Cl.31A |
| quote-checked prose | `terms.surfacing_items` | ['D.41.020', 'D.41.030', 'D.41.050', 'D.43.010', 'D.43.020'] | p.13 P21 |
| quote-checked prose | `terms.traffic_management_item` | E.51.020 | p.13 P21 |
| quote-checked prose | `terms.zone_factor_series` | ['A', 'B', 'C', 'D'] | p.20 Schedule 2 |

## drilling

- values extracted: 204; verified by the invoices: 108
- codes billed but missing from Schedule 1: none
- OCR corrections applied: 5
- reference check: contract_ref on 1903 of 1906 headers, issuer on 1906 of 1906 headers
- header check: VAT reproduced on 1906 of 1906 invoices; header check: DS-900 reproduced on 1903 of 1906 invoices
- open, Phase 3 calibration: 57 numbers
- open, Phase 4 linking: 68 numbers
- open, quote-checked prose: 7 numbers

### OCR corrections

| page | OCR text | corrected | reason |
|---|---|---|---|
| 16 | `(rows appended)` | `see file` | Schedule 1, Series 400 (end) to 600: OCR lost the table structure and listed codes, units and rates apart; rows re-paired in page order and each row read on the scan |
| 21 | `%00%` | `100%` | Schedule 3 Part 3, LW-420 standby charge: the scan reads 100% |
| 36 | `mnuod tr` | `mud motor` | Appendix G, LH-711 report term: the scan reads 'mud motor' |
| 39 | `MW-30IMWD` | `MW-301 MWD` | Amendment No. 1, 1.2 Substituted rates: OCR read the digit 1 as the letter I; the scan reads MW-301 |
| 41 | `19,237:00` | `19,237.00` | Amendment No. 2, 2.2 Substituted rates, MB-701: OCR read the decimal point as a colon; the scan reads 19,237.00 |

### Calibration below 90 % agreement

| value | reproduced | lines |
|---|---|---|

### Eye check and second OCR engine

| value | evidence |
|---|---|
| `standby.HC-640` | second OCR engine, Schedule 3 Part 3 p.20-21 |
| `daily_limits.DD-101` | eye check, crop 14 |
| `daily_limits.DD-102` | eye check, crop 14 |
| `daily_limits.DD-110` | eye check, crop 14 |
| `daily_limits.DD-120` | eye check, crop 14 |
| `daily_limits.DD-121` | eye check, crop 14 |
| `daily_limits.DD-130` | eye check, crop 14 |
| `daily_limits.PD-201` | eye check, crop 14 |
| `daily_limits.PD-220` | eye check, crop 14 |
| `daily_limits.PD-230` | eye check, crop 14 |
| `daily_limits.MW-301` | eye check, crop 14 |
| `daily_limits.MW-310` | eye check, crop 14 |
| `daily_limits.MW-320` | eye check, crop 14 |
| `daily_limits.MW-330` | eye check, crop 14 |
| `daily_limits.LW-401` | eye check, crop 14 |
| `daily_limits.LW-413` | eye check, crop 14 |
| `daily_limits.RM-511` | eye check, crop 14 |
| `daily_limits.RM-520` | eye check, crop 14 |
| `daily_limits.RM-530` | eye check, crop 14 |
| `daily_limits.HC-601` | eye check, crop 14 |
| `daily_limits.HC-610` | eye check, crop 14 |
| `daily_limits.HC-620` | eye check, crop 14 |
| `daily_limits.HC-640` | eye check, crop 14 |
| `once_per_well` | eye check, crop 15 |
| `instruments[0].issued` | eye check, crop 18 |
| `instruments[1].issued` | eye check, crop 19 |
| `instruments[1].term_end` | eye check, crop 19 |
| `instruments[2].issued` | eye check, crop 18 |
| `instruments[3].issued` | eye check, crop 20 |
| `instruments[3].term_end` | eye check, crop 20 |
| `instruments[4].issued` | second OCR engine, crop 21 |
| `terms.expiry` | second OCR engine, crop 17 |
| `terms.commencement` | second OCR engine, crop 17 |
| `terms.expiry_as_let` | second OCR engine, crop 17 |
| `terms.window_days` | second OCR engine, crop 13 |
| `terms.chargeable_hour_deduction` | eye check, crop 16 |
| `terms.metres_tolerance_pct` | eye check, crop 16 |
| `terms.lost_in_hole_depreciation_pct` | eye check, crop 12 |
| `terms.lost_in_hole_depreciation_hours` | eye check, crop 12 |
| `terms.lost_in_hole_depreciation_max_pct` | eye check, crop 12 |

### Open values

| group | value | extracted | source |
|---|---|---|---|
| Phase 3 calibration | `class_factors.items` | ['DD-120', 'PD-210', 'MW-310', 'MW-320', 'LW-410', 'LW-411', 'LW-412', 'LW-413'] | p.20 Schedule 3 Part 2 |
| Phase 3 calibration | `contract_year_bands[0]` | 100 | p.17 Schedule 2 Part 2 |
| Phase 3 calibration | `contract_year_bands[1]` | 96 | p.17 Schedule 2 Part 2 |
| Phase 3 calibration | `contract_year_bands[2]` | 92 | p.17 Schedule 2 Part 2 |
| Phase 3 calibration | `depth_bands[0]` | 42.35 | p.17 Schedule 2 |
| Phase 3 calibration | `instruments[0].effective` | 2025-07-01 | p.38 Supplement No. 1 |
| Phase 3 calibration | `instruments[0].monthly_rates.HC-601` | (month table) | p.38 Supplement No. 1 |
| Phase 3 calibration | `instruments[0].rates.DD-120` | 398.50 | p.38 Supplement No. 1 |
| Phase 3 calibration | `instruments[0].rates.DD-121` | 2984.00 | p.38 Supplement No. 1 |
| Phase 3 calibration | `instruments[1].effective` | 2026-01-01 | p.39 Amendment No. 1 |
| Phase 3 calibration | `instruments[1].rates.DD-101` | 1916.50 | p.39 Amendment No. 1 |
| Phase 3 calibration | `instruments[1].rates.LW-401` | 1969.00 | p.39 Amendment No. 1 |
| Phase 3 calibration | `instruments[1].rates.MW-301` | 1708.00 | p.39 Amendment No. 1 |
| Phase 3 calibration | `instruments[2].discount` | 4 | p.40 Supplement No. 2 |
| Phase 3 calibration | `instruments[2].effective` | 2026-04-01 | p.40 Supplement No. 2 |
| Phase 3 calibration | `instruments[2].monthly_rates.DD-120` | (month table) | p.40 Supplement No. 2 |
| Phase 3 calibration | `instruments[3].discount` | 7 | p.41 Amendment No. 2 |
| Phase 3 calibration | `instruments[3].effective` | 2026-07-01 | p.41 Amendment No. 2 |
| Phase 3 calibration | `instruments[3].rates.MB-701` | 19237.00 | p.41 Amendment No. 2 |
| Phase 3 calibration | `instruments[3].rates.MW-301` | 1763.00 | p.41 Amendment No. 2 |
| Phase 3 calibration | `instruments[4].effective` | 2026-02-01 | p.42 Amendment No. 3 |
| Phase 3 calibration | `instruments[4].rates.DD-101` | 1954.00 | p.42 Amendment No. 3 |
| Phase 3 calibration | `instruments[4].rates.DD-120` | 416.00 | p.42 Amendment No. 3 |
| Phase 3 calibration | `items.DD-121.rate` | 2893.65 | p.15 Schedule 1 |
| Phase 3 calibration | `items.HC-620.rate` | 539.65 | p.16 Schedule 1 |
| Phase 3 calibration | `items.LH-711.rate` | Clause 31 | p.16 Schedule 1 |
| Phase 3 calibration | `items.LH-712.rate` | Clause 31 | p.16 Schedule 1 |
| Phase 3 calibration | `items.LH-713.rate` | Clause 31 | p.16 Schedule 1 |
| Phase 3 calibration | `items.LH-714.rate` | Clause 31 | p.16 Schedule 1 |
| Phase 3 calibration | `items.MW-310.rate` | 2245.85 | p.15 Schedule 1 |
| Phase 3 calibration | `items.PD-210.rate` | Schedule 2 | p.15 Schedule 1 |
| Phase 3 calibration | `minimum_hours.DD-120` | 6 | p.22 Schedule 3 Part 7 |
| Phase 3 calibration | `section_factors.items` | ['DD-110', 'DD-120', 'PD-220', 'MW-310', 'RM-510', 'RM-511'] | p.20 Schedule 3 Part 1 |
| Phase 3 calibration | `standby.DD-120` | not chargeable | pp.20-21 Schedule 3 Part 3 |
| Phase 3 calibration | `standby.DD-130` | not chargeable | pp.20-21 Schedule 3 Part 3 |
| Phase 3 calibration | `standby.HC-610` | not chargeable | pp.20-21 Schedule 3 Part 3 |
| Phase 3 calibration | `standby.HC-630` | not chargeable | pp.20-21 Schedule 3 Part 3 |
| Phase 3 calibration | `standby.LW-410` | not chargeable | pp.20-21 Schedule 3 Part 3 |
| Phase 3 calibration | `standby.LW-411` | not chargeable | pp.20-21 Schedule 3 Part 3 |
| Phase 3 calibration | `standby.LW-412` | not chargeable | pp.20-21 Schedule 3 Part 3 |
| Phase 3 calibration | `standby.LW-413` | not chargeable | pp.20-21 Schedule 3 Part 3 |
| Phase 3 calibration | `standby.PD-210` | not chargeable | pp.20-21 Schedule 3 Part 3 |
| Phase 3 calibration | `standby.RM-510` | not chargeable | pp.20-21 Schedule 3 Part 3 |
| Phase 3 calibration | `standby.RM-530` | not chargeable | pp.20-21 Schedule 3 Part 3 |
| Phase 4 linking | `ddr_parts.DD-111` | B | p.24 Schedule 5 |
| Phase 4 linking | `ddr_parts.DD-130` | C | p.24 Schedule 5 |
| Phase 4 linking | `ddr_parts.LH-711` | E | p.24 Schedule 5 |
| Phase 4 linking | `ddr_parts.LH-712` | E | p.24 Schedule 5 |
| Phase 4 linking | `ddr_parts.LH-713` | E | p.24 Schedule 5 |
| Phase 4 linking | `ddr_parts.LH-714` | E | p.24 Schedule 5 |
| Phase 4 linking | `ddr_parts.LW-410` | B | p.24 Schedule 5 |
| Phase 4 linking | `ddr_parts.LW-411` | B | p.24 Schedule 5 |
| Phase 4 linking | `ddr_parts.LW-412` | B | p.24 Schedule 5 |
| Phase 4 linking | `ddr_parts.LW-413` | B | p.24 Schedule 5 |
| Phase 4 linking | `ddr_parts.LW-420` | D | p.24 Schedule 5 |
| Phase 4 linking | `ddr_parts.RM-510` | B | p.24 Schedule 5 |
| Phase 4 linking | `lost_in_hole.halalas_per_usd` | (month table) | p.19 Schedule 2D |
| Phase 4 linking | `lost_in_hole.sar_values.LH-711` | 543750.00 | p.19 Schedule 2D |
| Phase 4 linking | `lost_in_hole.sar_values.LH-712` | 4687500.00 | p.19 Schedule 2D |
| Phase 4 linking | `lost_in_hole.sar_values.LH-713` | 1443750.00 | p.19 Schedule 2D |
| Phase 4 linking | `lost_in_hole.sar_values.LH-714` | 1950000.00 | p.19 Schedule 2D |
| Phase 4 linking | `lost_in_hole.usd_values.LH-711` | 145000.00 | p.25 Schedule 6 |
| Phase 4 linking | `lost_in_hole.usd_values.LH-712` | 1250000.00 | p.25 Schedule 6 |
| Phase 4 linking | `lost_in_hole.usd_values.LH-713` | 385000.00 | p.25 Schedule 6 |
| Phase 4 linking | `lost_in_hole.usd_values.LH-714` | 520000.00 | p.25 Schedule 6 |
| Phase 4 linking | `report_terms.DD-101` | directional hands | p.36 Appendix G |
| Phase 4 linking | `report_terms.DD-102` | night man | p.36 Appendix G |
| Phase 4 linking | `report_terms.DD-110` | mud motor | p.36 Appendix G |
| Phase 4 linking | `report_terms.DD-120` | rotary steerable | p.36 Appendix G |
| Phase 4 linking | `report_terms.HC-601` | circulating sub | p.36 Appendix G |
| Phase 4 linking | `report_terms.HC-620` | drilling jars | p.36 Appendix G |
| Phase 4 linking | `report_terms.HC-640` | float sub | p.36 Appendix G |
| Phase 4 linking | `report_terms.LH-711` | mud motor | p.36 Appendix G |
| Phase 4 linking | `report_terms.LH-712` | rotary steerable | p.36 Appendix G |
| Phase 4 linking | `report_terms.LH-713` | MWD collar | p.36 Appendix G |
| Phase 4 linking | `report_terms.LH-714` | gamma tool | p.36 Appendix G |
| Phase 4 linking | `report_terms.LW-401` | logging engineers | p.36 Appendix G |
| Phase 4 linking | `report_terms.LW-410` | gamma tool | p.36 Appendix G |
| Phase 4 linking | `report_terms.LW-411` | resistivity tool | p.36 Appendix G |
| Phase 4 linking | `report_terms.LW-412` | density-neutron | p.36 Appendix G |
| Phase 4 linking | `report_terms.MW-301` | MWD engineers | p.36 Appendix G |
| Phase 4 linking | `report_terms.MW-310` | MWD collar | p.36 Appendix G |
| Phase 4 linking | `report_terms.MW-320` | survey package | p.36 Appendix G |
| Phase 4 linking | `report_terms.MW-330` | real-time link | p.36 Appendix G |
| Phase 4 linking | `report_terms.PD-201` | performance engineer | p.36 Appendix G |
| Phase 4 linking | `report_terms.PD-220` | bit and reamer | p.36 Appendix G |
| Phase 4 linking | `report_terms.PD-230` | hydraulics package | p.36 Appendix G |
| Phase 4 linking | `report_terms.RM-511` | hole opener | p.36 Appendix G |
| Phase 4 linking | `report_terms.RM-520` | stabiliser string | p.36 Appendix G |
| quote-checked prose | `terms.class_factor_on_pd210` | not_applied | p.35 Cl.17B |
| quote-checked prose | `terms.contract_year` | from_commencement_anniversary | p.35 Cl.3A |
| quote-checked prose | `terms.depth_band_boundary` | shallower_band | p.6 Cl.23 |
| quote-checked prose | `terms.discount_basis` | each_invoice_alone | p.11 P11 |
| quote-checked prose | `terms.retro_settlement` | first_invoice_on_or_after_issue | p.35 Cl.36A |
| quote-checked prose | `terms.section_factor_on_standby` | not_applied | p.35 Cl.17B |
| quote-checked prose | `terms.standby_only_items` | ['DD-121'] | p.21 Schedule 3 Part 4 |

