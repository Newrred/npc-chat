# NPC Chat Codex Master Handoff

Generated 2026-09-03. Individual files remain the operational source of truth.


---

<!-- SOURCE: README.md -->

# NPC Chat — Codex Development Handoff

검토일: **2026-09-03 (KST)**  
기준 저장소: **`Newrred/npc-chat`**  
레거시 프런트 저장소: **`Newrred/heroine`**

## 1. 이 패키지의 목적

기존 NPC 캐릭터 챗봇 프로토타입을 폐기하거나 새로 작성하지 않고, 현재 구현을 기준으로 다음 상태까지 발전시키기 위한 Codex 작업 문서 세트다.

- 현재 데스크톱의 NVIDIA GPU에서 로컬 LLM을 실행한다.
- 캐릭터는 짧고 자연스러운 한국어 대답을 한다.
- 대답마다 표정, 내면 감정, 감정 태그를 반환한다.
- `호감도·신뢰도·편안함·관심도·짜증도`의 5개 관계 수치를 관리한다.
- LLM은 상호작용을 해석하고, 관계 수치 계산은 서버가 결정론적으로 수행한다.
- 관계 상태와 기억은 재시작 뒤에도 유지한다.
- 정적 표정 이미지를 기본으로 사용하고 ComfyUI는 선택 기능으로 남긴다.
- 외부 공개 전에 인증, 제한, 고정 터널, 관측성을 갖춘다.

## 2. 기준 스냅샷

| 저장소 | 기준 브랜치 | 확인한 HEAD | 역할 |
|---|---|---|---|
| `Newrred/npc-chat` | `main` | `a9f6205045648e8889a4dbf4190de65e330caaed` | 유일한 개발 기준 저장소 |
| `Newrred/heroine` | `main` | `f722ae87a82775e3cf12c0f188a71f5165c5686e` | 과거 GitHub Pages 배포본; 레거시 취급 |

이 문서는 위 스냅샷의 정적 코드 검토를 기준으로 한다. 실제 실행 성공, 로컬 CUDA 환경, Redis 상태, 모델 파일 및 배포 URL의 현재 동작 여부는 아직 검증된 사실이 아니다. Codex는 첫 작업에서 반드시 현재 HEAD와 실행 상태를 다시 확인해야 한다.

## 3. 사용 방법

1. `Newrred/npc-chat`을 로컬에 clone한다.
2. 이 패키지의 `AGENTS.md`, `docs/`, `tasks/`를 저장소 루트에 복사한다.
3. `CODEX_START_PROMPT.md` 내용을 Codex에 전달한다.
4. 첫 실행에서는 **`tasks/00_BASELINE_STABILIZATION.md`만** 수행한다.
5. 한 작업 단위마다 테스트, 문서 갱신, 변경 요약을 완료한 뒤 다음 단계로 이동한다.
6. `heroine` 저장소는 별도 지시가 있기 전까지 기능 개발 대상으로 사용하지 않는다.

## 4. 문서 우선순위

충돌 시 아래 순서가 우선한다.

1. `AGENTS.md`
2. `docs/PRODUCT_AND_TECHNICAL_DIRECTION.md`
3. `docs/PROJECT_STATUS.md`
4. `docs/TARGET_ARCHITECTURE.md`
5. `docs/API_AND_DATA_CONTRACTS.md`
6. `docs/IMPLEMENTATION_PLAN.md`
7. 현재 수행 중인 `tasks/*.md`
8. 기존 저장소 `README.md`

현재 코드와 문서가 충돌하면 추측하지 말고 `docs/PROJECT_STATUS.md`에 차이를 기록한다. 사용자 결정이 없는 상태에서는 기존 동작을 보존하는 쪽을 선택한다.

## 5. 패키지 구성

```text
AGENTS.md
CODEX_START_PROMPT.md
README.md
docs/
  PRODUCT_AND_TECHNICAL_DIRECTION.md
  PROJECT_STATUS.md
  TARGET_ARCHITECTURE.md
  API_AND_DATA_CONTRACTS.md
  IMPLEMENTATION_PLAN.md
  LOCAL_4070TI_RUNBOOK.md
  TEST_AND_ACCEPTANCE_PLAN.md
  DEPLOYMENT_AND_SCALING_GATES.md
  DECISION_LOG.md
tasks/
  00_BASELINE_STABILIZATION.md
  01_LLM_CONTRACT_AND_LOCAL_RUNTIME.md
  02_RELATIONSHIP_ENGINE.md
  03_DURABLE_PERSISTENCE_AND_MEMORY.md
  04_FRONTEND_RELIABILITY_AND_EVALUATION.md
  05_SECURE_REMOTE_ALPHA.md
  06_OPTIONAL_COMFY_AND_CLOUD_FALLBACK.md
```

## 6. 중요한 범위 제한

- 프레임워크 전체 교체 금지: FastAPI + 정적 프런트 구조를 유지한다.
- 초기 목표에서 ComfyUI 이미지 생성은 비활성화한다.
- 모델 GGUF 파일, `.env`, 터널 자격증명, API 키를 Git에 커밋하지 않는다.
- LLM이 관계 총점 또는 최종 델타를 직접 확정하게 하지 않는다.
- 클라이언트가 보낸 대화 이력을 신뢰하지 않는다.
- 한 번에 여러 단계의 대규모 리팩터링을 하지 않는다.
- 공개 서비스 운영 조건을 갖추기 전에는 로컬 백엔드나 LLM 포트를 인터넷에 직접 노출하지 않는다.


---

<!-- SOURCE: AGENTS.md -->

# AGENTS.md — NPC Chat Repository Instructions

## Mission

기존 `npc-chat` 프로토타입을 로컬 우선 캐릭터 챗봇으로 안정화한다. 사용자는 짧은 한국어 대화를 주고받으며, 캐릭터의 표정·감정 태그와 5개 관계 수치 변화를 경험한다. 현재 구현을 보존하면서 테스트 가능한 작은 단위로 발전시킨다.

## Source-of-truth order

1. 이 `AGENTS.md`
2. `docs/PRODUCT_AND_TECHNICAL_DIRECTION.md`
3. `docs/PROJECT_STATUS.md`
4. `docs/TARGET_ARCHITECTURE.md`
5. `docs/API_AND_DATA_CONTRACTS.md`
6. `docs/IMPLEMENTATION_PLAN.md`
7. 현재 지정된 `tasks/*.md`
8. 기존 `README.md`

## Baseline

- Primary repository: `Newrred/npc-chat`
- Reviewed baseline: `main@a9f6205045648e8889a4dbf4190de65e330caaed`
- Legacy frontend repository: `Newrred/heroine@f722ae87a82775e3cf12c0f188a71f5165c5686e`
- `heroine` is not a second product. Treat it as a historical deployment copy.

If repository HEAD differs from the reviewed baseline:

1. Inspect the actual diff.
2. Update `docs/PROJECT_STATUS.md` before changing code.
3. Preserve newer working behavior unless it conflicts with a confirmed decision.
4. Do not reset, force-push, or discard user changes.

## Confirmed technical decisions

- Keep FastAPI as the backend.
- Keep the frontend deployable as static HTML/CSS/JavaScript.
- Keep LLM inference as a separate OpenAI-compatible process.
- Primary local reference runtime is `llama.cpp`; vLLM support remains optional.
- Initial hardware target is the user's existing Intel i7 / 64 GB RAM / RTX 4070 Ti desktop.
- Initial model class is a swappable 14B-class Q4 GGUF that fits the available VRAM.
- Start with context 4096, parallelism 1, short output, and thinking disabled.
- Static expression assets are the default. ComfyUI remains optional and OFF in the core milestone.
- The backend is authoritative for history, relationship state, flags, and memory.
- Relationship dimensions are `affection`, `trust`, `comfort`, `interest`, and `irritation`.
- The model classifies the interaction; deterministic server code computes relationship deltas.
- Redis may hold ephemeral session/lock/cache state. Durable relationship and memory state must not depend on an expiring Redis key.
- Do not expose the llama.cpp port directly to the internet.

