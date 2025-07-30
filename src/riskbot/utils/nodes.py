from typing import Any

from langgraph.types import interrupt
from models.riskbot_models import IntentResponse
from riskbot.utils.chains import get_router_chain
from riskbot.utils.states import RouterState


async def intent_router_node(state: RouterState) -> RouterState:
    chain = get_router_chain()
    result: IntentResponse = await chain.ainvoke({"question": state.question})
    state.router_label = result.label
    return state


def ask_again_node(state: RouterState) -> RouterState:
    new_question = interrupt("The question is not valid. Please rephrase it:")
    state.question = new_question
    state.router_label = None
    return state


async def planner_node(state: RouterState) -> RouterState:
    state.answer = (
        f"(Dummy) Received: «{state.question}». Here would go the real answer."
    )
    return state
