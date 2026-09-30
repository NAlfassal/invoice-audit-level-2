"""Score the pipeline on injected error sets (CLAUDE.md §8.2), Phase 6.

Input: the invoices, output/findings.csv from the audit stage (the clean pool: invoices with
no finding), and eval/inject.py. The clean invoices are split in two halves with a fixed
seed; set A plants errors in one half and set B in the other. Set A was used to check and
tune the confidences; set B is the reported result. For each set the full pipeline runs on
the modified data and the verdicts on the set's invoices are compared with the labels.
Output: eval/labels_A.csv, eval/labels_B.csv and output/eval.md (per category and overall:
TP, FP, FN, TN, precision, recall, F1, cost = 5 x FN + FP, category and amount accuracy,
and stated vs measured precision per confidence band). Loaded by `python -m audit eval`.
"""

from __future__ import annotations

import csv
import logging
import random
import runpy
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from audit import calibrate, config, decide, io, linker
from audit.checks import c10_duplicates, run_all, unmeasured_lines
from audit.pricing import civil, compare, drilling

log = logging.getLogger(__name__)
EVAL_DIR = Path(__file__).parent
SPLIT_SEED = 20260930
SET_SEEDS = {"A": 101, "B": 202}
BANDS = ((0.0, 0.4), (0.4, 0.6), (0.6, 0.8), (0.8, 1.01))
FN_COST, FP_COST = 5, 1


@dataclass
class Scores:
    """Detection and accuracy counts of one set."""

    tp: int = 0
    fp: int = 0
    fn: int = 0
    tn: int = 0
    category_ok: int = 0
    amount_ok: int = 0

    @property
    def precision(self) -> float:
        """Return TP / (TP + FP)."""
        return self.tp / (self.tp + self.fp) if self.tp + self.fp else 0.0

    @property
    def recall(self) -> float:
        """Return TP / (TP + FN)."""
        return self.tp / (self.tp + self.fn) if self.tp + self.fn else 0.0

    @property
    def f1(self) -> float:
        """Return 2PR / (P + R)."""
        p, r = self.precision, self.recall
        return 2 * p * r / (p + r) if p + r else 0.0

    @property
    def cost(self) -> int:
        """Return the brief's cost: 5 x FN + 1 x FP."""
        return FN_COST * self.fn + FP_COST * self.fp


def clear_caches() -> None:
    """Drop results cached for one data set, so the next set is priced afresh."""
    for cached in (
        civil.price_lines,
        drilling.price_lines,
        compare.differences,
        calibrate.line_agreement,
        calibrate.item_agreement,
        unmeasured_lines,
        c10_duplicates.exact_copies,
        linker.civil_records_of,
        linker.reports_of,
    ):
        cached.cache_clear()


def clean_pool(data: io.AuditData) -> list[str]:
    """Return the invoices with no finding on the real data (from output/findings.csv)."""
    findings_file = config.OUTPUT_DIR / "findings.csv"
    if not findings_file.exists():
        raise FileNotFoundError(f"{findings_file} is missing: run `python -m audit audit` first")
    with findings_file.open(encoding="utf-8") as handle:
        with_findings = {row["invoice_id"] for row in csv.DictReader(handle)}
    ids = list(data.civil_apps["application_no"]) + list(data.drill_invoices["invoice_no"])
    return sorted(set(ids) - with_findings)


def split(pool: list[str]) -> dict[str, list[str]]:
    """Split the clean pool into two fixed halves, A and B."""
    shuffled = sorted(pool)
    random.Random(SPLIT_SEED).shuffle(shuffled)
    half = len(shuffled) // 2
    return {"A": sorted(shuffled[:half]), "B": sorted(shuffled[half:])}