## Engineering constraints

- Prefer incremental refactoring over a rewrite.
- Keep each PR/commit phase-scoped and reversible.
- Preserve current API behavior until a compatibility path and tests exist.
- Centralize enums and schemas; do not duplicate face/emotion lists across modules.
- Use Pydantic for external and LLM output validation.
- Add dependency injection or test seams before adding complex behavior.
- All score updates must be bounded, deterministic, idempotent, and unit-tested.
- Never trust `history`, score totals, flags, or memory supplied by the browser.
- Add a client turn id before allowing retries that can mutate state twice.
- Do not log full private conversation content by default.
- Do not add a cloud dependency to complete a local milestone.

## Security and repository hygiene

Never commit:

- `.env` or local config with credentials
- `*.gguf`, model directories, generated images, or caches
- `trycloudflare.com` temporary URLs
- API keys, tunnel tokens, Redis credentials, or private user data

Required safeguards before public exposure:

- exact CORS origins
- authentication or Cloudflare Access
- request and concurrency limits
- structured error responses
- fixed/named tunnel or equivalent reverse proxy
- backend readiness checks
- content retention policy and backup behavior

## Required workflow for every task

1. Read this file and the task document.
2. Inspect actual code and current git status.
3. Record baseline commands and failures before editing.
4. Make the smallest coherent change that satisfies the task.
5. Add or update automated tests.
6. Run relevant test, lint, and smoke commands.
7. Update `docs/PROJECT_STATUS.md` and `docs/DECISION_LOG.md` when facts or decisions change.
8. Report modified files, behavior changes, commands run, results, known limitations, and the next unblocked task.

Do not silently skip a failing test. Distinguish failures introduced by the change from pre-existing or environment-dependent failures.

## Default verification commands

Discover and use the repository's actual tooling. Until a project-specific command replaces these, the expected baseline is:

```bash
python -m pytest -q
python -m compileall app
```

For a local smoke test:

