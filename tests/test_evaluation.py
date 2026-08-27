"""Tests for label loading and accuracy against generated grades."""

from pathlib import Path

import pytest

from app.evaluation import (
    HumanLabel,
    calculate_accuracy,
    evaluate,
    load_labels,
    load_results,
)
from app.schemas import CriterionGrade, GradedCall

_JUSTIFICATION = "Test justification."


def _criterion(score: int) -> CriterionGrade:
    """Build a criterion grade used in test fixtures.

    Args:
        score: Rubric score of 0, 5, or 10.

    Returns:
        A ``CriterionGrade`` with a placeholder justification.
    """
    return CriterionGrade(score=score, justification=_JUSTIFICATION)


def _graded_call(call_id: str, scores: tuple[int, int, int, int, int]) -> GradedCall:
    """Build a graded call from five criterion scores.

    Args:
        call_id: Transcript identifier.
        scores: Scores for C1 through C5.

    Returns:
        A ``GradedCall`` whose total is the sum of ``scores``.
    """
    c1, c2, c3, c4, c5 = scores
    return GradedCall(
        call_id=call_id,
        c1_greeting=_criterion(c1),
        c2_discovery=_criterion(c2),
        c3_compliance=_criterion(c3),
        c4_resolution=_criterion(c4),
        c5_professionalism=_criterion(c5),
        total=sum(scores),
    )


def _human_label(call_id: str, scores: tuple[int, int, int, int, int]) -> HumanLabel:
    """Build a human label from five criterion scores.

    Args:
        call_id: Transcript identifier.
        scores: Scores for C1 through C5.

    Returns:
        A ``HumanLabel`` whose total is the sum of ``scores``.
    """
    c1, c2, c3, c4, c5 = scores
    return HumanLabel(
        call_id=call_id,
        c1_greeting=c1,
        c2_discovery=c2,
        c3_compliance=c3,
        c4_resolution=c4,
        c5_professionalism=c5,
        total=sum(scores),
    )


def test_load_labels_reads_calibration_csv(tmp_path: Path) -> None:
    """Labels are keyed by call ID with integer criterion scores."""
    labels_path = tmp_path / "labels.csv"
    labels_path.write_text(
        "call_id,c1_greeting,c2_discovery,c3_compliance,"
        "c4_resolution,c5_professionalism,total\n"
        "C001,10,5,10,0,10,35\n",
        encoding="utf-8",
    )

    labels = load_labels(labels_path)

    assert set(labels) == {"C001"}
    assert labels["C001"].c2_discovery == 5
    assert labels["C001"].total == 35


def test_load_labels_missing_file_raises(tmp_path: Path) -> None:
    """A missing labels file raises FileNotFoundError."""
    with pytest.raises(FileNotFoundError):
        load_labels(tmp_path / "missing.csv")


def test_evaluate_perfect_match_is_one() -> None:
    """Identical labels and predictions yield accuracy 1.0."""
    scores = (10, 5, 10, 0, 10)
    labels = {"C001": _human_label("C001", scores)}
    results = {"C001": _graded_call("C001", scores)}

    report = evaluate(labels, results)

    assert report.accuracy == 1.0
    assert report.exact_call_match_accuracy == 1.0
    assert report.within_one_level_accuracy == 1.0
    assert report.disagreements == []


def test_evaluate_counts_criterion_mismatches() -> None:
    """Accuracy is the fraction of matching criterion scores."""
    labels = {"C001": _human_label("C001", (10, 10, 10, 10, 10))}
    results = {
        "C001": _graded_call("C001", (10, 5, 10, 10, 10)),
        "C099": _graded_call("C099", (0, 0, 0, 0, 0)),
    }

    report = evaluate(labels, results)

    assert report.n_compared_scores == 5
    assert report.n_correct == 4
    assert report.accuracy == pytest.approx(0.8)
    assert report.accuracy_by_criterion["c2_discovery"] == 0.0
    assert report.accuracy_by_criterion["c1_greeting"] == 1.0
    assert report.within_one_level_accuracy == 1.0
    assert report.exact_call_match_accuracy == 0.0
    assert len(report.disagreements) == 1
    assert report.disagreements[0].criterion == "c2_discovery"
    assert report.disagreements[0].label == 10
    assert report.disagreements[0].predicted == 5


def test_evaluate_missing_prediction_raises() -> None:
    """A labeled call without a generated grade is an error."""
    labels = {"C001": _human_label("C001", (10, 10, 10, 10, 10))}
    results = {"C002": _graded_call("C002", (10, 10, 10, 10, 10))}

    with pytest.raises(KeyError, match="C001"):
        evaluate(labels, results)


def test_calculate_accuracy_from_files(tmp_path: Path) -> None:
    """End-to-end accuracy uses the labels CSV and grades JSON."""
    labels_path = tmp_path / "labels.csv"
    labels_path.write_text(
        "call_id,c1_greeting,c2_discovery,c3_compliance,"
        "c4_resolution,c5_professionalism,total\n"
        "C001,10,10,10,10,10,50\n",
        encoding="utf-8",
    )
    results_path = tmp_path / "grades.json"
    graded = _graded_call("C001", (10, 10, 10, 5, 10))
    results_path.write_text(
        f"[{graded.model_dump_json()}]",
        encoding="utf-8",
    )

    report = calculate_accuracy(labels_path, results_path)

    assert load_results(results_path)["C001"].call_id == "C001"
    assert report.accuracy == pytest.approx(0.8)
    assert report.disagreements[0].criterion == "c4_resolution"
