# Decision Log

## 2026-09-09 검사 창 내 테스트 채팅

사용자 요청으로 기억/입력 표시를 카드 중심으로 바꾸고 로컬 브라우저 전용 guest 테스트 채팅을 추가했다. 관리자 일반 방문자 조회는 읽기 전용, 허용된 /api/test 경로만 정확한 Origin/JSON 조건으로 기존 웹 API에 연결한다. 다른 방문자의 방을 관리자가 선택해도 전송 대상은 자기 테스트 방이다. 모델/한도/원자적 저장은 유지한다. [구현·검증](LOCAL_INSPECTOR.md).

## 2026-09-09 로컬 모델 검사 창

사용자 요청으로 Task13 실제 요청/출력·기억 검사 창을 별도 로컬 관리자 경계에 추가했다. 일반 원문 로그는 기본OFF를 유지하고 NPC_DEBUG_TRACE=1일 때만 별도1시간/100회 진단 기록. 이번 시험 환경에 활성화, API키/환경 변수는 수집하지 않음. 현재 DB 기억과 과거 요청 스냅샷을 구분한다. 모델 행동·DB 본체 계약 변경 없음. [사용법](LOCAL_INSPECTOR.md).

## 2026-09-08 원문 기반 기억 전달 적용

사용자 승인으로 EXP08/Task12 구현. 모델 두 단계 유지, 원문 기반 최근 이력과 이름/호칭·출처 있는 사건을 분리한다. 새 테이블 대신 committed turns의 결정적 파생 뷰로 기존 대화도 활용한다. 이름/호칭은 별도 key이며 현재 정정 우선, 사건은 발언의 증거이지 현실 완료 사실이 아니다. 프로필/관련 사건의 입력 공간을 보존하고 일반 기억도 오래된 대화보다 우선한다. 데이터 형식 변화 없이 rollback 가능. 검증540 tests 및 실제 모델/공개 smoke. 긴 문맥 지연과 제한된 추출 패턴은 후속 과제. [상세](MEMORY_PIPELINE.md).

## 2026-09-08 동일 모델 두 단계 생성 승인·적용

사용자가 동일 모델 두 번 처리하는 구조를 선택했다. EXP-07은 reply JSON → 최종 대사 고정 → metadata JSON → 기존 원자적 저장으로 구현하고 공개 웹에 적용했다. canonical API와 DB는 유지하며 `NPC_GENERATION_MODE=single_pass`로 복구한다. 기존 설치의 미설정 기본값은 single_pass, 환경 예제와 현재 시험 설정은 two_stage다. 모델 추가나 대사 우선 스트리밍은 도입하지 않았다. 522개 테스트와 공개 합성 3턴/replay/reset 통과. 분류 오답과 어색한 대사는 남아 있어 전체 품질 개선을 확정하지 않는다. [구조·실측·한계](TWO_STAGE_GENERATION.md).

## 2026-09-08 대사 전용 JSON을 후속 구현 후보로 선택

EXP-05/06 합성 84회 비교에서 예시 없는 대사 전용 JSON은 일부 직접 답변과 다른 표현의 이유 회상/오염된 이름 복원에 개선을 보였다. 일반 텍스트는 말투 이탈과 요청 미충족이 남아 우선 후보로 삼지 않는다. 대사 JSON은 부가 정보가 없으므로 공개 API를 바로 교체하거나 임의 기본값으로 채우지 않는다. 다음 후보는 두 단계 생성의 총 지연·실패·원자적 저장을 검증하는 격리 시제품이며 아직 구현하지 않았다. 근거: EXAMPLE_AND_REPLY_ABLATION.md. 모델 전체 품질 개선이나 예시 혼입 원인을 확정한 것은 아니다.

## 2026-09-08 실험 계보 유지와 반복 억제 비교 결론

사용자 요청으로 EXPERIMENT_LINEAGE.md에 부모 실험·가설·결과·운영 적용·다음 질문을 누적 기록하고 AGENTS.md에 갱신 규칙을 명시한다. EXP-04에서 48개 합성 응답과 4개 서버 지원 probe를 검사했다. repeat 해제 시 일부 이름 표현은 개선됐으나 문맥/역할/반복 전체의 우월성을 확인하지 못해 운영값을 유지한다. 다음 후보는 예시와 실제 대화의 혼입 분리 검사다. 샘플링 또는 모델 크기를 단일 원인으로 확정하지 않는다. 근거: SAMPLING_COMPARISON.md.

