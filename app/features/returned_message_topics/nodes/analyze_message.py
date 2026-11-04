import json
from time import monotonic

from app.features.returned_message_topics.prompts.analyze_message_prompt import (
    SYSTEM_PROMPT,
)
from app.features.returned_message_topics.returned_message_topics_schemas import (
    ReturnedMessageTopicsAnalysis,
)
from app.features.returned_message_topics.returned_message_topics_state import (
    ReturnedMessageTopicsState,
)
from app.features.returned_message_topics.trace import (
    trace_development,
    trace_exception,
    trace_info,
)
from app.shared.llm.client.base import LlmClient
from app.shared.llm.model.request import LlmMessage, LlmRequest


def create_analyze_message_node(llm_client: LlmClient):
    async def analyze_message(
        state: ReturnedMessageTopicsState,
    ) -> dict[str, ReturnedMessageTopicsAnalysis]:
        started_at = monotonic()
        selected_items = sorted(
            state.task_input.selected_items,
            key=lambda item: item.sequence,
        )
        source_refs = {item.source_item_key for item in selected_items}

        trace_info(
            "llm_analysis_started",
            execution_id=state.execution_id,
            message_count=len(selected_items),
            request_id=state.task_input.request_id,
        )

        user_payload = json.dumps(
            {
                "messages": [
                    {
                        "source_message_ref": item.source_item_key,
                        "subject": _normalize_subject(item.subject),
                        "sequence": item.sequence,
                    }
                    for item in selected_items
                ]
            },
            ensure_ascii=False,
        )

        llm_request = LlmRequest(
            messages=[
                LlmMessage(role="system", content=SYSTEM_PROMPT),
                LlmMessage(role="user", content=user_payload),
            ],
            temperature=0.1,
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "returned_message_topics_analysis",
                    "strict": True,
                    "schema": ReturnedMessageTopicsAnalysis.model_json_schema(),
                },
            },
            max_tokens=4000,
        )
        trace_development(
            "llm_prompt_payload",
            execution_id=state.execution_id,
            max_tokens=llm_request.max_tokens,
            messages=[
                {
                    "role": message.role,
                    "content": message.content,
                }
                for message in llm_request.messages
            ],
            request_id=state.task_input.request_id,
            response_format=llm_request.response_format,
            temperature=llm_request.temperature,
        )

        try:
            response = await llm_client.generate(llm_request)
            trace_development(
                "llm_raw_response_payload",
                content=response.content,
                execution_id=state.execution_id,
                model=response.model,
                request_id=state.task_input.request_id,
                usage=response.usage,
            )

            analysis = ReturnedMessageTopicsAnalysis.model_validate_json(
                response.content
            )
            _validate_source_references(analysis, source_refs)
            trace_development(
                "llm_validated_result_payload",
                execution_id=state.execution_id,
                request_id=state.task_input.request_id,
                result=analysis.model_dump(mode="json"),
            )
        except Exception as exc:
            trace_exception(
                "llm_analysis_failed",
                elapsed_ms=int((monotonic() - started_at) * 1000),
                error_type=type(exc).__name__,
                execution_id=state.execution_id,
                request_id=state.task_input.request_id,
            )
            raise

        trace_info(
            "llm_analysis_completed",
            elapsed_ms=int((monotonic() - started_at) * 1000),
            execution_id=state.execution_id,
            model=response.model,
            request_id=state.task_input.request_id,
            topic_count=len(analysis.topics),
        )

        return {"analysis_result": analysis}

    return analyze_message  # 함수 자체를 반환
    # return analyze_message(...) 함수를 실행한 결과를 반환


def _normalize_subject(subject: str | None) -> str | None:
    if subject is None:
        return None
    normalized = " ".join(subject.split())
    return normalized or None


def _validate_source_references(
    analysis: ReturnedMessageTopicsAnalysis,
    expected_refs: set[str],
) -> None:
    analyzed_refs: set[str] = set()

    for topic in analysis.topics:
        topic_refs = set(topic.source_message_refs)
        unknown_refs = topic_refs - expected_refs
        if unknown_refs:
            raise ValueError(
                "LLM result contains unknown source_message_refs: "
                f"{sorted(unknown_refs)}"
            )

        duplicated_refs = analyzed_refs & topic_refs
        if duplicated_refs:
            raise ValueError(
                "LLM result assigns source_message_refs to multiple topics: "
                f"{sorted(duplicated_refs)}"
            )
        analyzed_refs.update(topic_refs)

    missing_refs = expected_refs - analyzed_refs
    if missing_refs:
        raise ValueError(
            "LLM result is missing source_message_refs: "
            f"{sorted(missing_refs)}"
        )
