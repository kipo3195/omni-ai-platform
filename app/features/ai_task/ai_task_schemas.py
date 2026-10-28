from typing import Generic, Literal, TypeVar

from pydantic import BaseModel, ConfigDict, Field


class ContractModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


InputT = TypeVar("InputT", bound=ContractModel)
ResultT = TypeVar("ResultT", bound=ContractModel)


class AiTaskRequest(ContractModel, Generic[InputT]):
    execution_id: str = Field(min_length=1)
    tenant_id: str = Field(min_length=1)
    task_type: str = Field(min_length=1)
    contract_version: int = Field(ge=1)
    input: InputT


class AiTaskResponse(ContractModel):
    execution_id: str = Field(min_length=1)
    task_type: str = Field(min_length=1)
    contract_version: int = Field(ge=1)


class AiTaskAcceptedResponse(AiTaskResponse):
    status: Literal["ACCEPTED"] = "ACCEPTED"


class AiTaskSuccessResponse(AiTaskResponse, Generic[ResultT]):
    status: Literal["SUCCEEDED"] = "SUCCEEDED"
    result: ResultT


class AiTaskError(ContractModel):
    code: str = Field(min_length=1)
    message: str = Field(min_length=1)
    retryable: bool


class AiTaskFailureResponse(AiTaskResponse):
    status: Literal["FAILED"] = "FAILED"
    error: AiTaskError