## 2026-09-08 역할·말투 비교 후 기본 프롬프트 유지

A/B/C 기본 60회와 A/C의 추가 표현 12회를 비교했다. 예시 수정은 일부 국소 개선이 있었지만 이름 정확성·이유 설명·다른 상황의 근거 없는 전제를 해결하지 못했고 더 어색한 표현도 관찰됐다. 사용자 요청의 수정·비교를 완료하되 B/C는 실험 스냅샷으로 남기고 공개 기본 캐릭터는 교체하지 않는다. 모델 크기의 한계나 반복 억제 설정이 원인이라고 단정하지 않는다. 근거: docs/IDENTITY_VOICE_COMPARISON.md.

## 2026-09-08 규칙 기반 기억 선택 1차 적용

사용자 승인 범위에 따라 현재 질문 우선, 제한된 최근 사용자 문맥 보조, 무관한 기억 0개 반환, 명확한 취향 정정의 생성 전 반영을 구현한다. 문맥 구성은 기존 모듈을 확장하고 새 프레임워크/모델/DB를 추가하지 않는다. 대명사 의미를 확정하는 시스템으로 주장하지 않으며 모호한 연결을 보류한다. 일반 사실 정정/사건·기분/동적 예시는 후속 범위다. 선택 정확도와 모델 답변 품질을 별도 평가한다. 상세: CONTEXT_AWARE_MEMORY.md.

## 2026-09-08 Python 3.11 요청 취소 보존

병합 전 CI에서 재현된 시작 이벤트/취소 경합에 대응해 직렬 큐 시작 대기는 asyncio.timeout과 직접 await를 사용한다. 기존 대기 시간 제한/큐 제한과 단일 추론 구조는 유지한다. 완료 이벤트와 외부 취소가 겹쳐도 요청 취소가 소실되지 않아야 한다.

## 2026-09-08 대화 기록 복원과 로컬 관리자

사용자 요청으로 새로고침 시 서버 기록 복원, 대화방 나가기에서 확인 후 기록·기억·관계 초기화, 방문자별 관리자 조회를 추가했다. 목록 뒤로가기는 기록 유지다. 관리자는 별도 loopback 앱과 읽기 전용 SQLite 연결을 사용하며 공개 터널에 연결하지 않는다. 브라우저 단위 익명 방문자를 실제 사람/PC로 간주하지 않는다. 초기화는 해당 캐릭터에만 적용하고 일일 한도·다른 방문자를 유지한다. 과거 세션을 폐기하여 오래된 초기화 재시도/대기 chat이 새 기록을 훼손하지 않게 한다. 현재 DB 논리적 삭제이며 백업의 물리적 소거는 별도다. 상세: CHAT_HISTORY_AND_ADMIN.md.

## 2026-09-08 메신저 목록과 영상 앱 형태

사용자는 얼굴을 단순 표시 토글 대신 영상 앱처럼 열고 닫으며, 대화 목록에서 캐릭터 방을 드나들 수 있는 모바일 디자인을 요청했다. 실제 연결된 유이 방과 준비 중 캐릭터 안내를 구분한다. 캐릭터 화면의 연결/축소/종료 조작은 프런트 표시 상태이며 영상 통신이나 모델 세션 생성을 뜻하지 않는다. 방에서 목록으로 이동해도 진행 중인 요청과 대화 DOM을 유지한다. 브라우저 새로고침 뒤 이력 조회와 실제 복수 캐릭터 지원은 별도 서버 계약 작업으로 남긴다.

## 2026-09-08 모바일 메신저와 캐릭터 화면

사용자가 모바일 중심의 카톡형 대화와 화상 채팅처럼 잘 보이는 캐릭터 얼굴, 답변 생성 중 점 세 개 모션을 요청했다. 상단 캐릭터 영역과 하단 독립 스크롤 말풍선/입력창으로 변경한다. 입력 중 표시는 실제 요청 중에만 보이며 성공·실패·오프라인에서 종료한다. 대화 말풍선은 표시 전용이고 기존 서버 권한/재전송 계약은 유지한다. 새로고침 시 과거 대화를 불러오는 기능은 이번 범위에 없으며 화면에 보이지 않아도 서버 대화 상태는 유지된다.

## 2026-09-08 공개 테스트 한도 사용자 지정

