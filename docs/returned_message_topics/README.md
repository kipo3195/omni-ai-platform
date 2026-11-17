# Returned Message Topics API Contract v2

이 문서는 AI Orchestrator가 Returned Message Topics 작업을 요청하고 결과를
역직렬화하기 위한 계약입니다.

## 문서 구성과 상태

- 이 문서: contract version 2의 Task input과 terminal result 데이터 schema
- [Asynchronous API Contract](api-contract.md): `202 Accepted`, status query와 callback wire contract
- [Execution Lifecycle](execution-lifecycle.md): durable execution repository, Queue와 Worker lifecycle
- [Callback Delivery](callback-delivery.md): callback outbox, 재전송과 Orchestrator polling의 관계

현재 구현은 `POST /generate` 요청 안에서 LLM 완료를 기다리고 `200 SUCCEEDED`를 반환하는 동기형이다. 목표 계약은 execution을 durable하게 접수한 뒤 `202 Accepted`를 반환하고 Queue Worker, callback과 status query로 완료를 전달하는 비동기형이다. 아래 input/result v2 schema는 현재와 목표 계약에서 동일하게 사용한다.

## 변경 요약

`contract_version: 2`는 v1과 호환되지 않는 변경입니다. Endpoint URL의
`/ai/v1`은 그대로 유지하고, task contract version만 `2`로 변경합니다.

- 토픽에는 그룹 요약과 원본 메시지 참조만 포함합니다.
- 우선순위, 회신 필요 여부, 작업 필요 여부를 `message_assessments`로 분리합니다.
- `message_count`는 `source_message_refs.length`로 계산할 수 있어 제거합니다.
- 요청 본문의 구조는 같지만 `contract_version`이 `1`에서 `2`로 변경됩니다.
- v2 엔드포인트는 `contract_version: 1` 요청을 HTTP 422로 거부합니다.

## Start Endpoint

```text
POST /ai/v1/returned-message-topics/generate
Content-Type: application/json
```

현재 구현은 이 endpoint에서 terminal result를 동기 반환한다. 목표 비동기 응답과 중복 start 규칙은 [Asynchronous API Contract](api-contract.md)를 따른다.

## Request

```json
{
  "execution_id": "c2fcb430-54d2-4753-a4d5-6576dd24dbd1",
  "tenant_id": "tenant-1",
  "task_type": "RETURNED_MESSAGE_TOPICS",
  "contract_version": 2,
  "input": {
    "request_id": "request-1",
    "user_id": "user-1",
    "absence_period_id": "absence-period-1",
    "message_selection_ref": "selection-1",
    "selected_items": [
      {
        "source_item_key": "bad3d5489d1c4d858e78bbfa09a7956a",
        "subject": "운영 점검 사전 회의록 공유",
        "sequence": 0
      },
      {
        "source_item_key": "3564f786465a47a597b6d0f7cf8a564b",
        "subject": "금요일까지 운영 점검 체크리스트 업데이트 요청",
        "sequence": 1
      },
      {
        "source_item_key": "6058b805e7d44623bee0e8c2f58ebc87",
        "subject": "운영 점검 참석 여부 회신 요청",
        "sequence": 2
      },
      {
        "source_item_key": "ec8ae38bc30340248ab1691a5beeb3c2",
        "subject": "긴급: 메신저 로그인 장애 즉시 확인 요청",
        "sequence": 3
      }
    ]
  }
}
```

### Request 필드

| 경로 | 타입 | 필수 | 제약/의미 |
| --- | --- | --- | --- |
| `execution_id` | string | Y | Orchestrator가 생성한 실행 식별자 |
| `tenant_id` | string | Y | 테넌트 식별자 |
| `task_type` | string | Y | 항상 `RETURNED_MESSAGE_TOPICS` |
| `contract_version` | integer | Y | 항상 `2` |
| `input.request_id` | string | Y | 비즈니스 요청 식별자 |
| `input.user_id` | string | Y | 대상 사용자 식별자 |
| `input.absence_period_id` | string | Y | 부재 기간 식별자 |
| `input.message_selection_ref` | string | Y | 메시지 선택 결과 식별자 |
| `input.selected_items` | array | Y | 1~30개 |
| `selected_items[].source_item_key` | string | Y | 요청 내에서 중복 불가 |
| `selected_items[].subject` | string/null | N | 분석할 메시지 제목. 생략 시 null |
| `selected_items[].sequence` | integer | Y | 0 이상이며 요청 내에서 중복 불가 |

