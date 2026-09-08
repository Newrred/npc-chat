# Target Architecture

2026-09-07 배포 진입 경로 갱신: 공개 HTTPS 링크 → Tunnel → FastAPI guest 모드(익명 서명 쿠키/Origin/한도) → 별도 llama.cpp. 기본 사용자 흐름에는 Cloudflare Access 로그인 없음. 전체 일일 한도와 활동 방문자 자리는 운영 DB 옆 usage SQLite 파일로 유지한다. PUBLIC_LINK_DEPLOYMENT.md 참고. 단일 앱 worker/모델 생성 1개 제한은 유지한다.

2026-09-07 현재 개발 장비 결정: 사용자 요청에 따라 RTX 3060 Ti 8 GB / RAM 약 32 GB에서 테스트한다. 속도 우선 4B Q4_K_M 모델, context 2048, parallel 1, output 256, GPU layers all, batch/ubatch 128, thinking OFF를 시작점으로 한다. 4070 Ti/14B Q4 관련 아래 기준은 향후 확장 프로파일이며 현재 단계의 필수 조건이 아니다. 실행과 실측은 [현재 로컬 런북](LOCAL_DEVELOPMENT_RUNBOOK.md), [상태 기록](PROJECT_STATUS.md)을 우선한다.

2026-09-07 사용자 승인 반영: Phase 02/03 검증 및 전환 완료. 현재 기본은 **통합 웹앱 1개 + 모델 1개 + SQLite 파일**이다. 전역 bounded queue와 DB 소유 잠금으로 한 worker를 강제한다. Redis는 선택적 이전 도구용이다. 상세 범위는 PHASE02_03_COMPLETION.md 참고.

## 1. 설계 목표

- 기존 FastAPI와 정적 프런트를 유지한다.
- 로컬 14B GGUF와 클라우드 OpenAI-compatible backend를 교체 가능하게 한다.
- 모델의 창의적 대사 생성과 게임 상태 계산을 분리한다.
- 관계·기억이 서버 재시작 및 Redis TTL로 사라지지 않게 한다.
- 실제 LLM 없이도 테스트할 수 있게 한다.
- 개인 로컬 사용에서 시작해 보안 게이트를 통과한 뒤 원격/공개 사용으로 확장한다.

## 2. 목표 구성

```text
Browser
        |
        | Same origin: /, static assets, /api
        v
FastAPI Web App (one instance / one worker)
  Static Frontend + API Layer
        |
        | POST /api/chat (client_turn_id, message)
        v
API Routes
        |
        v
Chat Orchestrator
  |          |             |              |
  |          |             |              +--> Optional Comfy Service
  |          |             +--> Memory Service
  |          +--> Deterministic Relationship Engine
  +--> LLM Adapter (OpenAI-compatible)
                   |
                   +--> llama.cpp on 127.0.0.1:8001
                   +--> optional vLLM/cloud later

Persistence
  SQLite (local file): profile, session mapping, relationship, turns, memories, processed turns
  App memory: bounded queue, per-profile/character locks, disposable cache
  Redis: transitional dependency until Phase 03; optional shared coordination later
```

## 3. 책임 경계

### Frontend

담당:

- 사용자 입력
- 대사·표정·상태 표시
- `client_turn_id` 생성
- loading/retry/offline UX
- non-secret runtime API URL
- 기본 API 경로는 상대 경로 `/api`이며 정적 파일은 같은 FastAPI 앱에서 제공한다. 별도 호스팅 override는 명시적 옵션이다.

금지:

- 관계 총점 계산
- 서버 이력 대신 로컬 history를 진실로 취급
- 비밀 API 키 보관
- LLM endpoint 직접 호출

### FastAPI route

담당:

- 요청 validation
- 인증/limit hook
- orchestrator 호출
- HTTP status 및 error serialization

금지:

- prompt 구성, 관계 계산, SQL 로직을 route에 직접 누적

### Chat orchestrator

담당:

