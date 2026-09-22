from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_chat_suggestions_generate_recent_context():
    response = client.post(
        "/ai/v1/chat/suggestions/generate",
        json={
            "session_id": "session-1",
            "user_id": "user-1",
            "room_id": "room-1",
            "suggestion_type": "RECENT_CONTEXT",
            "messages": [
                {
                    "sender_id": "user-2",
                    "sender_name": "Kim",
                    "content": "오늘 배포 일정 어떻게 되나요?",
                    "sent_at": "2026-08-19T10:00:00",
                }
            ],
            "options": {
                "max_suggestions": 2,
                "max_length": 80,
                "language": "ko",
            },
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "session_id": "session-1",
        "suggestions": [
            {
                "topic": "배포 일정",
                "question": "배포 일정 관련해서 진행 상황은 어떠세요?",
            },
            {
                "topic": "배포 일정",
                "question": "배포 일정 관련해서 추가로 확인할 내용 있을까요?",
            },
        ],
    }