사용자 요청에 따라 브라우저별 하루 300회, 전체 합계 하루 2000회로 확대한다. 현재 공개 테스트 private env에 적용하며 기존 사용량을 초기화하지 않는다. 활동 브라우저 수와 분당 제한은 유지한다.

## 2026-09-08 Aggressive 9B Q4_K_M 비교 시험

사용자가 더 큰 Aggressive 모델 사용을 승인하여 9B Q4_K_M을 내려받고 SHA-256을 확인했다. 현재 로컬/공개 테스트 프로파일을 context 4096, GPU auto, output 256으로 전환한다. 기존 4B/8192/all 파일과 모델 관련 설정은 무시된 로컬 복귀 기록에 보존한다. UI·대화 DB·서명 키·공개 터널은 유지한다. 6개 고정 합성 문맥 검사에서 4B보다 일부 대응이 나았지만 이유 답변 누락·자기 자신을 3인칭으로 언급하는 문제가 남았다. 지연 중앙값은 약 1.55초→4.69초이며 9B 첫 응답은 약 17.19초였다. 시험 적용이며 품질 우위나 일반 성능 보장이 아니다.

## 2026-09-08 짧은 긍정 뒤 응답 반복 개선

사용자가 보고한 연속 동일 응답은 서로 다른 turn ID에 저장되어 있었으므로 재전송 캐시 문제가 아닌 응답 생성 문제로 확인했다. 사용자 승인 후 canonical 호출에 설정된 top_k/presence/frequency/repetition penalty를 전달한다. llama.cpp는 repeat_penalty, 기타 기존 vLLM 경로는 repetition_penalty 이름을 사용한다. 설정값 자체는 현재 20/0.5/0.3/1.08을 유지한다. 이름·정체성을 유지하면서 짧은 긍정과 재확인 표현의 다중 턴 예시를 추가했다. 답변을 임의의 고정 문구로 교체하거나 사용자 이력을 삭제하지 않는다. 반복된 이력이 있는 합성 시나리오도 평가한다. 전체 대화 품질 해결을 뜻하지 않는다.

## 2026-09-08 4B 입력 문맥 확대

사용자의 넉넉한 문맥 사용 제안에 따라 RTX 3060 Ti에서 context 8192를 실제 검증 후 현재 개발/공개 테스트 프로파일에 적용한다. 출력 256과 여유 64를 예약하여 추가 용량을 주로 입력과 이력에 사용한다. 모델의 실제 n_ctx와 웹 설정을 일치시킨다. 최근 4메시지 고정 제한은 제거하고 서버에 저장된 12메시지 중 예산에 들어가는 완전한 대화 쌍을 전달한다. 이름·현재 사용자 입력·정정 처리·서버 점수 권한은 유지한다. 상세 측정과 검사 실패 원인은 PROJECT_STATUS를 따른다. 모델 교체/DB migration은 없다.

## 2026-09-08 작은 모델 대화 개선 조사 — 구현 결정 전

사용자 요청에 따라 외부 오픈소스/Reddit 자료를 조사하고 현재 코드와 교차 검증한 결과를 [별도 보고서](SMALL_MODEL_DIALOGUE_RESEARCH_2026-09-08.md)에 기록한다. 보고서의 우선순위와 수치는 제안된 실험 조건이며 승인된 설정 변경이 아니다. 기존 로컬 우선 구조와 복구한 유이 정체성을 유지한다. 외부 모델 제작자의 품질 주장이나 Reddit 개인 경험을 한국어 4B의 검증된 개선 효과로 취급하지 않는다.

## 2026-09-08 유이 정체성 복구 — 직전 이름 미정 판단 취소

원본 HEAD의 캐릭터는 '유이가하마 유이' 계열로 명시되어 있었다. Phase04 축약으로 이 설정을 누락한 것은 회귀다. 원본을 비교하지 않고 이름 미정으로 바꾼 직전 결정은 취소한다. 원래 성격과 말투를 유지하고 사용자가 지적한 유이 정체성을 이름으로도 명확히 전달한다. 프롬프트 최적화는 캐릭터의 정체성을 삭제해서는 안 되며, 기본 캐릭터가 재시도 시스템 프롬프트까지 전달되는 회귀 테스트를 유지한다.

## 2026-09-08 이름 질문 응답

