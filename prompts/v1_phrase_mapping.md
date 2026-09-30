# Phrase mapping prompt, v1

First version. Used in P4 step 2 for the site-record phrases that the regex and keyword rules
do not map. The output is reviewed by the user once and committed to `extracted/mappings/`.
The pipeline reads the committed JSON and makes no LLM call at runtime.

---

## Task

You map the wording of site records to the priced items of a contract. Each input row is one
phrase template taken from the work line of a record. Numbers in the phrase are replaced by N.
For each template, decide which contract item the phrase describes.

## Inputs

1. `templates`: one row per template, with `template_id`, `contract` (civil or drilling),
   `record_series` (for example CT, JS, PT, or DDR part A to E), `template`, `count` (how many
   records use it) and one `example` record text.
2. `items`: the priced items of that contract, with `code`, `description` and `unit`, as
   extracted from Schedule 1.
3. `series_items`: the items each record series can evidence (civil Schedule 5; drilling
   Schedule 5 parts and Appendix G).

## Rules

1. Choose only among the items that the template's record series can evidence
   (`series_items`). If none of them fits, return `no_match`.
2. The unit in the phrase must agree with the item unit (square metres = m2, cubic metres = m3,
   metres = lm or m, tonne = tonne, hours = hour, weeks = week, a count = no.). If the unit does
   not agree, the item does not fit.
3. Decide from the words of the phrase: the activity, the material, the size or the tool.
   Compare them with the item description. Do not use rates, amounts or how often an item is
   billed.
4. If two items fit equally well, return `ambiguous` and list both. Do not choose between them
   (guideline check 6).
5. Record words are written by site staff and do not repeat the Schedule wording (civil
   Cl.47A, drilling Cl.19A). A match needs the same activity and material, not the same words.
6. Quote the words from the phrase that decide the match in `evidence`.

## Output

Return JSON only: a list with one object per template, in the input order.

```json
{
  "template_id": "string",
  "item_code": "string or null",
  "status": "mapped | ambiguous | no_match",
  "candidates": ["codes considered that fit the series and unit"],
  "unit_in_phrase": "string or null",
  "evidence": "the words in the phrase that decide the match",
  "reason": "one sentence"
}
```

## Example

Input template (civil, series CT): `N square metres of sub-base in and compacted`

```json
{
  "template_id": "civ-CT-01",
  "item_code": "D.41.010",
  "status": "mapped",
  "candidates": ["D.41.010", "D.41.040"],
  "unit_in_phrase": "m2",
  "evidence": "square metres of sub-base ... compacted",
  "reason": "CT evidences A.14.010 (m3), D.41.010 and D.41.040 (m2); D.41.040 is a capping layer, D.41.010 is sub-base."
}
```

This example is checked against CT-00001 and line PA-00233-13 (D.41.010, 792 m2).
