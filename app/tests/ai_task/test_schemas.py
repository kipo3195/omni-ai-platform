from typing import Literal

from app.features.ai_task.ai_task_schemas import (
    AiTaskError,
    AiTaskFailureResponse,
    AiTaskSuccessResponse,
    ContractModel,
)


class ExampleResult(ContractModel):
    suggestions: list[str]


class ExampleSuccessResponse(AiTaskSuccessResponse[ExampleResult]):
    task_type: Literal["CONVERSATION_START"]
    contract_version: Literal[1]


class ExampleFailureResponse(AiTaskFailureResponse):
    task_type: Literal["CONVERSATION_START"]
    contract_version: Literal[1]


def test_ai_task_success_response():
    response = ExampleSuccessResponse(
        execution_id="exec-123",
        task_type="CONVERSATION_START",
        contract_version=1,
        result=ExampleResult(
            suggestions=[
                "이번 주말에 어디 갈 계획이야?",
                "요즘 재미있게 본 영화 있어?",
            ],
        ),
    )

    assert response.model_dump() == {
        "execution_id": "exec-123",
        "task_type": "CONVERSATION_START",
        "contract_version": 1,
        "status": "SUCCEEDED",
        "result": {
            "suggestions": [
                "이번 주말에 어디 갈 계획이야?",
                "요즘 재미있게 본 영화 있어?",
            ],
        },
    }


def test_ai_task_failure_response():
    response = ExampleFailureResponse(
        execution_id="exec-123",
        task_type="CONVERSATION_START",
        contract_version=1,
        error=AiTaskError(
            code="AI_GENERATION_FAILED",
            message="Generation failed",
            retryable=True,
        ),
    )

    assert response.model_dump() == {
        "execution_id": "exec-123",
        "task_type": "CONVERSATION_START",
        "contract_version": 1,
        "status": "FAILED",
        "error": {
            "code": "AI_GENERATION_FAILED",
            "message": "Generation failed",
            "retryable": True,
        },
    }