def score(submission: pd.DataFrame, labels: list, set_ids: list[str]) -> dict:
    """Compare the verdicts on a set's invoices with its labels."""
    verdicts = submission.set_index("invoice_id").loc[set_ids]
    planted = {label.invoice_id: label for label in labels}
    overall = Scores()
    per_category: dict[str, Scores] = {}
    false_flags: dict[str, int] = {}
    bands = {band: [0, 0] for band in BANDS}  # flagged, of which planted
    for invoice_id, row in verdicts.iterrows():
        label = planted.get(invoice_id)
        flagged = int(row["flagged"]) == 1
        if flagged:
            confidence = float(row["confidence"])
            band = next(b for b in BANDS if b[0] <= confidence < b[1])
            bands[band][0] += 1
            bands[band][1] += label is not None
        if label is None:
            overall.fp += flagged
            overall.tn += not flagged
            if flagged:
                false_flags[row["error_category"]] = false_flags.get(row["error_category"], 0) + 1
            continue
        own = per_category.setdefault(label.category, Scores())
        for scores in (overall, own):
            scores.tp += flagged
            scores.fn += not flagged
            if flagged:
                scores.category_ok += row["error_category"] == label.category
                scores.amount_ok += (
                    int(row["expected_total_cents"]) == label.true_expected_total_cents
                )
    return {
        "overall": overall,
        "categories": per_category,
        "false_flags": false_flags,
        "bands": bands,
    }


def run_set(data: io.AuditData, name: str, pool: list[str]) -> dict:
    """Build one set, run the pipeline on it, write its labels and return its scores."""
    inject = runpy.run_path(str(EVAL_DIR / "inject.py"))
    unpaid = unmeasured_lines(data)
    civil_prices, drill_prices = civil.price_lines(data, unpaid), drilling.price_lines(data, unpaid)
    modified, labels, set_ids = inject["build_set"](
        data, pool, SET_SEEDS[name], civil_prices, drill_prices
    )
    write_labels(labels, EVAL_DIR / f"labels_{name}.csv")
    clear_caches()
    findings = run_all(modified)
    submission = decide.decide(modified, findings)
    clear_caches()
    result = score(submission, labels, set_ids)
    result["size"] = (len(labels), len(set_ids) - len(labels))
    log.info("eval set %s: %d positives, %d negatives", name, *result["size"])
    return result


def write_labels(labels: list, path: Path) -> None:
    """Write a set's labels: invoice_id, category, true_expected_total_cents."""
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(["invoice_id", "category", "true_expected_total_cents"])
        for label in sorted(labels, key=lambda item: item.invoice_id):
            writer.writerow([label.invoice_id, label.category, label.true_expected_total_cents])


def pct(value: float) -> str:
    """Format a share as a percentage with one decimal."""
    return f"{100 * value:.1f}%"


def result_tables(result: dict) -> list[str]:
    """Render one set's scores as markdown tables."""
    overall = result["overall"]
    positives, negatives = result["size"]
    lines = [
        f"Positives {positives}, negatives {negatives}.",
        "",
        "| TP | FP | FN | TN | precision | recall | F1 | cost (5 x FN + FP) |",
        "|---|---|---|---|---|---|---|---|",
        f"| {overall.tp} | {overall.fp} | {overall.fn} | {overall.tn} | {pct(overall.precision)} | "
        f"{pct(overall.recall)} | {pct(overall.f1)} | {overall.cost} |",
        "",
        "| planted category | planted | detected (recall) | right category "
        "| right expected total |",
        "|---|---|---|---|---|",
    ]
    for category, scores in sorted(result["categories"].items()):
        planted = scores.tp + scores.fn
        lines.append(
            f"| {category} | {planted} | {scores.tp} ({pct(scores.recall)}) | "
            f"{scores.category_ok} of {scores.tp} | {scores.amount_ok} of {scores.tp} |"
        )
    detected = overall.tp
    lines += [
        "",
        f"Category accuracy: {overall.category_ok} of {detected}. "
        f"Amount accuracy: {overall.amount_ok} of {detected}.",
        "",
        "False flags on negatives, by stated category: "
        + (", ".join(f"{k} {v}" for k, v in sorted(result["false_flags"].items())) or "none"),
        "",
        "| stated confidence | flagged | planted errors among them | measured precision |",
        "|---|---|---|---|",
    ]
    for (low, high), (flagged, right) in result["bands"].items():
        measured = pct(right / flagged) if flagged else "-"
        lines.append(f"| {low:.1f}-{min(high, 1.0):.1f} | {flagged} | {right} | {measured} |")
    return lines