```bash
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Then verify liveness/readiness and one chat request with a fake or real OpenAI-compatible LLM endpoint. Do not make real-model tests mandatory in CI.

## Definition of done

A task is complete only when:

- acceptance criteria in its task file pass;
- tests cover both success and failure paths;
- no secret or machine-specific path is committed;
- old state can be migrated or safely ignored without data corruption;
- user-visible behavior and configuration are documented;
- `docs/PROJECT_STATUS.md` reflects the actual repository state;
- the final report includes exact commands and results.

## Final report format

```text
Scope completed
Files changed
Behavior changed
Tests/commands run and results
Migration/configuration required
Known limitations
Recommended next task
```


---

<!-- SOURCE: CODEX_START_PROMPT.md -->

# Codex Start Prompt

아래 내용을 `Newrred/npc-chat` 저장소를 연 Codex 작업에 그대로 전달한다.

---

당신은 이 저장소의 구현 담당자다. 먼저 저장소 루트의 `AGENTS.md`와 아래 문서를 우선순위대로 읽어라.

1. `docs/PRODUCT_AND_TECHNICAL_DIRECTION.md`
2. `docs/PROJECT_STATUS.md`
3. `docs/TARGET_ARCHITECTURE.md`
4. `docs/API_AND_DATA_CONTRACTS.md`
5. `docs/IMPLEMENTATION_PLAN.md`
6. `tasks/00_BASELINE_STABILIZATION.md`

이번 작업에서는 **`tasks/00_BASELINE_STABILIZATION.md`만 수행**한다. 관계 엔진, 장기 기억, 공개 배포 등 이후 단계까지 한 번에 구현하지 마라.

시작 전에 다음을 수행하라.

- 현재 브랜치, HEAD, working tree를 확인한다.
- 문서 기준선 `a9f6205045648e8889a4dbf4190de65e330caaed`와 다르면 차이를 검토하고 `docs/PROJECT_STATUS.md`에 기록한다.
- 현재 애플리케이션의 실행/테스트 가능 여부를 먼저 확인한다.
- 사용자 작업을 덮어쓰거나 강제 reset하지 않는다.

작업 원칙:

- `npc-chat`을 유일한 기준 저장소로 유지한다.
- `heroine`은 레거시 배포본으로만 취급한다.
- 기존 FastAPI + 정적 프런트 구조를 유지한다.
- API 호환성을 깨는 변경은 이번 단계에서 하지 않는다.
- 임시 Cloudflare URL, 모델 파일, `.env`, 키를 커밋하지 않는다.
- 실제 LLM이 없어도 테스트 가능한 fake/stub 경로를 마련한다.
- 변경과 함께 테스트, README, `PROJECT_STATUS`를 갱신한다.

완료 후 다음 형식으로 보고하라.

1. 발견한 현재 상태와 기준 문서의 차이
2. 변경한 파일
3. 변경한 동작
4. 실행한 명령과 결과
5. 아직 검증하지 못한 환경 의존 항목
6. 다음 작업으로 `tasks/01_LLM_CONTRACT_AND_LOCAL_RUNTIME.md`를 시작해도 되는지

---


---

<!-- SOURCE: docs/PRODUCT_AND_TECHNICAL_DIRECTION.md -->

# Product and Technical Direction

상태: **현재 기준선**  
검토일: **2026-09-03**

## 1. 제품 정의

이 프로젝트는 캐릭터와 짧게 대화하고, 대화 결과에 따라 표정과 관계가 누적되는 로컬 우선 NPC 챗봇이다. 범용 지식형 AI보다 다음 경험을 우선한다.

- 짧고 자연스러운 한국어 티키타카
- 캐릭터 말투와 태도의 일관성
- 발화에 맞는 표정 및 감정 태그
- 관계 상태에 따라 달라지는 반응
- 재접속·재시작 후에도 이어지는 관계와 기억
- 개인 PC에서 낮은 운영비로 실행 가능한 구조

## 2. 1차 완성 목표

사용자가 브라우저에서 한 문장을 보내면 시스템은 다음을 수행한다.

1. 서버가 사용자·캐릭터 관계 상태와 최근 대화를 불러온다.
2. 로컬 LLM에 캐릭터 지침, 상태 요약, 최근 문맥, 사용자 메시지를 전달한다.
3. LLM은 짧은 대사, 표정, 내면 감정, 감정 태그, 상호작용 분류를 구조화된 JSON으로 반환한다.
4. 서버 관계 엔진이 5개 수치의 변화를 결정한다.
5. 서버가 관계·기억·대화를 저장한다.
6. 프런트엔드가 대사와 정적 표정 이미지를 표시한다.

## 3. 관계 수치

| 키 | 의미 | 주의점 |
|---|---|---|
| `affection` | 사용자에 대한 정서적 호감 | `interest`와 동일하지 않다. |
| `trust` | 사용자를 안전하고 신뢰할 수 있다고 보는 정도 | 단순 칭찬만으로 빠르게 오르지 않는다. |
| `comfort` | 함께 있을 때의 익숙함과 편안함 | 장난을 긍정적으로 받아들일지에 영향을 준다. |
| `interest` | 사용자에게 기울이는 관심과 호기심 | 호감이 낮아도 높을 수 있다. |
| `irritation` | 현재 누적된 짜증·불쾌·긴장 | 다른 수치의 단순 역수가 아니다. |

공통 규칙:

- 총점 범위는 기본적으로 `0..100`이다.
- 초기값은 캐릭터 설정에서 정의한다.
- 일반 대화 한 번의 변화는 대부분 `-2..+2`, 강한 사건도 기본 `-3..+3`으로 제한한다.
- LLM은 총점이나 최종 델타를 직접 확정하지 않는다.
- 같은 긍정 상호작용 반복에 대한 수익 체감이 있어야 한다.
- 점수 변화는 동일 입력·동일 상태에서 동일해야 한다.

## 4. 대사·감정 출력 원칙

- 기본 대사 길이: 한국어 `1..80`자, 보통 1~2문장
- 긴 설명보다 직접적인 말대답을 우선한다.
- thinking/reasoning 텍스트는 사용자에게 노출하지 않는다.
- 표정은 제공된 정적 얼굴 자산 enum 안에서 선택한다.
- 감정 태그는 1~3개로 제한한다.
- 캐릭터 프롬프트와 관계 상태가 충돌하면 안전성과 확정된 캐릭터 원칙을 우선한다.

## 5. 현재 하드웨어·런타임 방향

초기 기준 장비는 사용자가 이미 보유한 다음 데스크톱이다.

- Intel i7 계열 CPU
- RAM 64 GB
- RTX 4070 Ti로 알려진 NVIDIA GPU

실제 VRAM과 드라이버는 `nvidia-smi`로 확인한다. 12 GB VRAM일 경우 초기 프로파일은 다음과 같다.

- 14B-class Q4 GGUF
- llama.cpp OpenAI-compatible server
- context 4096
- parallel 1
- thinking OFF
- ComfyUI OFF
- 정적 표정 이미지 사용

모델명과 양자화는 교체 가능해야 하며 코드에 하드코딩하지 않는다.

## 6. 저장과 기억 방향

### 단기 상태

- 최근 대화
- 처리 중 lock
- 임시 캐시
- 세션 만료

Redis를 사용할 수 있다.

### 장기 상태

- 5개 관계 총점
- 관계 변화 이벤트
- 스토리 플래그
- 롤링 대화 요약
- 중요한 사용자 정보 및 약속

장기 상태는 TTL이 있는 Redis 키 하나에만 저장하지 않는다. 로컬 기본은 SQLite, 이후 필요 시 PostgreSQL로 이동할 수 있도록 저장소 계층을 둔다.

## 7. 이미지 방향

- 기본 경험은 감정 enum → 정적 표정 이미지 전환이다.
- ComfyUI는 코어 대화 경로와 분리된 선택 기능이다.
- 초기 로컬 LLM 테스트에서는 ComfyUI를 끈다.
- 이미지 생성 실패가 대화 실패로 이어지면 안 된다.

## 8. 범위에서 제외되는 항목

1차 코어 완성 단계에서는 다음을 구현하지 않는다.

- 다중 캐릭터 마켓플레이스
- 음성 합성·음성 인식
- 실시간 3D/Live2D 애니메이션
- 결제·구독
- 대규모 공개 운영
- GPU 자동 확장
- 매 턴 실시간 이미지 생성
- 별도 모바일 네이티브 앱

## 9. 품질 목표

실제 모델 평가에서 측정하고 `PROJECT_STATUS`에 기록한다.

- 구조화 출력: 첫 시도 성공률 95% 이상, 재시도 포함 99% 이상
- 허용 enum 준수: 100%
- 서버 관계 계산 결정성: 100%
- 재시작 후 관계 상태 보존: 100%
- 4070 Ti 로컬 프로파일에서 OOM 없이 100턴 연속 실행
- 초기 체감 목표: 짧은 답변 기준 p50 4초 이하, p95 8초 이하

마지막 지연 목표는 실제 모델·드라이버·프롬프트 길이 측정 후 수정할 수 있다.

## 10. 공개 전 통과해야 하는 게이트

외부 사용자에게 열기 전에 최소한 다음이 필요하다.

- 고정 도메인 또는 named tunnel
- 인증 또는 접근 통제
- 정확한 CORS origin
- 사용자/세션별 rate limit 및 동시 요청 제한
- 대화 저장·삭제·보존 정책
- readiness 및 장애 표시
- 로그의 민감정보 최소화
- 백업 또는 복구 절차


---

<!-- SOURCE: docs/PROJECT_STATUS.md -->

# Project Status

마지막 검토: **2026-09-03**  
검토 방식: GitHub `main` 정적 코드 검토. 실제 로컬 실행은 아직 미검증.

## 1. Repository baseline

| 저장소 | HEAD | 상태 |
|---|---|---|
| `Newrred/npc-chat` | `a9f6205045648e8889a4dbf4190de65e330caaed` | 개발 기준 |
| `Newrred/heroine` | `f722ae87a82775e3cf12c0f188a71f5165c5686e` | 레거시 프런트 배포본 |

Codex는 실제 작업 시작 시 이 표를 현재 HEAD로 갱신한다.

## 2. 검증된 현재 구현

| 영역 | 현재 구현 | 주요 파일 |
|---|---|---|
| Backend | FastAPI 앱과 `/api/chat`, `/api/health`, `/api/image/status` | `app/main.py` |
| LLM | OpenAI-compatible 호출, vLLM/llama.cpp factory | `app/services/llm_service.py`, `llama_cpp_service.py`, `llm_service_factory.py` |
| Character | JSON 기반 캐릭터 prompt sections | `app/character_config.py`, `app/characters/default.json` |
| Structured output | reply, face, internal emotion, affection delta, tags, flags, one-line memory | `app/services/llm_service.py`, `app/models.py` |
| Session | Redis JSON state, TTL, per-session lock | `app/session_store.py` |
| Relationship | `affection_total` 한 개를 LLM delta로 누적 | `app/main.py`, `app/session_store.py` |
| Memory | 최근 history 최대 20메시지 + 덮어쓰기식 `memory_1line` | `app/main.py`, `llm_service.py` |
| Frontend | 정적 HTML/CSS/JS, 감정별 PNG, localStorage session id | `frontend/` |
| Image | 정적 표정 기본 + 선택적 비동기 ComfyUI 생성/캐시 | `app/services/comfy_service.py` |
| Front deployment | `frontend/`를 GitHub Pages에 배포하는 Action | `.github/workflows/pages.yml` |

## 3. 확인된 구조적 문제

### P0: 즉시 수정

- `.env.example`의 기본 LLM URL이 백엔드 실행 포트 `8000`과 충돌한다.
- `frontend/config.js`에 임시 `trycloudflare.com` URL이 하드코딩돼 있다.
- `frontend/app.js`는 한글 인코딩 및 문자열 손상이 있고, `index.html`은 별도 `app.fixed.js`를 로드한다.
- `npc-chat/frontend`와 `heroine`이 사실상 중복돼 배포 기준이 불명확하다.
- backend test/CI가 없다.
- `/api/health`는 의존성 상태를 확인하지 않고 항상 `ok`를 반환한다.
- CORS 기본값이 `*`이다.

### P1: 코어 구조 개선

- face enum과 감정 관련 규칙이 여러 파일에 중복돼 drift 가능성이 있다.
- llama.cpp 경로는 guided JSON 없이 텍스트 추출·재시도에 의존한다.
- 응답 길이가 10~50자로 강제돼 매우 짧은 캐릭터 반응을 막는다.
- `NPC_MAX_TOKENS=1024`는 짧은 구조화 응답에 과도하다.
- backend가 초기 세션에서 브라우저가 제공한 history를 수용한다.
- `flags_set`에 서버 allowlist가 없다.

### P2: 제품 기능 부족

- 관계 수치가 `affection_total` 하나뿐이다.
- LLM이 관계 delta를 직접 결정해 밸런스와 모델 교체 안정성이 낮다.
- Redis TTL 기본 1시간으로 모든 관계·기억이 사라질 수 있다.
- 장기 기억은 1줄 덮어쓰기뿐이다.
- 사용자 계정 또는 지속 가능한 로컬 profile 개념이 없다.
- 중복 요청의 상태 이중 적용을 막는 idempotency key가 없다.

### P3: 공개 운영 전 부족

- 인증 및 rate limit이 없다.
- 임시 quick tunnel을 전제로 한다.
- structured application error contract가 없다.
- 로그, metrics, readiness, 백업 정책이 없다.
- 메인 PC에서 게임/디자인 작업과 GPU 경합 시 동작 정책이 없다.

## 4. 아직 검증되지 않은 항목

- 사용자의 GPU가 정확히 RTX 4070 Ti 12 GB인지 여부
- 현재 Windows/CUDA/Python 버전
- 현재 코드가 Redis와 함께 실제로 부팅되는지
- 선택할 14B GGUF의 정확한 모델·파일 크기·chat template
- 4070 Ti에서 실제 latency, VRAM, schema 성공률
- 현재 GitHub Pages와 quick tunnel URL의 생존 여부
- ComfyUI remote `/generate` API의 실제 구현 여부

## 5. 단계별 상태

| 단계 | 상태 | 완료 조건 |
|---|---|---|
| 00 Baseline stabilization | 미착수 | 실행 기준·프런트 중복·config·기초 테스트 정리 |
| 01 LLM contract/local runtime | 미착수 | 중앙 schema, fake tests, 14B local profile 검증 |
| 02 Five-stat relationship | 미착수 | 5수치 결정론 엔진 및 migration 완료 |
| 03 Durable persistence/memory | 미착수 | 재시작 후 관계·기억 보존 |
| 04 Frontend/reliability/evaluation | 미착수 | backend-authoritative flow, UX, 평가 리포트 |
| 05 Secure remote alpha | 미착수 | fixed endpoint, access control, limits, readiness |
| 06 Optional Comfy/cloud fallback | 보류 | 코어 제품 지표와 운영 필요가 확인된 후 수행 |

## 6. Codex update rule

각 task 완료 시 다음을 이 파일에 반영한다.

- 실제 HEAD 및 브랜치
- 완료된 항목
- 실행한 테스트와 결과
- 새로 확인한 환경 사실
- 남은 blocker
- 다음 task 시작 가능 여부


---

<!-- SOURCE: docs/TARGET_ARCHITECTURE.md -->

# Target Architecture

## 1. 설계 목표

- 기존 FastAPI와 정적 프런트를 유지한다.
- 로컬 14B GGUF와 클라우드 OpenAI-compatible backend를 교체 가능하게 한다.
- 모델의 창의적 대사 생성과 게임 상태 계산을 분리한다.
- 관계·기억이 서버 재시작 및 Redis TTL로 사라지지 않게 한다.
- 실제 LLM 없이도 테스트할 수 있게 한다.
- 개인 로컬 사용에서 시작해 보안 게이트를 통과한 뒤 원격/공개 사용으로 확장한다.

## 2. 목표 구성

```text
Browser / Static Frontend
        |
        | POST /api/chat (client_turn_id, message)
        v