캐릭터 고유 이름이 설정되지 않은 현재 상태를 명시하고 표시 호칭 NPC를 안내하도록 지침/예시를 추가한다. 사용자 승인 없이 새로운 이름을 부여하지 않는다. 보고된 부적절한 응답을 모델 크기만의 문제로 단정하지 않는다. 실제 새 대화에서도 이름 창작/역할 혼동을 확인했으며 제한된 수정 후 재검증했다. 일반 지능 개선이나 모든 욕설 차단 완료로 취급하지 않는다.

## 2026-09-07 공개 링크 확정 — 앞선 초대 기본안 대체

사용자는 링크를 전달하면 특별한 절차 없이 즉시 사용하는 배포를 명시적으로 요청했다. 따라서 기본을 guest로 변경한다. 이메일/가입 없이 자동 발급하는 서명 쿠키로 브라우저별 기록을 분리한다. 누구든 주소를 전달받으면 이용 가능하다. Access 이메일 인증 코드는 선택 사항으로 보존한다.

초기 조정 가능한 값은 활동 브라우저 5개/TTL 300초, 한국 날짜 기준 전체 200회·브라우저 30회/일이다. 모델 생성 동시성은 여전히 1개다. 전체/개별 카운터는 별도 usage SQLite에 예약 차감하고 실패 시도도 포함하며 이미 저장된 응답 재전송은 중복 차감하지 않는다. 브라우저 쿠키 삭제로 실제 사람별 한도는 보장할 수 없지만 전체 총량은 유지한다. 개인 .env와 실행 중인 앱을 자동 변경하지 않는다.

## 2026-09-07 배포 준비 후속 결정

- 사용자는 테스트 이후의 배포 기준으로 준비를 요청했다. 도메인/Cloudflare 계정은 아직 없으므로 외부 리소스 생성 없이 인증 경계와 배포 설정·검증을 진행한다.
- Windows 직접 실행 + FastAPI/정적 UI + 별도 llama.cpp + SQLite 구조 유지. 운영 데이터는 코드와 개발 DB에서 분리한다.
- Cloudflare Access JWT를 origin 앱에서도 검증한다. 검증된 issuer/subject를 계정 키로 사용하며 브라우저 프로필 번호나 이메일 헤더를 인증으로 사용하지 않는다. 로컬 익명 프로필 자동 인계는 하지 않는다.
- 첫 배포의 초대 사용자 정책은 임시 기본안이다. 공개 가입 운영은 확정되지 않았으며 별도 가입/삭제/복구·용량 설계가 필요하다.
- 보관 기간 30일/백업 7일은 런북의 검토 초안일 뿐 승인된 자동 삭제 설정이 아니다. 정책 미확정 상태에서는 공개 준비 완료로 표시하지 않는다.
- Phase05 전체 완료 여부는 실제 외부망 검증, 개인정보 보관/삭제, 서비스 복구와 부하 검증 후 판단한다. 로컬 단위 테스트 성공을 배포 완료로 취급하지 않는다.

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
| WEB-01 | Default to one FastAPI web app serving static frontend and API at the same origin. | Confirmed 2026-09-07; planned | User approved simpler development/deployment; keep static source and optional separate hosting. |
| OPS-01 | Unified start/stop is required in Phase 01; inference remains separate. | Confirmed 2026-09-07; planned | Reduce manual process/config coordination and preserve model replacement. |
| PERSIST-02 | After Phase 03 gates, use SQLite + in-process coordination by default; Redis optional. | Confirmed 2026-09-07; planned | Reduce always-on dependencies without losing durable state or duplicate protection. |
| OPS-02 | One app instance/worker is the initial supported operating profile. | Confirmed 2026-09-07; planned | In-process locks/queues are not shared across replicas; scaling requires a reviewed shared design. |

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

## 2026-09-07 — Preparation audit

