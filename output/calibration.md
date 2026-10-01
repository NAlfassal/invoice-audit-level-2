# Calibration (Phase 3)

Share of priced lines whose billed rate and amount the pricing engine reproduces (the brief: 92-95% of invoices are correct). A rate period is the instrument (and month) and discount in force.

## Per contract

| contract | lines | rate_ok | amount_ok | rate_pct |
|---|---|---|---|---|
| civil | 7746 | 7693 | 7703 | 99.3 |
| drilling | 91122 | 91073 | 91070 | 99.9 |

## Invoices whose priced lines all agree

| contract | invoices | all_lines_agree | pct |
|---|---|---|---|
| civil | 900 | 853 | 94.8 |
| drilling | 1906 | 1857 | 97.4 |

## Differences by cause

| contract | category | lines |
|---|---|---|
| civil | discount_misapplied | 3 |
| civil | rate_buildup | 48 |
| civil | superseded_rate | 2 |
| drilling | discount_misapplied | 7 |
| drilling | rate_buildup | 32 |
| drilling | superseded_rate | 10 |

## Item x period groups with a difference

| contract | code | period | lines | rate_ok | amount_ok | rate_pct |
|---|---|---|---|---|---|---|
| civil | A.12.010 | Schedule 1 | 144 | 141 | 142 | 97.9 |
| civil | A.12.020 | Schedule 1 | 100 | 97 | 99 | 97.0 |
| civil | A.12.030 | Schedule 1 | 135 | 134 | 134 | 99.3 |
| civil | A.12.040 | Schedule 1 | 132 | 130 | 130 | 98.5 |
| civil | A.12.050 | Schedule 1 | 148 | 145 | 145 | 98.0 |
| civil | A.12.060 | Schedule 1 | 139 | 138 | 138 | 99.3 |
| civil | A.13.010 | Schedule 1 | 126 | 125 | 125 | 99.2 |
| civil | A.14.010 | CW-2025-0417-CIV/A3 | 22 | 18 | 19 | 81.8 |
| civil | A.14.010 | Schedule 1 | 95 | 94 | 95 | 98.9 |
| civil | A.14.020 | Schedule 1 | 125 | 124 | 124 | 99.2 |
| civil | B.22.010 | Schedule 1 | 145 | 143 | 145 | 98.6 |
| civil | B.23.010 | CW-2025-0417-CIV/A1, discount 8% | 32 | 29 | 30 | 90.6 |
| civil | B.23.010 | Schedule 1 | 21 | 19 | 20 | 90.5 |
| civil | B.23.020 | Schedule 1 | 129 | 128 | 128 | 99.2 |
| civil | B.24.010 | Schedule 1 | 127 | 126 | 126 | 99.2 |
| civil | B.25.010 | Schedule 1 | 126 | 124 | 124 | 98.4 |
| civil | B.26.010 | Schedule 1 | 128 | 127 | 127 | 99.2 |
| civil | C.31.010 | Schedule 1 | 140 | 136 | 136 | 97.1 |
| civil | C.31.020 | Schedule 1 | 135 | 134 | 133 | 99.3 |
| civil | C.31.030 | Schedule 1 | 133 | 132 | 132 | 99.2 |
| civil | C.32.010 | Schedule 1, discount 5% | 33 | 32 | 32 | 97.0 |
| civil | C.32.030 | Schedule 1 | 79 | 77 | 77 | 97.5 |
| civil | D.41.010 | Schedule 1 | 139 | 136 | 138 | 97.8 |
| civil | D.41.020 | CW-2025-0417-CIV/S1 2025-07 | 5 | 4 | 4 | 80.0 |
| civil | D.41.020 | CW-2025-0417-CIV/S1 2025-09 | 27 | 26 | 26 | 96.3 |
| civil | D.41.020 | CW-2025-0417-CIV/S2, discount 8% | 29 | 27 | 27 | 93.1 |
| civil | D.41.030 | Schedule 1 | 146 | 145 | 145 | 99.3 |
| civil | D.41.040 | Schedule 1 | 126 | 123 | 125 | 97.6 |
| civil | D.43.010 | Schedule 1 | 122 | 121 | 121 | 99.2 |
| drilling | DD-101 | DDS-2025-118/A3, discount 7% | 1270 | 1268 | 1268 | 99.8 |
| drilling | DD-110 | Schedule 1 | 3304 | 3302 | 3302 | 99.9 |
| drilling | DD-120 | DDS-2025-118/A3, discount 7% | 778 | 777 | 777 | 99.9 |
| drilling | DD-121 | DDS-2025-118/S1 | 186 | 181 | 181 | 97.3 |
| drilling | HC-620 | Schedule 1 | 8151 | 8149 | 8149 | 100.0 |
| drilling | LW-401 | DDS-2025-118/A1, discount 4% | 473 | 471 | 471 | 99.6 |
| drilling | LW-401 | Schedule 1 | 1766 | 1765 | 1765 | 99.9 |
| drilling | LW-410 | Schedule 1 | 2964 | 2963 | 2963 | 100.0 |
| drilling | LW-412 | Schedule 1 | 955 | 954 | 954 | 99.9 |
| drilling | MB-701 | DDS-2025-118/A2, discount 7% | 38 | 37 | 37 | 97.4 |
| drilling | MB-701 | Schedule 1, discount 4% | 28 | 27 | 27 | 96.4 |
| drilling | MW-301 | DDS-2025-118/A1 | 1085 | 1084 | 1084 | 99.9 |
| drilling | MW-301 | DDS-2025-118/A1, discount 4% | 1095 | 1094 | 1094 | 99.9 |
| drilling | MW-301 | Schedule 1 | 4366 | 4363 | 4363 | 99.9 |
| drilling | MW-310 | Schedule 1 | 8150 | 8134 | 8134 | 99.8 |
| drilling | MW-320 | Schedule 1 | 4847 | 4846 | 4845 | 100.0 |
| drilling | PD-210 | Schedule 2 | 2390 | 2383 | 2382 | 99.7 |
| drilling | RM-511 | Schedule 1 | 806 | 805 | 804 | 99.9 |

