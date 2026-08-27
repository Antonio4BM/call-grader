"""Agreement metrics between human labels and generated call grades."""

from __future__ import annotations

import csv
import json
from pathlib import Path

from app.schemas import EvaluationReport, GradedCall, HumanLabel, ScoreDisagreement

PROJECT_ROOT = Path(__file__).resolve().parent.parent
LABELS_PATH = PROJECT_ROOT / "data" / "labels.csv"
RESULTS_PATH = PROJECT_ROOT / "results" / "grades.json"

CRITERIA = (
    "c1_greeting",
    "c2_discovery",
    "c3_compliance",
    "c4_resolution",
    "c5_professionalism",
)

# Rubric scores are 0, 5, or 10; one level is a 5-point step.
_LEVEL_STEP = 5


def load_labels(path: Path = LABELS_PATH) -> dict[str, HumanLabel]:
    """Read human grades from the calibration CSV.

    Args:
        path: Path to ``labels.csv``.

    Returns:
        Mapping of call ID to human scores.

    Raises:
        FileNotFoundError: If the labels file is missing.
        ValueError: If required columns are missing or the file is empty.
    """
    if not path.is_file():
        raise FileNotFoundError(f"Labels file not found: {path}")

    required = ("call_id", *CRITERIA, "total")
    labels: dict[str, HumanLabel] = {}
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        fieldnames = reader.fieldnames or []
        missing = [column for column in required if column not in fieldnames]
        if missing:
            raise ValueError(f"Labels CSV missing columns: {missing}")
        for row in reader:
            label = HumanLabel(
                call_id=row["call_id"].strip(),
                c1_greeting=int(row["c1_greeting"]),
                c2_discovery=int(row["c2_discovery"]),
                c3_compliance=int(row["c3_compliance"]),
                c4_resolution=int(row["c4_resolution"]),
                c5_professionalism=int(row["c5_professionalism"]),
                total=int(row["total"]),
            )
            labels[label.call_id] = label

    if not labels:
        raise ValueError(f"No labels found in {path}")
    return labels


def load_results(path: Path = RESULTS_PATH) -> dict[str, GradedCall]:
    """Read generated grades from ``results/grades.json``.

    Args:
        path: Path to the JSON file written by the grader.

    Returns:
        Mapping of call ID to generated grades.

    Raises:
        FileNotFoundError: If the results file is missing.
        ValueError: If the file is empty or is not a JSON list.
    """
    if not path.is_file():
        raise FileNotFoundError(f"Results file not found: {path}")

    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list) or not payload:
        raise ValueError(f"Expected a non-empty JSON list in {path}")

    results = [GradedCall.model_validate(item) for item in payload]
    return {item.call_id: item for item in results}


def evaluate(
    labels: dict[str, HumanLabel],
    results: dict[str, GradedCall],
) -> EvaluationReport:
    """Calculate exact-match accuracy between labels and generated grades.

    Unlabeled generated calls are ignored. Accuracy is the fraction of
    criterion scores (five per labeled call) that match the human label
    exactly. ``within_one_level_accuracy`` treats a 5-point gap as one
    rubric step and counts it as agreement.

    Args:
        labels: Human scores keyed by call ID.
        results: Generated grades keyed by call ID.

    Returns:
        Accuracy totals, per-criterion rates, and mismatches.

    Raises:
        ValueError: If ``labels`` is empty.
        KeyError: If a labeled call has no generated result.
    """
    if not labels:
        raise ValueError("No labels were provided for evaluation.")

    missing = sorted(set(labels) - set(results))
    if missing:
        raise KeyError(f"Generated results missing labeled calls: {missing}")

    n_correct = 0
    n_within_one = 0
    n_compared = 0
    n_total_match = 0
    correct_by_criterion = {criterion: 0 for criterion in CRITERIA}
    disagreements: list[ScoreDisagreement] = []

    for call_id, label in labels.items():
        predicted = results[call_id]
        if predicted.total == label.total:
            n_total_match += 1
        for criterion in CRITERIA:
            gold = getattr(label, criterion)
            pred = getattr(predicted, criterion).score
            n_compared += 1
            if gold == pred:
                n_correct += 1
                correct_by_criterion[criterion] += 1
            else:
                disagreements.append(
                    ScoreDisagreement(
                        call_id=call_id,
                        criterion=criterion,
                        label=gold,
                        predicted=pred,
                    )
                )
            if abs(gold - pred) <= _LEVEL_STEP:
                n_within_one += 1

    n_calls = len(labels)
    return EvaluationReport(
        n_labeled_calls=n_calls,
        n_compared_scores=n_compared,
        n_correct=n_correct,
        accuracy=n_correct / n_compared,
        accuracy_by_criterion={
            criterion: correct_by_criterion[criterion] / n_calls
            for criterion in CRITERIA
        },
        exact_call_match_accuracy=n_total_match / n_calls,
        within_one_level_accuracy=n_within_one / n_compared,
        disagreements=disagreements,
    )


def calculate_accuracy(
    labels_path: Path = LABELS_PATH,
    results_path: Path = RESULTS_PATH,
) -> EvaluationReport:
    """Read labels and generated results, then calculate accuracy.

    The calibration set in ``labels.csv`` (C001-C015) is compared against
    ``results/grades.json``. Calls without human labels are skipped.

    Args:
        labels_path: Path to the human labels CSV.
        results_path: Path to the generated grades JSON.

    Returns:
        Accuracy of the grader against the human labels.
    """
    labels = load_labels(labels_path)
    results = load_results(results_path)
    return evaluate(labels, results)
