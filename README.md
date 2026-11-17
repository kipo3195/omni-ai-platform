# 이미지 생성 
docker build --platform linux/amd64 -t messenger-ai-platform-v1:latest .

# 이미지 -> tar 
docker save -o ./omni-ai-platform-latest.tar omni-ai-platform:latest

# 서비스 실행 
docker run \
  --restart unless-stopped \
  --env-file .env \
  -p 8000:8000 \
  omni-ai-platform:latest

# 개발환경의 Returned Message Topics prompt/결과 payload 로그 활성화
# prompt에 메시지 제목이 포함되므로 운영환경에서는 반드시 production으로 설정한다.
APP_ENV=development

# API contracts

- [Returned Message Topics API Contract v2](docs/returned_message_topics/README.md)

# Returned Message Topics 비동기 실행 설정

Execution, result와 callback outbox는 MariaDB에 저장한다. Python 서비스는
Spring 형식의 `jdbc:mariadb://` URL에서 `jdbc:` 접두사를 제거해 연결한다.

```bash
docker run \
  --restart unless-stopped \
  --env-file .env \
  -e RETURNED_MESSAGE_CALLBACK_BASE_URL=http://ai-orchestrator:8080 \
  -p 8000:8000 \
  omni-ai-platform:latest
```

| 환경 변수 | 기본값 | 의미 |
| --- | --- | --- |
| `DATASOURCE_URL` | 없음 | `jdbc:mariadb://host:3306/database` 형식의 MariaDB URL |
| `DATASOURCE_USERNAME` | 없음 | MariaDB 사용자 |
| `DATASOURCE_PASSWORD` | 없음 | MariaDB 비밀번호 |
| `RETURNED_MESSAGE_WORKER_COUNT` | `2` | 비동기 LLM 실행 worker 수 |
| `RETURNED_MESSAGE_EXECUTION_LEASE_SECONDS` | `900` | 실행 worker claim lease |
| `RETURNED_MESSAGE_RECOVERY_POLL_INTERVAL_SECONDS` | `5` | 미처리·lease 만료 실행 복구 주기 |
| `RETURNED_MESSAGE_CALLBACK_BASE_URL` | 빈 값 | AI Orchestrator base URL. 빈 값이면 callback worker를 시작하지 않음 |
| `RETURNED_MESSAGE_CALLBACK_TIMEOUT_SECONDS` | `5` | callback HTTP timeout |
| `RETURNED_MESSAGE_CALLBACK_POLL_INTERVAL_SECONDS` | `1` | outbox 확인 주기 |
| `RETURNED_MESSAGE_CALLBACK_MAX_ATTEMPTS` | `3` | callback 실패 후 dead-letter 전환 전 최대 시도 수 |

애플리케이션 계정에는 두 Returned Message 테이블을 생성·조회·갱신할 권한이 필요하다. 운영에서 DDL 권한을 분리한다면 배포 전에 동일 schema를 migration으로 생성해야 한다.
DDL은 [`deployment/mariadb/returned_message_topics.sql`](deployment/mariadb/returned_message_topics.sql)에 있다.
