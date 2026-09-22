# Implementation Plan

2026-09-22 외부 검토 후속: Task27 정확성, Task28 비개인 계측·독립 세트 뒤 Task29의 metadata compact는 분류 비열화로 미채택했다. Task30에서 exact TokenCounter의 연결 재사용과 요청 범위 동일 입력 cache를 적용해 prepare p50을 0.578→0.297초로 줄였지만 전체 모델 생성 시간 개선은 확인하지 못했다. 기본/공개는 full을 유지한다. 다음은 테스터 확대 전 고정 주소·guest 지속성·두 DB 백업/복구·자동 복구/1→2→3→5명 부하 게이트다. 의미 검색은 검색 실패 단계를 분리한 뒤 shadow 비교로만 시작한다.

2026-09-08 Task12/EXP08 기억 전달 경로 구현·공개 적용 완료. 다음은 다양한 정정/추천 충돌·취소와 긴 문맥의 비용 평가다. [결과](MEMORY_PIPELINE.md).

2026-09-08 Task 11/EXP-07 동일 모델 두 단계 생성 구현·공개 검증 완료. 다음 검증은 새로운 표현에서 대사 품질과 부가 정보 오분류를 분리 평가하고 총 지연을 측정하는 것이다. [결과와 한계](TWO_STAGE_GENERATION.md).

2026-09-07 최신 배포 방향: 사용자 요청에 따라 기본을 로그인 없는 guest 공개 링크로 전환했다. 공개 전 검증은 이메일 로그인 대신 자동 쿠키·브라우저별 기록 분리·활동 방문자/일일 한도·쿠키 초기화 후 전체 한도 유지에 집중한다. 나머지 보관/삭제·복구·부하/품질 게이트는 유지한다. PUBLIC_LINK_DEPLOYMENT.md 참고.

2026-09-07 후속 요청: 테스트 이후 운영을 염두에 둔 Phase05 배포 준비를 시작했다. Phase04 품질 검토는 남아 있으며 공개 전 게이트로 유지한다. 현재 인증/소유권/제한 및 설정 검사 구현, 실제 도메인 연결·보관 삭제·서비스 복구·부하 검증은 미완료다. REMOTE_DEPLOYMENT_RUNBOOK.md 참고.

2026-09-07 현재 개발 장비 결정: 사용자 요청에 따라 RTX 3060 Ti 8 GB / RAM 약 32 GB에서 테스트한다. 속도 우선 4B Q4_K_M 모델, context 2048, parallel 1, output 256, GPU layers all, batch/ubatch 128, thinking OFF를 시작점으로 한다. 4070 Ti/14B Q4 관련 아래 기준은 향후 확장 프로파일이며 현재 단계의 필수 조건이 아니다. 실행과 실측은 [현재 로컬 런북](LOCAL_DEVELOPMENT_RUNBOOK.md), [상태 기록](PROJECT_STATUS.md)을 우선한다.

## Execution rule

한 번에 한 단계만 구현한다. 각 단계는 독립 branch/PR 또는 명확한 commit 범위를 사용한다. 다음 단계는 이전 단계의 acceptance criteria가 통과한 뒤 시작한다.

2026-09-07 합의: 목표 기본 배포는 **웹앱 하나 + 모델 서버 하나**다. SQLite는 파일 저장소이며 별도 서버가 아니다. 아래 순서를 필수로 적용하고 각 단계의 실제 완료 여부는 `PROJECT_STATUS`에 별도로 기록한다.

| 순서 | 담당 단계 | 완료 조건 |
|---|---|---|
| 화면/API 통합 | Phase 01의 첫 작업 | FastAPI 한 주소에서 화면·정적 자산·API 사용, 별도 프런트 서버 없이 smoke 통과 |
| 시작/종료 통합 | Phase 01 | 필수 start-local/stop-local, 준비 확인·부분 기동 실패 정리·중복 실행 방지·소유 프로세스만 종료 |
| 영속 저장 및 동시성 | Phase 03 | SQLite migration, 재시작/rollback, 제한 큐, 동시 요청 및 중복 turn 검증 |
| Redis 기본 의존성 제거 | Phase 03의 마지막 작업 | Redis 없이 정상/장애/restart/duplicate 검사 통과 후 기본 설정·실행기·readiness 갱신 |

2026-09-07 실행 결과: Phase 01/02/03 및 위 전환 게이트 완료. 단일 앱 인스턴스·단일 worker를 유지한다. 품질 기준 12턴 기록 후 관계/저장을 구현했으며 Phase 04 신뢰성 구현/52사례 평가도 완료했다. 이후 공개 배포보다 남은 대사 품질 문제와 사용자 검토를 우선한다. 자세한 검증과 제한은 PHASE02_03_COMPLETION.md 참고.

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
- 먼저 정적 프런트와 `/api`를 같은 FastAPI 앱에서 제공하고, 이어서 실행/종료 진입점을 통합한다.
- 현재 3060 Ti + 기존 9B Q6_K 로컬 실행을 검증한다. 4070 Ti/14B Q4는 향후 확장 프로파일이다.

핵심 작업:

- face/emotion enum 중앙화
- Pydantic `LLMDecision` schema
- nested output, reply 1..80, max token 축소
- capability-aware JSON mode/fallback parser
- test injection seam 및 fake LLM
- local model start/doctor/benchmark scripts
- 필수 `start-local.ps1` / `stop-local.ps1`: model 실행 도구 재사용, Redis 전환기 사전 확인, 단일 worker, readiness 대기, 소유권 기반 종료
- same-origin frontend/API, 상대 API 경로, API/정적 경로 충돌 및 파일 공개 범위 검사
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
- 기본 SQLite 저장 + 앱 내 잠금/제한 대기열 구축; 검증 후 Redis를 기본 실행에서 제외
- `client_turn_id` idempotency transaction
- rolling summary and memory candidates
- restart/migration tests
- 동시 요청·동일 turn ID·다른 payload 충돌·commit 후 응답 유실·큐 포화/취소 테스트
- Redis 없이 재시작/채팅/readiness smoke, 기존 Redis 데이터 보존 및 복구 절차

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
- 같은 origin의 화면/API를 웹앱 하나로 배포; 별도 프런트 배포는 선택 사항
- 서비스 관리자에서 앱/모델 시작·종료·재시작·로그 관리, 단일 worker/인스턴스 조건 유지
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
- Redis 의존성 제거와 기존 데이터 삭제를 같은 작업으로 취급하지 않는다. 새 SQLite 데이터가 생긴 뒤 과거 Redis로 돌아가는 절차는 별도 backup/restore 검증 없이 자동 수행하지 않는다.
- 기존 frontend가 새 API로 전환될 때까지 compatibility fields를 유지한다.
- `heroine`은 archive/deprecation 안내 외에 기능 개발하지 않는다.
- database migration에는 downgrade 또는 명확한 backup/restore 절차가 있어야 한다.
- 각 단계에서 문서와 code reality가 일치하도록 `PROJECT_STATUS`를 갱신한다.


2026-09-07 Phase 04 실행 결과: PHASE04_IMPLEMENTATION.md, PHASE04_EVALUATION.md. 모델 형식/속도와 제품 대화 품질을 구분해 판정한다.
