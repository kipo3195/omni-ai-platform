import asyncio
from typing import Literal

from app.features.ai_task.ai_task_executor import AiTaskExecutor
from app.features.ai_task.ai_task_schemas import AiTaskRequest, ContractModel


class ExampleInput(ContractModel):
    value: str


class ExampleResult(ContractModel):
    echoed: str


class ExampleRequest(AiTaskRequest[ExampleInput]):
    task_type: Literal["EXAMPLE"]
    contract_version: Literal[1]


class ExampleHandler:
    async def execute(
        self,
        execution_id: str,
        tenant_id: str,
        task_input: ExampleInput,
    ) -> ExampleResult:
        return ExampleResult(echoed=f"{tenant_id}:{execution_id}:{task_input.value}")


def test_executor_preserves_common_correlation_and_wraps_typed_result():
    request = ExampleRequest(
        execution_id="execution-1",
        tenant_id="tenant-1",
        task_type="EXAMPLE",
        contract_version=1,
        input=ExampleInput(value="hello"),
    )

    response = asyncio.run(
        AiTaskExecutor[ExampleInput, ExampleResult]().execute(
            request=request,
            handler=ExampleHandler(),
        )
    )

    assert response.model_dump() == {
        "execution_id": "execution-1",
        "task_type": "EXAMPLE",
        "contract_version": 1,
        "status": "SUCCEEDED",
        "result": {
            "echoed": "tenant-1:execution-1:hello",
        },
    }
