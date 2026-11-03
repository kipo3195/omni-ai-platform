from datetime import datetime, timezone
from time import monotonic

from app.features.returned_message_topics.ports import ReturnedMessageTopicsRunner
from app.features.returned_message_topics.returned_message_topics_schemas import (
    ReturnedMessageTopicsAnalysis,
    ReturnedMessageTopicsInput,
    ReturnedMessageTopicsResult,
)
from app.features.returned_message_topics.returned_message_topics_state import (
    ReturnedMessageTopicsState,
)
from app.features.returned_message_topics.trace import trace_info

# AITaskExecutor에 주입한 Handler
# API 호출시 Handler의 execute가 실행되는구조.
# 이 Handler는 runner를 가지며, runner는 ainvoke를 실행하는데 ainvoke는 LangGraph의 내장메소드이므로 실행가능하다.
class ReturnedMessageTopicsHandler:
    def __init__(self, runner: ReturnedMessageTopicsRunner):
        self.runner = runner

    async def execute(
        self,
        execution_id: str,
        tenant_id: str,
        task_input: ReturnedMessageTopicsInput,
    ) -> ReturnedMessageTopicsResult:
        started_at = monotonic()
        trace_info(
            "graph_invocation_started",
            execution_id=execution_id,
            request_id=task_input.request_id,
            selected_item_count=len(task_input.selected_items),
        )

        # ReturnedMessageTopicsHandler가 LangGraph의 구체적인 클래스에 직접 의존하지 않도록 경계
        graph_result = await self.runner.ainvoke(
            ReturnedMessageTopicsState(
                execution_id=execution_id,
                tenant_id=tenant_id,
                task_input=task_input,
            )
        )
        trace_info(
            "graph_invocation_completed",
            elapsed_ms=int((monotonic() - started_at) * 1000),
            execution_id=execution_id,
            has_analysis_result=graph_result.get("analysis_result") is not None,
            request_id=task_input.request_id,
        )
        analysis = ReturnedMessageTopicsAnalysis.model_validate(
            graph_result.get("analysis_result")
        )

        return ReturnedMessageTopicsResult(
            topics=analysis.topics,
            generated_at=datetime.now(timezone.utc),
        )