- 사용자 요청 범위는 전달 문서와 연결 저장소의 최신성 확인, 필요한 업데이트, 구현 준비다. 패키지 `CODEX_START_PROMPT.md`의 Phase 00 실행 문구는 다음 구현 작업용 참고 자료이며 이번 요청을 구현 전체로 확대하지 않는다.
- 원격 `npc-chat/main`과 로컬 HEAD가 검토 기준선과 동일하여 코드 갱신/병합은 필요하지 않았다. 기존 문서 22개도 전달 ZIP과 일치했다. 이번에는 상태/준비 문서만 갱신한다.
- `RUNTIME-01`의 기준 장비 결정은 유지한다. 다만 현재 작업 PC 실측은 i7-11700 / RAM 약 32 GB / RTX 3060 Ti 8 GB이므로 4070 Ti 12 GB용 14B Q4 프로파일의 실행 가능성을 이 PC에서 검증된 사실로 취급하지 않는다. 모델 평가 전에 기준 장비 또는 별도 프로파일을 확인한다.
- 목표 API 문서의 invalid-message 400과 실제 FastAPI 기본 422는 구분한다. Phase 00은 기존 422 동작을 보존하고, 목표 오류 계약 변경은 명시적 호환 계획과 테스트를 갖춘 후 수행한다.
- 다음 구현 범위는 `tasks/00_BASELINE_STABILIZATION.md`다. 관계 엔진·영속 기억·배포 작업은 해당 단계의 완료 조건을 충족한 뒤 진행한다.

## 2026-09-07 — Phase 00 implementation amendments

- 사용자 후속 요청으로 Phase 00 구현을 시작하고 해당 범위만 완료했다. 모델 평가, 관계 엔진, 영속 기억, 공개 배포는 후속 단계로 유지한다.
- `create_app`에 모델/저장소/Comfy/readiness 함수를 주입할 수 있게 했다. 운영 환경 변수나 공개 API를 통한 fake 모드는 추가하지 않았다.
- startup의 필수 Redis PING을 readiness로 이동했다. 의존성 장애 중에도 `/api/live`를 사용할 수 있으며 `/api/ready`가 503을 반환한다. Redis/LLM 검사는 병렬이며 의존성별 timeout은 기본 2초, 0.1~10초로 제한한다. 모델 목록 응답은 Pydantic 검증을 거친다.
- 기본 로컬 프로파일은 `llama_cpp`, `127.0.0.1:8001/v1`, completion cap 256, 명시적 로컬 CORS다. `local-model`은 설정용 임시 ID이며 실제 모델 선택을 의미하지 않는다. 기존 `.env`는 보존한다.
- 기존에 추적 중이던 `frontend/config.js`를 비밀값 없는 로컬 기본 config로 유지하고 ignore 항목을 제거했다. 예시도 제공한다. 주소 변경은 공개 가능한 설정으로 관리하며 모델/API 키를 브라우저에 넣지 않는다.
- `STATE-01`과 저장소 지침에 따라 브라우저 history의 초기 세션 주입을 차단했다. 요청 schema와 응답은 유지하지만 내용은 무시한다. 서버 이력 지속 및 위조 history 차단 테스트를 추가했고 README에 동작 차이를 기록했다. 이 보안 수정은 Phase 01까지 연기하지 않는다.
- 프런트 중복 submit은 전송 중 입력/버튼 잠금으로 차단한다. 실패 자동 재시도는 추가하지 않았다. 서버 idempotency와 관계 총점 규칙은 이번에 변경하지 않았다.
- `OUTPUT-01`, `REL-01/02`, `PERSIST-01`의 목표 계약은 유지한다. 이번 cap 축소가 실제 모델의 schema 성공률을 보장하지 않으며 Phase 01 평가가 필요하다.

## 2026-09-07 — Approved deployment simplification plan

사용자가 개발 중 관리/운영 편의를 위해 제안된 단순 구조를 선택하고 계획 문서 반영을 요청했다. 이번 요청은 문서 업데이트이며 구현 변경이 아니다.

- Phase 01: 화면/API를 FastAPI 한 origin으로 통합한 뒤 `start-local`/`stop-local`과 모델 실행 도구를 완성한다. 현재 Redis는 유지한다.
- Phase 03: SQLite 영속 저장, 제한 큐/잠금, DB turn-ID 제약, migration/rollback/restart/동시 요청 검증 후 Redis를 기본 의존성에서 제외한다. 기존 데이터 삭제와 의존성 비활성화를 분리한다.
- 기존 `PERSIST-01`의 SQLite 방향은 유지한다. `TARGET_ARCHITECTURE`의 "Redis 없는 최소 개발 모드" 및 Task 03의 "Redis를 항상 유지" 전제를 위 기본 프로파일로 대체한다. 현재 코드가 이미 Redis 없이 실행된다고 주장하지 않는다.
- 웹앱/모델 프로세스는 분리하고 내부 도메인 모듈도 유지한다. HTTPS/인증·요청 제한·백업과 Phase 05 서비스 관리 요구는 줄이지 않는다.
- 영향 문서: AGENTS, 제품 방향, 목표 구조, 실행 계획, 로컬 런북, API/readiness 계약, 테스트 계획, 배포 게이트, Tasks 01/03/04/05, README, PROJECT_STATUS.
- 호환성: 현재 수동 실행/Redis/응답 계약은 구현 단계의 검증 전까지 유지한다. 단일 worker에서 다중 worker/인스턴스로 확대하려면 공유 조정 설계와 검증이 먼저다.

