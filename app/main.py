"""RAG pipeline that grades call transcripts against the QA rubric."""

from __future__ import annotations

import json
import logging
import os
import sys
import time
from collections.abc import Iterator
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if __package__ in {None, ""}:
    sys.path.insert(0, str(PROJECT_ROOT))

from langchain_core.runnables import Runnable  # noqa: E402
from openrouter.errors import (  # noqa: E402
    BadGatewayResponseError,
    InternalServerResponseError,
    ResponseValidationError,
    ServiceUnavailableResponseError,
    TooManyRequestsResponseError,
)

from app.evaluation import EvaluationReport, calculate_accuracy  # noqa: E402
from app.pipeline import build_chain  # noqa: E402
from app.schemas import CallGrade, GradedCall  # noqa: E402

TRANSCRIPTS_DIR = PROJECT_ROOT / "data" / "transcripts"
RUBRIC_PATH = PROJECT_ROOT / "rubric.md"
RESULTS_PATH = PROJECT_ROOT / "results" / "grades.json"
REPORT_PATH = PROJECT_ROOT / "results" / "report.json"

_TRANSIENT_HTTP_ERRORS = (
    BadGatewayResponseError,
    InternalServerResponseError,
    ServiceUnavailableResponseError,
    TooManyRequestsResponseError,
)


def iter_transcripts(
    directory: Path = TRANSCRIPTS_DIR,
) -> Iterator[tuple[str, str]]:
    """Yield call IDs and transcript text, one file at a time.

    Transcripts are processed in sorted filename order.

    Args:
        directory: Directory containing ``C*.txt`` transcript files.

    Yields:
        Pairs of ``(call_id, transcript_text)``, for example
        ``("C001", "...")``.

    Raises:
        FileNotFoundError: If the directory is missing or has no transcripts.
    """
    if not directory.is_dir():
        raise FileNotFoundError(f"Transcripts directory not found: {directory}")
    paths = sorted(directory.glob("C*.txt"))
    if not paths:
        raise FileNotFoundError(f"No transcripts found in {directory}")
    for path in paths:
        yield path.stem, path.read_text(encoding="utf-8")


def is_transient_error(exc: BaseException) -> bool:
    """Return whether an OpenRouter failure is worth retrying.

    The SDK sometimes returns HTTP 200 with an error body such as
    ``Upstream overloaded`` (code 502). That surfaces as
    ``ResponseValidationError`` instead of a typed 502.

    Args:
        exc: Exception raised while invoking the grader chain.

    Returns:
        True when a later retry may succeed.
    """
    if isinstance(exc, _TRANSIENT_HTTP_ERRORS):
        return True
    if isinstance(exc, ResponseValidationError):
        blob = f"{exc} {getattr(exc, 'body', '')}".lower()
        return any(
            token in blob
            for token in ("overload", "502", "503", "429", "rate limit")
        )
    return False


def grade_transcript(
    chain: Runnable,
    call_id: str,
    transcript: str,
) -> GradedCall:
    """Grade a single transcript with the RAG chain.

    Transient OpenRouter failures (overloaded upstream, 429, 5xx) are
    retried with exponential backoff.

    Args:
        chain: Compiled RAG pipeline.
        call_id: Transcript identifier taken from the filename.
        transcript: Full transcript text.

    Returns:
        Structured scores, justifications, and the total for the call.

    Raises:
        TypeError: If the chain does not return a ``CallGrade``.
        RuntimeError: If every retry is exhausted on a transient error.
    """
    max_attempts = int(os.getenv("OPENROUTER_MAX_ATTEMPTS", "6"))
    last_error: BaseException | None = None
    for attempt in range(max_attempts):
        try:
            grade = chain.invoke(
                {"call_id": call_id, "transcript": transcript}
            )
            if not isinstance(grade, CallGrade):
                raise TypeError(
                    "Expected CallGrade from the grader, got "
                    f"{type(grade).__name__}: {grade!r}"
                )
            return GradedCall.from_grade(call_id, grade)
        except Exception as exc:
            last_error = exc
            if not is_transient_error(exc) or attempt >= max_attempts - 1:
                break
            logger.warning(
                "Transient error on %s; retrying in 5 seconds "
                "(attempt %s/%s): %s",
                call_id,
                attempt + 1,
                max_attempts,
                exc,
            )
            time.sleep(5)
    if last_error is not None and is_transient_error(last_error):
        raise RuntimeError(
            f"OpenRouter stayed overloaded while grading {call_id}. "
        ) from last_error
    if last_error is not None:
        raise last_error
    raise RuntimeError(f"Failed to grade {call_id} with no captured error.")


def run_pipeline(
    transcripts_dir: Path = TRANSCRIPTS_DIR,
    rubric_path: Path = RUBRIC_PATH,
) -> list[GradedCall]:
    """Grade every transcript in the data directory.

    Args:
        transcripts_dir: Directory of ``C*.txt`` files.
        rubric_path: Path to ``rubric.md``.

    Returns:
        A list of graded calls in filename order.
    """
    if not rubric_path.is_file():
        raise FileNotFoundError(f"Rubric not found: {rubric_path}")
    rubric_text = rubric_path.read_text(encoding="utf-8")
    chain = build_chain(rubric_text, rubric_path)
    results: list[GradedCall] = []
    for call_id, transcript in iter_transcripts(transcripts_dir):
        try:
            graded = grade_transcript(chain, call_id, transcript)
        except Exception:
            if results:
                dump_grades(results)
                logger.error(
                    "Stopped at %s after %s grades; partial results "
                    "written to %s",
                    call_id,
                    len(results),
                    RESULTS_PATH,
                )
            raise
        results.append(graded)
        dump_grades(results)
        logger.info("Graded %s (total=%s)", call_id, graded.total)
    return results


def dump_grades(
    results: list[GradedCall],
    path: Path = RESULTS_PATH,
) -> None:
    """Write graded calls to ``results/grades.json``.

    The ``results`` directory is created if it does not exist.

    Args:
        results: Graded transcripts in filename order.
        path: Destination JSON file.

    Returns:
        The path that was written.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = [item.model_dump() for item in results]
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def dump_report(
    report: EvaluationReport,
    path: Path = REPORT_PATH,
) -> None:
    """Write the evaluation report to ``results/report.json``.

    Args:
        report: Evaluation report from ``calculate_accuracy``.
        path: Destination JSON file.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(report.model_dump(), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    """Run the RAG grader, dump grades, then evaluate against labels."""
    try:
        results = run_pipeline()
        payload = [item.model_dump() for item in results]
        logger.info("%s", json.dumps(payload, ensure_ascii=False, indent=2))
    except Exception:
        logger.error("Failed to complete the pipeline")
    report = calculate_accuracy(results_path=RESULTS_PATH)
    logger.info(
        "Exact-match accuracy: %.2f%% (%s/%s criterion scores)",
        report.accuracy * 100,
        report.n_correct,
        report.n_compared_scores,
    )
    logger.info(
        "Within-one-level accuracy: %.2f%% | exact call match accuracy: %.2f%%",
        report.within_one_level_accuracy * 100,
        report.exact_call_match_accuracy * 100,
    )
    logger.info(
        "%s",
        json.dumps(report.model_dump(), indent=2, ensure_ascii=False),
    )
    dump_report(report)


if __name__ == "__main__":
    main()
