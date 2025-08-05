from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph

from riskbot.utils.nodes import (
    ask_again_node,
    executor_node,
    intent_router_node,
    planner_node,
    reasoner_node,
)
from riskbot.utils.states import ConversationState


def build_graph() -> StateGraph:
    g = StateGraph(ConversationState)

    # Nodes
    g.add_node("router", intent_router_node)
    g.add_node("ask_again", ask_again_node)
    g.add_node("planner", planner_node)
    g.add_node("executor", executor_node)
    g.add_node("reasoner", reasoner_node)

    g.add_conditional_edges(
        "router",
        lambda s: s.router_label,
        {"VALID": "planner", "INVALID": "ask_again"},
    )

    g.add_edge(START, "router")
    g.add_edge("ask_again", "router")
    g.add_edge("planner", "executor")
    g.add_edge("executor", "reasoner")
    g.add_edge("reasoner", END)
    return g.compile(checkpointer=InMemorySaver())


router_graph: StateGraph = build_graph()


def classify(question: str, graph: StateGraph = router_graph) -> str:
    state: ConversationState = {"question": question, "router_label": ""}
    result = graph.astream(state)
    return result["router_label"]
