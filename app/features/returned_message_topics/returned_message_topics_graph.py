from langgraph.graph import END, START, StateGraph

from app.features.returned_message_topics.nodes.analyze_message import (
    create_analyze_message_node,
)
from app.features.returned_message_topics.returned_message_topics_state import (
    ReturnedMessageTopicsState,
)
from app.shared.llm.client.base import LlmClient


def create_returned_message_topics_graph(llm_client: LlmClient):
    builder = StateGraph(ReturnedMessageTopicsState)
    builder.add_node(
        "analyze_message",
        create_analyze_message_node(llm_client),
    )
    builder.add_edge(START, "analyze_message")
    builder.add_edge("analyze_message", END)
    # builder.compile()은 실행 가능한 컴파일된 LangGraph 객체를 반환합니다. 이 객체가 비동기 실행 메서드인 ainvoke()를 제공
    return builder.compile()
