from asyncio.log import logger

import chainlit as cl
from langgraph.types import Command

from riskbot.agent import router_graph


@cl.on_message
async def on_message(msg: cl.Message):
    # Check if the graph has already finished
    if cl.user_session.get("graph_finished"):
        await cl.Message("The conversation has ended.").send()
        return

    # 1) Retrieve the thread_id, if it exists
    thread_id = cl.user_session.get("tid")

    if not thread_id:
        # 2) First turn: start the graph
        stream = router_graph.astream(
            {"question": msg.content},
            {"configurable": {"thread_id": msg.id}},
        )
        # 3) Save the id in the session
        cl.user_session.set("tid", msg.id)
    else:
        # 4) Subsequent turns: resume with Command(resume=...)
        stream = router_graph.astream(
            Command(resume=msg.content),
            {"configurable": {"thread_id": thread_id}},
        )

    # 5) Listen to the event stream
    answer_sent = False
    interrupt_sent = False

    try:
        async for event in stream:
            logger.info(f"Received event: {event}")
            if "__interrupt__" in event and not interrupt_sent:
                await cl.Message(event["__interrupt__"][0].value).send()
                interrupt_sent = True
                continue

            # Search for the answer field in any node of the event
            for _, node_data in event.items():
                if (
                    isinstance(node_data, dict)
                    and "answer" in node_data
                    and node_data["answer"]
                    and not answer_sent
                ):
                    await cl.Message(content=node_data["answer"]).send()
                    # Mark the conversation as finished when we send an answer
                    cl.user_session.set("graph_finished", True)
                    cl.user_session.set("tid", None)
                    answer_sent = True
                    break

            # If both the interruption and the answer have been sent, we can exit
            if interrupt_sent and answer_sent:
                break

    except Exception as e:
        print(f"Error processing stream: {e}")
    finally:
        # Ensure the stream is closed properly
        try:
            await stream.aclose()
        except Exception:
            pass  # Ignore errors when closing
