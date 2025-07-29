from functools import lru_cache

from langchain.callbacks.base import Callbacks
from langchain_openai import ChatOpenAI

from utils.config import LLMSettings


@lru_cache(maxsize=1)
def get_llm(
    settings: LLMSettings | None = None, callbacks: Callbacks | None = None
) -> ChatOpenAI:
    """Return a *singleton* ChatOpenAI client.

    * We memoise it with ``lru_cache`` so every node in the LangGraph shares the
      same underlying HTTP session, drastically reducing connection overhead as
      the graph grows.
    * ``settings`` can be injected for testing or to run temporary overrides.
    * ``callbacks`` lets you plug tracing/streaming without touching the core.
    """

    if settings is None:
        settings = LLMSettings()

    return ChatOpenAI(
        model=settings.openai_model,
        temperature=settings.openai_temperature,
        max_tokens=settings.openai_max_tokens,
        request_timeout=settings.openai_request_timeout,
        callbacks=callbacks,
    )
