# Manual review list (15 flagged invoices, across the categories)

For each invoice: check the finding against the contract clause and the record, and
mark it right or wrong. The share right per category is the real-data precision
(the reviewer's estimate).

| invoice | category | billed | expected | confidence | finding (clause; evidence) | right? |
|---|---|---|---|---|---|---|
| MDS-00551 | arithmetic | 232,901.95 | 230,515.04 | 0.95 | p.8 Cl.40; net 200447.86 + VAT 30067.18 = 230515.04, total 232901.95 | |
| MDS-00072 | discount_misapplied | 1,503,685.26 | 1,455,037.84 | 0.95 | p.8 Cl.38; services 1307552.40: DS-900 should be -42302.10, billed 0.00 | |
| MDS-00476 | duplicate_charge | 151,646.30 | 147,859.24 | 0.95 | p.7 Cl.29; same well, date, service and depth interval; first billed on MDS-00476-045 | |
| PA-00700 | invoice_window | 49,814.70 | 16,211.98 | 0.9 | p.8 Cl.40; stated period 2025-02-18..2025-02-24, work executed 2025-02-18..2025-03-14 | |
| PA-00845 | limit_exceeded | 392,233.85 | 368,284.25 | 0.85 | p.6 Cl.31; pp.25-26 Schedule 4 Part 4; D.41.030 on S-01 Platform North 2025-09-14: limit 3200 m2 a day, 3200 of 3440 within it | |
| PA-00766 | missing_record | 313,278.66 | 197,454.66 | 0.85 | p.27 Schedule 5; p.8 Cl.46; A.16.010 requires a DW record; record_ref is blank | |
| PA-00678 | outside_term | 526,097.77 | 510,294.90 | 0.9 | p.38 Schedule of Variations; work date 2026-10-22 outside term 2025-01-05..2026-09-30 | |
| MDS-01341 | quantity_over_record | 50,966.79 | 44,378.10 | 0.85 | p.36 Appendix G ('MWD collar'); pp.27-28 Schedule 8; p.7 Cl.28; MW-310 billed 3 day; DDR-118-20260426 supports 1 | |
| MDS-00639 | rate_buildup | 674,867.84 | 645,115.04 | 0.9 | p.7 Cl.31; p.35 Cl.31A; p.19 Schedule 2D; LH-713 billed 385000.00; Schedule 2D value for 2025-08 less depreciation for 189 h is 358050.00 | |
| MDS-01458 | rate_buildup | 631,488.94 | 558,200.35 | 0.9 | p.7 Cl.31; p.35 Cl.31A; p.19 Schedule 2D; LH-713 billed 385000.00; Schedule 2D value for 2026-06 less depreciation for 428 h is 318615.40 | |
| MDS-01625 | retro_adjustment | 226,300.58 | 226,300.58 | 0.9 | p.35 Cl.36A; p.42 Amendment No. 3; DDS-2025-118/A3 issued 2026-08-17: settlement of 309965.52 on 3309 lines due on the first invoice submitted on or after the issue date; MDS-01625 (2026-08-17) carries 0.00 | |
| PA-00297 | superseded_rate | 208,403.01 | 359,886.87 | 0.9 | p.38 Schedule of Variations; p.39 Supplement No. 1; D.41.020: billed 72.71 (61730.79); contract 252.47 (214347.03); billed at the Schedule 1 rate 63.50; in force: CW-2025-0417-CIV/S1 2025-09 220.50 | |
| MDS-00901 | unsigned_record | 151,460.66 | 104,269.44 | 0.85 | p.5 Cl.15; DDR-149-20251122 is not signed by the Company Representative and the lead directional driller | |
| MDS-00672 | wrong_contract_ref | 47,992.77 | 47,992.77 | 0.9 | p.1 Agreement; contract_ref 'DSS-2025-118', contract is 'DDS-2025-118' | |
| PA-00406 | wrong_unit | 144,671.39 | 136,889.63 | 0.9 | p.6 Cl.26; p.17 Schedule 1; A.14.030 billed in 'lm'; Schedule 1 unit is 'm2' | |
