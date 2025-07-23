from typing import Any

from models.riskbot_models import IntentResponse
from riskbot.utils.chains import get_router_chain
from riskbot.utils.states import RouterState


async def intent_router_node(state: RouterState) -> RouterState:
    chain = get_router_chain()
    result: IntentResponse = await chain.ainvoke({"query": state.query})
    state.router_label = result.label
    return state