FastAPI API Layer
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
  Redis: ephemeral session, distributed lock, cache
  SQLite: profile, relationship, flags, memories, processed turns
```

## 3. 책임 경계

### Frontend

담당:

- 사용자 입력
- 대사·표정·상태 표시
- `client_turn_id` 생성
- loading/retry/offline UX
- non-secret runtime API URL

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
  session_store.py          # Redis ephemeral state/lock
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
- Redis는 lock/cache/session 용도

이 선택의 이유:

- SQLite로 별도 유료 서비스 없이 시작할 수 있다.
- 저장소 계층을 통해 PostgreSQL로 이동 가능하다.
- 관계·기억을 TTL과 분리한다.
- schema migration을 명시적으로 관리할 수 있다.

Redis가 없는 최소 개발 모드를 둘 수 있으나, 실제 동시 요청 검증에서는 Redis lock 경로를 유지한다.

## 7. LLM runtime profile

기본 로컬 profile:

```text
Backend: llama.cpp OpenAI-compatible server
Bind: 127.0.0.1 only
Port: 8001
Model: configurable 14B-class Q4 GGUF
Context: 4096
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
| Redis lock timeout | 409/503 및 재시도 안내 | 변경 없음 |
| DB commit failure | 오류 반환 | transaction rollback |
| Comfy failure | 정적 표정 유지 | 대화 성공 유지 |
| local GPU OOM | readiness false 및 명확한 오류 | 변경 없음 |

## 10. Remote access boundary

```text
Internet
   |
Cloudflare Access / Reverse Proxy
   |
FastAPI 127.0.0.1:8000
   |
llama.cpp 127.0.0.1:8001
```

외부 클라이언트가 llama.cpp 포트에 도달하는 경로를 만들지 않는다. quick tunnel은 일시적 개발 확인 외에 운영 경로로 사용하지 않는다.


---

<!-- SOURCE: docs/API_AND_DATA_CONTRACTS.md -->

# API and Data Contracts

상태: 목표 계약. 단계별 migration 동안 기존 필드를 임시 호환할 수 있다.

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

```json
{
  "status": "ready",
  "dependencies": {
    "llm": "ok",
    "redis": "ok",
    "database": "ok"
  },
  "model": "configured-model-id"
}
```

의존성 하나라도 필수 조건을 충족하지 않으면 503을 반환한다. ComfyUI는 코어 readiness의 필수 의존성이 아니다.

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


---

<!-- SOURCE: docs/IMPLEMENTATION_PLAN.md -->

# Implementation Plan

## Execution rule

한 번에 한 단계만 구현한다. 각 단계는 독립 branch/PR 또는 명확한 commit 범위를 사용한다. 다음 단계는 이전 단계의 acceptance criteria가 통과한 뒤 시작한다.

## Phase 00 — Baseline stabilization

Task file: `tasks/00_BASELINE_STABILIZATION.md`

목표:

- 현재 코드를 재현 가능하고 테스트 가능한 기준선으로 만든다.
- API 기능은 바꾸지 않고 저장소·프런트·config 혼선을 정리한다.

핵심 작업:

- current HEAD/runtime audit
- backend/LLM port 분리
- `app.fixed.js`/손상된 `app.js` 정리
- quick tunnel URL 제거
- `npc-chat`을 유일한 frontend source로 확정
- liveness/readiness groundwork
- fake LLM을 이용한 baseline API test
- Python CI 추가
- Windows local helper scripts 및 README 갱신

## Phase 01 — LLM contract and local runtime

Task file: `tasks/01_LLM_CONTRACT_AND_LOCAL_RUNTIME.md`

목표:

- 모델 backend와 무관한 canonical structured output을 만든다.
- 4070 Ti + 14B Q4 로컬 실행을 검증한다.

핵심 작업:

- face/emotion enum 중앙화
- Pydantic `LLMDecision` schema
- nested output, reply 1..80, max token 축소
- capability-aware JSON mode/fallback parser
- test injection seam 및 fake LLM
- local model start/doctor/benchmark scripts
- real-model evaluation 결과 기록

## Phase 02 — Five-stat relationship engine

Task file: `tasks/02_RELATIONSHIP_ENGINE.md`

목표:

- 기존 단일 호감도를 5개 관계 수치로 확장한다.
- LLM delta를 결정론적 server engine으로 대체한다.

핵심 작업:

- `RelationshipState`, `RelationshipDelta`
- `InteractionType` and intensity
- deterministic matrix and modifiers
- migration compatibility
- prompt state injection
- API response and temporary compatibility fields
- relationship unit/property tests
- frontend debug visualization

