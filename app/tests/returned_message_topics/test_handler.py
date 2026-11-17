import asyncio

from app.features.returned_message_topics.returned_message_topics_handler import (
    ReturnedMessageTopicsHandler,
)
from app.features.returned_message_topics.returned_message_topics_schemas import (
    ReturnedMessageSelectedItem,
    ReturnedMessageTopicsInput,
)


class FakeRunner:
    async def ainvoke(self, state):
        return {
            "analysis_result": {
                "topics": [
                    {
                        "topic": "운영 점검",
                        "summary": "운영 점검 체크리스트 업데이트 요청입니다.",
                        "source_message_refs": ["message-1"],
                    }
                ],
                "message_assessments": [
                    {
                        "message_ref": "message-1",
                        "priority": "HIGH",
                        "priority_reason": "마감이 명시된 요청입니다.",
                        "reply_required": False,
                        "reply_reason": "명시적인 회신 요청이 없습니다.",
                        "action_required": True,
                        "action_reason": "체크리스트 업데이트 요청입니다.",
                    }
                ],
            }
        }


def test_handler_adds_generated_at_to_analysis_result():
    result = asyncio.run(
        ReturnedMessageTopicsHandler(FakeRunner()).execute(
            execution_id="execution-1",
            tenant_id="tenant-1",
            task_input=ReturnedMessageTopicsInput(
                request_id="request-1",
                user_id="user-1",
                absence_period_id="period-1",
                message_selection_ref="selection-1",
                selected_items=[
                    ReturnedMessageSelectedItem(
                        source_item_key="message-1",
                        subject="운영 점검 체크리스트 업데이트 요청",
                        sequence=0,
                    )
                ],
            ),
        )
    )

    assert result.topics[0].source_message_refs == ["message-1"]
    assert result.message_assessments[0].message_ref == "message-1"
    assert result.generated_at.tzinfo is not None
