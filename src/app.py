from utils.config import load_required_env_vars

# Load environment variables from .env file before anything else
load_required_env_vars()

import chainlit as cl
from riskbot.agent import router_graph
from riskbot.utils.states import ConversationState


@cl.on_chat_start
async def on_chat_start():
    cl.user_session.set("graph", router_graph)


@cl.on_message
async def on_message(message: cl.Message):
    graph = cl.user_session.get("graph")
    # The state must be a dictionary for LangGraph
    state: ConversationState = {"question": message.content}  # type: ignore
    # Configurable dictionary with a thread_id is required for the checkpointer
    config = {"configurable": {"thread_id": cl.user_session.get("id")}}

    response_message = cl.Message(content="")
    await response_message.send()

    full_response = ""
    # Pass the config to the astream method
    async for event in graph.astream(state, config=config):
        if "reasoner" in event:
            answer = event["reasoner"].get("answer", "")
            if answer:
                full_response += answer
                response_message.content = full_response
                await response_message.update()

    response_message.content = full_response
    await response_message.update()