1. profile/session load
2. idempotency 확인
3. prompt context 구성
4. LLM decision 요청
5. output validation
6. relationship engine 실행
7. memory 후보 반영
8. 단일 transaction으로 turn 저장
9. response 구성
10. optional image job trigger

### LLM adapter

담당:

- OpenAI-compatible request
- backend-specific capability 처리
- thinking OFF
- JSON/schema mode 사용 가능 시 적용
- text fallback extraction/retry
- timeout 및 retry 분류

금지:

- DB 상태 직접 변경
- 최종 관계 델타 결정

### Relationship engine

담당:

- `interaction.type`, `interaction.intensity`, 현재 상태와 최근 이벤트를 입력받는다.
- 5개 delta를 결정론적으로 계산한다.
- per-turn cap, total clamp, 반복 감쇠, 조건부 modifier를 적용한다.
- 계산 이유 코드를 남긴다.

### Memory service

담당:

- 최근 대화 window 관리
- rolling summary 갱신
- LLM이 제안한 memory candidate 정규화
- 중복 제거 및 중요도 제한
- prompt budget에 맞는 기억 선택

## 4. 권장 모듈 구조

대규모 rewrite 없이 아래 방향으로 점진적으로 분리한다.

```text
app/
  main.py
  config.py
  models.py                 # HTTP schemas; later api/schemas.py로 이동 가능
  domain/
    enums.py                # Face, internal emotion, interaction type
    relationship.py         # RelationshipState/Delta
    memory.py               # MemoryCandidate/StoredMemory
  services/
    chat_orchestrator.py
    relationship_service.py
    memory_service.py
    llm_service.py
    llama_cpp_service.py
    llm_service_factory.py
    comfy_service.py
  repositories/
    profile_store.py        # protocol/interface
    sqlalchemy_profile_store.py
  session_store.py          # current Redis adapter; retained during migration
  characters/
    default.json
  db/
    models.py
    migrations/
frontend/
scripts/
tests/
```

현재 파일을 한 번에 전부 이동하지 않는다. 테스트 seam을 추가한 뒤 단계별로 route의 책임을 빼낸다.

## 5. 상태 모델

### Durable profile state

```text
profile_id
character_id
relationship: five totals
flags
rolling_summary
revision
created_at
updated_at
```

### Durable turn event

```text
turn_id
client_turn_id
profile_id
character_id
user_message
assistant_reply
expression
interaction
relationship_delta
relationship_after
created_at
```

### Durable memory

```text
memory_id
kind
content
importance
confidence
created_at
last_used_at
source_turn_id
```

### Ephemeral session state

```text
session_id
profile_id
recent turn ids or short history cache
lock
last access
image job cache
```

## 6. Persistence choice

초기 로컬 기본:

- SQLAlchemy 2.x
- SQLite file DB
- Alembic migration
- 단일 앱 인스턴스·worker 하나, 로컬 디스크 SQLite 파일
- 메모리 잠금/제한 대기열/캐시; Redis는 전환 완료 후 기본 실행에서 제외

이 선택의 이유:

- SQLite로 별도 유료 서비스 없이 시작할 수 있다.
- 저장소 계층을 통해 PostgreSQL로 이동 가능하다.
- 관계·기억을 TTL과 분리한다.
- schema migration을 명시적으로 관리할 수 있다.

Redis 없는 경로를 개발용 임시 fallback이 아닌 기본 로컬/소규모 배포 경로로 검증한다. 현재 Redis는 Phase 03 전환 게이트 전까지 유지한다. Redis가 중단됐다는 이유로 런타임 저장 방식을 자동 전환하지 않는다.

동시성과 내구성 조건:

