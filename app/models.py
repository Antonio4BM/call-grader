import os

from langchain_openrouter import ChatOpenRouter  # noqa: E402
from pydantic import SecretStr  # noqa: E402


def build_llm() -> ChatOpenRouter:
    """Create the OpenRouter chat model used by the pipeline.

    The model name can be overridden with ``OPENROUTER_MODEL``. Defaults to
    ``openai/gpt-4o-mini``.

    Returns:
        A configured ``ChatOpenRouter`` instance.

    Raises:
        RuntimeError: If ``OPENROUTER_API_KEY`` is not set.
    """
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise RuntimeError(
            "OPENROUTER_API_KEY is not set. Export it before running "
            "the grader."
        )
    model_name = os.getenv("OPENROUTER_MODEL", "openai/gpt-4o-mini")
    return ChatOpenRouter(
        model=model_name,
        api_key=SecretStr(api_key),
        temperature=0,
        max_retries=2,
        app_title="Call Grader",
    )