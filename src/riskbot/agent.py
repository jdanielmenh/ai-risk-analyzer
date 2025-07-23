import asyncio
from typing import Any, Protocol, TypeVar

from langgraph.graph import END, START, StateGraph

from riskbot.utils.nodes import intent_router_node
from riskbot.utils.states import RouterState


class AsyncGraph(Protocol):
    async def ainvoke(self, state: Any) -> Any:  # noqa: D401, D403
        ...


GraphT = TypeVar("GraphT", bound=AsyncGraph)


def build_graph() -> GraphT:  # type: ignore[valid-type]
    graph = StateGraph(RouterState)
    graph.add_edge(START, "router")
    graph.add_node("router", intent_router_node)
    graph.set_entry_point("router")
    graph.add_edge("router", END)
    return graph.compile()  # type: ignore[return-value]


router_graph: GraphT = build_graph()
aSyncResult = TypeVar("aSyncResult")


async def run_async(graph: GraphT, state: Any) -> Any:
    return await graph.ainvoke(state)


def run(graph: GraphT, state: Any) -> Any:
    return asyncio.run(run_async(graph, state))


def classify(question: str, graph: GraphT = router_graph) -> str:
    state: RouterState = {"query": question, "router_label": ""}
    result = run(graph, state)
    return result["router_label"]