## Phase 03 — Durable persistence and memory

Task file: `tasks/03_DURABLE_PERSISTENCE_AND_MEMORY.md`

목표:

- 관계·플래그·기억이 Redis TTL 또는 재시작으로 사라지지 않게 한다.

핵심 작업:

- SQLAlchemy + SQLite + Alembic
- profile/relationship/turn/memory tables
- repository interface
- Redis를 ephemeral state/lock로 제한
- `client_turn_id` idempotency transaction
- rolling summary and memory candidates
- restart/migration tests

## Phase 04 — Frontend reliability and evaluation

Task file: `tasks/04_FRONTEND_RELIABILITY_AND_EVALUATION.md`

목표:

- 실제 개인 사용에 필요한 오류·재시도·상태 표시를 완성하고 모델 품질을 측정한다.

핵심 작업:

- client history 제거
- client turn id 및 safe retry
- loading/offline/error states
- 관계 변화 UI와 debug mode
- expression asset fallback validation
- model conversation evaluation suite
- latency/schema/VRAM report
- main PC GPU conflict runbook

## Phase 05 — Secure remote alpha

Task file: `tasks/05_SECURE_REMOTE_ALPHA.md`

목표:

- 개인 원격 사용 또는 제한된 테스트 사용자에게 안전하게 노출한다.

핵심 작업:

- named tunnel/fixed domain
- Cloudflare Access or equivalent auth
- exact CORS
- per-user/session rate and concurrency limits
- frontend config injection through deployment variables
- readiness, structured logs, retention, backup
- remote smoke and failure tests

## Phase 06 — Optional Comfy and cloud fallback

Task file: `tasks/06_OPTIONAL_COMFY_AND_CLOUD_FALLBACK.md`

목표:

- 코어 지표로 필요성이 확인된 경우에만 이미지 생성 또는 cloud fallback을 추가한다.

진입 조건:

- 100턴 이상 안정적인 로컬 대화
- 관계·기억 persistence 안정화
- 외부 사용량 또는 메인 PC 경합 데이터 확보
- 추가 GPU 비용을 정당화하는 사용자 경험 이득 확인

## Cross-phase migration constraints

- 기존 Redis state는 durable migration 성공 전 삭제하지 않는다.
- 기존 frontend가 새 API로 전환될 때까지 compatibility fields를 유지한다.
- `heroine`은 archive/deprecation 안내 외에 기능 개발하지 않는다.
- database migration에는 downgrade 또는 명확한 backup/restore 절차가 있어야 한다.
- 각 단계에서 문서와 code reality가 일치하도록 `PROJECT_STATUS`를 갱신한다.


---

<!-- SOURCE: docs/LOCAL_4070TI_RUNBOOK.md -->

# Local RTX 4070 Ti Runbook

상태: Codex가 실제 PC에서 검증하고 명령을 조정해야 하는 기준 절차.

## 1. 목적

사용자의 메인 Windows 데스크톱에서 다음 프로세스를 분리해 실행한다.

```text
llama.cpp server : 127.0.0.1:8001
FastAPI backend  : 127.0.0.1:8000
Redis            : 127.0.0.1:6379
Static frontend  : local server or GitHub Pages
```

초기 단계에서는 ComfyUI를 실행하지 않는다.

## 2. 사전 확인

PowerShell:

```powershell
nvidia-smi
python --version
git --version
```

기록할 정보:

- GPU 정확한 이름
- total/free VRAM
- NVIDIA driver 및 CUDA runtime
- Python version
- Windows version
- LLM 실행 전·후 VRAM

GPU가 12 GB라면 14B Q4, context 4096, parallel 1을 시작점으로 한다. 실제 모델이 fit하지 않으면 context를 먼저 낮추고, GPU를 사용하는 다른 앱을 닫은 뒤, 더 작은 quant/model을 검토한다.

## 3. Model storage

모델 파일은 저장소 밖에 둔다.

예:

```text
D:\AI\models\npc-chat\model-14b-q4.gguf
```

Repository `.gitignore`에는 최소한 다음을 포함한다.

```gitignore
models/
*.gguf
*.safetensors
```

## 4. llama.cpp reference launch

로컬 llama.cpp build의 `--help`를 먼저 확인한다. 일반적인 기준 명령은 다음과 같다.

```powershell
.\llama-server.exe `
  --model "D:\AI\models\npc-chat\model-14b-q4.gguf" `
  --host 127.0.0.1 `
  --port 8001 `
  --n-gpu-layers 999 `
  --ctx-size 4096 `
  --parallel 1
```

Flash attention 및 chat-template 관련 옵션은 설치된 llama.cpp 버전과 모델 metadata를 확인한 후 launch script에 추가한다. 지원 여부를 추측해 하드코딩하지 않는다.

검증:

```powershell
Invoke-RestMethod http://127.0.0.1:8001/v1/models
```

## 5. Redis reference launch

Docker 사용 시 Redis만 container로 실행할 수 있다.

```powershell
docker run --name npc-chat-redis `
  -p 127.0.0.1:6379:6379 `
  -v npc_chat_redis_data:/data `
  -d redis:7-alpine redis-server --appendonly yes
```

Codex는 반복 사용을 위해 `docker-compose.dev.yml` 또는 동등한 script를 추가한다.

검증:

```powershell
docker exec npc-chat-redis redis-cli ping
```

## 6. Python backend

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
```

Local `.env` 기준:

```env
NPC_CHARACTER_ID=default
NPC_LLM_BACKEND=llama_cpp
NPC_BASE_URL=http://127.0.0.1:8001/v1
NPC_API_KEY=local-only
NPC_MODEL=local-14b-q4
NPC_TIMEOUT=120
NPC_MAX_TOKENS=256
CORS_ORIGINS=http://127.0.0.1:5500,http://localhost:5500
REDIS_URL=redis://127.0.0.1:6379/0
COMFY_ENABLED=false
COMFY_CONNECT=false
```

Backend:

```powershell
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

## 7. Smoke checks

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/live
Invoke-RestMethod http://127.0.0.1:8000/api/ready
```

Chat example after the target contract exists:

```powershell
$body = @{
  client_turn_id = [guid]::NewGuid().ToString()
  message = "오늘 뭐 했어?"
  comfy_on = $false
} | ConvertTo-Json

Invoke-RestMethod `
  -Method Post `
  -Uri http://127.0.0.1:8000/api/chat `
  -ContentType "application/json" `
  -Body $body
```

## 8. Start and stop order

Start:

1. Redis
2. llama.cpp
3. FastAPI
4. frontend

Stop:

1. frontend dev server
2. FastAPI
3. llama.cpp
4. Redis only when maintenance is required

## 9. Main-PC coexistence policy

초기에는 Windows 부팅 시 자동 실행하지 않는다. 명시적인 start/stop script로 운영한다.

- 게임, 3D, 영상, Stable Diffusion 작업 전 llama.cpp를 종료한다.
- LLM startup script는 free VRAM을 검사하고 부족하면 시작을 거부하거나 경고한다.
- inference 중 GPU OOM이 발생하면 백엔드는 상태를 변경하지 않고 503을 반환한다.
- 메인 PC 작업 중 클라우드 fallback은 Phase 06 이전에 구현하지 않는다.

Codex가 추가할 권장 scripts:

```text
scripts/doctor.ps1
scripts/start-local.ps1
scripts/stop-local.ps1
scripts/benchmark-local.ps1
```

## 10. Benchmark record

`benchmark-local`은 최소한 다음을 JSON/Markdown으로 기록한다.

- model id / file hash or filename
- llama.cpp build identifier
- context / parallel / token cap
- prompt tokens / completion tokens
- time to first token when available
- total latency
- tokens per second
- VRAM before/peak/after
- schema first-pass success
- retry count

