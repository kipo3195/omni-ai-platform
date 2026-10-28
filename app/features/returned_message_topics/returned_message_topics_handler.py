from datetime import datetime, timezone

from app.features.returned_message_topics.returned_message_topics_schemas import (
    ReturnedMessageTopic,
    ReturnedMessageTopicsInput,
    ReturnedMessageTopicsResult,
)


class ReturnedMessageTopicsHandler:
    async def execute(
        self,
        execution_id: str,
        tenant_id: str,
        task_input: ReturnedMessageTopicsInput,
    ) -> ReturnedMessageTopicsResult:
        topics = [
            ReturnedMessageTopic(
                topic=item.subject or "제목 없음",
                summary="선택된 쪽지의 Topic 생성을 위한 고정 응답입니다.",
                priority="NORMAL",
                priority_reason=None,
                message_count=1,
                source_message_refs=[item.source_item_key],
            )
            for item in sorted(task_input.selected_items, key=lambda item: item.sequence)
        ]
        return ReturnedMessageTopicsResult(
            topics=topics,
            generated_at=datetime.now(timezone.utc),
        )
