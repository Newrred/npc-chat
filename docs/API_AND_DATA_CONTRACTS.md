# API and Data Contracts

## 2026-09-07 guest 공개 링크 계약

기본 배포 모드 guest에서는 Access JWT 대신 서버가 발급/검증하는 `__Host-npc_guest` Secure/HttpOnly/SameSite=Lax 쿠키를 사용한다. GET /로 바로 입장하고 별도 인증 UI가 없다. 계정 대신 브라우저 이용권에서 remote_owner를 도출하여 기존 소유권/중복 처리 경계를 재사용한다. 쿠키 없음/위조/만료 시 새 방문자로 처리하고 과거 profile/session은 접근 거절한다. 정확한 Host/Origin/JSON과 본문 제한은 유지된다. `/api/ready`는 guest에서 403이고 `/api/live`는 익명 생존 확인이다.

새 429 오류: VISITOR_CAPACITY(재시도 가능), DAILY_TOTAL_LIMIT/DAILY_VISITOR_LIMIT(당일 재시도 불가). 일일 한도는 한국 날짜로 구분하고 모델 처리 시도 직전 원자적으로 차감한다. 이미 commit된 같은 turn은 한도 소진 후에도 재전송할 수 있다. 카운터는 `<database>.usage.sqlite3`에 보관되며 앱 재시작에도 유지한다. PUBLIC_LINK_DEPLOYMENT.md에 제한의 정확한 의미와 운영 조건을 기록했다.

## 2026-09-07 선택적 원격 인증 계약

`NPC_ACCESS_MODE=cloudflare`에서 liveness(`/api/live`, `/api/health`) 이외의 모든 화면/정적/API 요청은 검증된 `Cf-Access-Jwt-Assertion`을 요구한다. 정확한 public Host 및 변경 요청의 Origin/JSON을 검증한다. 인증 키 서버 장애는 503, 미인증은 401, 잘못된 Host/Origin 및 다른 계정 profile/session은 403이다.

`POST /api/session`은 로그인 계정에 묶인 동일 프로필/캐릭터 세션을 반환한다. 로컬 프로필의 자동 인계는 없다. `POST /api/chat`은 원격 모드에서 client_turn_id와 계정 소유 세션이 필요하다. 중복 결과 재사용 계약은 동일하다. `GET /api/image/status`도 세션 소유권을 확인한다.

원격 사용자당 변경 요청 20회/분, 채팅 active/queued 1개, 본문 16 KiB가 기본이다. 오류 코드는 AUTH_REQUIRED, AUTH_UNAVAILABLE, AUTH_BUSY, ACCESS_DENIED, HOST_REJECTED, ORIGIN_REJECTED, JSON_REQUIRED, RATE_LIMITED, TURN_IN_PROGRESS, BODY_TOO_LARGE, REQUEST_TIMEOUT, TURN_ID_REQUIRED 등이 추가된다. 429에는 Retry-After: 60, 원격 HTTP 응답에는 X-Request-ID와 Cache-Control: no-store가 있다. 수신 chunk마다 10초 timeout을 적용한다. 내부 rate/active 상태는 단일 worker 메모리이며 재시작으로 초기화된다.

스키마 0001 유지. 원격 profile ID는 검증된 issuer/subject의 서버 파생값이고 ID 자체는 인증 자격이 아니다. 같은 계정은 브라우저 간 상태를 공유한다. 토큰·이메일을 대화 DB에 저장하지 않는다. 운영 DB 경로와 개발 DB는 분리한다. 외부 공개와 보관/삭제 정책은 REMOTE_DEPLOYMENT_RUNBOOK.md의 미완료 게이트를 따라야 한다.

상태: Phase 04 구현 반영 (2026-09-07). 아래 계약의 실제 구현 세부값은 다음을 우선한다.

