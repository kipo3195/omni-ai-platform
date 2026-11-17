import hashlib
import json
import re
import time
import uuid
from contextlib import contextmanager
from dataclasses import dataclass
from urllib.parse import parse_qs, unquote, urlparse

import pymysql
from pymysql.cursors import DictCursor

from app.features.returned_message_topics.returned_message_topics_schemas import (
    ReturnedMessageTopicsRequest,
)


TASK_TYPE = "RETURNED_MESSAGE_TOPICS"
CONTRACT_VERSION = 2


class ExecutionConflictError(RuntimeError):
    pass


@dataclass(frozen=True)
class ExecutionRecord:
    tenant_id: str
    execution_id: str
    request_id: str
    request_payload: str
    request_fingerprint: str
    status: str
    result_payload: str | None
    error_payload: str | None


@dataclass(frozen=True)
class OutboxRecord:
    event_id: str
    tenant_id: str
    execution_id: str
    request_id: str
    payload: str
    attempt_count: int


@dataclass(frozen=True)
class MariaDbConnectionSettings:
    host: str
    port: int
    database: str
    username: str
    password: str
    charset: str


class MariaDbReturnedMessageTopicsExecutionRepository:
    def __init__(
        self,
        *,
        datasource_url: str,
        username: str,
        password: str,
        table_prefix: str = "",
    ):
        self._settings = _parse_datasource_url(
            datasource_url,
            username,
            password,
        )
        self._table_prefix = _validate_table_prefix(table_prefix)
        self._execution_table = (
            f"{self._table_prefix}returned_message_topics_execution"
        )
        self._outbox_table = (
            f"{self._table_prefix}returned_message_topics_callback_outbox"
        )
        self._foreign_key_name = (
            f"fk_{self._table_prefix}rmt_callback_execution"
        )
        self._initialize()

    def accept(
        self,
        request: ReturnedMessageTopicsRequest,
    ) -> tuple[ExecutionRecord, bool]:
        request_payload = _canonical_json(request.model_dump(mode="json"))
        request_fingerprint = hashlib.sha256(
            request_payload.encode("utf-8")
        ).hexdigest()
        now = time.time()

        try:
            with self._connection() as connection:
                connection.begin()
                with connection.cursor() as cursor:
                    existing = self._find_with_cursor(
                        cursor,
                        request.tenant_id,
                        request.execution_id,
                        for_update=True,
                    )
                    if existing is not None:
                        if existing.request_fingerprint != request_fingerprint:
                            raise ExecutionConflictError(
                                "execution_id is already associated with "
                                "another request"
                            )
                        connection.commit()
                        return existing, False

                    cursor.execute(
                        f"""
                        INSERT INTO {self._execution_table} (
                            tenant_id,
                            execution_id,
                            request_id,
                            request_payload,
                            request_fingerprint,
                            status,
                            accepted_at,
                            created_at,
                            updated_at
                        ) VALUES (%s, %s, %s, %s, %s, 'ACCEPTED', %s, %s, %s)
                        """,
                        (
                            request.tenant_id,
                            request.execution_id,
                            request.input.request_id,
                            request_payload,
                            request_fingerprint,
                            now,
                            now,
                            now,
                        ),
                    )
                connection.commit()
        except pymysql.IntegrityError:
            existing = self.find(request.tenant_id, request.execution_id)
            if existing is None:
                raise
            if existing.request_fingerprint != request_fingerprint:
                raise ExecutionConflictError(
                    "execution_id is already associated with another request"
                )
            return existing, False

        record = self.find(request.tenant_id, request.execution_id)
        if record is None:
            raise RuntimeError("accepted execution could not be reloaded")
        return record, True

    def find(self, tenant_id: str, execution_id: str) -> ExecutionRecord | None:
        with self._connection() as connection, connection.cursor() as cursor:
            return self._find_with_cursor(cursor, tenant_id, execution_id)

    def find_recoverable(self) -> list[tuple[str, str]]:
        now = time.time()
        with self._connection() as connection, connection.cursor() as cursor:
            cursor.execute(
                f"""
                SELECT tenant_id, execution_id
                FROM {self._execution_table}
                WHERE status = 'ACCEPTED'
                   OR (status = 'RUNNING'
                       AND (lease_until IS NULL OR lease_until <= %s))
                ORDER BY created_at, tenant_id, execution_id
                """,
                (now,),
            )
            rows = cursor.fetchall()
        return [(row["tenant_id"], row["execution_id"]) for row in rows]

    def claim_execution(
        self,
        tenant_id: str,
        execution_id: str,
        owner: str,
        lease_seconds: float,
    ) -> bool:
        now = time.time()
        with self._connection() as connection, connection.cursor() as cursor:
            cursor.execute(
                f"""
                UPDATE {self._execution_table}
                SET status = 'RUNNING',
                    started_at = COALESCE(started_at, %s),
                    worker_owner = %s,
                    lease_until = %s,
                    updated_at = %s
                WHERE tenant_id = %s
                  AND execution_id = %s
                  AND (status = 'ACCEPTED'
                    OR (status = 'RUNNING'
                        AND (lease_until IS NULL OR lease_until <= %s)))
                """,
                (
                    now,
                    owner,
                    now + lease_seconds,
                    now,
                    tenant_id,
                    execution_id,
                    now,
                ),
            )
            claimed = cursor.rowcount == 1
            connection.commit()
            return claimed

    def complete_success(
        self,
        tenant_id: str,
        execution_id: str,
        owner: str,
        result_payload: dict[str, object],
        callback_payload: dict[str, object],
    ) -> bool:
        return self._complete(
            tenant_id=tenant_id,
            execution_id=execution_id,
            owner=owner,
            status="SUCCEEDED",
            result_payload=_canonical_json(result_payload),
            error_payload=None,
            callback_payload=callback_payload,
        )

    def complete_failure(
        self,
        tenant_id: str,
        execution_id: str,
        owner: str,
        error_payload: dict[str, object],
        callback_payload: dict[str, object],
    ) -> bool:
        return self._complete(
            tenant_id=tenant_id,
            execution_id=execution_id,
            owner=owner,
            status="FAILED",
            result_payload=None,
            error_payload=_canonical_json(error_payload),
            callback_payload=callback_payload,
        )

    def claim_due_outbox(
        self,
        owner: str,
        lease_seconds: float,
    ) -> OutboxRecord | None:
        now = time.time()
        with self._connection() as connection:
            connection.begin()
            with connection.cursor() as cursor:
                cursor.execute(
                    f"""
                    SELECT event_id, tenant_id, execution_id, request_id,
                           payload, attempt_count
                    FROM {self._outbox_table}
                    WHERE (status = 'PENDING' AND next_attempt_at <= %s)
                       OR (status = 'IN_FLIGHT' AND lease_until <= %s)
                    ORDER BY next_attempt_at, created_at, event_id
                    LIMIT 1
                    FOR UPDATE
                    """,
                    (now, now),
                )
                row = cursor.fetchone()
                if row is None:
                    connection.commit()
                    return None

                cursor.execute(
                    f"""
                    UPDATE {self._outbox_table}
                    SET status = 'IN_FLIGHT',
                        worker_owner = %s,
                        lease_until = %s,
                        updated_at = %s
                    WHERE event_id = %s
                    """,
                    (owner, now + lease_seconds, now, row["event_id"]),
                )
            connection.commit()
            return OutboxRecord(
                event_id=row["event_id"],
                tenant_id=row["tenant_id"],
                execution_id=row["execution_id"],
                request_id=row["request_id"],
                payload=row["payload"],
                attempt_count=row["attempt_count"],
            )

    def mark_outbox_delivered(self, event_id: str, owner: str) -> None:
        now = time.time()
        with self._connection() as connection, connection.cursor() as cursor:
            cursor.execute(
                f"""
                UPDATE {self._outbox_table}
                SET status = 'DELIVERED',
                    delivered_at = %s,
                    worker_owner = NULL,
                    lease_until = NULL,
                    updated_at = %s
                WHERE event_id = %s
                  AND status = 'IN_FLIGHT'
                  AND worker_owner = %s
                """,
                (now, now, event_id, owner),
            )
            connection.commit()

    def reschedule_outbox(
        self,
        event_id: str,
        owner: str,
        delay_seconds: float,
        last_error: str,
        max_attempts: int,
    ) -> None:
        now = time.time()
        with self._connection() as connection, connection.cursor() as cursor:
            cursor.execute(
                f"""
                UPDATE {self._outbox_table}
                SET status = CASE
                        WHEN attempt_count + 1 >= %s THEN 'DEAD_LETTER'
                        ELSE 'PENDING'
                    END,
                    attempt_count = attempt_count + 1,
                    next_attempt_at = %s,
                    worker_owner = NULL,
                    lease_until = NULL,
                    last_error = %s,
                    updated_at = %s
                WHERE event_id = %s
                  AND status = 'IN_FLIGHT'
                  AND worker_owner = %s
                """,
                (
                    max_attempts,
                    now + delay_seconds,
                    last_error[:500],
                    now,
                    event_id,
                    owner,
                ),
            )
            connection.commit()

    def _complete(
        self,
        *,
        tenant_id: str,
        execution_id: str,
        owner: str,
        status: str,
        result_payload: str | None,
        error_payload: str | None,
        callback_payload: dict[str, object],
    ) -> bool:
        now = time.time()
        event_id = str(uuid.uuid4())
        callback_payload = dict(callback_payload)
        callback_payload["eventId"] = event_id

        with self._connection() as connection:
            connection.begin()
            with connection.cursor() as cursor:
                cursor.execute(
                    f"""
                    SELECT request_id
                    FROM {self._execution_table}
                    WHERE tenant_id = %s
                      AND execution_id = %s
                      AND status = 'RUNNING'
                      AND worker_owner = %s
                    FOR UPDATE
                    """,
                    (tenant_id, execution_id, owner),
                )
                row = cursor.fetchone()
                if row is None:
                    connection.commit()
                    return False

                cursor.execute(
                    f"""
                    UPDATE {self._execution_table}
                    SET status = %s,
                        result_payload = %s,
                        error_payload = %s,
                        worker_owner = NULL,
                        lease_until = NULL,
                        completed_at = %s,
                        updated_at = %s
                    WHERE tenant_id = %s
                      AND execution_id = %s
                      AND status = 'RUNNING'
                      AND worker_owner = %s
                    """,
                    (
                        status,
                        result_payload,
                        error_payload,
                        now,
                        now,
                        tenant_id,
                        execution_id,
                        owner,
                    ),
                )
                if cursor.rowcount != 1:
                    connection.rollback()
                    return False

                cursor.execute(
                    f"""
                    INSERT INTO {self._outbox_table} (
                        event_id,
                        tenant_id,
                        execution_id,
                        request_id,
                        payload,
                        status,
                        attempt_count,
                        next_attempt_at,
                        created_at,
                        updated_at
                    ) VALUES (%s, %s, %s, %s, %s, 'PENDING', 0, %s, %s, %s)
                    """,
                    (
                        event_id,
                        tenant_id,
                        execution_id,
                        row["request_id"],
                        _canonical_json(callback_payload),
                        now,
                        now,
                        now,
                    ),
                )
            connection.commit()
            return True

    def _find_with_cursor(
        self,
        cursor,
        tenant_id: str,
        execution_id: str,
        *,
        for_update: bool = False,
    ) -> ExecutionRecord | None:
        lock_clause = " FOR UPDATE" if for_update else ""
        cursor.execute(
            f"""
            SELECT tenant_id, execution_id, request_id, request_payload,
                   request_fingerprint, status, result_payload, error_payload
            FROM {self._execution_table}
            WHERE tenant_id = %s AND execution_id = %s{lock_clause}
            """,
            (tenant_id, execution_id),
        )
        row = cursor.fetchone()
        if row is None:
            return None
        return ExecutionRecord(
            tenant_id=row["tenant_id"],
            execution_id=row["execution_id"],
            request_id=row["request_id"],
            request_payload=row["request_payload"],
            request_fingerprint=row["request_fingerprint"],
            status=row["status"],
            result_payload=row["result_payload"],
            error_payload=row["error_payload"],
        )

    @contextmanager
    def _connection(self):
        connection = pymysql.connect(
            host=self._settings.host,
            port=self._settings.port,
            user=self._settings.username,
            password=self._settings.password,
            database=self._settings.database,
            charset=self._settings.charset,
            autocommit=False,
            cursorclass=DictCursor,
            connect_timeout=5,
            read_timeout=10,
            write_timeout=10,
        )
        try:
            yield connection
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def _initialize(self) -> None:
        statements = (
            f"""
            CREATE TABLE IF NOT EXISTS {self._execution_table} (
                tenant_id VARCHAR(191) NOT NULL,
                execution_id VARCHAR(191) NOT NULL,
                request_id VARCHAR(191) NOT NULL,
                request_payload LONGTEXT NOT NULL,
                request_fingerprint CHAR(64) NOT NULL,
                status VARCHAR(32) NOT NULL,
                result_payload LONGTEXT NULL,
                error_payload LONGTEXT NULL,
                worker_owner VARCHAR(64) NULL,
                lease_until DOUBLE NULL,
                accepted_at DOUBLE NULL,
                started_at DOUBLE NULL,
                completed_at DOUBLE NULL,
                created_at DOUBLE NOT NULL,
                updated_at DOUBLE NOT NULL,
                PRIMARY KEY (tenant_id, execution_id),
                KEY idx_rmt_execution_status (status, lease_until, updated_at)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
              COLLATE=utf8mb4_unicode_ci
            """,
            f"""
            CREATE TABLE IF NOT EXISTS {self._outbox_table} (
                event_id CHAR(36) NOT NULL,
                tenant_id VARCHAR(191) NOT NULL,
                execution_id VARCHAR(191) NOT NULL,
                request_id VARCHAR(191) NOT NULL,
                payload LONGTEXT NOT NULL,
                status VARCHAR(32) NOT NULL,
                attempt_count INT NOT NULL,
                next_attempt_at DOUBLE NOT NULL,
                worker_owner VARCHAR(64) NULL,
                lease_until DOUBLE NULL,
                last_error VARCHAR(500) NULL,
                created_at DOUBLE NOT NULL,
                delivered_at DOUBLE NULL,
                updated_at DOUBLE NOT NULL,
                PRIMARY KEY (event_id),
                KEY idx_rmt_outbox_due (
                    status, next_attempt_at, lease_until
                ),
                CONSTRAINT {self._foreign_key_name}
                    FOREIGN KEY (tenant_id, execution_id)
                    REFERENCES {self._execution_table} (
                        tenant_id, execution_id
                    )
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
              COLLATE=utf8mb4_unicode_ci
            """,
        )
        with self._connection() as connection, connection.cursor() as cursor:
            for statement in statements:
                cursor.execute(statement)
            connection.commit()


