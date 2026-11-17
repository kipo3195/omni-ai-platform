# Returned Message Topics Asynchronous API Contract

Status: Implemented baseline

이 문서는 Returned Message Topics contract version 2를 durable asynchronous execution으로 제공하기 위한 HTTP 계약을 정의한다. Topic과 message assessment의 상세 result schema는 [README](README.md)를 따른다.

## Common rules

- AI Orchestrator가 `execution_id`를 생성한다.
- 모든 start, status query와 callback은 같은 `tenant_id + execution_id`를 사용한다.
- Omni AI API wire field는 `snake_case`를 사용한다.
- `task_type`은 `RETURNED_MESSAGE_TOPICS`, `contract_version`은 숫자 `2`다.
- `202 Accepted`는 실행 접수만 의미하며 LLM 성공을 의미하지 않는다.
- Omni AI Server는 tenant 범위를 body와 trusted service identity 또는 `X-Tenant-Id`로 검증한다.

## Start execution

```http
POST /ai/v1/returned-message-topics/generate
Content-Type: application/json
Accept: application/json
X-Tenant-Id: tenant-1
```

Request body는 README의 v2 request schema를 사용한다.

### First acceptance

Omni AI Server는 execution record와 durable execution queue 등록을 완료한 뒤 응답한다.

```http
HTTP/1.1 202 Accepted
```

```json
{
  "execution_id": "c2fcb430-54d2-4753-a4d5-6576dd24dbd1",
  "task_type": "RETURNED_MESSAGE_TOPICS",
  "contract_version": 2,
  "status": "ACCEPTED"
}
```

Execution record 또는 queue 등록을 내구성 있게 완료하지 못하면 202를 반환하지 않는다.

### Duplicate start

Start는 `tenant_id + execution_id`에 대해 멱등하다. Omni AI Server는 최초 immutable request의 canonical fingerprint를 저장한다.

| 기존 실행 | 같은 immutable request | 응답 |
| --- | --- | --- |
| 없음 | 해당 없음 | 실행 생성 후 `202 ACCEPTED` |
| `ACCEPTED` 또는 `RUNNING` | 예 | 새 LLM 실행 없이 현재 non-terminal envelope |
| terminal | 예 | 새 LLM 실행 없이 저장된 terminal envelope |
| 어떤 상태든 | 아니오 | `409 Conflict` |

Duplicate start의 HTTP status는 non-terminal이면 202, terminal이면 200을 사용한다. 어떤 경우에도 같은 execution ID로 두 번째 LLM 실행을 만들지 않는다.

Fingerprint에는 최소한 다음 immutable field가 포함된다.

```text
tenant_id
execution_id
task_type
contract_version
input.request_id
input.user_id
input.absence_period_id
input.message_selection_ref
input.selected_items 전체
```

JSON key 순서나 표현 차이가 fingerprint를 바꾸지 않도록 canonical serialization을 사용한다.

### Start errors

| Status | 의미 |
| --- | --- |
| `400` | 요청을 해석할 수 없거나 공통 계약 위반 |
| `401`, `403` | 서비스 인증 또는 tenant 권한 실패 |
| `409` | 동일 execution ID에 다른 immutable request |
| `422` | Returned Message Topics v2 schema validation 실패 |
| `429` | 접수 용량 제한, 실행 생성 여부를 응답 계약으로 명확히 표시해야 함 |
| `5xx` | 접수 결과 불확실할 수 있으므로 Orchestrator는 status query로 확인 |

## Get execution status

```http
GET /ai/v1/returned-message-topics/executions/{executionId}
Accept: application/json
X-Tenant-Id: tenant-1
```

Path의 execution ID는 tenant scope 안에서만 조회한다. 다른 tenant의 실행 존재 여부를 노출하지 않는다.

### Accepted

```json
{
  "execution_id": "c2fcb430-54d2-4753-a4d5-6576dd24dbd1",
  "task_type": "RETURNED_MESSAGE_TOPICS",
  "contract_version": 2,
  "status": "ACCEPTED"
}
```

### Running

```json
{
  "execution_id": "c2fcb430-54d2-4753-a4d5-6576dd24dbd1",
  "task_type": "RETURNED_MESSAGE_TOPICS",
  "contract_version": 2,
  "status": "RUNNING"
}
```