실제 결과를 `docs/PROJECT_STATUS.md`에 요약하고, raw 결과는 `artifacts/benchmarks/`에 저장하되 개인 대화 내용은 포함하지 않는다.


---

<!-- SOURCE: docs/TEST_AND_ACCEPTANCE_PLAN.md -->

# Test and Acceptance Plan

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
- error response conforms to contract

### Persistence tests

- backend restart preserves relationship
- Redis key expiry does not delete durable relationship
- legacy Redis state migrates once
- migration can be rerun safely
- SQLite transaction remains consistent after injected failure

### Frontend tests

최소 smoke scope:

- frontend loads with neutral image
- submit button prevents accidental double submit
- loading/error/retry state
- face slug mapping and fallback
- relationship delta display in debug mode
- no hardcoded quick tunnel URL in built artifact

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


---

<!-- SOURCE: docs/DEPLOYMENT_AND_SCALING_GATES.md -->

# Deployment and Scaling Gates

## Stage A — Local development

Users: developer only  
Runtime: localhost  
Required:

- llama.cpp bound to 127.0.0.1
- FastAPI bound to 127.0.0.1
- Redis/SQLite local
- Comfy OFF
- automated tests and local runbook

No tunnel is required.

## Stage B — Personal remote access

Users: owner only  
Required before entry:

- Phase 00~04 complete
- named/fixed tunnel
- Cloudflare Access or equivalent identity gate
- exact CORS origin
- no direct LLM exposure
- safe restart and readiness
- state backup

A temporary `trycloudflare.com` URL is not an acceptable 24/7 endpoint.

## Stage C — Small private beta

Users: invited testers  
Required:

- per-user or per-session authentication
- rate limit and single-session concurrency control
- terms/notice for stored conversations
- delete/reset relationship function
- structured logs without raw content by default
- queue depth and latency visibility
- clear offline state when the home PC is unavailable

## Stage D — Public alpha

Required:

- durable user identity and access revocation
- abuse and prompt injection testing
- privacy/retention policy
- backup and restore drill
- uptime expectation and maintenance behavior
- capacity test using measured tokens/sec and concurrency
- public-safe character/IP configuration
- cloud or second-node failure strategy if uptime is promised

## Stage E — Cloud fallback or dedicated server

Do not enter based on assumed user counts. Use measured triggers.

Possible triggers:

- main PC must remain available for work/games and LLM interruption is frequent
- queue p95 exceeds the product threshold during real usage
- local machine unavailability causes unacceptable failed sessions
- cloud serverless monthly spend is consistently above the amortized cost of a dedicated node
- one GPU cannot meet measured concurrency after batching/queue controls

## Capacity policy for the current PC

Initial service mode:

```text
one local model
one parallel slot
one active generation per session
bounded queue
short response cap
```

Before increasing `parallel`, measure VRAM and latency. 12 GB VRAM should not be assumed to support multiple long-context slots safely.

## Failure and availability disclosure

When the home PC or LLM is unavailable:

- frontend must show an explicit offline/unavailable state
- do not fabricate a reply
- do not mutate relationship or memory
- retry must reuse the same `client_turn_id`

Cloud fallback is optional. It must not silently use a different model without recording the serving backend and validating compatible behavior.

## Hardware purchase gate

Do not purchase a dedicated sub-1,000,000 KRW server until at least one is true:

1. the main PC cannot be kept available for the intended use;
2. local LLM materially interferes with normal work or gaming;
3. measured remote usage justifies always-on hardware;
4. serverless/cloud cost and usage data show a credible local payback;
5. the product has passed relationship, persistence, and quality validation.

The existing RTX 4070 Ti machine remains the development and validation baseline.


---

<!-- SOURCE: docs/DECISION_LOG.md -->

# Decision Log

## Confirmed decisions

| ID | Decision | Status | Rationale |
|---|---|---|---|
| REPO-01 | `Newrred/npc-chat` is the single source repository. | Confirmed | Backend and frontend already coexist and Pages workflow exists. |
| REPO-02 | `Newrred/heroine` is a legacy deployment copy. | Confirmed | Avoid duplicate frontend drift. |
| STACK-01 | Keep FastAPI + static HTML/CSS/JS. | Confirmed | Existing implementation is sufficient; no rewrite needed. |
| RUNTIME-01 | Use the existing i7/64 GB/RTX 4070 Ti desktop first. | Confirmed | Zero additional hardware cost for validation. |
| MODEL-01 | Initial target is a swappable 14B-class Q4 GGUF. | Confirmed baseline | Exact model remains an evaluation choice. |
| LLM-01 | LLM runs as a separate OpenAI-compatible service. | Confirmed | Supports llama.cpp locally and other backends later. |
| OUTPUT-01 | Reply is short Korean dialogue plus expression/emotion metadata. | Confirmed | Core product requirement. |
| REL-01 | Relationship has affection, trust, comfort, interest, irritation. | Confirmed baseline | Implements requested approximately five relationship/emotion scores. |
| REL-02 | LLM classifies interaction; server calculates deltas. | Confirmed | Stable balancing and model portability. |
| STATE-01 | Backend is authoritative for history, scores, flags, memory. | Confirmed | Prevent client tampering and drift. |
| PERSIST-01 | Redis is ephemeral; durable state uses SQLite initially. | Confirmed direction | Prevent TTL data loss and support later PostgreSQL migration. |
| IMAGE-01 | Static expressions are default; ComfyUI is optional and OFF initially. | Confirmed | Avoid 12 GB VRAM contention and protect chat reliability. |
| DEPLOY-01 | Local-first; no public exposure until security gates pass. | Confirmed | Current quick tunnel/CORS/auth state is insufficient. |
| DELIVERY-01 | Implement one task/phase at a time with tests. | Confirmed | Limits regression and Codex scope drift. |

## Open gates

| ID | Question | Blocks |
|---|---|---|
| MODEL-G01 | Which exact 14B model/quant/chat template wins evaluation? | Final runtime profile |
| CHAR-G01 | Final original character identity, tone, boundaries, and initial scores? | Production prompt/content |
| UI-G01 | Are the five scores user-visible, partially visible, or debug-only? | Final frontend design |
| MEMORY-G01 | Which memory types and retention duration are acceptable? | Public/persistent memory policy |
| AUTH-G01 | Personal-only access, invited beta, or public accounts? | Remote architecture |
| IMAGE-G01 | Does generated portrait variation materially improve experience? | Comfy phase |
| SCALE-G01 | What measured concurrency/uptime target is required? | Cloud fallback/dedicated hardware |
| DATA-G01 | Are full message bodies retained, summarized, or deleted after processing? | Privacy and DB schema |

## Decision change procedure

When changing a confirmed decision:

1. add a new row or amendment with date;
2. explain measured evidence or user instruction;
3. list affected schemas, migrations, tests, and docs;
4. preserve backward compatibility or document explicit breaking migration;
5. update `PROJECT_STATUS`.

Do not silently alter score semantics or API fields during implementation.


---

<!-- SOURCE: tasks/00_BASELINE_STABILIZATION.md -->

# Task 00 — Baseline Stabilization

Priority: P0  
Allowed scope: repository/config/testability cleanup only  
Do not implement five-stat relationship or durable memory in this task.

## Objective

Create a reproducible, non-secret, testable baseline while preserving the current chat API behavior.

## Required work

### 1. Audit and branch

- Record branch, HEAD, dirty files, Python version, and available runtime dependencies.
- Compare actual HEAD with reviewed `a9f6205045648e8889a4dbf4190de65e330caaed`.
- Create a phase-scoped branch such as `codex/p0-baseline-stabilization` when permitted.
- Update `docs/PROJECT_STATUS.md` with any divergence.

