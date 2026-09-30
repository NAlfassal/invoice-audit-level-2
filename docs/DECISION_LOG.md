# Decision log

The assumptions made, the ambiguities found, and what was decided about each. The contract
governs over the guidelines. **AN** = assumption that no source settles. IDs are kept from the
working log, so gaps mark entries that were settled by the text and removed.
 
| ID | Question | Decision | Why | Clause, page | Invoices |
| --- | --- | --- | --- | --- | --- |
| D05 | AN. Expected total of an invoice with a wrong contract reference, an early or late submission, or a misstated period: (a) the billed total, (b) 0 | (a): flagged, expected = billed; only lines outside the term or the stated period = 0 | These clauses do not make the work unpayable, unlike Cl.43 and Cl.46 | Cl.40-41 p.8; Cl.33 p.8 | 21 |
| D07 | One weekly dewatering log billed on several applications: each billing valid, or the week payable once | Payable once; later lines duplicate_charge (0.85) | A recorded week is one measurement (Cl.44), evidenced once by its record (Cl.46) | Cl.44, Cl.46 p.8 | 20 |
| D09 | A total that does not equal its lines "shall be returned unpaid": expected 0, or the sum of the corrected lines | The sum of the corrected lines | "Returned unpaid" is the remedy, not the value of the work | Cl.43 p.8 | 1 |
| D12 | DD-120 from 2026-04-01: Supplement 2's monthly rates, or Amendment 3's 416.00 (issued later, effective 2026-02-01) | Amendment 3 | Instruments are read in the order issued; the later governs from its effective date | Schedule of Variations p.37 | DD-120 lines |
| D13 | Civil discount of 5% (from 2025-12-01) then 8% (from 2026-04-01) on the same four items: added together, or replacing | 8% replaces 5% | Each instrument states the percentage in force from its date | Supplement 2, Amendment 2 pp.41-42 | 4 items |
| D14 | Band quantities counted from Commencement (Cl.30) or per Contract Year (Sch.4 Pt3); when a year restarts | Per Contract Year, restarting on each anniversary of Commencement, not on an extension | Sch.4 Pt3 substitutes Cl.30 and a Schedule prevails (Cl.2); Cl.3A defines the year | Cl.2 p.3; Sch.4 Pt3 p.24; Cl.3A p.32 | 8 items |
| D16 | Retro settlement on the first invoice submitted "after" the issue date (Amendment 3 pages) or "on or after" (the clauses) | On or after, by submission date; an invoice submitted on the issue date is priced at the new rate | The Amendment pages cite the clause, so they restate it; Cl.31A protects only invoices submitted before the issue date | Cl.31A p.32; Cl.36A p.35 | 4 |
| D17 | Is the retro settlement, or the Cl.45A retention release, part of the judged total? | No: the invoice that omits it is flagged, expected = the measured total | Cl.45A lists the adjustment apart from the measured total; both invoice files carry it in a separate column | Cl.45A p.32; Cl.36A p.35 | 5 |
| D18 | Drilling is invoiced per well: one settlement per well, or one for the contract | One for the contract (MDS-01625) | "a single adjustment ... and on no other" | Cl.36A p.35; Cl.31A p.32 | 1 |
| D19 | AN. Band quantities: count every billed line, or only payable lines | Payable lines only | The same reading as the daily limits ("measurable", Cl.31) | Sch.4 Pt3 p.24; Cl.31 p.6 | 0 changed |
| D21 | Well-class factor on PD-210: Sch.2 and Sch.3 Pt2 apply it, Cl.17B excludes it, and Cl.2 says a Schedule prevails over a Part | No factor | 17B names PD-210 and gives the reason; Cl.2 ranks Parts I-VII and 17B is in Part IX; the Appendix B form prices an HPHT well without the factor; the other reading makes 939 lines on 248 invoices wrong | Cl.17B p.35; App. B p.30; Cl.2 p.3 | 2 lines differ |
| D22 | AN. A line without its record: the error is on that application (Cl.46), or the next application should deduct it (P23) | On that application; the line = 0 | Cl.46: "not payable in any valuation until that record has been delivered"; no uncited record of the same series, area and date exists for these lines; P23 states how an amount already paid is recovered | Cl.46 p.8; P23 p.14 | 8 lines, 7 applications |
| D23 | "The first hour of each period in the hole" is not chargeable: once per run, or once per report day | Once per report day | The invoices deduct one hour on every report day (DD-120 4,601 lines, RM-530 941 lines) | Cl.21A p.35 | hour lines |
| D24 | AN (open). The 6-hour minimum before or after the one-hour deduction | After: max(hours - 1, 6) | No billed line is below 7 hours, so both readings agree | Cl.21 p.6; Cl.21A p.35 | 0 |
| D25 | AN. Three applications submitted on the Amendment 3 issue date: which is "the first"? | Each flagged at 0.33 | No source orders submissions made on the same date; 1/3 is above the 1/6 threshold | Cl.31A p.32 | 3 |
| D26 | AN. "A period which has closed" and "not before the last day": is submission on the last day allowed? | Allowed | "Not before the last day" is the sentence that sets the test | Cl.41 p.8 | 0 |
| D27 | AN. A.14.020 is not measurable "within 2 days following" A.14.010: does the same day count? | Yes, confidence 0.60 | Across all pairs, none falls on days 1-2 and only one on day 0, against 6 on the day before and 9 on day 3 | Cl.32 p.6; Sch.4 Pt5 p.26 | 1 |
| D28 | AN (open). PD-210 only on the sections nominated in the call-off | Section checked, well not | p.29 limits the section to 12-1/4" or 8-1/2", and all 2,390 PD-210 lines comply; the call-offs are not in the data | Cl.23 p.6; p.29 | 0 |
| D29 | AN (open). Civil standby rules that need times of day, flood watches or safety suspensions | S20 applied from the recorded hours; P2, P9 and H15 not checked | The records do not carry these facts | pp.11-16 | not measured |
 
**Brief.** `confidence` is read as the probability that the verdict is right (flagged: that the
invoice is wrong; unflagged: that it is correct). "Severity" is not defined; it is taken as
money impact, and no error is dropped for being small.
 
**Guidelines vs contract.** Guideline 10 ("nothing is billed twice") follows the Cl.44 key: the
same item, work area and date. Guideline 11 ("the arithmetic reconciles") allows a line split
across two quantity bands: of 32 civil lines below quantity x rate, 29 are band splits and 3
are arithmetic errors. Guideline 3 ("the period had closed") is read with Cl.41 (D26).