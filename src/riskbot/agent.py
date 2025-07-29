from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph

from riskbot.utils.nodes import ask_again_node, intent_router_node, planner_node
from riskbot.utils.states import RouterState


def build_graph() -> StateGraph:
    g = StateGraph(RouterState)

    # Nodes
    g.add_node("router", intent_router_node)
    g.add_node("ask_again", ask_again_node)
    g.add_node("planner", planner_node)

    g.add_conditional_edges(
        "router",
        lambda s: s.router_label,
        {"VALID": "planner", "INVALID": "ask_again"},
    )

    g.add_edge(START, "router")
    g.add_edge("ask_again", "router")
    g.add_edge("planner", END)
    return g.compile(checkpointer=InMemorySaver())


router_graph: StateGraph = build_graph()


def classify(question: str, graph: StateGraph = router_graph) -> str:
    state: RouterState = {"question": question, "router_label": ""}
    result = graph.astream(state)
    return result["router_label"]