## All items x periods

| contract | code | period | lines | rate_ok | amount_ok | rate_pct |
|---|---|---|---|---|---|---|
| civil | A.11.010 | Schedule 1 | 148 | 148 | 148 | 100.0 |
| civil | A.11.020 | Schedule 1 | 141 | 141 | 141 | 100.0 |
| civil | A.11.030 | Schedule 1 | 130 | 130 | 130 | 100.0 |
| civil | A.12.010 | Schedule 1 | 144 | 141 | 142 | 97.9 |
| civil | A.12.020 | Schedule 1 | 100 | 97 | 99 | 97.0 |
| civil | A.12.030 | Schedule 1 | 135 | 134 | 134 | 99.3 |
| civil | A.12.040 | Schedule 1 | 132 | 130 | 130 | 98.5 |
| civil | A.12.050 | Schedule 1 | 148 | 145 | 145 | 98.0 |
| civil | A.12.060 | Schedule 1 | 139 | 138 | 138 | 99.3 |
| civil | A.13.010 | Schedule 1 | 126 | 125 | 125 | 99.2 |
| civil | A.13.020 | Schedule 1 | 128 | 128 | 128 | 100.0 |
| civil | A.13.030 | Schedule 1 | 141 | 141 | 141 | 100.0 |
| civil | A.14.010 | CW-2025-0417-CIV/A3 | 22 | 18 | 19 | 81.8 |
| civil | A.14.010 | Schedule 1 | 95 | 94 | 95 | 98.9 |
| civil | A.14.020 | Schedule 1 | 125 | 124 | 124 | 99.2 |
| civil | A.14.030 | Schedule 1 | 131 | 131 | 131 | 100.0 |
| civil | A.15.010 | Schedule 1 | 122 | 122 | 122 | 100.0 |
| civil | A.15.020 | Schedule 1 | 120 | 120 | 120 | 100.0 |
| civil | A.16.010 | CW-2025-0417-CIV/S1 | 110 | 110 | 110 | 100.0 |
| civil | A.16.010 | Schedule 1 | 25 | 25 | 25 | 100.0 |
| civil | B.21.010 | Schedule 1 | 107 | 107 | 107 | 100.0 |
| civil | B.21.020 | CW-2025-0417-CIV/S1 | 89 | 89 | 89 | 100.0 |
| civil | B.21.020 | Schedule 1 | 17 | 17 | 17 | 100.0 |
| civil | B.21.030 | Schedule 1 | 121 | 121 | 121 | 100.0 |
| civil | B.21.040 | Schedule 1 | 138 | 138 | 138 | 100.0 |
| civil | B.21.050 | Schedule 1 | 134 | 134 | 134 | 100.0 |
| civil | B.22.010 | Schedule 1 | 145 | 143 | 145 | 98.6 |
| civil | B.22.020 | Schedule 1 | 125 | 125 | 125 | 100.0 |
| civil | B.22.030 | Schedule 1 | 128 | 128 | 128 | 100.0 |
| civil | B.23.010 | CW-2025-0417-CIV/A1 | 19 | 19 | 19 | 100.0 |
| civil | B.23.010 | CW-2025-0417-CIV/A1, discount 5% | 26 | 26 | 26 | 100.0 |
| civil | B.23.010 | CW-2025-0417-CIV/A1, discount 8% | 32 | 29 | 30 | 90.6 |
| civil | B.23.010 | CW-2025-0417-CIV/S1 | 31 | 31 | 31 | 100.0 |
| civil | B.23.010 | Schedule 1 | 21 | 19 | 20 | 90.5 |
| civil | B.23.020 | Schedule 1 | 129 | 128 | 128 | 99.2 |
| civil | B.24.010 | Schedule 1 | 127 | 126 | 126 | 99.2 |
| civil | B.25.010 | Schedule 1 | 126 | 124 | 124 | 98.4 |
| civil | B.26.010 | Schedule 1 | 128 | 127 | 127 | 99.2 |
| civil | B.27.010 | Schedule 1 | 133 | 133 | 133 | 100.0 |
| civil | C.31.010 | Schedule 1 | 140 | 136 | 136 | 97.1 |
| civil | C.31.020 | Schedule 1 | 135 | 134 | 133 | 99.3 |
| civil | C.31.030 | Schedule 1 | 133 | 132 | 132 | 99.2 |
| civil | C.31.040 | Schedule 1 | 131 | 131 | 131 | 100.0 |
| civil | C.32.010 | CW-2025-0417-CIV/A3, discount 8% | 25 | 25 | 25 | 100.0 |
| civil | C.32.010 | Schedule 1 | 66 | 66 | 65 | 100.0 |
| civil | C.32.010 | Schedule 1, discount 5% | 33 | 32 | 32 | 97.0 |
| civil | C.32.010 | Schedule 1, discount 8% | 5 | 5 | 5 | 100.0 |
| civil | C.32.020 | Schedule 1 | 137 | 137 | 137 | 100.0 |
| civil | C.32.030 | Schedule 1 | 79 | 77 | 77 | 97.5 |
| civil | C.32.030 | Schedule 1, discount 5% | 28 | 28 | 28 | 100.0 |
| civil | C.32.030 | Schedule 1, discount 8% | 28 | 28 | 28 | 100.0 |
| civil | C.32.040 | Schedule 1 | 135 | 135 | 135 | 100.0 |
| civil | C.33.010 | Schedule 1 | 115 | 115 | 115 | 100.0 |
| civil | C.34.010 | Schedule 1 | 119 | 119 | 119 | 100.0 |
| civil | C.35.010 | Schedule 1 | 120 | 120 | 119 | 100.0 |
| civil | D.41.010 | Schedule 1 | 139 | 136 | 138 | 97.8 |
| civil | D.41.020 | CW-2025-0417-CIV/S1 2025-05 | 6 | 6 | 6 | 100.0 |
| civil | D.41.020 | CW-2025-0417-CIV/S1 2025-06 | 8 | 8 | 8 | 100.0 |
| civil | D.41.020 | CW-2025-0417-CIV/S1 2025-07 | 5 | 4 | 4 | 80.0 |
| civil | D.41.020 | CW-2025-0417-CIV/S1 2025-08 | 7 | 7 | 7 | 100.0 |
| civil | D.41.020 | CW-2025-0417-CIV/S1 2025-09 | 27 | 26 | 26 | 96.3 |
| civil | D.41.020 | CW-2025-0417-CIV/S2, discount 5% | 29 | 29 | 29 | 100.0 |
| civil | D.41.020 | CW-2025-0417-CIV/S2, discount 8% | 29 | 27 | 27 | 93.1 |
| civil | D.41.020 | Schedule 1 | 20 | 20 | 20 | 100.0 |
| civil | D.41.030 | Schedule 1 | 146 | 145 | 145 | 99.3 |
| civil | D.41.040 | Schedule 1 | 126 | 123 | 125 | 97.6 |
| civil | D.41.050 | Schedule 1 | 140 | 140 | 140 | 100.0 |
| civil | D.42.010 | Schedule 1 | 119 | 119 | 119 | 100.0 |
| civil | D.42.020 | Schedule 1 | 119 | 119 | 119 | 100.0 |
| civil | D.42.030 | Schedule 1 | 125 | 125 | 125 | 100.0 |
| civil | D.43.010 | Schedule 1 | 122 | 121 | 121 | 99.2 |
| civil | D.43.020 | Schedule 1 | 120 | 120 | 120 | 100.0 |
| civil | D.44.010 | Schedule 1 | 135 | 135 | 135 | 100.0 |
| civil | E.51.010 | Schedule 1 | 143 | 143 | 143 | 100.0 |
| civil | E.51.020 | Schedule 1 | 104 | 104 | 104 | 100.0 |
| civil | E.51.030 | Schedule 1 | 144 | 144 | 144 | 100.0 |
| civil | E.52.010 | Schedule 1 | 113 | 113 | 113 | 100.0 |
| civil | E.53.010 | Schedule 1 | 130 | 130 | 130 | 100.0 |
| civil | E.54.010 | CW-2025-0417-CIV/A1 | 37 | 37 | 37 | 100.0 |
| civil | E.54.010 | CW-2025-0417-CIV/A2 2026-04 | 4 | 4 | 4 | 100.0 |
| civil | E.54.010 | CW-2025-0417-CIV/A2 2026-05 | 10 | 10 | 10 | 100.0 |
| civil | E.54.010 | CW-2025-0417-CIV/A2 2026-06 | 1 | 1 | 1 | 100.0 |
| civil | E.54.010 | CW-2025-0417-CIV/A2 2026-07 | 4 | 4 | 4 | 100.0 |
| civil | E.54.010 | CW-2025-0417-CIV/A2 2026-08 | 4 | 4 | 4 | 100.0 |
| civil | E.54.010 | Schedule 1 | 63 | 63 | 63 | 100.0 |
| drilling | DD-101 | DDS-2025-118/A1 | 1085 | 1085 | 1085 | 100.0 |
| drilling | DD-101 | DDS-2025-118/A1, discount 4% | 1095 | 1095 | 1095 | 100.0 |
| drilling | DD-101 | DDS-2025-118/A1, discount 7% | 336 | 336 | 336 | 100.0 |
| drilling | DD-101 | DDS-2025-118/A3, discount 7% | 1270 | 1268 | 1268 | 99.8 |
| drilling | DD-101 | Schedule 1 | 4365 | 4365 | 4365 | 100.0 |
| drilling | DD-102 | Schedule 1 | 8151 | 8151 | 8151 | 100.0 |
| drilling | DD-110 | Schedule 1 | 3304 | 3302 | 3302 | 99.9 |
| drilling | DD-111 | Schedule 1 | 654 | 654 | 654 | 100.0 |
| drilling | DD-120 | DDS-2025-118/A3, discount 7% | 778 | 777 | 777 | 99.9 |
| drilling | DD-120 | DDS-2025-118/S1 | 1855 | 1855 | 1855 | 100.0 |
| drilling | DD-120 | DDS-2025-118/S2 2026-04, discount 4% | 213 | 213 | 213 | 100.0 |
| drilling | DD-120 | DDS-2025-118/S2 2026-05, discount 4% | 204 | 204 | 204 | 100.0 |
| drilling | DD-120 | DDS-2025-118/S2 2026-06, discount 4% | 203 | 203 | 203 | 100.0 |
| drilling | DD-120 | DDS-2025-118/S2 2026-07, discount 7% | 157 | 157 | 157 | 100.0 |
| drilling | DD-120 | DDS-2025-118/S2 2026-08, discount 7% | 23 | 23 | 23 | 100.0 |
| drilling | DD-120 | Schedule 1 | 1173 | 1173 | 1173 | 100.0 |
| drilling | DD-121 | DDS-2025-118/S1 | 186 | 181 | 181 | 97.3 |
| drilling | DD-121 | Schedule 1 | 59 | 59 | 59 | 100.0 |
| drilling | DD-130 | Schedule 1 | 480 | 480 | 480 | 100.0 |
| drilling | DD-140 | Schedule 1 | 214 | 214 | 214 | 100.0 |
| drilling | HC-601 | DDS-2025-118/S1 2025-07 | 66 | 66 | 66 | 100.0 |
| drilling | HC-601 | DDS-2025-118/S1 2025-08 | 88 | 88 | 88 | 100.0 |
| drilling | HC-601 | DDS-2025-118/S1 2025-09 | 61 | 61 | 61 | 100.0 |
| drilling | HC-601 | DDS-2025-118/S1 2025-10 | 88 | 88 | 88 | 100.0 |
| drilling | HC-601 | DDS-2025-118/S1 2025-11 | 93 | 93 | 93 | 100.0 |
| drilling | HC-601 | DDS-2025-118/S1 2025-12 | 855 | 855 | 855 | 100.0 |
| drilling | HC-601 | Schedule 1 | 516 | 516 | 516 | 100.0 |
| drilling | HC-610 | Schedule 1 | 943 | 943 | 943 | 100.0 |
| drilling | HC-620 | Schedule 1 | 8151 | 8149 | 8149 | 100.0 |
| drilling | HC-630 | Schedule 1 | 428 | 428 | 428 | 100.0 |
| drilling | HC-640 | Schedule 1 | 2142 | 2142 | 2142 | 100.0 |
| drilling | LW-401 | DDS-2025-118/A1 | 483 | 483 | 483 | 100.0 |
| drilling | LW-401 | DDS-2025-118/A1, discount 4% | 473 | 471 | 471 | 99.6 |
| drilling | LW-401 | DDS-2025-118/A1, discount 7% | 710 | 710 | 710 | 100.0 |
| drilling | LW-401 | Schedule 1 | 1766 | 1765 | 1765 | 99.9 |
| drilling | LW-410 | Schedule 1 | 2964 | 2963 | 2963 | 100.0 |
| drilling | LW-411 | Schedule 1 | 2250 | 2250 | 2250 | 100.0 |
| drilling | LW-412 | Schedule 1 | 955 | 954 | 954 | 99.9 |
| drilling | LW-413 | Schedule 1 | 445 | 445 | 445 | 100.0 |
| drilling | LW-420 | Schedule 1 | 369 | 369 | 369 | 100.0 |
| drilling | LW-430 | Schedule 1 | 214 | 214 | 214 | 100.0 |
| drilling | MB-701 | DDS-2025-118/A2, discount 7% | 38 | 37 | 37 | 97.4 |
| drilling | MB-701 | Schedule 1 | 151 | 151 | 151 | 100.0 |
| drilling | MB-701 | Schedule 1, discount 4% | 28 | 27 | 27 | 96.4 |
| drilling | MB-702 | Schedule 1 | 214 | 214 | 214 | 100.0 |
| drilling | MW-301 | DDS-2025-118/A1 | 1085 | 1084 | 1084 | 99.9 |
| drilling | MW-301 | DDS-2025-118/A1, discount 4% | 1095 | 1094 | 1094 | 99.9 |
| drilling | MW-301 | DDS-2025-118/A2, discount 7% | 1606 | 1606 | 1606 | 100.0 |
| drilling | MW-301 | Schedule 1 | 4366 | 4363 | 4363 | 99.9 |
| drilling | MW-310 | Schedule 1 | 8150 | 8134 | 8134 | 99.8 |
| drilling | MW-320 | Schedule 1 | 4847 | 4846 | 4845 | 100.0 |
| drilling | MW-330 | Schedule 1 | 8151 | 8151 | 8151 | 100.0 |
| drilling | PD-201 | Schedule 1 | 2561 | 2561 | 2561 | 100.0 |
| drilling | PD-210 | Schedule 2 | 2390 | 2383 | 2382 | 99.7 |
| drilling | PD-220 | Schedule 1 | 1190 | 1190 | 1190 | 100.0 |
| drilling | PD-230 | Schedule 1 | 1190 | 1190 | 1190 | 100.0 |
| drilling | RM-510 | Schedule 1 | 679 | 679 | 679 | 100.0 |
| drilling | RM-511 | Schedule 1 | 806 | 805 | 804 | 99.9 |
| drilling | RM-520 | Schedule 1 | 1767 | 1767 | 1767 | 100.0 |
| drilling | RM-530 | Schedule 1 | 943 | 943 | 943 | 100.0 |