- POST /api/session: optional session_id/profile_id → 두 식별자 반환. 안정된 profile이 세션 간 상태를 소유한다.
- POST /api/chat: 기존 message/comfy_on + optional session_id/profile_id/client_turn_id. ID가 있는 요청은 기존 세션/프로필이 필요하다. history는 받아도 무시한다. 새 프런트는 보내지 않는다.
- api_version은 문자열 "1". profile_id, turn_id, relationship(values/delta/reason_codes/rule_version), expression(face/internal_emotion/tags), memory(summary_updated/accepted_candidates), image(status/source/url)와 기존 flat 필드를 함께 반환한다.
- affection_total/delta와 flat memory/expression/image는 deprecated 호환 필드다. LLM delta는 어떤 모드에서도 권위 있는 값으로 사용하지 않는다. legacy adapter 분류는 neutral/0이다.
- 저장소: SQLite schema 0001. 동일 프로필/캐릭터/turn ID는 고유하며 동일 message/comfy_on은 최초 응답 재사용, 다른 payload는 409 DUPLICATE_TURN_CONFLICT다.
- 422 요청 검증/SESSION_REQUIRED, 404 SESSION_NOT_FOUND/PROFILE_NOT_FOUND, 409 상태·식별자 충돌, 429 QUEUE_FULL, 503 QUEUE_TIMEOUT/PERSISTENCE_FAILURE/LLM_UNAVAILABLE, 502 LLM_INVALID_OUTPUT. 오류는 error.code/message/retryable이다. 일반 Pydantic 422는 FastAPI detail 형식을 유지한다.
- /api/ready는 database와 llm을 검사하며 200 ready 또는 503 not_ready다. Redis는 검사하지 않는다.
- canonical schema_version 정수1, reply 1..80, interaction intensity/importance 엄격한 정수 0..3, extra 금지, memory kind preference/fact/promise. shy smile은 shy_smile로 정규화한다. flag allowlist 적용.
- 규칙 1.0과 초기값 0/30/30/30/0, 최근 이력 12/전달4, 순환 요약400자, 기억50/검색3. 상세 보수적 기억 정책은 PHASE02_03_COMPLETION.md 참고.

## 1. Canonical enums

### FaceType

```text
neutral
happy
sad
angry
crying
smiling
smirk
shy_smile
blushing
teary
surprised
confused
annoyed
pouting
tired
scared
excited
```

내부 canonical 값은 underscore를 사용한다. 기존 LLM의 `"shy smile"`은 입력 normalization 단계에서 `shy_smile`로 변환한다.

### InternalEmotion

```text
neutral
happy
sad
angry
anxious
lonely
guilty
betrayed
nostalgic
embarrassed
confused
grateful
affectionate
curious
excited
tired
```

### InteractionType

```text
neutral
compliment
affection
support
self_disclosure
shared_activity
apology
teasing
conflict
insult
boundary_violation
repair
```

## 2. LLM decision schema

LLM은 다음 정보만 결정한다. 관계 총점과 최종 delta는 포함하지 않는다.

```json
{
  "schema_version": 1,
  "reply": "뭐야, 갑자기 그런 말을 왜 해.",
  "face": "blushing",
  "internal_emotion": "embarrassed",
  "emotion_tags": ["당황", "호감"],
  "interaction": {
    "type": "compliment",
    "intensity": 2
  },
  "memory_candidates": [
    {
      "kind": "preference",
      "content": "사용자는 직접적인 칭찬을 자주 한다.",
      "importance": 1
    }
  ],
  "flags_set": []
}
```

Constraints:

- `reply`: 1..80 characters after whitespace normalization
- `emotion_tags`: 1..3 short strings
- `interaction.intensity`: integer 0..3
- `memory_candidates`: 0..2
- `memory_candidate.content`: 1..120 characters
- `importance`: integer 0..3
- `flags_set`: character-config allowlist만 허용
- additional properties: false

## 3. Relationship data

```json
{
  "values": {
    "affection": 42,
    "trust": 28,
    "comfort": 35,
    "interest": 47,
    "irritation": 4
  },
  "delta": {
    "affection": 2,
    "trust": 0,
    "comfort": 1,
    "interest": 1,
    "irritation": 0
  },
  "reason_codes": ["COMPLIMENT", "INTENSITY_2"]
}
```

