from langgraph.types import interrupt

from clients.fmp_client import FMPClient
from models.fmp_models import FreeRiskAPI
from models.riskbot_models import ExecutionPlan, IntentResponse
from riskbot.utils.chains import get_planner_chain, get_reasoner_chain, get_router_chain
from riskbot.utils.states import ConversationState


async def intent_router_node(state: ConversationState) -> ConversationState:
    chain = get_router_chain()
    result: IntentResponse = await chain.ainvoke({"question": state.question})
    state.router_label = result.label
    return state


def ask_again_node(state: ConversationState) -> ConversationState:
    new_question = interrupt("The question is not valid. Please rephrase it:")
    state.question = new_question
    state.router_label = None
    return state


async def planner_node(state: ConversationState) -> ConversationState:
    """
    Planner node that analyzes the question and creates an execution plan
    with the necessary FMP API calls to answer the user's question about market risk.
    """
    chain = get_planner_chain()
    execution_plan: ExecutionPlan = await chain.ainvoke({"question": state.question})

    # Store the execution plan in state
    state.execution_plan = execution_plan
    return state


async def executor_node(state: ConversationState) -> ConversationState:
    """
    Executor node that makes the actual API calls based on the execution plan.
    """
    if not state.execution_plan:
        raise ValueError("No execution plan found in state")

    # Preserve any existing results (e.g., from document_retriever)
    api_results = dict(state.api_results or {})

    async with FMPClient() as client:
        for i, api_call in enumerate(state.execution_plan.api_calls):
            try:
                # Get the API enum (expects the enum member name, e.g., "ECONOMICS_CALENDAR")
                api_enum = FreeRiskAPI[api_call.endpoint]

                # Format the URL template with provided params
                fmt_params = {k: str(v) for k, v in api_call.params.items()}
                path = api_enum.value.format(**fmt_params)

                # Make the API call
                result = await client._fmp_get(path)

                # Store result with a descriptive key
                result_key = f"{api_call.endpoint.lower()}_{i}"
                api_results[result_key] = {
                    "endpoint": api_call.endpoint,
                    "params": api_call.params,
                    "purpose": api_call.purpose,
                    "data": result,
                }

            except KeyError as e:
                # Missing format parameter or bad enum name
                result_key = f"{api_call.endpoint.lower()}_{i}_error"
                api_results[result_key] = {
                    "endpoint": api_call.endpoint,
                    "params": api_call.params,
                    "purpose": api_call.purpose,
                    "error": f"Missing parameter for endpoint template: {e}",
                }
            except Exception as e:
                # Store error information
                result_key = f"{api_call.endpoint.lower()}_{i}_error"
                api_results[result_key] = {
                    "endpoint": api_call.endpoint,
                    "params": api_call.params,
                    "purpose": api_call.purpose,
                    "error": str(e),
                }

    # Merge API results with any previously stored results
    state.api_results = api_results
    return state


async def reasoner_node(state: ConversationState) -> ConversationState:
    """
    Reasoner node that analyzes the API results and provides a comprehensive answer
    to the user's question about market risk.
    """
    if not state.execution_plan or not state.api_results:
        state.answer = "I apologize, but I couldn't gather the necessary data to answer your question."
        return state

    chain = get_reasoner_chain()

    # Prepare context for the reasoner
    context = {
        "question": state.question,
        "execution_plan": state.execution_plan.model_dump(),
        "api_results": state.api_results,
        "document_results": state.api_results.get("document_search", {})
        if state.api_results
        else {},
    }

    try:
        result = await chain.ainvoke(context)
        # Format the structured response into a readable answer
        answer_parts = [
            f"**Direct Answer:** {result.direct_answer}",
            f"**Supporting Analysis:** {result.supporting_analysis}",
        ]

        if result.current_position:
            answer_parts.append(f"**Current Position:** {result.current_position}")

        if result.potential_impact:
            answer_parts.append(f"**Potential Impact:** {result.potential_impact}")

        state.answer = "\n\n".join(answer_parts)
    except Exception as e:
        state.answer = f"I encountered an error while analyzing the data: {str(e)}"

    return state