### 2. Resolve port/config ambiguity

- Backend remains `127.0.0.1:8000`.
- LLM reference endpoint becomes `127.0.0.1:8001/v1`.
- Correct `.env.example` and README.
- Keep `.env` ignored.
- Reduce the reference completion cap from 1024 to a reasonable temporary value, but do not change output schema yet.
- Replace wildcard CORS example with explicit local origins and document how to override it.

### 3. Consolidate frontend source

- Make `frontend/app.js` the single production script.
- Use the valid UTF-8 logic currently represented by `app.fixed.js` as the safe basis.
- Remove the broken/duplicate script only after verifying `index.html` uses the canonical file.
- Add or retain face asset fallback behavior.
- Remove committed temporary `trycloudflare.com` endpoint values.
- Add `frontend/config.example.js` or deployment-time config generation.
- Do not store a secret in frontend config.

### 4. Repository role clarity

- State in the main README that `npc-chat/frontend` is the source frontend.
- State that `heroine` is a legacy deployment copy and must not receive parallel feature work.
- Do not delete or rewrite the `heroine` repository in this task.

### 5. Health foundation

- Preserve `/api/health` for compatibility.
- Add `/api/live` and an initial `/api/ready` or refactor health so dependency status can be tested.
- ComfyUI must not be a required readiness dependency.
- Dependency checks must have bounded timeouts.

### 6. Test seam and baseline tests

- Introduce the minimum injection seam needed to test `/api/chat` without a real GPU model.
- Add pytest configuration and tests for:
  - liveness
  - current chat success using fake LLM/session dependencies
  - current invalid request behavior
  - Comfy disabled path
- Do not require Redis, GPU, or internet for unit CI unless a service test is explicitly marked integration.

### 7. CI and developer scripts

- Add a GitHub Action for Python tests/compile checks.
- Add initial `scripts/doctor.ps1` that checks ports, Python, `nvidia-smi`, Redis, and LLM endpoint without modifying the machine.
- Add documented local start commands; a full model benchmark can wait for Task 01.

## Acceptance criteria

- `python -m pytest -q` passes without a real LLM.
- `python -m compileall app` passes.
- frontend loads exactly one canonical app script.
- no mojibake in displayed Korean strings.
- no `trycloudflare.com` URL is present in tracked production config.
- README clearly names `npc-chat` as source and `heroine` as legacy.
- backend and LLM reference ports no longer conflict.
- existing response fields remain compatible.
- no model, credential, `.env`, local DB, or generated image is committed.

## Explicit non-goals

- five relationship scores
- SQLAlchemy/Alembic
- long-term memory
- public authentication
- cloud fallback
- ComfyUI redesign

## Completion report

Use the format required by `AGENTS.md` and include exact test output summary.


---

<!-- SOURCE: tasks/01_LLM_CONTRACT_AND_LOCAL_RUNTIME.md -->

# Task 01 — LLM Contract and Local Runtime

Prerequisite: Task 00 accepted.

## Objective

Create one canonical LLM decision contract and verify a 14B-class Q4 GGUF profile on the existing NVIDIA desktop without coupling CI to the real model.

## Required work

### Canonical domain schema

- Centralize FaceType, InternalEmotion, InteractionType.
- Normalize legacy `shy smile` to `shy_smile` at boundaries.
- Implement Pydantic models matching `docs/API_AND_DATA_CONTRACTS.md`.
- Permit reply length 1..80 characters.
- Reject extra keys and out-of-range intensity/memory values.
- Keep a compatibility adapter for the old flat LLM output during migration if required.

### LLM adapter

- Keep OpenAI-compatible transport.
- Represent backend capability explicitly: schema/guided JSON supported or fallback text parsing.
- Disable thinking through backend-appropriate options when supported.
- Use bounded retries and classify transport vs parse failures.
- Avoid app-global hard coupling that prevents fake injection.
- Keep model id, URL, token cap, timeout, temperature, and backend in config.

### Prompt/output

- Update character prompt to request only canonical LLM decision fields.
- Do not ask the model for relationship totals or final deltas.
- Add flag allowlist to character config; unknown flags are discarded and logged as structured diagnostics.
- Reduce completion token default to 256 or lower only after measured schema success.

### Local scripts

Add or complete:

```text
scripts/start-llm.ps1
scripts/stop-llm.ps1
scripts/doctor.ps1
scripts/benchmark-local.ps1
```

Requirements:

- model path is an argument or environment variable
- bind to 127.0.0.1:8001
- context default 4096
- parallel default 1
- free VRAM check before start
- no auto-download and no model file in repository
- print the exact effective command

### Evaluation

- Add fake adapter tests.
- Add a real-model evaluation command that is opt-in.
- Record exact GPU/model/llama.cpp/runtime facts in `PROJECT_STATUS`.
- Run at least 20 representative prompts for the first runtime check; the full 50-case suite is Task 04.

## Acceptance criteria

- CI passes without GPU.
- all canonical schema tests pass.
- old and new response handling cannot produce an invalid face value.
- real local profile either passes 20 prompts or is honestly documented as blocked with the exact failure.
- first-pass and retry schema rates are recorded.
- actual VRAM before/peak/after and latency are recorded when real-model run is possible.
- no relationship totals are model-generated in the new contract.

## Non-goals

- persistent five-stat totals
- score balancing
- public deployment
- Comfy generation


---

<!-- SOURCE: tasks/02_RELATIONSHIP_ENGINE.md -->

# Task 02 — Five-Stat Relationship Engine

Prerequisite: canonical LLM decision contract from Task 01.

## Objective

Replace model-controlled single affection delta with a deterministic five-dimension relationship system while maintaining a safe migration path.

## Required work

### Domain model

Implement:

```text
RelationshipState
RelationshipDelta
RelationshipResult
```

Dimensions:

```text
affection
trust
comfort
interest
irritation
```

- totals 0..100
- per-turn deltas -3..+3
- character-config initial values
- validation at every persistence/API boundary

### Engine

- Implement the base matrix and modifiers in `API_AND_DATA_CONTRACTS.md`.
- Input: current state, canonical interaction, recent successful interaction events.
- Output: delta, next state, reason codes.
- No randomness.
- Repeated invocation with identical input returns identical result.
- Engine has no network or database side effects.

### Chat flow

- Call LLM for decision.
- Call relationship engine after successful validation.
- Apply changes only inside the successful turn transaction boundary.
- On LLM/parse/persistence failure, do not mutate state.
- Add `client_turn_id` support or temporary server idempotency seam if Task 03 transaction storage is not yet present.

### Migration compatibility

- Map legacy `affection_total` to `affection`.
- Use character defaults for other dimensions.
- Continue returning legacy `affection_total`/`affection_delta` while old frontend requires them.
- Mark compatibility fields deprecated in docs.

### Prompt

- Inject all five current values and a compact relationship stage/summary as trusted server context.
- Do not inject raw reason codes unless useful.
- Do not allow user text to masquerade as state.

### Frontend debug

- Show values and per-turn deltas behind a debug toggle or development panel.
- Do not finalize whether all scores are permanently visible to users.

## Required tests

- every base interaction type
- intensity 0..3
- clamp at lower/upper totals
- teasing low/high comfort
- irritation >=70 modifier
- repeated positive interaction attenuation
- legacy migration
- identical input determinism
- failed turn leaves state unchanged
- duplicate application prevention seam

## Acceptance criteria

- no code path accepts LLM-provided final delta as authoritative.
- all five totals are returned in the new API shape.
- legacy frontend still works through compatibility fields.
- relationship engine has complete unit coverage for documented rules.
- `PROJECT_STATUS` contains the implemented rule version.