- totals: 0..100
- per-turn delta: -3..+3 per dimension
- delta calculation is server-side and deterministic
- `irritation` may decrease below current value but total is clamped at 0

## 4. Initial relationship engine matrix

아래 값은 intensity 1의 기본 vector다. intensity 0은 전부 0이며, intensity 2~3은 기본 vector를 배수 적용한 뒤 각 차원을 -3..+3으로 clamp한다.

| Interaction | affection | trust | comfort | interest | irritation |
|---|---:|---:|---:|---:|---:|
| neutral | 0 | 0 | 0 | 0 | 0 |
| compliment | +1 | 0 | 0 | +1 | 0 |
| affection | +1 | 0 | +1 | +1 | 0 |
| support | 0 | +1 | +1 | 0 | -1 |
| self_disclosure | 0 | +1 | 0 | +1 | 0 |
| shared_activity | 0 | 0 | +1 | +1 | 0 |
| apology | 0 | +1 | 0 | 0 | -1 |
| teasing | 0 | 0 | +1 | 0 | 0 |
| conflict | 0 | -1 | -1 | 0 | +1 |
| insult | -1 | -1 | 0 | 0 | +2 |
| boundary_violation | -1 | -2 | -2 | 0 | +2 |
| repair | 0 | +1 | +1 | 0 | -2 |

Required deterministic modifiers:

1. `teasing` with `comfort < 40`: remove comfort gain and add `irritation +1`.
2. `apology` or `repair` cannot reduce irritation below 0.
3. Positive repetition of the same interaction within the previous 3 successful turns lowers effective intensity by 1, minimum 0.
4. When `irritation >= 70`, positive affection/comfort gains are reduced by 1, minimum 0.
5. Final totals are clamped to 0..100.
6. Engine returns reason codes for every modifier.
7. No random number is used in score calculation.

캐릭터별 balancing을 지원하되, 기본 matrix 변경은 decision log에 기록한다.

## 5. Public chat API

### POST `/api/chat`

Target request:

```json
{
  "session_id": "optional-session-id",
  "client_turn_id": "uuid-generated-by-client",
  "message": "오늘 나 보고 싶었어?",
  "comfy_on": false
}
```

Rules:

- `message`: 1..1000 characters
- `client_turn_id`: required after migration; unique per attempted user turn
- browser-provided `history`, scores, flags, or memory are ignored and eventually removed
- same `client_turn_id` returns the original successful response

Target response:

```json
{
  "api_version": "1",
  "session_id": "server-session-id",
  "turn_id": "server-turn-id",
  "reply": "별로. ...조금은.",
  "expression": {
    "face": "shy_smile",
    "internal_emotion": "embarrassed",
    "tags": ["부끄러움", "호감"]
  },
  "relationship": {
    "values": {
      "affection": 42,
      "trust": 28,
      "comfort": 35,
      "interest": 47,
      "irritation": 4
    },
    "delta": {
      "affection": 1,
      "trust": 0,
      "comfort": 1,
      "interest": 1,
      "irritation": 0
    },
    "reason_codes": ["AFFECTION", "INTENSITY_1"]
  },
  "memory": {
    "summary_updated": false,
    "accepted_candidates": 0
  },
  "flags": [],
  "image": {
    "status": "disabled",
    "source": "base",
    "url": null
  }
}
```

### Compatibility window

프런트 migration이 끝날 때까지 다음 기존 top-level 필드를 함께 반환할 수 있다.

```text
face
internal_emotion
tags
affection_delta
affection_total
comfy_status
image_url
image_prompt
image_source
memory_1line
```

호환 필드 제거 시 API version을 올리고 frontend contract test를 갱신한다.

## 6. Health API

### GET `/api/live`

프로세스가 응답 가능한지만 확인한다.

```json
{"status":"ok"}
```

### GET `/api/ready`

