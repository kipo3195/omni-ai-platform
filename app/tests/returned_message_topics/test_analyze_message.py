import asyncio
import json

import pytest
from pydantic import ValidationError

from app.features.returned_message_topics.nodes.analyze_message import (
    create_analyze_message_node,
)
from app.features.returned_message_topics.returned_message_topics_schemas import (
    ReturnedMessageAssessment,
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
                "source_message_refs": ["message-1", "message-2"],
            }
        ],
        "message_assessments": [
            {
                "message_ref": "message-1",
                "priority": "NORMAL",
                "priority_reason": "일반적인 배포 일정 회신 요청입니다.",
                "reply_required": True,
                "reply_reason": "회신 요청이 명시되어 있습니다.",
                "action_required": False,
                "action_reason": "명시적인 작업 요청이 없습니다.",
            },
            {
                "message_ref": "message-2",
                "priority": "NORMAL",
                "priority_reason": "일반적인 배포 일정 확인 요청입니다.",
                "reply_required": False,
                "reply_reason": "명시적인 회신 요청이 없습니다.",
                "action_required": True,
                "action_reason": "배포 일정 확인을 요청했습니다.",
            },
        ],
    }


def test_analyze_message_calls_llm_once_with_strict_structured_output():
    llm_client = FakeLlmClient(valid_analysis())
    node = create_analyze_message_node(llm_client)
    result = asyncio.run(node(make_state()))

    assert len(llm_client.requests) == 1
    request = llm_client.requests[0]
    assert request.temperature == 0.1
    assert request.max_tokens == 8000
    assert request.response_format["type"] == "json_schema"
    assert request.response_format["json_schema"]["strict"] is True
    assert (
        request.response_format["json_schema"]["name"]
        == "returned_message_topics_analysis_v2"
    )
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
    assert result["analysis_result"].topics[0].topic == "배포 일정"
    assert result["analysis_result"].message_assessments[0].priority == "NORMAL"


def test_analyze_message_rejects_unknown_source_reference():
    response = valid_analysis()
    response["topics"][0]["source_message_refs"] = ["message-1", "unknown"]
    llm_client = FakeLlmClient(response)
    with pytest.raises(ValueError, match="contains unknown message references"):
        asyncio.run(create_analyze_message_node(llm_client)(make_state()))


def test_analyze_message_rejects_missing_source_reference():
    response = valid_analysis()
    response["topics"][0]["source_message_refs"] = ["message-1"]
    llm_client = FakeLlmClient(response)
    with pytest.raises(ValueError, match="is missing message references"):
        asyncio.run(create_analyze_message_node(llm_client)(make_state()))


def test_analyze_message_rejects_duplicate_topic_reference():
    response = valid_analysis()
    response["topics"].append(
        {
            "topic": "다른 토픽",
            "summary": "중복 검증을 위한 토픽입니다.",
            "source_message_refs": ["message-1"],
        }
    )
    llm_client = FakeLlmClient(response)
    with pytest.raises(ValueError, match="contains duplicate message references"):
        asyncio.run(create_analyze_message_node(llm_client)(make_state()))


def test_analyze_message_rejects_unknown_assessment_reference():
    response = valid_analysis()
    response["message_assessments"][1]["message_ref"] = "unknown"
    llm_client = FakeLlmClient(response)
    with pytest.raises(ValueError, match="contains unknown message references"):
        asyncio.run(create_analyze_message_node(llm_client)(make_state()))


def test_analyze_message_rejects_missing_assessment_reference():
    response = valid_analysis()
    response["message_assessments"] = response["message_assessments"][:1]
    llm_client = FakeLlmClient(response)
    with pytest.raises(ValueError, match="is missing message references"):
        asyncio.run(create_analyze_message_node(llm_client)(make_state()))


def test_analyze_message_rejects_duplicate_assessment_reference():
    response = valid_analysis()
    response["message_assessments"][1]["message_ref"] = "message-1"
    llm_client = FakeLlmClient(response)
    with pytest.raises(ValueError, match="contains duplicate message references"):
        asyncio.run(create_analyze_message_node(llm_client)(make_state()))


def test_assessment_rejects_reason_longer_than_50_characters():
    with pytest.raises(ValidationError):
        ReturnedMessageAssessment(
            message_ref="message-1",
            priority="UNKNOWN",
            priority_reason="가" * 51,
            reply_required=False,
            reply_reason="답변 요청이 없습니다.",
            action_required=True,
            action_reason="일정 확인이 필요합니다.",
        )


def test_topic_rejects_duplicate_source_references():
    with pytest.raises(
        ValidationError,
        match="source_message_refs values must be unique",
    ):
        ReturnedMessageTopic(
            topic="배포 일정",
            summary="배포 일정 확인이 필요합니다.",
            source_message_refs=["message-1", "message-1"],
        )