## Terminal Success Result

다음은 `SUCCEEDED` terminal envelope다. 현재 동기 구현에서는 HTTP 200 start response로 반환하고, 목표 비동기 구현에서는 callback과 GET execution status response에서 동일한 result를 사용한다.

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
        "summary": "사전 회의록이 공유됐고, 체크리스트 업데이트와 참석 여부 회신이 요청됐습니다.",
        "source_message_refs": [
          "bad3d5489d1c4d858e78bbfa09a7956a",
          "3564f786465a47a597b6d0f7cf8a564b",
          "6058b805e7d44623bee0e8c2f58ebc87"
        ]
      },
      {
        "topic": "메신저 로그인 장애",
        "summary": "메신저 로그인 장애를 즉시 확인해 달라는 요청입니다.",
        "source_message_refs": [
          "ec8ae38bc30340248ab1691a5beeb3c2"
        ]
      }
    ],
    "message_assessments": [
      {
        "message_ref": "bad3d5489d1c4d858e78bbfa09a7956a",
        "priority": "NORMAL",
        "priority_reason": "정보 공유",
        "reply_required": false,
        "reply_reason": "명시적인 회신 요청 없음",
        "action_required": false,
        "action_reason": "명시적인 작업 요청 없음"
      },
      {
        "message_ref": "3564f786465a47a597b6d0f7cf8a564b",
        "priority": "HIGH",
        "priority_reason": "금요일까지 마감",
        "reply_required": false,
        "reply_reason": "명시적인 회신 요청 없음",
        "action_required": true,
        "action_reason": "체크리스트 업데이트 요청"
      },
      {
        "message_ref": "6058b805e7d44623bee0e8c2f58ebc87",
        "priority": "NORMAL",
        "priority_reason": "일정 확인 요청",
        "reply_required": true,
        "reply_reason": "참석 여부 회신 요청",
        "action_required": false,
        "action_reason": "명시적인 작업 요청 없음"
      },
      {
        "message_ref": "ec8ae38bc30340248ab1691a5beeb3c2",
        "priority": "URGENT",
        "priority_reason": "긴급 장애",
        "reply_required": false,
        "reply_reason": "명시적인 회신 요청 없음",
        "action_required": true,
        "action_reason": "장애 즉시 확인 요청"
      }
    ],
    "generated_at": "2026-11-16T02:12:38.581170Z"
  }
}
```

### Response 필드

| 경로 | 타입 | 필수 | 제약/의미 |
| --- | --- | --- | --- |
| `execution_id` | string | Y | 요청의 `execution_id`와 동일 |
| `task_type` | string | Y | `RETURNED_MESSAGE_TOPICS` |
| `contract_version` | integer | Y | `2` |
| `status` | string | Y | 성공 시 `SUCCEEDED` |
| `result.topics` | array | Y | 하나 이상의 토픽 |
| `topics[].topic` | string | Y | 토픽 이름 |
| `topics[].summary` | string | Y | 그룹에 포함된 메시지 요약 |
| `topics[].source_message_refs` | string[] | Y | 해당 토픽에 속한 원본 메시지 키 |
| `result.message_assessments` | array | Y | 원본 메시지별 평가 |
| `message_assessments[].message_ref` | string | Y | 요청의 `source_item_key`와 연결되는 키 |
| `message_assessments[].priority` | enum | Y | `LOW`, `NORMAL`, `HIGH`, `URGENT`, `UNKNOWN` |
| `message_assessments[].priority_reason` | string | Y | 1~50자 |
| `message_assessments[].reply_required` | boolean | Y | 명시적인 회신 필요 여부 |
| `message_assessments[].reply_reason` | string | Y | 1~50자 |
| `message_assessments[].action_required` | boolean | Y | 명시적인 작업 필요 여부 |
| `message_assessments[].action_reason` | string | Y | 1~50자 |
| `result.generated_at` | RFC 3339 datetime | Y | 서버가 생성한 UTC 시각 |

## 응답 불변조건

Orchestrator는 배열 순서 대신 메시지 참조 키를 기준으로 결과를 연결해야 합니다.

1. 요청의 모든 `source_item_key`는 전체
   `topics[].source_message_refs`에 정확히 한 번 나타납니다.
2. 요청의 모든 `source_item_key`는
   `message_assessments[].message_ref`에 정확히 한 번 나타납니다.
3. 요청에 없는 메시지 참조는 응답에 나타나지 않습니다.
4. `message_ref`와 `source_message_refs[]`는 요청의
   `source_item_key`를 변경하지 않고 그대로 사용합니다.
5. 토픽/평가 배열의 순서는 계약상 의미가 없습니다.

## Orchestrator 처리 권장 순서

1. 요청 시 `contract_version`을 `2`로 전송합니다.
2. 목표 비동기 계약에서는 HTTP 202와 `status == ACCEPTED`를 접수로 기록합니다.
3. Callback 또는 status query의 terminal 응답에서 `status == SUCCEEDED`를 확인합니다.
4. 응답의 `execution_id`, `task_type`, `contract_version`이 요청과 일치하는지
   확인합니다.
5. `message_assessments`를 `message_ref` 기준 Map으로 변환합니다.
6. `topics[].source_message_refs`를 이용해 메시지를 토픽에 연결합니다.
7. 알 수 없거나 누락·중복된 참조가 있으면 계약 위반으로 처리합니다.

## Execution Delivery Contract

목표 계약은 다음 세 경로를 사용한다.

```text
POST /ai/v1/returned-message-topics/generate
  → durable acceptance와 202 ACCEPTED

