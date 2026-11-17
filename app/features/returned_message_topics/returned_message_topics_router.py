from fastapi import APIRouter, Header, HTTPException, Response, status

from app.features.returned_message_topics.mariadb_execution_repository import (
    ExecutionConflictError,
)
from app.features.returned_message_topics.execution_service import (
    ReturnedMessageTopicsExecutionService,
)
from app.features.returned_message_topics.returned_message_topics_schemas import (
    ReturnedMessageTopicsExecutionResponse,
    ReturnedMessageTopicsRequest,
)
from app.features.returned_message_topics.trace import trace_info


def create_returned_message_topics_router(
    execution_service: ReturnedMessageTopicsExecutionService,
) -> APIRouter:
    router = APIRouter(
        prefix="/returned-message-topics",
        tags=["returned-message-topics"],
    )

    @router.post(
        "/generate",
        response_model=ReturnedMessageTopicsExecutionResponse,
        status_code=status.HTTP_202_ACCEPTED,
    )
    async def generate_returned_message_topics(
        request: ReturnedMessageTopicsRequest,
        response: Response,
        x_tenant_id: str = Header(alias="X-Tenant-Id"),
    ) -> ReturnedMessageTopicsExecutionResponse:
        if x_tenant_id != request.tenant_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="tenant scope does not match request",
            )
        trace_info(
            "request_received",
            execution_id=request.execution_id,
            request_id=request.input.request_id,
            selected_item_count=len(request.input.selected_items),
            tenant_id=request.tenant_id,
        )
        try:
            execution = execution_service.accept(request)
        except ExecutionConflictError as exception:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="execution_id request fingerprint does not match",
            ) from exception

        response.status_code = (
            status.HTTP_202_ACCEPTED
            if execution.status in {"ACCEPTED", "RUNNING"}
            else status.HTTP_200_OK
        )
        trace_info(
            "request_accepted",
            execution_id=request.execution_id,
            request_id=request.input.request_id,
            status=execution.status,
        )
        return execution

    @router.get(
        "/executions/{execution_id}",
        response_model=ReturnedMessageTopicsExecutionResponse,
    )
    async def get_returned_message_topics_execution(
        execution_id: str,
        x_tenant_id: str = Header(alias="X-Tenant-Id"),
    ) -> ReturnedMessageTopicsExecutionResponse:
        execution = execution_service.find(x_tenant_id, execution_id)
        if execution is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="execution was not found",
            )
        return execution

    return router
