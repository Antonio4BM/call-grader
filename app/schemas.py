"""Structured output schema for the call grading pipeline."""

from typing import Literal, TypedDict

from pydantic import BaseModel, ConfigDict, Field

Score = Literal[0, 5, 10]


class CriterionGrade(BaseModel):
    """Score and one-sentence justification for a single rubric criterion.

    Attributes:
        score: Rubric score. Must be 0, 5, or 10.
        justification: One sentence citing the transcript and the rubric.
    """

    model_config = ConfigDict(extra="forbid")

    score: Score = Field(
        ...,
        description="Numeric score allowed by the rubric: 0, 5, or 10.",
    )
    justification: str = Field(
        ...,
        description=(
            "One sentence explaining why this score was given. Cite a "
            "specific quote or moment from the transcript and the matching "
            "rule from the rubric."
        ),
    )


class CallGrade(BaseModel):
    """Structured grader output for one call transcript.

    Attributes:
        c1_greeting: Grade for greeting and identification.
        c2_discovery: Grade for needs discovery.
        c3_compliance: Grade for compliance and disclosures.
        c4_resolution: Grade for resolution and next steps.
        c5_professionalism: Grade for professionalism and call control.
    """

    model_config = ConfigDict(extra="forbid")

    c1_greeting: CriterionGrade = Field(
        ...,
        description=(
            "C1. Greeting and Identification: agent greets, states company "
            "and own name, and offers help near the opening of the call."
        ),
    )
    c2_discovery: CriterionGrade = Field(
        ...,
        description=(
            "C2. Needs Discovery: agent asks questions to understand the "
            "customer's situation before proposing anything, and confirms "
            "understanding."
        ),
    )
    c3_compliance: CriterionGrade = Field(
        ...,
        description=(
            "C3. Compliance and Disclosures: recording disclosure near the "
            "start, and no prohibited statements anywhere in the call."
        ),
    )
    c4_resolution: CriterionGrade = Field(
        ...,
        description=(
            "C4. Resolution and Next Steps: the reason for calling is "
            "resolved, or a concrete next step has a specific owner and "
            "timeframe."
        ),
    )
    c5_professionalism: CriterionGrade = Field(
        ...,
        description=(
            "C5. Professionalism and Call Control: courteous throughout, "
            "lets the customer finish, and keeps the call on track."
        ),
    )

    def total_score(self) -> int:
        """Return the sum of the five criterion scores.

        Returns:
            Total score in the range 0 to 50.
        """
        return (
            self.c1_greeting.score
            + self.c2_discovery.score
            + self.c3_compliance.score
            + self.c4_resolution.score
            + self.c5_professionalism.score
        )


class GradedCall(BaseModel):
    """Pipeline result for one transcript, including identifiers and total.

    Attributes:
        call_id: Transcript identifier such as ``C001``.
        c1_greeting: Grade for greeting and identification.
        c2_discovery: Grade for needs discovery.
        c3_compliance: Grade for compliance and disclosures.
        c4_resolution: Grade for resolution and next steps.
        c5_professionalism: Grade for professionalism and call control.
        total: Sum of the five criterion scores (0 to 50).
    """

    call_id: str = Field(..., description="Transcript identifier, e.g. C001.")
    c1_greeting: CriterionGrade
    c2_discovery: CriterionGrade
    c3_compliance: CriterionGrade
    c4_resolution: CriterionGrade
    c5_professionalism: CriterionGrade
    total: int = Field(..., ge=0, le=50)

    @classmethod
    def from_grade(cls, call_id: str, grade: CallGrade) -> "GradedCall":
        """Build a graded call from an LLM structured output.

        Args:
            call_id: Transcript identifier taken from the filename.
            grade: Structured scores returned by the model.

        Returns:
            A ``GradedCall`` with the computed total.
        """
        return cls(
            call_id=call_id,
            c1_greeting=grade.c1_greeting,
            c2_discovery=grade.c2_discovery,
            c3_compliance=grade.c3_compliance,
            c4_resolution=grade.c4_resolution,
            c5_professionalism=grade.c5_professionalism,
            total=grade.total_score(),
        )

class TranscriptInput(TypedDict):
    """Inputs required to grade one call transcript.

    Attributes:
        call_id: Transcript identifier such as ``C001``.
        transcript: Full transcript text.
    """

    call_id: str
    transcript: str

class HumanLabel(BaseModel):
    """Human scores for one call from ``labels.csv``.

    Attributes:
        call_id: Transcript identifier such as ``C001``.
        c1_greeting: Human score for greeting and identification.
        c2_discovery: Human score for needs discovery.
        c3_compliance: Human score for compliance and disclosures.
        c4_resolution: Human score for resolution and next steps.
        c5_professionalism: Human score for professionalism and call control.
        total: Sum of the five criterion scores.
    """

    call_id: str
    c1_greeting: int
    c2_discovery: int
    c3_compliance: int
    c4_resolution: int
    c5_professionalism: int
    total: int


class ScoreDisagreement(BaseModel):
    """One criterion where the generated score differs from the label.

    Attributes:
        call_id: Transcript identifier such as ``C001``.
        criterion: Rubric criterion field name.
        label: Human score.
        predicted: Generated score.
    """

    call_id: str
    criterion: str
    label: int
    predicted: int


class EvaluationReport(BaseModel):
    """Accuracy of generated grades against the human calibration set.

    Attributes:
        n_labeled_calls: Number of calls compared from ``labels.csv``.
        n_compared_scores: Number of criterion scores compared (calls x 5).
        n_correct: Number of exact criterion matches.
        accuracy: Exact-match rate over all criterion scores.
        accuracy_by_criterion: Exact-match rate for each criterion.
        exact_call_match_accuracy: Exact-match rate of the summed total score.
        within_one_level_accuracy: Rate where the absolute error is at most 5.
        disagreements: Criterion-level mismatches.
    """

    n_labeled_calls: int
    n_compared_scores: int
    n_correct: int
    accuracy: float
    accuracy_by_criterion: dict[str, float]
    exact_call_match_accuracy: float
    within_one_level_accuracy: float
    disagreements: list[ScoreDisagreement]
