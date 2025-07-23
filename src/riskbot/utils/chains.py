from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from jinja2 import Environment, FileSystemLoader
from langchain.output_parsers import PydanticOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableSequence

from models.riskbot_models import IntentResponse  # noqa: F401
from utils.llm import get_llm

_TEMPLATES_DIR = Path(__file__).parent / "prompts"
_env = Environment(
    loader=FileSystemLoader(_TEMPLATES_DIR),
    autoescape=False,
    trim_blocks=True,
    lstrip_blocks=True,
)


@lru_cache(maxsize=1)
def get_router_chain() -> RunnableSequence:
    template_text, *_ = _env.loader.get_source(_env, "intent_router_prompt.j2")

    llm = get_llm()
    parser = PydanticOutputParser(pydantic_object=IntentResponse)
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", template_text + "\n\n{format_instructions}"),
            ("user", "{query}"),
        ]
    ).partial(format_instructions=parser.get_format_instructions())

    return prompt | llm | parser
