from langchain_core.documents import Document  # noqa: E402
from pathlib import Path


def retrieve_rubric(rubric_text: str, rubric_path: Path) -> list[Document]:
    """Retrieve the rubric document that will be stuffed into the prompt.

    The rubric is small and every criterion must be scored, so the retriever
    returns the full document rather than a subset of chunks.

    Args:
        rubric_text: Contents of ``rubric.md``.

    Returns:
        A single-document list used as RAG context.
    """
    documents = [
        Document(
            page_content=rubric_text,
            metadata={"source": str(rubric_path)},
        )
    ]
    return "\n\n".join(document.page_content for document in documents)