### Succeeded

```json
{
  "execution_id": "c2fcb430-54d2-4753-a4d5-6576dd24dbd1",
  "task_type": "RETURNED_MESSAGE_TOPICS",
  "contract_version": 2,
  "status": "SUCCEEDED",
  "result": {
    "topics": [
      {
        "topic": "운영 점검",
        "summary": "운영 점검 관련 요청입니다.",
        "source_message_refs": ["message-1"]
      }
    ],
    "message_assessments": [
      {
        "message_ref": "message-1",
        "priority": "NORMAL",
        "priority_reason": "일반 업무",
        "reply_required": false,
        "reply_reason": "명시적인 회신 요청 없음",
        "action_required": true,
        "action_reason": "확인 작업 요청"
      }
    ],
    "generated_at": "2026-11-17T01:30:00Z"
  }
}
```

### Failed

```json
{
  "execution_id": "c2fcb430-54d2-4753-a4d5-6576dd24dbd1",
  "task_type": "RETURNED_MESSAGE_TOPICS",
  "contract_version": 2,
  "status": "FAILED",
  "error": {
    "code": "AI_GENERATION_FAILED",
    "message": "Returned Message Topics generation failed",
    "retryable": false
  }
}
```

### Cancelled

```json
{
  "execution_id": "c2fcb430-54d2-4753-a4d5-6576dd24dbd1",
  "task_type": "RETURNED_MESSAGE_TOPICS",
  "contract_version": 2,
  "status": "CANCELLED"
}
```

### Not found

404는 현재 tenant scope에서 해당 execution이 보이지 않는다는 뜻이다. Orchestrator는 최초 start 직후의 visibility grace 동안 재조회하며 한 번의 404를 generate 재호출로 연결하지 않는다.

## Result callback

Omni AI Server는 terminal execution과 callback outbox event를 먼저 저장한 뒤 AI Orchestrator endpoint를 호출한다.

```http
POST /api/v1/returned-messages/{requestId}/execution-results
Content-Type: application/json
```

AI Orchestrator API는 현재 Java REST naming에 맞춰 lowerCamelCase를 사용한다.

```json
{
  "eventId": "cb-96f004a4-9cc9-4ee0-bbc3-78921bc5cc61",
  "tenantId": "tenant-1",
  "userId": "user-1",
  "executionId": "c2fcb430-54d2-4753-a4d5-6576dd24dbd1",
  "taskType": "RETURNED_MESSAGE_TOPICS",
  "contractVersion": 2,
  "status": "SUCCEEDED",
  "result": {
    "topics": [
      {
        "topic": "운영 점검",
        "summary": "운영 점검 관련 요청입니다.",
        "sourceMessageRefs": ["message-1"]
      }
    ],
    "messageAssessments": [
      {
        "messageRef": "message-1",
        "priority": "NORMAL",
        "priorityReason": "일반 업무",
        "replyRequired": false,
        "replyReason": "명시적인 회신 요청 없음",
        "actionRequired": true,
        "actionReason": "확인 작업 요청"
      }
    ],
    "generatedAt": "2026-11-17T01:30:00Z"
  }
}
```

Callback 결과가 durable하게 반영됐거나 같은 `eventId` 또는 execution terminal result가 이미 반영된 경우 Orchestrator는 2xx acknowledgement를 반환한다. Timeout, connection failure와 retryable 5xx에서는 Omni AI callback worker가 같은 event ID로 재전송한다.

## Callback and polling convergence

Callback과 GET status query는 같은 terminal envelope 의미를 가진다. Orchestrator는 둘을 같은 result handler에 전달하고 `PROCESSING + executionId` conditional update로 한 번만 반영한다.

```text
callback 먼저 성공 → 이후 polling result는 existing terminal state
polling 먼저 성공  → 이후 callback은 idempotent 2xx
callback 중복      → 기존 terminal state 유지
```

## Remaining implementation gaps

현재 baseline은 MariaDB repository, lease 기반 in-process worker와 callback outbox로 위 계약을 구현한다. 운영 배포 전에는 service-to-service 인증, lease heartbeat 또는 broker 기반 실행 queue, retention/cleanup 정책과 dead-letter 운영 도구를 추가해야 한다.
