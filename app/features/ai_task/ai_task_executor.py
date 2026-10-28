from typing import Generic

from app.features.ai_task.ai_task_handler import AiTaskHandler
from app.features.ai_task.ai_task_schemas import (
    AiTaskRequest,
    AiTaskSuccessResponse,
    InputT,
    ResultT,
)


class AiTaskExecutor(Generic[InputT, ResultT]):
    async def execute(
        self,
        request: AiTaskRequest[InputT],
        handler: AiTaskHandler[InputT, ResultT],
    ) -> AiTaskSuccessResponse[ResultT]:
        result = await handler.execute(
            execution_id=request.execution_id,
            tenant_id=request.tenant_id,
            task_input=request.input,
        )
        return AiTaskSuccessResponse[ResultT](
            execution_id=request.execution_id,
            task_type=request.task_type,
            contract_version=request.contract_version,
            result=result,
        )
