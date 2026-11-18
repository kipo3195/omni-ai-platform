# Returned Message Topics Execution Lifecycle

Status: Implemented baseline

이 문서는 Omni AI Server 내부에서 Returned Message Topics를 durable asynchronous execution으로 처리하는 구현 경계를 설명한다. HTTP wire schema는 [API Contract](api-contract.md), result v2 schema는 [README](README.md)를 따른다.

## State model

```text
ACCEPTED
→ RUNNING
   ├─ SUCCEEDED
   ├─ FAILED
   └─ CANCELLED
```

Terminal 상태는 다시 non-terminal로 변경하지 않는다. Workflow 내부 LangGraph node와 LLM provider retry 상태는 외부 execution 상태로 그대로 노출하지 않는다.

## Acceptance transaction

Start handler는 validation과 tenant scope 확인 후 다음 작업을 내구성 있게 완료한다.

```text
1. tenant_id + execution_id로 기존 실행 조회
2. immutable request canonical fingerprint 계산
3. 새 실행이면 execution record 생성
4. execution record commit
5. process-local Queue에 실행 작업 등록
6. 202 Accepted 반환
```

현재 baseline의 내구성 경계는 MariaDB execution record commit이다. Commit 이후 process-local Queue 등록 전후에 process가 종료되더라도 주기적인 recovery scan이 `ACCEPTED` execution을 다시 Queue에 넣는다. 따라서 Queue 자체는 durable하지 않지만 execution record와 recovery worker의 조합으로 Queue 등록 유실을 복구한다.

## Suggested execution record

논리 모델은 최소한 다음 정보를 보유한다. 실제 테이블명과 DB 제품은 별도 구현 결정이다.

```text
tenant_id
execution_id
task_type
contract_version
request_id
request_fingerprint
input_payload 또는 durable input reference
status
recovery_status (`NONE` 또는 `LEASE_EXPIRED`)
recovery_detected_at
result_payload
error_payload
accepted_at
started_at
completed_at
worker_owner
lease_until
created_at
updated_at
```

`tenant_id + execution_id`는 unique해야 한다. Result payload는 contract version과 함께 저장해 status query와 callback이 같은 schema를 사용하게 한다.

## Worker claim and execution

Worker는 ACCEPTED 작업을 bounded batch로 claim한다. 여러 instance가 같은 execution을 동시에 실행하지 않도록 owner token과 lease 또는 queue의 동등한 exclusive delivery 기능을 사용한다. Lease가 만료된 RUNNING execution은 자동 claim하지 않는다.

```text
ACCEPTED claim
→ RUNNING conditional transition
→ DB transaction 종료
→ LangGraph / LLM 실행
→ terminal result validation
→ terminal transaction
```

LLM 호출 중에는 execution DB transaction이나 row lock을 유지하지 않는다. Lease 만료는 실행이 실패했다는 뜻이 아니므로 provider 호출이 계속 실행 중일 가능성을 고려해야 한다. 만료된 RUNNING execution은 `recovery_status = LEASE_EXPIRED`와 감지 시각을 기록하고 Queue에 다시 넣지 않는다. 기존 worker가 늦게 terminal 결과를 저장하면 recovery 상태를 해제한다.

## Terminal transaction

성공 시 하나의 local transaction에서 다음을 수행한다.

```text
RUNNING → SUCCEEDED
result_payload v2 저장
callback outbox PENDING event 저장
```

실패 또는 취소도 terminal error/cancellation 상태와 callback event를 같은 transaction에 저장한다. Terminal result가 저장되지 않았는데 callback만 생성되거나, terminal result는 저장됐지만 callback event가 없는 crash window를 허용하지 않는다.

## Start idempotency

같은 `tenant_id + execution_id`의 duplicate start는 최초 request fingerprint와 비교한다.

- 같은 fingerprint이면 저장된 현재 상태를 반환한다.
- 다른 fingerprint이면 409 conflict다.
- terminal 상태라도 같은 start로 LLM을 다시 실행하지 않는다.
- JSON field 순서와 whitespace는 fingerprint에 영향을 주지 않는다.

Immutable request 비교에는 selected item key뿐 아니라 subject, sequence와 모든 correlation input을 포함한다. 동일 execution ID에 변경된 message selection을 허용하지 않는다.

## Status query

GET status는 execution repository의 authoritative snapshot을 반환한다.

- ACCEPTED와 RUNNING에는 result가 없다.
- SUCCEEDED에는 v2 result가 필수다.
- FAILED에는 안전한 error code와 retryable 의미가 필요하다.
- 다른 tenant의 실행 존재 여부를 노출하지 않는다.
- Terminal result는 설정된 retention 기간 동안 조회 가능해야 한다.

## Periodic recovery and process restart

Recovery worker는 서비스 시작 직후와 설정된 polling interval마다 다음 항목을 복구한다.

- Queue 등록 전후에 남은 ACCEPTED execution
- Queue에 다시 넣지 않고 `recovery_status = LEASE_EXPIRED`로 격리할 RUNNING execution
- Terminal이지만 callback PENDING인 execution
- Callback 전송 중 worker가 종료된 outbox event

RUNNING lease 만료 작업을 무조건 새 LLM 호출로 시작하면 provider 측 실행과 중복될 수 있으므로 자동 재실행하지 않는다. 공개 execution 상태는 RUNNING을 유지하고 내부 recovery 상태로 결과 불확실성을 구분한다.

## Retention and cleanup

Execution과 terminal result는 Orchestrator reconciliation deadline보다 길게 유지한다. Callback outbox cleanup은 execution/result cleanup보다 먼저 authoritative 결과를 제거하지 않는다. Retention 값과 개인정보 삭제 요구는 운영 설정으로 관리한다.

## Observability

최소한 다음 correlation과 지표를 제공한다.

```text
tenant_id
request_id
execution_id
task_type
contract_version
queue wait duration
LLM execution duration
execution terminal status
duplicate start count
status query count
```

Prompt, credential, 전체 입력과 결과를 일반 운영 로그에 그대로 남기지 않는다.

## Remaining implementation gaps

현재 baseline은 MariaDB에 execution과 terminal result를 저장하고, conditional update와 `worker_owner`/`lease_until`로 ACCEPTED 실행을 claim한다. Recovery worker는 `ACCEPTED`만 다시 Queue에 넣고, lease가 만료된 `RUNNING`은 `LEASE_EXPIRED` recovery 상태로 격리한다. 장시간 LLM 호출에 대한 lease heartbeat는 아직 없으므로 정상 실행이 격리되지 않도록 값을 잡거나 후속 heartbeat 구현이 필요하다.
