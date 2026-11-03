import asyncio
import json

import pytest
from pydantic import ValidationError

from app.features.returned_message_topics.nodes.analyze_message import (
    create_analyze_message_node,
)
from app.features.returned_message_topics.returned_message_topics_schemas import (
    ReturnedMessageSelectedItem,
    ReturnedMessageTopic,
    ReturnedMessageTopicsInput,
)
from app.features.returned_message_topics.returned_message_topics_state import (
    ReturnedMessageTopicsState,
)
from app.shared.llm.model.response import LlmResponse


class FakeLlmClient:
    def __init__(self, content: dict):
        self.content = content
        self.requests = []

    async def generate(self, request):
        self.requests.append(request)
        return LlmResponse(
            content=json.dumps(self.content, ensure_ascii=False),
            model="fake-model",
        )


def make_state() -> ReturnedMessageTopicsState:
    return ReturnedMessageTopicsState(
        execution_id="execution-1",
        tenant_id="tenant-1",
        task_input=ReturnedMessageTopicsInput(
            request_id="request-1",
            user_id="user-1",
            absence_period_id="period-1",
            message_selection_ref="selection-1",
            selected_items=[
                ReturnedMessageSelectedItem(
                    source_item_key="message-2",
                    subject="  배포   일정 확인  ",
                    sequence=1,
                ),
                ReturnedMessageSelectedItem(
                    source_item_key="message-1",
                    subject="배포 일정 회신 요청",
                    sequence=0,
                ),
            ],
        ),
    )


def valid_analysis() -> dict:
    return {
        "topics": [
            {
                "topic": "배포 일정",
                "summary": "배포 일정 확인과 회신이 필요합니다.",
                "priority": "UNKNOWN",
                "priority_reason": "제목에 긴급도나 기한이 드러나지 않습니다.",
                "reply_required": True,
                "reply_reason": "회신 요청이 제목에 명시되어 있습니다.",
                "action_required": True,
                "action_reason": "배포 일정 확인 요청이 포함되어 있습니다.",
                "message_count": 2,
                "source_message_refs": ["message-1", "message-2"],
            }
        ]
    }


def test_analyze_message_calls_llm_once_with_strict_structured_output():
    llm_client = FakeLlmClient(valid_analysis())
    node = create_analyze_message_node(llm_client)
    result = asyncio.run(node(make_state()))

    assert len(llm_client.requests) == 1
    request = llm_client.requests[0]
    assert request.temperature == 0.1
    assert request.response_format["type"] == "json_schema"
    assert request.response_format["json_schema"]["strict"] is True
    payload = json.loads(request.messages[1].content)
    assert payload["messages"] == [
        {
            "source_message_ref": "message-1",
            "subject": "배포 일정 회신 요청",
            "sequence": 0,
        },
        {
            "source_message_ref": "message-2",
            "subject": "배포 일정 확인",
            "sequence": 1,
        },
    ]
    assert result["analysis_result"].topics[0].priority == "UNKNOWN"


def test_analyze_message_rejects_unknown_source_reference():
    response = valid_analysis()
    response["topics"][0]["source_message_refs"] = ["message-1", "unknown"]
    llm_client = FakeLlmClient(response)
    with pytest.raises(ValueError, match="unknown source_message_refs"):
        asyncio.run(create_analyze_message_node(llm_client)(make_state()))


def test_analyze_message_rejects_missing_source_reference():
    response = valid_analysis()
    response["topics"][0]["source_message_refs"] = ["message-1"]
    response["topics"][0]["message_count"] = 1
    llm_client = FakeLlmClient(response)
    with pytest.raises(ValueError, match="missing source_message_refs"):
        asyncio.run(create_analyze_message_node(llm_client)(make_state()))


def test_topic_rejects_reason_longer_than_50_characters():
    with pytest.raises(ValidationError):
        ReturnedMessageTopic(
            topic="배포 일정",
            summary="배포 일정 확인이 필요합니다.",
            priority="UNKNOWN",
            priority_reason="가" * 51,
            reply_required=False,
            reply_reason="답변 요청이 없습니다.",
            action_required=True,
            action_reason="일정 확인이 필요합니다.",
            message_count=1,
            source_message_refs=["message-1"],
        )


def test_topic_requires_message_count_to_match_source_references():
    with pytest.raises(ValidationError, match="message_count must match"):
        ReturnedMessageTopic(
            topic="배포 일정",
            summary="배포 일정 확인이 필요합니다.",
            priority="NORMAL",
            priority_reason="일반적인 일정 확인 요청입니다.",
            reply_required=False,
            reply_reason="답변 요청이 없습니다.",
            action_required=True,
            action_reason="일정 확인이 필요합니다.",
            message_count=2,
            source_message_refs=["message-1"],
        )
