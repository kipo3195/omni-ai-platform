from copy import deepcopy

from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


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


def test_generate_returned_message_topics_accepts_valid_request():
    response = client.post(
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
            "summary": "선택된 쪽지의 Topic 생성을 위한 고정 응답입니다.",
            "priority": "NORMAL",
            "priority_reason": None,
            "message_count": 1,
            "source_message_refs": ["MSG_KEY_1"],
        }
    ]
    assert body["result"]["generated_at"]


def test_generate_returned_message_topics_rejects_unknown_task_type():
    request = deepcopy(VALID_REQUEST)
    request["task_type"] = "CONVERSATION_START"

    response = client.post(
        "/ai/v1/returned-message-topics/generate",
        json=request,
    )

    assert response.status_code == 422


def test_generate_returned_message_topics_rejects_unsupported_contract_version():
    request = deepcopy(VALID_REQUEST)
    request["contract_version"] = 2

    response = client.post(
        "/ai/v1/returned-message-topics/generate",
        json=request,
    )

    assert response.status_code == 422


def test_generate_returned_message_topics_requires_selected_items():
    request = deepcopy(VALID_REQUEST)
    request["input"]["selected_items"] = []

    response = client.post(
        "/ai/v1/returned-message-topics/generate",
        json=request,
    )

    assert response.status_code == 422


def test_generate_returned_message_topics_allows_nullable_subject():
    request = deepcopy(VALID_REQUEST)
    request["input"]["selected_items"][0]["subject"] = None

    response = client.post(
        "/ai/v1/returned-message-topics/generate",
        json=request,
    )

    assert response.status_code == 200
    assert response.json()["result"]["topics"][0]["topic"] == "제목 없음"


def test_generate_returned_message_topics_rejects_duplicate_source_keys():
    request = deepcopy(VALID_REQUEST)
    request["input"]["selected_items"].append(
        {
            "source_item_key": "MSG_KEY_1",
            "subject": "중복 쪽지",
            "sequence": 1,
        }
    )

    response = client.post(
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

    response = client.post(
        "/ai/v1/returned-message-topics/generate",
        json=request,
    )

    assert response.status_code == 422