## Decision change procedure

When changing a confirmed decision:

1. add a new row or amendment with date;
2. explain measured evidence or user instruction;
3. list affected schemas, migrations, tests, and docs;
4. preserve backward compatibility or document explicit breaking migration;
5. update `PROJECT_STATUS`.

Do not silently alter score semantics or API fields during implementation.

## 2026-09-08 — 채팅 전송 피드백 순서

사용자 지시에 따라 새 메시지는 전송 이벤트 안에서 즉시 사용자 버블로 표시하고 입력창을 비운 채 잠근다. 캐릭터가 이미 입력하고 있는 것처럼 보이지 않도록 유이의 입력 중 표시는 650ms 뒤에도 처리 중일 때만 시작한다. 빠른 응답은 표시를 건너뛴다. 실패 시 원문 복원, 수동 재시도, 동일 `client_turn_id`, 서버 권위 이력 원칙은 유지하며 API나 저장 schema 변경은 없다.

## 2026-09-07 — Current PC profile and Phase 01 implementation

- 사용자 확인: 현재 개발 PC는 RTX 3060 Ti 8 GB 데스크톱이다. 4070 Ti/14B Q4를 현재 수용 게이트에서 제외하고 기존 9B Q6_K를 우선 테스트한다. 시작값은 context 2048, parallel 1, completion 256, GPU layers 12, batch/ubatch 128, thinking OFF다.
- 설치된 Vulkan b8119는 auto 및 12-layer offload 모두 로딩 중 같은 buffer assertion으로 종료했다. 공식 b10830 CUDA 12.4 zip과 DLL의 SHA-256을 검증해 프로젝트 전용 무시 디렉터리에 설치했다. 기존 설치와 GGUF는 보존했다. 새 모델은 다운로드하지 않았다.
- 화면/API를 FastAPI 한 주소로 통합했다. 명시적인 공개 정적 경로만 등록해 API 404/405와 비공개 파일 차단을 유지한다.
- 공통 Python 실행기 + PowerShell start/stop 도구를 사용한다. Windows 숨김 프로세스, 준비 제한시간, 단일 worker, PID+생성 시간+실행 파일+인자 소유권, 호출별 롤백을 적용한다. 외부 모델 재사용은 명시적이며 Redis는 PING만 한다.
- canonical adapter를 기본으로 전환했다. 관계 엔진 전까지 flat API에서 delta=0으로 기존 총점·메모를 보존한다. 모델이 생성한 관계 점수를 쓰는 동작은 명시적 legacy 모드에만 남긴다. 이는 Phase 02 관계 계산 완료를 뜻하지 않는다.
- flags allowlist 검증, 명시적 JSON capability 선택, 최대 3회 전송/파싱 시도, 502/503 정형 오류를 추가했다. 상세 원문은 진단에 기록하지 않는다. 긴 CPU/GPU 분할 추론을 위해 Redis lock 최소 lease를 3*timeout+15초로 늘렸다. 큐/idempotency는 후속 단계다.
- 이 PC의 무시된 `.env`에서 모델/실행 파일 경로, 로컬 8001 주소 및 해당 프로파일 값만 갱신했다. 기존 인증값/Redis 설정은 유지했다. 공유 예시에는 실제 PC 경로를 넣지 않는다.
- 관련 문서: AGENTS, README, 현재/향후 런북, 제품 방향, 목표 구조, 구현/검증 계획, API 계약, Task 01, PROJECT_STATUS. 원본 handoff-package는 수정하지 않는다.

## 2026-09-07 — Response latency: small model on GPU

사용자가 실제 응답 지연을 지적해 9B Q6_K + CPU/GPU 분할 설정과 4B Q4_K_M + GPU 전체 처리를 비교했다. 기존 9B 모델과 원래 설정을 보존하고 현재 개발용 기본값을 더 작은 모델로 변경한다. 문맥 2048 / 출력 256 / parallel 1 / batch 128 / thinking OFF는 유지한다. 정확한 실측은 PROJECT_STATUS section 11을 따른다.