Phase 03 전환 후 기본 프로파일 예시다. 현재 Phase 00의 Redis+LLM 응답은 전환 전까지 유지한다.

```json
{
  "status": "ready",
  "dependencies": {
    "llm": "ok",
    "database": "ok"
  },
  "model": "configured-model-id"
}
```

의존성 하나라도 필수 조건을 충족하지 않으면 503을 반환한다. ComfyUI는 코어 readiness의 필수 의존성이 아니다.

전환 후에는 SQLite와 LLM만 기본 필수 의존성이다. 비활성 Redis에는 접속하지 않으며 readiness 실패 사유로 삼지 않는다. Redis 확장 프로파일을 명시적으로 사용한다면 해당 프로파일에서만 Redis 상태를 추가한다. 위 `model` 필드는 목표 정보이며 모델 ID 일치/실제 추론 검증 여부는 별도로 기록한다.

## 7. Error schema

```json
{
  "error": {
    "code": "LLM_UNAVAILABLE",
    "message": "대화 모델에 연결할 수 없습니다.",
    "retryable": true,
    "request_id": "request-id"
  }
}
```

Recommended codes:

```text
INVALID_REQUEST
SESSION_BUSY
DUPLICATE_TURN_CONFLICT
LLM_TIMEOUT
LLM_UNAVAILABLE
LLM_INVALID_OUTPUT
PERSISTENCE_FAILURE
RATE_LIMITED
UNAUTHORIZED
INTERNAL_ERROR
```

HTTP guidance:

- 400 invalid input
- 401/403 access failure
- 409 session lock or idempotency conflict
- 429 rate limit
- 502 invalid/upstream LLM response
- 503 dependency unavailable
- 500 unexpected server failure

## 8. Migration from existing state

Existing:

```json
{
  "affection_total": 17,
  "flags": [],
  "memory_1line": "...",
  "history": []
}
```

Migration:

- `affection = clamp(affection_total, 0, 100)`
- other relationship dimensions use character-config defaults
- `memory_1line`, if nonempty, becomes one legacy summary note
- existing session id may be linked to a generated local profile id
- migration must be idempotent
- preserve old Redis state until successful durable commit


## Phase 04 추가 계약

- INPUT_TOO_LONG: 422, retryable=false. 출력 토큰+64 여유를 제외한 입력 예산에 맞지 않는 요청이며 현재 입력은 자르지 않는다.
- TOKENIZER_UNAVAILABLE: 503, retryable=true. 명시적 llama_cpp count API 실패. 자동 estimate fallback 없음.
- memory.grounded_recall: 명시적 사용자 취향 회상에 저장된 최신 원문을 인용한 응답인지 표시한다. LLM이 실패하면 이 경로도 실행하지 않는다.
- 브라우저 pending 요청에는 session_id/profile_id/client_turn_id/message/comfy_on 전체를 저장한다. reload/retry는 같은 payload를 보낸다.
- 단순 1인칭 취향 직접 추출, 동일 대상의 취향 정정, 관련도+최신성 검색을 추가했다. 스키마0001은 그대로다.

## 2026-09-08 Conversation history and reset

`GET /api/conversation` requires session_id/profile_id, accepts limit 1–100 (default 50) and optional before turn ID. After server ownership validation, returns chronological items containing turn_id, user_message, reply, face, created, plus before for older pages. Generated prompt history limits do not limit this endpoint. Private responses are no-store.

`POST /api/conversation/reset` accepts session_id/profile_id and returns closed:true after an atomic reset. It revokes old sessions and deletes this profile/character's turns and memory, restores relationship defaults and clears summary/flags. Other profiles/characters and durable quotas remain. Old-session retries fail with 403/404 and cannot reset a newly opened room. Chat checks the session again inside the serial queue before replay or quota charging. Public guest Origin and owner checks apply to both operations.

The administrator runs as a separate read-only loopback app. Its /api/rooms and /api/turns routes are not public application routes. See CHAT_HISTORY_AND_ADMIN.md for contracts and lifecycle.