def _parse_datasource_url(
    datasource_url: str,
    username: str,
    password: str,
) -> MariaDbConnectionSettings:
    raw_url = datasource_url.strip()
    if raw_url.startswith("jdbc:"):
        raw_url = raw_url[5:]
    parsed = urlparse(raw_url)
    if parsed.scheme not in {"mariadb", "mysql"}:
        raise ValueError(
            "DATASOURCE_URL must use jdbc:mariadb:// or mariadb://"
        )
    database = unquote(parsed.path.lstrip("/"))
    effective_username = username or unquote(parsed.username or "")
    effective_password = password or unquote(parsed.password or "")
    if not parsed.hostname or not database or not effective_username:
        raise ValueError(
            "DATASOURCE_URL, DATASOURCE_USERNAME and database are required"
        )
    query = parse_qs(parsed.query)
    charset = query.get("characterEncoding", ["utf8mb4"])[0]
    if charset.lower().replace("-", "") == "utf8":
        charset = "utf8mb4"
    return MariaDbConnectionSettings(
        host=parsed.hostname,
        port=parsed.port or 3306,
        database=database,
        username=effective_username,
        password=effective_password,
        charset=charset,
    )


def _validate_table_prefix(value: str) -> str:
    if len(value) > 20 or re.fullmatch(r"[A-Za-z0-9_]*", value) is None:
        raise ValueError("table_prefix must contain only letters, digits or underscore")
    return value


def _canonical_json(value: object) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )
