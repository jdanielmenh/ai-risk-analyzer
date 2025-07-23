import gradio as gr

from riskbot.agent import classify
from utils.logging_utils import setup_logging

logger = setup_logging(__name__)


def respond(
    message: str, history: list[tuple[str, str]]
) -> tuple[str, list[tuple[str, str]]]:
    """Takes the user's message, runs the classifier, and updates the chat history."""
    label = classify(message)
    history.append((message, label))
    return "", history


with gr.Blocks(title="RiskBot Router Tester") as demo:
    gr.Markdown("""
    # RiskBot Chatbot Tester
    Enter a question and the model will return the corresponding *router_label*.
    """)

    chatbot = gr.Chatbot()

    with gr.Row():
        msg = gr.Textbox(
            placeholder="How can I help you?",
            label="Your question",
            scale=4,
        )
        send = gr.Button("Send")

    msg.submit(respond, [msg, chatbot], [msg, chatbot])
    send.click(respond, [msg, chatbot], [msg, chatbot])

if __name__ == "__main__":
    logger.info("Initializing RiskBot Router Tester...")
    demo.launch()