작은 모델에서도 캐릭터 지침이 긴 스키마보다 뒤에 오도록 prompt 순서를 조정하고 default 캐릭터의 기존 반말 규칙을 예시와 함께 재강조했다. 이는 목표 말투 변경이 아니다. 하지만 별도 대화 점검에서 말투 혼용과 문맥에 없는 설명이 나왔으므로 형식 통과를 품질 동등성으로 해석하지 않는다. Phase 04 품질 평가가 필요하다.

benchmark의 `--model` 인자로 후보 alias를 명시해 기본 `.env`를 바꾸기 전에 시험한다. 새 GGUF를 시작기에서 자동 다운로드하는 기능은 추가하지 않았다. 모델 파일은 저장소 밖에 보관하고 원본 LFS SHA-256을 검증했다. 대화 상태 migration/Redis 초기화/인증값 변경은 없다.


## 2026-09-07 — Phase 02/03 구현과 SQLite 전환

사용자 승인에 따라 12턴 품질 기준을 먼저 남기고 규칙 1.0 관계 엔진과 영속 저장을 구현했다. 초기값은 캐릭터별 0/30/30/30/0으로 시작하며 밸런스 확정이 아니다. 전역 단일 추론 큐를 선택해 per-profile 잠금 객체 누적을 없앴다. queue8/wait30, 한 DB 소유 앱 한 개를 강제한다.

기억은 추측의 영속화를 줄이기 위해 사용자 현재 발화와 정확히 일치하는 후보만 채택한다. 요약은 생성형 압축 대신 출처가 명확한 발화 인용으로 제한한다. reset은 식별자를 교체하며 migration receipt는 삭제 후에도 유지한다.

재시작·원자성·중복·동시성·취소·복구·Redis import 차단 검증 후 Redis 기본 의존성을 제거했다. 기존 Redis 1건은 무시된 로컬 파일로 백업 후 이전하고 재실행 중복 검증했다. 모델 프로세스는 유지하고 웹앱만 다시 시작했다. 이전 이후 복구 기준은 SQLite 백업이며 오래된 Redis로 자동 후퇴하지 않는다. 상세: PHASE02_03_COMPLETION.md, DATABASE_OPERATIONS.md.


## 2026-09-07 — Phase 04 실사용 UI와 품질 평가

오류 안내를 NPC 대사와 분리하고 자동 재시도 없이 동일 payload를 보존한다. 정확한 점수 표시는 debug/hidden 설정으로 유지하며 상시 점수 공개를 제품 결정으로 확정하지 않았다.

현재 4B 프로파일은 실제 llama.cpp tokenizer count를 사용한다. 사용자 입력을 몰래 잘라 답변하는 대신 예산 초과 시 수정 가능한 오류를 반환한다. 다른 제공자용 estimate는 명시적 근사 모드이며 정확한 보장을 주장하지 않는다.

말투 지시를 압축하고 역할/공감/미지 사실 예시를 추가했다. 단순 취향은 원문 기반 직접 추출과 대상별 정정을 허용한다. 모델이 부정 취향을 긍정으로 뒤집는 실측 실패 때문에 명시적 취향 회상 질문은 저장된 원문을 인용한다. 이는 실제 상태에 근거한 응답이며 LLM 실패를 숨기는 대체 대사가 아니다.

품질 평가는 synthetic 입력만 저장한다. 에이전트 정성 점수는 인간/블라인드 평가로 포장하지 않으며, 별도 익명 혼합 검토표와 키를 제공한다. 측정 결과가 공개 배포 승인을 의미하지 않는다. 기존9B 비교 후 현재4B를 유지하며 향후 추가 모델 다운로드는 별도 사용자 결정이다.

## 2026-09-09 — 로컬 프롬프트 편집과 처리 순서

사용자는 실험실에서 캐릭터 프롬프트를 직접 수정하며 테스트하고 호출 순서를 이해하기를 요청했다. 공유 파일을 덮어쓰지 않고 로컬 서명 요청별 초안을 적용한다. 사용자 기억·대화는 유지, 리셋은 명시적 기존 버튼. 대사/분석 호출 입력·출력을 시간순으로 표시하고 현재 기억은 분리한다. 일반 요청은 기존 동작 유지. 자세한 계약/검증은 LOCAL_INSPECTOR.md Task15.


