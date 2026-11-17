from app.features.returned_message_topics.returned_message_topics_graph import (
    create_returned_message_topics_graph,
)
from app.features.returned_message_topics.returned_message_topics_handler import (
    ReturnedMessageTopicsHandler,
)
from app.features.returned_message_topics.mariadb_execution_repository import (
    MariaDbReturnedMessageTopicsExecutionRepository,
)
from app.features.returned_message_topics.execution_service import (
    ReturnedMessageTopicsExecutionService,
)
from app.shared.llm.client.base import LlmClient


def create_returned_message_topics_handler(
    llm_client: LlmClient,
) -> ReturnedMessageTopicsHandler:
    return ReturnedMessageTopicsHandler(
        runner=create_returned_message_topics_graph(llm_client),
    )


def create_returned_message_topics_execution_service(
    *,
    handler: ReturnedMessageTopicsHandler,
    datasource_url: str,
    datasource_username: str,
    datasource_password: str,
    worker_count: int,
    execution_lease_seconds: float,
    recovery_poll_interval_seconds: float,
    callback_base_url: str,
    callback_timeout_seconds: float,
    callback_poll_interval_seconds: float,
    callback_max_attempts: int,
) -> ReturnedMessageTopicsExecutionService:
    return ReturnedMessageTopicsExecutionService(
        repository=MariaDbReturnedMessageTopicsExecutionRepository(
            datasource_url=datasource_url,
            username=datasource_username,
            password=datasource_password,
        ),
        handler=handler,
        worker_count=worker_count,
        execution_lease_seconds=execution_lease_seconds,
        recovery_poll_interval_seconds=recovery_poll_interval_seconds,
        callback_base_url=callback_base_url,
        callback_timeout_seconds=callback_timeout_seconds,
        callback_poll_interval_seconds=callback_poll_interval_seconds,
        callback_max_attempts=callback_max_attempts,
    )
