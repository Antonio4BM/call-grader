from pathlib import Path  # noqa: E402

from langchain_core.prompts import ChatPromptTemplate  # noqa: E402
from langchain_core.runnables import Runnable, RunnableLambda  # noqa: E402

from app.prompts import SYSTEM_PROMPT, HUMAN_PROMPT  # noqa: E402
from app.models import build_llm  # noqa: E402
from app.schemas import CallGrade, TranscriptInput  # noqa: E402
from app.documents import retrieve_rubric  # noqa: E402


def build_prompt_inputs(
    inputs: TranscriptInput,
    rubric_context: str,
) -> dict[str, str]:
    """Assemble prompt variables from a transcript and retrieved rubric.

    Args:
        inputs: Call identifier and transcript text.
        rubric_context: Rubric document stuffed into the prompt.

    Returns:
        Mapping with ``call_id``, ``transcript``, and ``rubric``.
    """
    return {
        "call_id": inputs["call_id"],
        "transcript": inputs["transcript"],
        "rubric": rubric_context,
    }

def build_chain(rubric_text: str, rubric_path: Path) -> Runnable:
    """Build the retrieve-augment-generate grading chain.

    Retrieved rubric context is stuffed into the prompt. The LLM returns a
    structured ``CallGrade``.

    Args:
        rubric_text: Contents of ``rubric.md`` used as RAG context.

    Returns:
        A LangChain runnable that accepts ``call_id`` and ``transcript``
        and returns a ``CallGrade``.
    """
    rubric_context = retrieve_rubric(rubric_text, rubric_path)
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", SYSTEM_PROMPT),
            ("human", HUMAN_PROMPT),
        ]
    )
    structured_llm = build_llm().with_structured_output(
        CallGrade,
        method="json_schema",
        strict=True,
    )
    def fill_prompt_inputs(inputs: TranscriptInput) -> dict[str, str]:
        """Bind the retrieved rubric onto one transcript's prompt variables.

        Args:
            inputs: Call identifier and transcript text.

        Returns:
            Mapping of variables expected by the chat prompt.
        """
        return build_prompt_inputs(inputs, rubric_context)

    return RunnableLambda(fill_prompt_inputs) | prompt | structured_llm