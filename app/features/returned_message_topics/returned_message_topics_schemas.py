from datetime import datetime
from typing import Literal

from pydantic import Field, model_validator

from app.features.ai_task.ai_task_schemas import (
    AiTaskRequest,
    AiTaskSuccessResponse,
    ContractModel,
)


class ReturnedMessageSelectedItem(ContractModel):
    source_item_key: str = Field(min_length=1)
    subject: str | None = None
    sequence: int = Field(ge=0)


class ReturnedMessageTopicsInput(ContractModel):
    request_id: str = Field(min_length=1)
    user_id: str = Field(min_length=1)
    absence_period_id: str = Field(min_length=1)
    message_selection_ref: str = Field(min_length=1)
    selected_items: list[ReturnedMessageSelectedItem] = Field(
        min_length=1,
        max_length=30,
    )

    @model_validator(mode="after")
    def validate_selected_items(self) -> "ReturnedMessageTopicsInput":
        source_keys = [item.source_item_key for item in self.selected_items]
        if len(source_keys) != len(set(source_keys)):
            raise ValueError("selected_items source_item_key values must be unique")

        sequences = [item.sequence for item in self.selected_items]
        if len(sequences) != len(set(sequences)):
            raise ValueError("selected_items sequence values must be unique")
        return self


class ReturnedMessageTopicsRequest(AiTaskRequest[ReturnedMessageTopicsInput]):
    task_type: Literal["RETURNED_MESSAGE_TOPICS"]
    contract_version: Literal[1]


class ReturnedMessageTopic(ContractModel):
    topic: str = Field(min_length=1)
    summary: str = Field(min_length=1)
    priority: Literal["LOW", "NORMAL", "HIGH", "URGENT"]
    priority_reason: str | None = None
    message_count: int = Field(ge=1)
    source_message_refs: list[str] = Field(min_length=1)


class ReturnedMessageTopicsResult(ContractModel):
    topics: list[ReturnedMessageTopic]
    generated_at: datetime


class ReturnedMessageTopicsSuccessResponse(
    AiTaskSuccessResponse[ReturnedMessageTopicsResult]
):
    task_type: Literal["RETURNED_MESSAGE_TOPICS"]
    contract_version: Literal[1]
