from app.features.returned_message_topics.returned_message_topics_graph import (
    create_returned_message_topics_graph,
)
from app.features.returned_message_topics.returned_message_topics_handler import (
    ReturnedMessageTopicsHandler,
)
from app.shared.llm.client.base import LlmClient


def create_returned_message_topics_handler(
    llm_client: LlmClient,
) -> ReturnedMessageTopicsHandler:
    return ReturnedMessageTopicsHandler(
        runner=create_returned_message_topics_graph(llm_client),
    )
