# Test and Acceptance Plan

2026-09-07 현재 개발 장비 결정: 사용자 요청에 따라 RTX 3060 Ti 8 GB / RAM 약 32 GB에서 테스트한다. 속도 우선 4B Q4_K_M 모델, context 2048, parallel 1, output 256, GPU layers all, batch/ubatch 128, thinking OFF를 시작점으로 한다. 4070 Ti/14B Q4 관련 아래 기준은 향후 확장 프로파일이며 현재 단계의 필수 조건이 아니다. 실행과 실측은 [현재 로컬 런북](LOCAL_DEVELOPMENT_RUNBOOK.md), [상태 기록](PROJECT_STATUS.md)을 우선한다.

## 1. 원칙

- CI는 실제 GPU나 실제 LLM 없이 통과할 수 있어야 한다.
- 실제 모델 평가는 별도 명령으로 실행하고 결과를 기록한다.
- 관계 및 persistence 변화는 성공한 turn transaction에서만 한 번 적용한다.
- 오류 경로는 상태 불변을 검증한다.

## 2. Test layers

### Unit tests

필수 대상:

- face/internal-emotion normalization
- Pydantic LLM decision validation
- JSON extraction/fallback parser
- relationship matrix
- intensity scaling and per-stat clamp
- total 0..100 clamp
- teasing/irritation/repetition modifiers
- legacy affection migration
- flag allowlist
- memory candidate normalization and dedupe
- reply character-length limits

### Service tests

- fake LLM success
- invalid JSON then successful retry
- repeated invalid output
- LLM timeout/unavailable
- relationship engine invocation
- Comfy disabled does not block chat
- DB transaction rollback

### API integration tests

- first chat creates session/profile
- existing session continues state
- same `client_turn_id` returns identical prior result
- concurrent same-session turns are serialized or rejected predictably
- client-supplied history/state is ignored
- invalid message returns 400
- readiness reflects LLM/Redis/DB state
- readiness follows the selected profile: transitional Redis+LLM, after Phase 03 SQLite+LLM; disabled optional services do not block readiness
- error response conforms to contract

### Persistence tests

- backend restart preserves relationship
- Redis key expiry does not delete durable relationship
- legacy Redis state migrates once
- migration can be rerun safely
- SQLite transaction remains consistent after injected failure
- concurrent duplicate requests and same ID/different payload; retry after commit but lost response
- same profile/character from different sessions, queue full/timeout/cancel, bounded lock/cache cleanup
- Redis-free startup/chat/restart and no Redis connection from the default profile after cutover
- default startup prevents unsupported multiple app instances/workers

### Frontend tests

최소 smoke scope:

- frontend loads with neutral image
- submit button prevents accidental double submit
- loading/error/retry state
- face slug mapping and fallback
- relationship delta display in debug mode
- no hardcoded quick tunnel URL in built artifact
- Phase 01: page/assets/chat work from one FastAPI origin with relative API URLs and no separate frontend server
- static fallback cannot hide API errors or expose `.env`, DB, model, logs or parent paths

### Managed lifecycle tests (Phase 01)

- one start/stop command manages owned model and web processes, preserving transitional Redis data
- missing runtime/model, port collision, bounded readiness failure and partial-start cleanup
- repeated start/stop and pre-existing processes are handled without unintended termination
- use fake endpoints/processes in automation; test real model launch separately
- Phase 05: supervised restart/backoff, upgrade/rollback and persistent DB backup/restore

## 3. Real-model evaluation suite

`tests/eval_cases/*.json` 또는 `evaluation/cases.jsonl`에 최소 50개 한국어 사례를 둔다.

필수 범주:

- 인사와 단답
- 칭찬
- 애정 표현
- 장난
- 반복 질문
- 사과와 관계 회복
- 모욕과 경계 침해
- 힘든 상황에 대한 지지
- 자기 공개
- 이전 대화 참조
- 관계 수치가 낮을 때와 높을 때의 동일 질문
- prompt injection 시도
- 매우 짧은 답이 자연스러운 상황
- 모델이 모르는 사실을 억지로 만들지 않아야 하는 상황

각 case에는 다음을 넣는다.

```json
{
  "id": "compliment-low-affection-01",
  "relationship": {},
  "history": [],
  "message": "오늘 좀 귀엽네",
  "expected": {
    "interaction_types": ["compliment", "affection"],
    "allowed_faces": ["blushing", "shy_smile", "smiling"],
    "max_reply_chars": 80
  }
}
```

대사의 미적 품질은 자동 pass/fail만으로 확정하지 않고 blind review sheet를 함께 생성한다.

## 4. Acceptance metrics

### Structured output

- valid canonical schema on first attempt: >=95%
- valid schema after bounded retries: >=99%
- valid face/internal-emotion enum: 100%
- no markdown fence or explanation leaked to UI: 100%

### Relationship system

- deterministic output for identical state/interaction: 100%
- each per-turn delta within -3..+3: 100%
- totals within 0..100: 100%
- duplicate turn causes no second mutation: 100%

### Persistence

- relationship, flags, summary survive restart: 100%
- Redis expiry leaves durable state intact: 100%
- transaction failure leaves no partial mutation: 100%

### Local runtime initial target

- no OOM for 100 sequential turns at documented profile
- p50 <=4 seconds for short target response
- p95 <=8 seconds for short target response
- readiness detects stopped LLM within a bounded timeout

Latency thresholds are initial targets and may be revised only with measured evidence recorded in the decision log.

## 5. Required CI

At minimum:

```bash
python -m pytest -q
python -m compileall app
```

Recommended:

```bash
ruff check app tests
ruff format --check app tests
```

Add type checking only after annotations are sufficiently stable; do not block early baseline stabilization on a large unrelated type cleanup.

## 6. Manual release checklist

- [ ] no uncommitted secret/config file
- [ ] backend tests pass
- [ ] frontend smoke passes
- [ ] liveness/readiness correct
- [ ] one clean local conversation session
- [ ] backend restart preserves state
- [ ] duplicate submit test passes
- [ ] LLM stopped test returns retryable error without score change
- [ ] GPU resource usage recorded
- [ ] Comfy remains disabled unless explicitly in scope
- [ ] `PROJECT_STATUS` and `DECISION_LOG` updated


## 2026-09-07 Phase 04 실측 판정

4B 변경 후100회에서 첫시도/최종schema100%,enum100%,p50 1.524초/p95 2.125초,관찰OOM0으로 해당 정량게이트를 통과했다. Python375개,프런트13개 검사 통과. 기존9B 핵심20회는 지연15.039/22.421초로 현재속도게이트미달이다. 전체품질판정/환경제한/비블라인드에이전트점수/인간검토표는 PHASE04_EVALUATION.md 참고. 인간품질평가는 미실시이고 공개릴리스승인으로 취급하지 않는다.
