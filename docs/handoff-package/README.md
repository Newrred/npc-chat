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