POST AI Orchestrator execution-results callback
  → 정상 terminal result 전달

GET /ai/v1/returned-message-topics/executions/{executionId}
  → callback 지연·유실과 불확실 dispatch reconciliation
```

Callback과 polling은 같은 terminal envelope를 사용하고 Orchestrator의 같은 result handler로 수렴한다. Callback outbox는 발신 측 유실을 복구하고 polling은 수신 측에서 callback 장기 지연을 복구한다.

현재 구현에는 `202 Accepted`, durable execution Queue, callback과 GET execution endpoint가 없다. 따라서 비동기 계약이 구현되기 전에는 다음 내용을 보장하지 않는다.

- Start가 빠르게 `202 Accepted`를 반환함
- 동일 execution ID의 start가 LLM을 중복 실행하지 않음
- GET 조회의 `SUCCEEDED.result`가 contract version 2 구조임
- `ACCEPTED`, `RUNNING`, `FAILED`, `CANCELLED` 조회 envelope
- Callback outbox와 callback retry

구현 목표와 HTTP schema는 [Asynchronous API Contract](api-contract.md)를 따른다.

## Non-2xx 및 불확실 상태 복구 규칙

HTTP 응답을 받지 못했거나 5xx를 받았다는 사실만으로 AI 작업이
실패했다고 확정할 수 없습니다. 서버가 작업을 접수한 뒤 응답 전송에
실패했을 수 있기 때문입니다. 따라서 Orchestrator의 목표 복구 전략인
`PROCESSING` 유지 후 재조회를 계속 사용하는 것이 의도에 맞습니다.

| 결과 | Orchestrator 처리 |
| --- | --- |
| HTTP 202 + `ACCEPTED` | 실행 접수, `PROCESSING` 유지 후 callback 대기와 reconciliation 예약 |
| 중복 start의 기존 terminal 결과 | 새 LLM 실행 없이 기존 결과 반영 |
| HTTP 422 | 요청 계약 오류. payload 수정 없이 재시도하지 않고 실패 처리 |
| HTTP 400/401/403 | 요청·인증·권한 문제로 실패 처리 |
| timeout/연결 오류/HTTP 408/429/5xx | 결과 불확실. `PROCESSING` 유지, backoff 후 `executionId`로 재조회 |
| GET 404 | 초기 visibility 지연을 고려해 유한 횟수 재조회. 복구 기한 초과 시 `EXECUTION_STATUS_UNRESOLVED` 등으로 실패 종료 |
| GET 200 + terminal `FAILED`/`CANCELLED` | envelope에 따라 terminal 상태로 종료 |
| callback 또는 GET 200 + `SUCCEEDED` | v2 `result`를 멱등 저장하고 delivery 단계로 전이 |

이 전략을 운영 계약으로 사용하려면 다음이 함께 구현되어야 합니다.

1. `executionId`별 내구성 있는 execution 상태·결과 저장
2. execution record와 durable Queue 등록 후 `202 Accepted`
3. `GET /ai/v1/returned-message-topics/executions/{executionId}`
4. terminal result와 callback outbox의 atomic 저장 및 재전송
5. `ACCEPTED`, `RUNNING`, `SUCCEEDED`, `FAILED`, `CANCELLED` envelope 스키마
6. `SUCCEEDED.result`는 이 문서의 contract version 2 result와 동일하다는 보장
7. 404 visibility grace period, polling backoff, 최종 복구 deadline

Execution ID 기반 멱등성이 구현되기 전에는 POST를 자동 재시도하면 안 된다. Status query의 단일 404도 즉시 POST 재호출로 연결하지 않는다.

## Java 수신 DTO 예시

Java 17 record와 Jackson을 사용하는 예시입니다. 프로젝트의 ObjectMapper에
snake case 정책이 이미 설정되어 있다면 각 DTO의 `@JsonNaming`은 공통 설정으로
대체할 수 있습니다.

```java
import com.fasterxml.jackson.databind.PropertyNamingStrategies;
import com.fasterxml.jackson.databind.annotation.JsonNaming;
import java.time.OffsetDateTime;
import java.util.List;