---

<!-- SOURCE: tasks/03_DURABLE_PERSISTENCE_AND_MEMORY.md -->

# Task 03 — Durable Persistence and Memory

Prerequisite: Task 02 relationship domain and tests.

## Objective

Persist relationship, flags, turns, summary, and selected memories independently of Redis TTL and make turn processing idempotent.

## Required work

### Database foundation

- Add SQLAlchemy 2.x and Alembic.
- Default local database: SQLite file under an ignored runtime data directory.
- Define a repository protocol so PostgreSQL can replace SQLite later.
- Add backup/export documentation before destructive migration.

### Minimum tables

- profiles
- character_relationships
- turns or relationship_events
- memories
- processed client turns/idempotency records

Use normalized columns for five scores. JSON may be used for small metadata but not as a substitute for all queryable state.

### Transaction boundary

One successful chat turn must atomically persist:

- user/assistant turn
- canonical expression and interaction
- relationship delta and resulting totals
- flags
- accepted memory candidates
- rolling summary when updated
- processed `client_turn_id`

If commit fails, return an error and leave no partial mutation.

### Redis role

Keep Redis for:

- session lookup/cache
- session lock
- short-lived image state

Do not make durable relationship depend on Redis expiration. Add a documented development fallback only if it does not weaken production correctness.

### Memory v1

Implement:

- recent turn window
- rolling summary with a strict size budget
- memory candidates of limited kinds
- normalization and duplicate detection
- importance/confidence bounds
- retrieval of a small relevant set for prompt construction

Do not implement embeddings/vector DB in this task. Deterministic lexical/recency/importance selection is sufficient.

### Legacy migration

- Migrate existing Redis affection/flags/memory/history when present.
- Migration must be idempotent.
- Preserve source until durable commit succeeds.
- Provide a dry-run or clear log summary.

## Required tests

- fresh profile creation
- restart persistence
- Redis expiry independence
- duplicate `client_turn_id`
- transaction rollback at injected failure points
- legacy migration once and repeat
- memory dedupe and size cap
- profile reset/delete behavior at repository layer

## Acceptance criteria

- relationship survives backend and Redis restart.
- same client turn never changes state twice.
- all persistence tests use temporary isolated databases.
- Alembic upgrade from empty DB succeeds.
- documented backup/restore procedure exists.


---

<!-- SOURCE: tasks/04_FRONTEND_RELIABILITY_AND_EVALUATION.md -->

# Task 04 — Frontend Reliability and Model Evaluation

Prerequisite: durable chat flow.

## Objective

Make the static frontend reliable for daily personal use and produce measured evidence for the chosen local model.

## Required work

### Backend-authoritative client

- Stop sending history or state as authoritative request data.
- Generate and retain `client_turn_id` for retries.
- Prevent double submission while a turn is active.
- Reuse the same id on network retry; generate a new id only for a new user message.

### UX states

Implement explicit states:

```text
idle
sending
waiting_for_model
success
retryable_error
non_retryable_error
offline
```

- Never show a fabricated character response on failure.
- Show static face immediately after a valid response.
- Comfy status remains secondary.
- Keep a hidden/debug panel for raw emotion, reason codes, latency, and five score deltas.

### Expression assets

- Validate all canonical face files at build/test time.
- Keep fallback chain to neutral.
- Remove obsolete spelling aliases from user-facing output while accepting legacy input.

### Relationship UI

Implement a configuration-controlled choice:

- debug-only exact values, default for development
- optional user-facing bars/labels later

Do not make hidden exact score visibility a permanent product decision without updating `DECISION_LOG`.

### Evaluation suite

- Expand to at least 50 representative Korean cases.
- Run the exact chosen model profile.
- Record:
  - schema first-pass/retry rates
  - latency p50/p95
  - output length distribution
  - face/emotion distribution
  - VRAM and OOM behavior
  - manual naturalness scores
  - failure examples
- Compare at least one smaller or alternative model only if readily available; do not auto-download large models without user direction.

### Main-PC operation

- Verify stop/start scripts.
- Confirm behavior while common GPU applications are open.
- Document the condition that should block model startup based on free VRAM.

## Acceptance criteria

- duplicate clicks/retries do not duplicate state.
- offline LLM produces clear retryable UI and no score change.
- all canonical face assets have a valid fallback.
- 50-case evaluation report is stored in docs/artifacts without private conversations.
- quality and latency gates in `TEST_AND_ACCEPTANCE_PLAN` are evaluated with measured results.


---

<!-- SOURCE: tasks/05_SECURE_REMOTE_ALPHA.md -->

# Task 05 — Secure Remote Alpha

Prerequisite: local daily-use path is stable and measured.

## Objective

Expose the app for owner-only or invited remote use without exposing the model server or relying on temporary tunnel URLs.

## Required work

### Network boundary

- Use a named/fixed tunnel or equivalent reverse proxy.
- Publish only the FastAPI application or a controlled frontend/API boundary.
- Keep llama.cpp on 127.0.0.1:8001.
- Remove all quick-tunnel assumptions from documentation and deployment config.

### Access control

Choose and document one entry mode:

- owner-only Cloudflare Access, or
- invited user authentication.

Do not put a reusable secret in static JavaScript.

### Limits

- per-user/session requests per minute
- maximum concurrent active turn per session
- global bounded queue
- input/output caps
- explicit 429/503 errors

### Frontend deployment config

- Generate non-secret API URL from GitHub Actions variables or equivalent.
- No hardcoded machine-specific URL in source.
- exact CORS origins
- cache behavior that does not pin obsolete config indefinitely

### Observability and operations

- request id
- structured status/error logs
- no raw message body by default
- readiness dependency status
- queue/latency/error counters
- startup and recovery runbook
- SQLite backup and restore
- clear UI when home server is offline

### Security tests

- unauthorized access denied
- CORS rejects unexpected origin
- rate limit works
- prompt injection cannot alter server-owned state/schema
- direct LLM port not externally reachable
- duplicate turn remains idempotent across network retries

## Acceptance criteria

- remote access works through a stable endpoint.
- no model endpoint or Redis port is public.
- access control is enforced before chat requests reach the app.
- security and failure checks are documented with results.
- public alpha is not claimed unless privacy/retention decisions are completed.


---

<!-- SOURCE: tasks/06_OPTIONAL_COMFY_AND_CLOUD_FALLBACK.md -->

# Task 06 — Optional ComfyUI and Cloud Fallback

Status: gated; do not execute automatically.

## Entry conditions

- local chat, relationship, persistence, and secure remote path are complete
- measured user experience shows a need
- GPU/resource and cloud cost limits are approved

## Track A — ComfyUI

Goals:

- generated portrait never blocks text chat
- explicit queue, timeout, cancellation, cache, and retry behavior
- GPU coexistence policy with the 14B model
- persistent or disposable image policy
- generated image provenance/status visible in debug

Required review of current implementation:

- in-memory cache/status loss on restart
- background task shutdown/cancellation
- remote `/generate` API contract
- per-session cache key and retention
- image URL trust and expiry
- 12 GB VRAM contention

Prefer a separate worker or remote GPU over running full image generation concurrently with a near-VRAM-capacity LLM on the same 4070 Ti.

## Track B — Cloud fallback

Goals:

- fallback only after local readiness failure or queue policy
- same canonical schema and relationship engine
- serving backend recorded per turn
- explicit cost and request limits
- no silent model behavior mismatch
- health-based circuit breaker and manual disable switch

## Acceptance criteria

- text chat remains functional when image generation fails.
- fallback cannot apply one user turn twice.
- monthly spending cap and observability exist before enabling cloud calls.
- evaluation confirms fallback model is contract-compatible.
