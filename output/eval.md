# Evaluation on injected errors (CLAUDE.md §8.2)

Clean invoices (no finding on the real data) are split into two fixed halves. Each set
plants one error in each of 10 invoices per category (5 civil, 5 drilling where both
contracts can carry it) and leaves the rest of its half untouched. Amounts, subtotals,
retention / DS-900 / VAT and totals are recomputed as a contractor would, except for the
planted arithmetic errors. Only error types planted here are measured; recall on other
kinds of error is not measured.

## Set B (reported result; run once, not tuned on)

Positives 120, negatives 1176.

| TP | FP | FN | TN | precision | recall | F1 | cost (5 x FN + FP) |
|---|---|---|---|---|---|---|---|
| 120 | 0 | 0 | 1176 | 100.0% | 100.0% | 100.0% | 0 |

| planted category | planted | detected (recall) | right category | right expected total |
|---|---|---|---|---|
| arithmetic | 10 | 10 (100.0%) | 10 of 10 | 10 of 10 |
| discount_misapplied | 10 | 10 (100.0%) | 10 of 10 | 10 of 10 |
| duplicate_charge | 10 | 10 (100.0%) | 10 of 10 | 10 of 10 |
| invoice_window | 10 | 10 (100.0%) | 10 of 10 | 10 of 10 |
| limit_exceeded | 10 | 10 (100.0%) | 10 of 10 | 10 of 10 |
| missing_record | 10 | 10 (100.0%) | 10 of 10 | 10 of 10 |
| outside_term | 10 | 10 (100.0%) | 10 of 10 | 10 of 10 |
| quantity_over_record | 10 | 10 (100.0%) | 10 of 10 | 10 of 10 |
| rate_buildup | 10 | 10 (100.0%) | 10 of 10 | 10 of 10 |
| retro_adjustment | 10 | 10 (100.0%) | 10 of 10 | 10 of 10 |
| superseded_rate | 10 | 10 (100.0%) | 10 of 10 | 10 of 10 |
| wrong_contract_ref | 10 | 10 (100.0%) | 10 of 10 | 10 of 10 |

Category accuracy: 120 of 120. Amount accuracy: 120 of 120.

False flags on negatives, by stated category: none

| stated confidence | flagged | planted errors among them | measured precision |
|---|---|---|---|
| 0.0-0.4 | 0 | 0 | - |
| 0.4-0.6 | 0 | 0 | - |
| 0.6-0.8 | 0 | 0 | - |
| 0.8-1.0 | 120 | 120 | 100.0% |

## Set A (tuning set; not a result)

Used to check the confidences and the threshold before set B was run. The first run of
set A gave 4 false flags and 1 wrong category, all caused by the injector: removing a
banded line moved the bands of later lines on other invoices (D19), and a late date
brought Amendment 3 into force. The injector now avoids both; no check, confidence or
threshold was changed. The threshold stays at P(error) >= 1/6.

The planted errors follow the rules the checks encode, so these sets measure whether
each check works as built, not how often the contract has been read correctly. The
real-data evidence for the reading is the calibration (output/calibration.md) and the
manual review (output/manual_review.md).

Positives 120, negatives 1176.

| TP | FP | FN | TN | precision | recall | F1 | cost (5 x FN + FP) |
|---|---|---|---|---|---|---|---|
| 120 | 0 | 0 | 1176 | 100.0% | 100.0% | 100.0% | 0 |

| planted category | planted | detected (recall) | right category | right expected total |
|---|---|---|---|---|
| arithmetic | 10 | 10 (100.0%) | 10 of 10 | 10 of 10 |
| discount_misapplied | 10 | 10 (100.0%) | 10 of 10 | 10 of 10 |
| duplicate_charge | 10 | 10 (100.0%) | 10 of 10 | 10 of 10 |
| invoice_window | 10 | 10 (100.0%) | 10 of 10 | 10 of 10 |
| limit_exceeded | 10 | 10 (100.0%) | 10 of 10 | 10 of 10 |
| missing_record | 10 | 10 (100.0%) | 10 of 10 | 10 of 10 |
| outside_term | 10 | 10 (100.0%) | 10 of 10 | 10 of 10 |
| quantity_over_record | 10 | 10 (100.0%) | 10 of 10 | 10 of 10 |
| rate_buildup | 10 | 10 (100.0%) | 10 of 10 | 10 of 10 |
| retro_adjustment | 10 | 10 (100.0%) | 10 of 10 | 10 of 10 |
| superseded_rate | 10 | 10 (100.0%) | 10 of 10 | 10 of 10 |
| wrong_contract_ref | 10 | 10 (100.0%) | 10 of 10 | 10 of 10 |

Category accuracy: 120 of 120. Amount accuracy: 120 of 120.

False flags on negatives, by stated category: none

| stated confidence | flagged | planted errors among them | measured precision |
|---|---|---|---|
| 0.0-0.4 | 0 | 0 | - |
| 0.4-0.6 | 0 | 0 | - |
| 0.6-0.8 | 0 | 0 | - |
| 0.8-1.0 | 120 | 120 | 100.0% |
