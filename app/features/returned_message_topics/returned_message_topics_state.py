from pydantic import BaseModel, ConfigDict

from app.features.returned_message_topics.returned_message_topics_schemas import (
    ReturnedMessageTopicsAnalysis,
    ReturnedMessageTopicsInput,
)


class ReturnedMessageTopicsState(BaseModel):
    model_config = ConfigDict(extra="forbid")

    execution_id: str
    tenant_id: str
    task_input: ReturnedMessageTopicsInput
    analysis_result: ReturnedMessageTopicsAnalysis | None = None