- 여러 세션이 같은 profile/character를 가리켜도 같은 관계 상태의 턴은 직렬 처리한다. 잠금 수명과 메모리 상한을 관리한다.
- 전역 추론 슬롯 1개와 크기/대기시간이 제한된 대기열을 둔다. 큐 포화·취소·timeout은 상태를 변경하지 않는다.
- LLM 응답을 기다리는 동안 SQLite 쓰기 transaction을 열어 두지 않는다. 짧은 commit에서 상태와 처리된 turn을 함께 저장한다.
- DB 고유 제약과 transaction으로 `client_turn_id` 재처리를 방지한다. 동일 ID/동일 요청은 저장된 결과를 재사용하고 다른 요청 본문으로 ID를 재사용하면 거부한다.
- 큐는 영속 작업 큐가 아니다. 재시작으로 미완료 요청이 끊겨도 같은 turn ID로 재시도할 수 있어야 하며 commit된 요청은 중복 적용되지 않아야 한다.
- migration/rollback/restart/concurrent duplicate 테스트를 통과한 후에만 Redis를 기본 의존성에서 제외한다. 기존 Redis 데이터는 전환 과정에서 삭제하지 않는다.
- 기본 프로파일에서 다중 worker/인스턴스를 지원한다고 주장하지 않는다. 관리 실행기는 중복 기동을 막고, 확장 시 공유 잠금/큐/요청 제한 및 저장소를 다시 검증한다.

readiness도 단계에 맞춰 변경한다. Phase 01~02에는 Redis+LLM, Phase 03 전환 후에는 SQLite+LLM을 필수로 확인한다. 비활성 Redis와 Comfy는 필수 의존성에서 제외한다.

## 7. LLM runtime profile

기본 로컬 profile:

```text
Backend: llama.cpp OpenAI-compatible server
Bind: 127.0.0.1 only
Port: 8001
Model: configurable 4B Q4_K_M GGUF (current 3060 Ti speed profile)
Context: 2048
GPU layers: all (4B only)
Batch / ubatch: 128 / 128
Parallel slots: 1
Thinking: off
Max completion tokens: 256
ComfyUI: off
```

모델 파일명, chat template, GPU layer 수는 환경 변수 또는 launch script 인자로 관리한다.

## 8. Prompt composition

순서는 다음을 기준으로 한다.

1. 캐릭터 identity/style/safety
2. 구조화 출력 계약
3. 관계 수치와 파생 상태
4. 관련 장기 기억
5. rolling summary
6. 최근 N턴
7. 현재 사용자 메시지

관계 상태와 서버 지침은 system/developer 역할로 전달하고 사용자 메시지 안에 문자열로 합치지 않는다. backend별 chat template 제약이 있으면 adapter가 안전한 형태로 변환한다.

## 9. Failure behavior

| 장애 | 사용자 동작 | 상태 변경 |
|---|---|---|
| LLM timeout/unavailable | 재시도 가능한 오류 표시 | 관계·기억 변경 없음 |
| JSON parse failure | 제한된 재시도 후 오류 | 변경 없음 |
| duplicate `client_turn_id` | 이전 성공 응답 재사용 | 중복 변경 없음 |
| lock/queue timeout or queue full | bounded 429/503 및 재시도 안내 | 변경 없음 |
| DB commit failure | 오류 반환 | transaction rollback |
| Comfy failure | 정적 표정 유지 | 대화 성공 유지 |
| local GPU OOM | readiness false 및 명확한 오류 | 변경 없음 |

## 10. Remote access boundary

```text
Internet
   |
Cloudflare Access / Reverse Proxy
   |
FastAPI 127.0.0.1:8000 (static frontend + /api)
   |
llama.cpp 127.0.0.1:8001
```

외부 클라이언트가 llama.cpp 포트에 도달하는 경로를 만들지 않는다. quick tunnel은 일시적 개발 확인 외에 운영 경로로 사용하지 않는다.

로컬과 배포 모두 화면/API를 같은 origin으로 제공하는 것을 기본으로 한다. 정적 루트를 mount할 때 `/api`와 health 경로를 가리지 않으며, 정적 공개 디렉터리에 DB·모델·`.env`·로그를 포함하지 않는다. 별도 프런트 배포는 선택 사항이며 그 경우에만 명시적 API 주소/CORS 설정이 추가로 필요하다. 같은 origin이어도 인증·쿠키 사용 시 CSRF 방어·요청 제한은 별도로 검증한다.