## 2026-09-09 — 실제 기억 판단 관측
사용자 요청에 따라 입력/출력과 분석기 지시문을 명확히 표시하고, 실제 검색 및 저장 함수의 분기에서 opt-in 비공개 진단을 기록한다. 정책 변경 없이 선택/제외/병합/저장 근거를 제공하며 과거 턴을 현재 데이터로 추정하지 않는다. LOCAL_INSPECTOR.md Task16 참고.

## 2026-09-09 — 구조 유지·실제 인식 누락 수정
사용자는 구조를 유지하고 의도대로 작동하지 않는 부분만 수정하도록 요청했다. 기존 규칙의 이름/추천/시간 제안 누락과 요약 중복만 보완하고 추가 모델 호출·기억 체계 재설계·프롬프트 변경은 도입하지 않았다. 제안과 실제 완료는 계속 구분한다. MEMORY_PIPELINE.md Task17 참고.

## 2026-09-09 — EXP10 검색단서 실험 보류
기존metadata호출에다음턴단서추출을추가하는사용자승인실험을진행. 호출수유지/일부회상개선은확인했으나누락과오래된주제잔류때문에운영은기존방식유지. 실제원문존재검증과의미적관련성검증은다르다. SEARCH_CUE_EXPERIMENT.md 참고.

## 2026-09-09 — EXP11 추가 검증 후 보류 유지

새로운 표현에서도 단서 누락·이전 화제 잔류가 재현되고 기존 대비 답변 이득이 없었다. 기존 키워드 검색 자체도 화제 종료 발화를 구분하지 못함을 코드와 출력으로 확인했다. 운영 설정은 유지하며 다음 개선은 관련성 및 단서 폐기 기준에 집중한다. SEARCH_CUE_VALIDATION.md 참고.

## 2026-09-09 — EXP12 활성 화제 규칙 적용

추가 호출 없이 committed history에서 활성 사용자 화제를 파생한다. 종료·전환·취소 전 단서는 폐기하고, 작품/추천 지칭은 최근 출처 있는 추천 하나에 연결하며, 무근거 생략 질문은 사건을 선택하지 않는다. 합성 검색 지표는 개선되어 기본 규칙에 적용한다. 모델이 만든 search_cues는 불안정하여 계속 운영 OFF다. 선택된 제목을 모델이 사용하지 않는 1/2 사례는 별도 생성 문제로 남긴다. ACTIVE_TOPIC_RETRIEVAL.md 참고.

## 2026-09-09 — 반복 대사에는 대사 입력만 최소 축약

실제 긴 이력에서 assistant의 유사 대사가 모델 입력 예시로 누적되어 반복을 강화했다. DB 이력은 보존하고 reply 단계의 입력 사본에서만 3개 이상 유사 군집의 중간 pair를 생략한다. 첫 후보가 최근 대사 2개 이상과 유사할 때만 reply를 한 번 더 생성하고, 덜 유사한 후보를 metadata가 분석한다. 전면 구체화·경계 프롬프트는 합성 검증에서 근거 없는 단정과 경계 실패를 만들어 채택하지 않는다. 정상 요청은 계속 2호출이며 반복 후보에서만 3호출 가능하다. REPLY_LOOP_GUARD.md 참고.

## 2026-09-09 — 계획 구조와 기존 4B 품질 미채택

현재 9B의 reply 단계에 같은 호출 안의 계획 필드 또는 별도 계획 호출을 추가했지만 역할 주체 역전과 경계 실패가 개선되지 않았다. 별도 계획은 지연만 크게 늘어 두 방식 모두 적용하지 않는다. 설치된 4B는 빨랐지만 주체 역전과 근거 없는 원인·증상 추측이 더 뚜렷해 속도 rollback으로만 보존한다. 현재 9B와 반복 루프 가드를 유지한다. REPLY_PLANNING_COMPARISON.md 참고.

## 2026-09-09 — Windows 종료는 검증된 자식 트리까지 처리

venv Python 부모만 종료하면 uvicorn 시스템 Python 자식이 남을 수 있어 등록된 부모와 당시 자식 트리를 각 신원 정보로 재검증해 함께 종료한다. 이름이나 포트만으로 프로세스를 선택하지 않는다. `stop-local`은 관리자·웹·모델 전체 종료, `stop-public-test`는 공개 터널만 종료하는 의미를 유지한다. LOCAL_DEVELOPMENT_RUNBOOK.md 참고.
