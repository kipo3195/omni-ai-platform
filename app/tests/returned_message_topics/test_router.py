from copy import deepcopy
from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.features.returned_message_topics.returned_message_topics_router import (
    create_returned_message_topics_router,
)
from app.features.returned_message_topics.returned_message_topics_schemas import (
    ReturnedMessageTopic,
    ReturnedMessageTopicsResult,
)


VALID_REQUEST = {
    "execution_id": "execution-1",
    "tenant_id": "tenant-1",
    "task_type": "RETURNED_MESSAGE_TOPICS",
    "contract_version": 1,
    "input": {
        "request_id": "request-1",
        "user_id": "user-1",
        "absence_period_id": "period-1",
        "message_selection_ref": "selection-1",
        "selected_items": [
            {
                "source_item_key": "MSG_KEY_1",
                "subject": "업무 보고",
                "sequence": 0,
            }
        ],
    },
}


class FakeReturnedMessageTopicsHandler:
    async def execute(self, execution_id, tenant_id, task_input):
        return ReturnedMessageTopicsResult(
            topics=[
                ReturnedMessageTopic(
                    topic="업무 보고",
                    summary="업무 보고 관련 쪽지입니다.",
                    priority="UNKNOWN",
                    priority_reason="제목만으로 우선순위를 판단하기 어렵습니다.",
                    reply_required=False,
                    reply_reason="명시적인 답변 요청이 없습니다.",
                    action_required=False,
                    action_reason="명시적인 후속 조치 요청이 없습니다.",
                    message_count=1,
                    source_message_refs=["MSG_KEY_1"],
                )
            ],
            generated_at=datetime(2026, 11, 2, tzinfo=timezone.utc),
        )


def create_client() -> TestClient:
    app = FastAPI()
    app.include_router(
        create_returned_message_topics_router(
            FakeReturnedMessageTopicsHandler()
        ),
        prefix="/ai/v1",
    )
    return TestClient(app)


def test_generate_returned_message_topics_accepts_valid_request():
    response = create_client().post(
        "/ai/v1/returned-message-topics/generate",
        json=VALID_REQUEST,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["execution_id"] == "execution-1"
    assert body["task_type"] == "RETURNED_MESSAGE_TOPICS"
    assert body["contract_version"] == 1
    assert body["status"] == "SUCCEEDED"
    assert body["result"]["topics"] == [
        {
            "topic": "업무 보고",
            "summary": "업무 보고 관련 쪽지입니다.",
            "priority": "UNKNOWN",
            "priority_reason": "제목만으로 우선순위를 판단하기 어렵습니다.",
            "reply_required": False,
            "reply_reason": "명시적인 답변 요청이 없습니다.",
            "action_required": False,
            "action_reason": "명시적인 후속 조치 요청이 없습니다.",
            "message_count": 1,
            "source_message_refs": ["MSG_KEY_1"],
        }
    ]
    assert body["result"]["generated_at"] == "2026-11-02T00:00:00Z"


def test_generate_returned_message_topics_rejects_unknown_task_type():
    request = deepcopy(VALID_REQUEST)
    request["task_type"] = "CONVERSATION_START"
    response = create_client().post(
        "/ai/v1/returned-message-topics/generate",
        json=request,
    )
    assert response.status_code == 422


def test_generate_returned_message_topics_rejects_unsupported_contract_version():
    request = deepcopy(VALID_REQUEST)
    request["contract_version"] = 2
    response = create_client().post(
        "/ai/v1/returned-message-topics/generate",
        json=request,
    )
    assert response.status_code == 422


def test_generate_returned_message_topics_requires_selected_items():
    request = deepcopy(VALID_REQUEST)
    request["input"]["selected_items"] = []
    response = create_client().post(
        "/ai/v1/returned-message-topics/generate",
        json=request,
    )
    assert response.status_code == 422


def test_generate_returned_message_topics_allows_nullable_subject():
    request = deepcopy(VALID_REQUEST)
    request["input"]["selected_items"][0]["subject"] = None
    response = create_client().post(
        "/ai/v1/returned-message-topics/generate",
        json=request,
    )
    assert response.status_code == 200


def test_generate_returned_message_topics_rejects_duplicate_source_keys():
    request = deepcopy(VALID_REQUEST)
    request["input"]["selected_items"].append(
        {
            "source_item_key": "MSG_KEY_1",
            "subject": "중복 쪽지",
            "sequence": 1,
        }
    )
    response = create_client().post(
        "/ai/v1/returned-message-topics/generate",
        json=request,
    )
    assert response.status_code == 422


def test_generate_returned_message_topics_rejects_duplicate_sequences():
    request = deepcopy(VALID_REQUEST)
    request["input"]["selected_items"].append(
        {
            "source_item_key": "MSG_KEY_2",
            "subject": "다른 쪽지",
            "sequence": 0,
        }
    )
    response = create_client().post(
        "/ai/v1/returned-message-topics/generate",
        json=request,
    )
    assert response.status_code == 422