@JsonNaming(PropertyNamingStrategies.SnakeCaseStrategy.class)
public record ReturnedMessageTopicsSuccessResponse(
    String executionId,
    String taskType,
    int contractVersion,
    String status,
    ReturnedMessageTopicsResult result
) {}

@JsonNaming(PropertyNamingStrategies.SnakeCaseStrategy.class)
public record ReturnedMessageTopicsResult(
    List<ReturnedMessageTopic> topics,
    List<ReturnedMessageAssessment> messageAssessments,
    OffsetDateTime generatedAt
) {}

@JsonNaming(PropertyNamingStrategies.SnakeCaseStrategy.class)
public record ReturnedMessageTopic(
    String topic,
    String summary,
    List<String> sourceMessageRefs
) {}

@JsonNaming(PropertyNamingStrategies.SnakeCaseStrategy.class)
public record ReturnedMessageAssessment(
    String messageRef,
    ReturnedMessagePriority priority,
    String priorityReason,
    boolean replyRequired,
    String replyReason,
    boolean actionRequired,
    String actionReason
) {}

public enum ReturnedMessagePriority {
    LOW,
    NORMAL,
    HIGH,
    URGENT,
    UNKNOWN
}
```

요청 DTO에서 바뀌는 값은 `contractVersion = 2`입니다. 전체 요청 DTO 예시는
다음과 같습니다.

```java
import com.fasterxml.jackson.databind.PropertyNamingStrategies;
import com.fasterxml.jackson.databind.annotation.JsonNaming;
import java.util.List;

@JsonNaming(PropertyNamingStrategies.SnakeCaseStrategy.class)
public record ReturnedMessageTopicsRequest(
    String executionId,
    String tenantId,
    String taskType,
    int contractVersion,
    ReturnedMessageTopicsInput input
) {}

@JsonNaming(PropertyNamingStrategies.SnakeCaseStrategy.class)
public record ReturnedMessageTopicsInput(
    String requestId,
    String userId,
    String absencePeriodId,
    String messageSelectionRef,
    List<ReturnedMessageSelectedItem> selectedItems
) {}

@JsonNaming(PropertyNamingStrategies.SnakeCaseStrategy.class)
public record ReturnedMessageSelectedItem(
    String sourceItemKey,
    String subject,
    int sequence
) {}
```

수신 직후에는 최소한 다음 값을 확인하는 것을 권장합니다.

```java
if (!"RETURNED_MESSAGE_TOPICS".equals(response.taskType())
        || response.contractVersion() != 2
        || !"SUCCEEDED".equals(response.status())) {
    throw new IllegalStateException("Unsupported returned-message response contract");
}
```

## v1에서 제거된 응답 필드

다음 필드는 더 이상 `topics[]`에 존재하지 않습니다.

```text
priority
priority_reason
reply_required
reply_reason
action_required
action_reason
message_count
```

앞의 여섯 필드는 동일한 원본 메시지의
`message_assessments[message_ref]`에서 조회해야 합니다. `message_count`가 필요한
경우 `topics[].source_message_refs.size()`로 계산합니다.
