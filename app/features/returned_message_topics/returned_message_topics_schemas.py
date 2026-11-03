from datetime import datetime
from enum import Enum
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


class ReturnedMessagePriority(str, Enum):
    LOW = "LOW"
    NORMAL = "NORMAL"
    HIGH = "HIGH"
    URGENT = "URGENT"
    UNKNOWN = "UNKNOWN"


class ReturnedMessageTopic(ContractModel):
    topic: str = Field(min_length=1)
    summary: str = Field(min_length=1)
    priority: ReturnedMessagePriority
    priority_reason: str = Field(min_length=1, max_length=50)
    reply_required: bool
    reply_reason: str = Field(min_length=1, max_length=50)
    action_required: bool
    action_reason: str = Field(min_length=1, max_length=50)
    message_count: int = Field(ge=1)
    source_message_refs: list[str] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_source_message_refs(self) -> "ReturnedMessageTopic":
        unique_refs = set(self.source_message_refs)
        if len(unique_refs) != len(self.source_message_refs):
            raise ValueError("source_message_refs values must be unique")
        if self.message_count != len(unique_refs):
            raise ValueError(
                "message_count must match the number of source_message_refs"
            )
        return self


class ReturnedMessageTopicsAnalysis(ContractModel):
    topics: list[ReturnedMessageTopic] = Field(min_length=1)


class ReturnedMessageTopicsResult(ContractModel):
    topics: list[ReturnedMessageTopic] = Field(min_length=1)
    generated_at: datetime


class ReturnedMessageTopicsSuccessResponse(
    AiTaskSuccessResponse[ReturnedMessageTopicsResult]
):
    task_type: Literal["RETURNED_MESSAGE_TOPICS"]
    contract_version: Literal[1]
