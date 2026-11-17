# Returned Message Topics Callback Delivery

Status: Implemented baseline

이 문서는 Omni AI Server가 terminal execution 결과를 AI Orchestrator에 전달하는 callback outbox와 retry 규칙을 정의한다. Callback은 정상 결과 전달 경로이고 Orchestrator status polling은 유실과 장기 지연을 복구하는 별도 안전망이다.

## Delivery guarantee

Callback은 at-least-once delivery를 제공한다.

- 결과 callback을 가능한 한 빠르게 전달한다.
- Network timeout과 retryable server failure에서 같은 event를 재전송한다.
- 중복 callback은 허용하며 Orchestrator가 `eventId`와 `executionId`로 멱등 처리한다.
- exactly-once network delivery를 주장하지 않는다.

## Outbox write

Workflow terminal transaction에서 execution result와 outbox event를 함께 저장한다.

```text
execution.status = SUCCEEDED | FAILED | CANCELLED
execution.result 또는 error 저장
callback_outbox.status = PENDING
commit
```

Callback을 먼저 전송하고 acknowledgement 이후 처음 결과를 저장하지 않는다. 이 순서는 callback 성공 직전 process가 종료될 때 authoritative result가 사라질 수 있다.

## Suggested outbox record

```text
event_id
tenant_id
execution_id
request_id
event_type
payload
status: PENDING | IN_FLIGHT | DELIVERED | DEAD_LETTER
attempt_count
next_attempt_at
worker_owner
lease_until
last_status_code
last_error_code
created_at
delivered_at
updated_at
```

`event_id`는 immutable하고 unique하다. Callback retry마다 새 event ID를 만들지 않는다.

## Delivery worker

Callback worker는 due PENDING event를 bounded batch로 claim하고 외부 HTTP 호출 중 DB transaction을 유지하지 않는다.

```text
PENDING claim
→ IN_FLIGHT와 lease 기록
→ transaction 종료
→ Orchestrator callback POST
→ 결과에 따라 DELIVERED 또는 retry 예약
```

Worker가 callback 2xx를 받은 뒤 DELIVERED 저장 전에 종료되면 같은 event가 다시 전송될 수 있다. Orchestrator는 이미 처리한 event를 2xx로 acknowledgement해야 한다.

## Response classification

| Callback 관찰 결과 | 처리 |
| --- | --- |
| 2xx | 결과가 durable하게 반영됐거나 이미 처리됨, `DELIVERED` |
| timeout / connection failure | 결과 불확실, backoff 후 같은 event 재전송 |
| 408 / 429 / 5xx | retryable, backoff와 jitter 적용 |
| 400 / 422 | callback contract 오류, 제한된 retry 후 운영 확인 |
| 401 / 403 | 인증 또는 권한 설정 오류, 빠른 운영 경보와 제한된 retry |
| 404 | request correlation 또는 배포 순서 문제, 무제한 retry하지 않고 운영 확인 |
| 409 | 기존 결과와 충돌, 자동 덮어쓰기 금지 |

정확한 retry budget과 backoff 값은 운영 SLO로 정한다. Retry 횟수만 소진했다고 execution result를 삭제하지 않는다.

## Callback acknowledgement meaning

Orchestrator의 2xx는 최소한 다음을 의미한다.

- 서비스 인증과 tenant scope 검증 완료
- request ID와 execution ID correlation 검증 완료
- terminal 결과가 durable lifecycle에 반영됨, 또는 같은 결과가 이미 반영됨

단순히 callback body를 메모리에 수신했다는 이유로 2xx를 반환하지 않는다.

## Idempotency and ordering

Orchestrator는 다음 입력을 안전하게 처리해야 한다.

```text
같은 eventId의 중복 callback
같은 executionId terminal result의 다른 delivery attempt
polling 결과가 먼저 반영된 뒤 도착한 callback
callback이 먼저 반영된 뒤 수행된 polling
terminal 상태 이후 도착한 오래된 RUNNING 관찰
```

같은 execution ID에 서로 다른 terminal payload가 도착하면 기존 결과를 덮어쓰지 않고 correlation conflict로 처리한다.

## Interaction with reconciliation

Outbox retry와 Orchestrator polling은 서로 대체하지 않는다.

```text
Omni AI callback worker
→ 발신 측 delivery 유실 복구

AI Orchestrator reconciliation worker
→ callback 장기 지연, Orchestrator 재시작 또는 callback 경로 장애 복구
```

Polling이 terminal result를 먼저 반영해도 이후 callback은 idempotent 2xx를 받아 outbox가 DELIVERED로 종료될 수 있어야 한다.

## Security and data handling

- Callback은 service-to-service 인증을 사용한다.
- Tenant를 URL 또는 body 값만으로 신뢰하지 않는다.
- Credential, stack trace와 내부 provider error를 callback payload에 포함하지 않는다.
- Outbox payload는 terminal result를 포함하므로 execution result와 같은 보존·암호화·삭제 정책을 적용한다.

## Operations

최소한 다음 지표와 경보를 제공한다.

```text
PENDING outbox count와 oldest age
callback attempt/success/failure count
callback latency
retry status code distribution
DEAD_LETTER count
execution terminal 이후 callback delivered까지의 시간
```

Dead-letter event는 수동 재전송 전에 Orchestrator가 이미 polling으로 결과를 반영했는지 확인한다.

## Remaining implementation gaps

현재 baseline은 terminal result와 outbox event를 MariaDB transaction 하나로 저장하고, `FOR UPDATE SKIP LOCKED`로 due event를 claim한다. 동일 `eventId`를 최대 설정 횟수까지 exponential backoff로 재전송한 뒤 `DEAD_LETTER`로 전환한다. 운영 배포 전에는 status code별 retry budget/jitter, service-to-service 인증, 지표·경보와 dead-letter 조회/재전송 도구가 필요하다.
