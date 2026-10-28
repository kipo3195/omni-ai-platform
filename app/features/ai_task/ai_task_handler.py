from typing import Generic, Protocol

from app.features.ai_task.ai_task_schemas import InputT, ResultT


class AiTaskHandler(Protocol, Generic[InputT, ResultT]):
    async def execute(
        self,
        execution_id: str,
        tenant_id: str,
        task_input: InputT,
    ) -> ResultT:
        ...