def write_report(results: dict[str, dict], path: Path) -> None:
    """Write output/eval.md: set B as the result, set A as the tuning record."""
    lines = [
        "# Evaluation on injected errors (CLAUDE.md §8.2)",
        "",
        "Clean invoices (no finding on the real data) are split into two fixed halves. Each set",
        "plants one error in each of 10 invoices per category (5 civil, 5 drilling where both",
        "contracts can carry it) and leaves the rest of its half untouched. Amounts, subtotals,",
        "retention / DS-900 / VAT and totals are recomputed as a contractor would, except for the",
        "planted arithmetic errors. Only error types planted here are measured; recall on other",
        "kinds of error is not measured.",
        "",
        "## Set B (reported result; run once, not tuned on)",
        "",
        *result_tables(results["B"]),
        "",
        "## Set A (tuning set; not a result)",
        "",
        "Used to check the confidences and the threshold before set B was run. The first run of",
        "set A gave 4 false flags and 1 wrong category, all caused by the injector: removing a",
        "banded line moved the bands of later lines on other invoices (D19), and a late date",
        "brought Amendment 3 into force. The injector now avoids both; no check, confidence or",
        "threshold was changed. The threshold stays at P(error) >= 1/6.",
        "",
        "The planted errors follow the rules the checks encode, so these sets measure whether",
        "each check works as built, not how often the contract has been read correctly. The",
        "real-data evidence for the reading is the calibration (output/calibration.md) and the",
        "manual review (output/manual_review.md).",
        "",
        *result_tables(results["A"]),
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


REVIEW_SIZE = 15


def review_list(submission: pd.DataFrame, findings: pd.DataFrame) -> pd.DataFrame:
    """Pick 15 flagged invoices across the categories for the manual review (CLAUDE.md §9).

    Every category gets one invoice (the largest money impact); the remaining places go to
    the largest categories, next largest impact first.
    """
    flagged = submission[submission["flagged"] == 1].copy()
    flagged["impact"] = (flagged["expected_total_cents"] - flagged["billed_total_cents"]).abs()
    flagged = flagged.sort_values(["impact", "invoice_id"], ascending=[False, True])
    picked = [group.iloc[0] for _, group in flagged.groupby("error_category", sort=True)]
    chosen = {row["invoice_id"] for row in picked}
    sizes = flagged["error_category"].value_counts()
    for category in sizes.index:
        if len(picked) >= REVIEW_SIZE:
            break
        rest = flagged[
            (flagged["error_category"] == category) & ~flagged["invoice_id"].isin(chosen)
        ]
        if not rest.empty:
            picked.append(rest.iloc[0])
            chosen.add(rest.iloc[0]["invoice_id"])
    return pd.DataFrame(picked[:REVIEW_SIZE]).sort_values(["error_category", "invoice_id"])


def write_review(path: Path) -> None:
    """Write output/manual_review.md: 15 flagged real invoices with their findings."""
    submission = pd.read_csv(config.SUBMISSION_PATH, dtype={"invoice_id": str})
    findings = pd.read_csv(config.OUTPUT_DIR / "findings.csv", dtype=str, keep_default_na=False)
    lines = [
        "# Manual review list (15 flagged invoices, across the categories)",
        "",
        "For each invoice: check the finding against the contract clause and the record, and",
        "mark it right or wrong. The share right per category is the real-data precision",
        "(CLAUDE.md §8.3).",
        "",
        "| invoice | category | billed | expected | confidence "
        "| finding (clause; evidence) | right? |",
        "|---|---|---|---|---|---|---|",
    ]
    for row in review_list(submission, findings).itertuples(index=False):
        own = findings[(findings["invoice_id"] == row.invoice_id) & (findings["status"] == "error")]
        main = own[own["category"] == row.error_category].iloc[0]
        evidence = f"{main['clause']}; {main['evidence']}".replace("|", "/")
        lines.append(
            f"| {row.invoice_id} | {row.error_category} | {row.billed_total_cents / 100:,.2f} | "
            f"{row.expected_total_cents / 100:,.2f} | {row.confidence} | {evidence} | |"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    """Build and score sets A and B; write the labels, output/eval.md and the review list."""
    paths = config.input_paths()
    data = io.load_all(paths)
    halves = split(clean_pool(data))
    results = {}
    for name in ("A", "B"):
        results[name] = run_set(data, name, halves[name])
    write_report(results, config.OUTPUT_DIR / "eval.md")
    write_review(config.OUTPUT_DIR / "manual_review.md")
    log.info("eval: wrote output/eval.md and eval/labels_A.csv, eval/labels_B.csv")
