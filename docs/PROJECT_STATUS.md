# Project Status

## 2026-09-23 Task32 애니 시청 기록 서비스 통합 검토 브리프 — 완료

GPT Pro와 후속 제품 방향을 논의할 수 있도록 현재 `main@96746a0`의 실제 코드·저장 schema·생성·기억·배포·계측 상태를 다시 대조했다. 현재 구조와 요청 순서, 검증 결과, 재사용 가능한 강점과 모델·기억·운영 한계를 정리하고, 애니 시청 기록 서비스를 source of truth로 유지하는 통합 경계, spoiler-safe context, 확인형 기록 변경, 세 가지 통합 방식과 읽기 전용→확인형 쓰기→제한 베타 단계를 새 브리프에 문서화했다. 기존 일반 GPT Pro 브리프와 README도 최신 통합 문서로 연결했다.

문서 작업 전 전체 629 Python tests와 프런트·검사창29 tests가 통과했다. 서버는 모델·웹·검사창·공개 터널 모두 중지된 상태이며 실행 설정이나 DB를 변경하지 않았다. 개인 대화·로컬 경로·임시 터널 URL·비밀값은 문서에 포함하지 않았다. [애니 서비스 통합 브리프](GPT_PRO_ANIME_INTEGRATION_BRIEF.md), Task32 참고.

## 2026-09-22 Task31 모바일 답변 후 키보드 자동 재등장 방지 — 완료

대화 요청이 끝날 때 모든 환경에서 입력창을 자동 포커스하던 동작을 포인터 환경에 맞게 제한했다. 모바일처럼 hover가 없고 coarse pointer를 사용하는 환경에서는 답변 성공·실패 후 입력창을 자동 포커스하지 않아 내려간 가상 키보드가 다시 열리지 않는다. hover 가능한 fine pointer 데스크톱은 기존처럼 바로 다음 메시지를 입력할 수 있으며, 사용자가 `내용 수정`을 직접 누른 경우의 명시적 포커스도 유지한다. 전체 629 Python tests, 프런트·검사창29 tests와 정적 검사가 통과했고 공개 정적 파일에도 즉시 반영된 것을 확인했다. API·서버·모델·저장 데이터 변경은 없다. Task31 참고.

## 2026-09-22 Task30/EXP22 TokenCounter 연결 재사용 — 완료·적용

GPT Pro 원문의 TokenCounter 제안을 확인하고, 정확한 llama.cpp apply-template/tokenize 검증을 유지한 채 HTTP client를 서비스 생명주기 동안 재사용하도록 바꿨다. 한 최상위 생성 요청 안의 완전히 같은 messages만 SHA-256 키로 재사용하고 종료 시 지우며, 정상 reply/metadata의 서로 다른 입력은 계속 각각 검증한다. 앱 종료와 평가 스크립트가 모델 client와 tokenizer client를 함께 닫고, 비개인 계측에 cache hit 수를 추가했다.

합성 동일 입력은 client40→1·HTTP80→40·12.003→0.582초, 서로 다른 정상 입력 모사는 client40→1·HTTP80 유지·11.744→0.388초였고 token 결과가 같았다. 실제 9B development24개는 형식24/24·parse/transport0을 유지하며 prepare p50 0.578→0.297초였지만 모델 생성 변동으로 전체 p50은2.531→3.546초였다. 따라서 입력 준비 최적화로만 채택하고 전체 응답 속도 개선을 주장하지 않는다.

최종 629 Python tests, 프런트·검사창28 tests, Ruff/compileall/JavaScript/diff 검사가 통과했다. 재시작한 공개 full/two-stage 구성에서 화면/live와 합성 chat2회/reset이 모두200이었고, 두 번째 턴 reply/metadata prepare가0.000/0.015초였다. 공개 quota2회를 사용했고 합성 대화는 즉시 삭제했다. DB migration·API·프롬프트·모델 호출 수 변화는 없다. [상세](TOKEN_COUNTER_REUSE.md), Task30 참고.

## 2026-09-22 Task29/EXP21 metadata 전용 문맥 A/B — 완료, compact 미채택

reply 입력과 확정 대사를 고정한 채 metadata에 전체 문맥을 주는 full과 최근 완전2쌍·source-backed 근거만 주는 compact를 비교했다. 전체 two-stage 사전 비교는 확률적 reply 차이로 오염되어 최종 판정에서 제외하고, EXP20의 같은 합성 reply 24개로 조건 순서를 교대한 48 metadata 호출을 사용했다. 양쪽 모두 최초 형식24/24, parse·transport 실패0이었다. compact는 prompt 중앙903.5→900, 평균956.9→925.4였고 metadata 전체 중앙2.062→2.094초로 일반적 개선이 없었다. 긴24쌍 이력 한 건은659 token·약0.36초 줄었다. interaction 차이7건에서 compact 비열화가 확인돼 공개/default는 full을 유지한다. 원시 기억 후보는 양쪽 모두 많았으나 서버 원문 검증 후 실제 수용은0건이었다. holdout과 사용자DB는 사용하지 않았다.

최종 전체627 Python tests, 프런트·검사창28 tests와 Ruff/compileall/JavaScript/diff 검사가 통과했다. 공개 설정에 full을 명시하고 재시작해 화면/live/합성 chat/reset 200, manifest full·two_stage 및 reply/metadata 두 단계를 확인했다. 공개 smoke가 quota1회를 사용했고 합성 대화는 즉시 삭제했다. DB migration과 API 응답 변경은 없다. [상세](METADATA_CONTEXT_AB.md), Task29 참고.

## 2026-09-21 Task28 비개인 운영 계측·독립 평가 기준선 — 구현 및 개발 세트 완료

비밀값과 대화 원문을 제외한 유효 설정 manifest, 채팅의 queue/load/recall/reply/metadata/commit/total 단계 지연, token·재시도·실패·취소·replay를 하나의 익명 schema로 기록하는 회전 JSONL과 p50/p95 오프라인 집계를 추가했다. 현재 llama.cpp가 실제 반환하는 `cache_n`, `cached_tokens`, timing만 허용 목록으로 보존하며 없는 값은 추정하지 않는다. 기본 설정은 OFF다.

실제 사용자 대화를 포함하지 않은 8범주 48개 합성 세트를 development/holdout 24개씩 분리했다. development 기준선은 48 모델 호출 모두 최초 형식 유효, parse/transport 실패0, 전체 중앙2.532초·표본 p95 3.891초였다. 자동 보조검사는18/24였으나 경계3건 실패를 모두 놓쳐 사람 rubric과 분리해야 함을 재확인했다. 이름·저장 기억·긴 대화 뒤 장소·기억 부재는 대체로 작동했고 추천 이유, 취향 의미 보존, 중국어 혼입, 경계 수락, 일부 말투 문제가 남았다. holdout은 실행하지 않았다. 첫 CLI 실행 경로 실패는 모델 호출 전 발견해 회귀 테스트로 수정했다.

현재 공개 시험 구성에 계측을 활성화해 재시작했다. 공개 합성 1턴과 즉시 reset이 200이었고 JSONL의 manifest+turn에는 원문·답변·사용자 식별자가 없었다. 그 1턴은 quota 1회를 사용했다. 최종 Python 623 tests, 프런트·검사창28 tests, Ruff/compileall/JavaScript/diff 검사 통과. 전체 첫 실행의 queue 테스트 대역 1건 실패는 새 시작 콜백 계약에 맞춰 수정했다. API·DB schema·모델·프롬프트·호출 수 변화는 없다. [계측/사용법](OBSERVABILITY_AND_EVALUATION.md), [기준선](DIALOGUE_SUITE_BASELINE.md), Task28 참고.

## 2026-09-21 Task27 외부 검토 정확성 회귀 수정 — 완료

GPT Pro 검토가 지적한 취소 부정의 활성 화제 손실과 캐릭터 무관 취향 회상 반말을 현재 코드로 독립 재현했다. 새 회귀를 먼저 추가해 6개 예상 실패를 확인한 뒤, 취소 저장·활성 화제 경계가 공통 판정을 사용하도록 통합했다. 실제 취소 뒤 같은 발화의 새 제안은 별도 사건으로 보존한다. 근거 있는 취향 회상은 캐릭터 설정 템플릿을 사용해 유이 반말과 띳띠 해요체를 유지하며, 두 단계 metadata에는 화면에 표시할 확정 대사가 그대로 전달된다.

관련 70 tests, 전체 613 tests, 프런트·검사창 28 tests, Ruff/compileall/JavaScript/diff 검사가 통과했다. 비저장 실제 9B 두 단계 호출에서 두 캐릭터의 기대 말투와 reply/metadata 성공을 확인했다. DB migration, 추가 모델 호출, API·저장 데이터 변경은 없다. Task27 참고. 다음 검토 우선순위는 유효 설정·단계별 지연 계측과 metadata 전용 문맥 A/B이며 별도 작업으로 유지한다.

## 2026-09-21 GPT Pro 검토용 저장소 점검 — 완료

로컬 `main`과 공개 `origin/main`이 동일하고 작업 트리가 깨끗한지 확인했으며, `.env`, `.runtime`, DB, 모델, 로그와 실제 Quick Tunnel 주소가 Git에서 제외되는 것을 재검증했다. 저장소는 공개 상태다. 외부 AI가 2026-09-03 handoff 스냅샷과 현재 구현을 혼동하지 않도록 `GPT_PRO_PROJECT_REVIEW_BRIEF.md`에 현재 제품·요청 흐름·9B 두 단계 생성·기억 구조·운영 게이트·권장 검토 질문을 정리하고 README에서 연결했다. README와 제품 방향 문서에 남아 있던 고정 12메시지 및 기본 Redis 의존 표현도 현재 토큰 예산·SQLite 구현에 맞게 고쳤다.

읽기 전용 운영 점검에서 모델·웹·검사창·Quick Tunnel은 약 239시간 연속 실행 중이었고 외부/로컬 생존 응답, DB 무결성, CPU·RAM·GPU 상태에 이상이 없었다. 실제 대화 사용량은 적어 동시 부하 검증으로 해석하지 않는다. 제품 코드·DB·실행 설정·서버 프로세스는 변경하지 않았다.

## 2026-09-11 띳띠 자유대화 프롬프트 완화 — 완료

띳띠가 일상 대화마다 기사·방랑자·검·바람 같은 설정 표현을 꺼내던 문제를 프롬프트만 조정해 완화했다. 본명 카르티시아, 별명 띳띠, 다정하고 장난기 있는 성격과 해요체는 유지했다. 기본 `방랑자` 호칭을 없애고, 원작 고유어는 사용자가 직접 묻거나 현재 화제와 분명히 관련 있을 때만 사용하도록 범위를 좁혔다. 추천 요청에는 구체적인 선택 하나와 짧은 이유를 먼저 말하게 했다. 현재 두 단계 생성의 대사 입력은 IDENTITY·CHARACTER만 사용하며 수정한 EXAMPLES는 단일 단계 복구 모드의 일관성을 위한 것이다. 합성 9B 점검에서 이름·일상·감정·취향·추천·문맥 대화에는 불필요한 원작 고유어가 없었고, 명시적인 설정 질문에는 리나시타 배경이 유지됐다. 재시작한 공개 구성의 저녁 메뉴 질문에도 설정어 없이 라면·치킨을 제안했고 합성 대화는 즉시 초기화했다.

## 2026-09-11 두 번째 캐릭터 이름을 띳띠로 변경 — 완료

사용자 결정에 따라 두 번째 캐릭터의 화면 이름은 자주 불리는 별명 `띳띠`로 표시한다. 모델 설정에는 본명 `카르티시아`와 별명 `띳띠`를 함께 명시하며, 이름 질문에는 둘을 함께 알려 준다. 기존 세션·대화·관계·기억과 이미지 경로가 끊기지 않도록 내부 `character_id`와 디렉터리는 `cartethyia`를 그대로 사용한다. DB migration은 필요 없다. 전체 606 Python tests, 프런트 23 tests, Ruff/compile/JS/diff 검사가 통과했고 실제 9B 및 재시작한 공개 구성에서 본명과 별명이 모두 포함된 응답을 확인한 뒤 합성 대화를 초기화했다.

## 2026-09-11 Task26 카르티시아 다중 캐릭터 대화 — 완료

사용자 제공 512×600 PNG 17개를 canonical 표정 태그와 대조하고 카르티시아 정적 표정 세트로 추가했다. 기존 생략 요청은 유이(`default`)를 유지하면서 세션·채팅·이력·초기화·이미지 상태 요청에 선택적 `character_id`를 연결했다. 같은 사용자 프로필 안에서도 DB의 기존 `(profile_id, character_id)` 경계에 따라 대화·관계·기억·중복 방지가 분리된다. 대화 목록에서 `#chat/yui`와 `#chat/cartethyia`를 선택하고 브라우저 세션·pending 요청도 캐릭터별 키로 보존한다. DB migration과 모델 프로세스 추가는 없다.

카르티시아 설정은 리나시타의 유랑 기사, 상냥함·자유분방함·용기, 플뢰르드리스 전투 형태를 정체성 범위로 삼고 자연스러운 해요체와 구체 답변 규칙을 사용한다. 메타데이터 분석기의 유이 고정 문구는 캐릭터 일반 표현으로 바꿔 분류 단계에서 정체성이 섞이지 않게 했다. 작업 전 전체 599 tests 통과. 최종 전체 606 tests, Ruff/compile, 프런트 23 tests, JS 구문과 diff 검사가 통과했다. 브라우저에서 두 방과 카르티시아 전체 얼굴 화면을 확인했다. 재시작한 공개 구성의 실제 9B에서 이름 질문에 카르티시아라고 해요체로 답하고 happy 표정·캐릭터 이력 1건을 확인한 뒤 합성 방을 초기화했다. 모델·웹·검사창·터널은 정상이며 DB migration은 없다. Task26 참고.

## 2026-09-11 Task25 기억 주체·문맥 예산 보호 — 완료

fact 후보가 원문의 명시적 주체를 생략하면 저장하지 않고, 입력 예산에서 최신 완전한 대화 1쌍을 일반 기억보다 우선 보존한다. 긴 profile/episode evidence도 항목 단위로 제거해 짧은 입력의 불필요한 INPUT_TOO_LONG을 막는다. 첫 구현의 음수 반복 분기를 500턴 회귀가 발견해 수정했다. 관련110 tests, 전체599 tests, Ruff/compile 통과. 실제 llama.cpp 3776 예산에서 75 tokens·직전 pair 보존·긴 evidence 제거 및 재시작 후 model/web/admin/public 정상 확인. MEMORY_SUBJECT_AND_BUDGET.md 참고.

## 2026-09-11 Task24 문맥 정보 보존 P0 수정 — 완료

고정 커밋 검토에서 재현된 반복 축약의 사용자 정정 손실, 취소 의미·대상 혼합, 복합 취향 질문의 답변 강제 교체를 현재 구조와 호출 수를 유지하며 수정했다. 수정 전 새 probe 4건이 예상대로 실패했고, 단계별 수정 후 새 회귀 5건을 포함한 관련67 tests와 전체596 tests, Ruff/compile 검사가 통과했다. 실제 서버 재시작 후 model/web/admin/public 200을 확인했고 사용자 DB·공개 quota는 사용하지 않았다. 긴 evidence 예산과 일반 fact 주체 보존은 남는다. CONTEXT_INTEGRITY_FIXES.md 참고.

## 2026-09-11 Task23 서버 원클릭 관리 — 완료

기존 공개 테스트 설정과 DB를 그대로 사용해 루트 `server.ps1` 하나로 start/stop/restart/status를 제공한다. 모델·Quick Tunnel·공개 웹·관리자 순서를 내부에서 관리하며 반복 실행·부분 실패 롤백·비밀값 비출력을 검증했다. 실제 전체 stop/반복 stop/start/restart와 공개 HTTP 200을 확인했고 관련20 tests, 전체591 tests, Ruff/compile/PowerShell 구문 검사가 통과했다. Quick Tunnel 주소는 시작·재시작 시 바뀌며 대화·기억·한도 DB는 유지한다.

## 2026-09-09 Task22 Windows 종료 스크립트 — 완료

등록된 venv Python 부모를 종료해도 실제 uvicorn 자식이 남는 문제를 확인했다. 생성 시간·실행 파일·인자를 검증한 등록 프로세스와 당시 자식 트리만 종료하도록 수정했다. `stop-local`은 관리자→웹→모델을 한 번씩 종료하며, `stop-public-test`는 의도대로 터널만 종료한다. 실제 종료 후 8000/8001/8002 listener, llama-server/cloudflared, 런타임 등록부가 모두 비었고 반복 stop도 성공했다. 관련15 tests, 전체586 tests, Ruff/compile/diff 검사 통과.

## 2026-09-09 EXP15/16 답변 계획·4B 교차 비교 — 완료, 미채택

현재 9B에서 direct/scaffold/sequential 42결정/56호출을 비교했다. scaffold는 길이만 늘고 주체 역전·경계 실패, sequential은 구체성 감소·추가 지연·근거 없는 관계 단정이 생겨 미채택했다. 설치된 4B rollback은 14/14 형식 성공과 reply 중앙0.617초였지만 역할 주체 역전과 면접 원인·신체 증상 추측으로 품질 후보에서 제외했다. 584 tests/Ruff/compile/diff 검사 통과. 현재 9B·웹·관리자·터널 복구, web/admin/model/public root 200 확인. 사용자 DB·공개 quota 미사용. REPLY_PLANNING_COMPARISON.md 참고.

## 2026-09-09 EXP13/14 반복 대사 루프 차단 — 구현·검증 완료

실제 최근 추적에서 10턴 중 7턴의 유사 맞장구와 74메시지 assistant 자기오염을 확인했다. 전면 구체화·경계 프롬프트는 근거 없는 단정과 경계 실패를 만들어 폐기했다. 대사 입력에서만 반복 pair의 중간 항목을 축약하고, 새 후보가 최근 답변 2개 이상과 겹칠 때 한 번만 다시 생성하도록 최소 개입을 적용했다. 실제 비저장 재현에서 5 pair를 생략한 뒤 최대 유사도는 seed109 1.000→0.400, seed211 0.714→0.400으로 낮아졌다. 581 tests/Ruff/compile/diff 검사 통과. 웹·관리자 재시작 후 공개 합성 root/session/chat/reset 200, 합성방 reset. 모델·터널·DB/API/80자/metadata 원본 이력은 유지한다. 일반적인 단답 깊이는 별도 모델·계획 단계 비교 대상으로 남는다. REPLY_LOOP_GUARD.md 참고.

## 2026-09-09 EXP12 활성 화제 검색 — 구현·검증 완료

최근 사용자 발화의 화제 종료/전환/취소 경계를 적용하고 작품·추천 지칭과 시간 기반 목적지 생략을 출처 있는 사건에 보수적으로 연결. 새 호출/DB/설정 없음. EXP11 대비 영화 검색0/2→2/2, 종료 화제 오선택2/2→0/2; 제목 대사 사용은1/2. 최종574tests/Ruff/compile 통과. 웹·관리자만 재시작하고 모델·터널·DB 유지; 합성 공개 chat/reset 200. 모델 search_cues 운영OFF 유지. ACTIVE_TOPIC_RETRIEVAL.md 참고.

## 2026-09-09 EXP11 완료 — 채택 보류 유지

새 표현·주제전환·취소 16실행/32턴/64호출 완료. 제목 회상은 영화 양쪽0/2, 책 양쪽2/2로 추가 이득 없음. 영화 단서 누락 및 화제 전환 뒤 이전 영화 검색 재현(기존 검색에도 존재). 취소한 영화 약속을 현행으로 답하지 않았으나 장기 취소 저장 검증은 아님. 관련17tests 통과. 구현·운영 설정 고정. SEARCH_CUE_VALIDATION.md 참고.


## 2026-09-09 EXP10 완료 — 운영 채택 보류

기존2호출 유지 실험:48턴/96모델호출,단서로 회상 일부 개선(근거있는8건중4건),단서누락/주제잔류 존재. 주실험단서생성턴 중앙값2.781→2.922s. 571tests통과. 명시적 실험속성으로만동작,운영/DB/공개계약유지. SEARCH_CUE_EXPERIMENT.md 참고.


## 2026-09-09 EXP09 완료

합성2질문×3조건×2seed=12회,24모델 호출 정상. 명시적 영화 검색은 원문 없이 대상 회상에 도움, 암시적 어딜은 검색0개여서 효과 없음. 이력만 조건은 영화관 회상. 운영 설정/DB 변경 없음. docs/MEMORY_ABLATION.md 참고.


## 2026-09-09 Task17 기존 기억 규칙 수정 — 완료

구조 유지: 이름 교환 직후의 단축 소개, 영화 제목 추천 제안, 시간 포함 만남 제안 인식과 관련 검색을 보완했다. 최근 대화와 중복된 요약 발언은 모델 입력에서 제외. 기존 대화·모델·프롬프트 설정 유지. 569 pytest(12.33s), Ruff/compileall/diff 검사 통과. 웹·관리자 재시작 및 현재 기억 조회 확인. DB migration/commit/push 없음. 생성 품질 실험 미실시. docs/MEMORY_PIPELINE.md Task17 참고.

## 2026-09-09 Task16 입력/출력·기억 판단 추적 — 완료

입력/출력 색상과 영역 분리, 실제 분석 지시문 기본 펼침. 검색 기준과 후보별 선택·제외, 입력 포함 여부, 모델/서버 후보 경로 및 원문 근거 검사·저장 결과를 당시 trace로 표시한다. 이름·사건 파생은 일반 기억 테이블과 구분. 과거 상세 미기록은 명시. 검색/저장 정책 유지.

562 pytest passed(16.02s), UI5 tests, lint/compile/syntax/diff 검사 통과. 실제 모델 별도2턴 취향 저장/검색/질문 후보 제외 확인 후 합성방 reset, 사용자방 유지. 웹만 재시작. DB migration/commit/push 없음. [상세](LOCAL_INSPECTOR.md).

## 2026-09-09 Task15 프롬프트 편집·시간순 검사 — 완료

로컬 테스트 요청에만 캐릭터 소개·말투 편집본을 적용하고 버전/정확한 입력을 진단에 기록한다. 기본값 복원, 재시도 편집본 보존, 공유 설정 격리. 입력 준비→대사 생성→부가정보 분석→저장 순서로 각 입력/출력 표시. 현재 기억은 별도 조회, 모델 입력과 전체 진단 JSON 설명 분리.

pytest555 passed(11.62s), UI4 tests, Ruff/compileall/JS 구문 및 diff 검사 통과. 실제 브라우저 편집·1턴 전송·두 단계 반영·기본 복원 확인. 웹/관리자만 재시작. 확인용1턴 유지, 모델 언어 혼입 미해결. 준비 상태 첫 조회403은 guest 자격 누락이며 실제 생성 정상. DB migration/commit/push 없음. [상세](LOCAL_INSPECTOR.md).

## 2026-09-09 검사 창 가독성·통합 테스트 채팅 — 완료

Task14: 검사 내용을 기억 근거/역할별 입력/처리 단계 카드로 바꾸고 원본JSON은 접었다. 별도 테스트 채팅을 같은 창에 추가해 자기 테스트 guest 방으로만 전송하며 검사도 자동 선택한다. 새로고침 이력 복원·동일 요청 재시도·방 초기화 지원. 정확한 로컬 Origin/Host/JSON/경로/본문 제한을 적용한 bridge가 고정 loopback 웹 API를 사용하므로 기존 소유권·큐·한도 유지.

기준545 → pytest552 passed(11.89s), Ruff/compileall/JS 구문검사, UI3 tests 통과. 실제 브라우저 테스트2턴/기억카드/프롬프트/새로고침 복원 확인. 관리자만 재시작, 웹/모델/터널 유지. 확인용 테스트 대화2턴 남김. 모델 언어 혼입 등 생성 품질 문제는 별개다. 기존 미커밋 변경 보존, DB migration/commit/push 없음. [상세](LOCAL_INSPECTOR.md).

## 2026-09-09 로컬 모델 검사 창 — 구현·활성화 완료

Task13: 로컬 관리자 /inspector 별도 창, 1초 갱신/방·처리·시도 선택. 실제 두 단계 요청/응답·검증 실패·저장 결과와 선택 기억/현재 저장·파생 기억을 구분한다. NPC_DEBUG_TRACE 기본OFF, 이번 시험 환경만ON. 별도 로컬 진단 SQLite에1시간/100회 한도, reset 정리, 공개 경로 없음. 진단 장애는 채팅에 영향 없음.

기준540 → pytest545 passed(10.97s), Ruff/compileall/JS 구문 검사 통과. 공개 합성 실제9B1턴 두 단계·저장 응답 일치/공개 비노출/reset 확인, 브라우저 창과 기억 탭 확인. 웹/관리자만 재시작, 모델/터널 및 기존 미커밋 변경 보존. 추적 이전 입력은 소급 복원하지 않으며 현재 기억은 조회 가능. [사용법·보관·검증](LOCAL_INSPECTOR.md). commit/push 없음.

## 2026-09-08 기억 전달 경로 개선 — 구현·공개 적용 완료

Task12/EXP08: 원문 turns에서 최근 대화를 읽고 실제 토큰 예산으로 선택한다. 명시적 이름/호칭과 정정, 출처 있는 추천/약속/취소를 원문 기반 파생 뷰로 구성하여 전달한다. 기존 캐릭터 대사 생성과 메타데이터 스키마 유지, 추가 모델/테이블/DB migration 없음. 기존 UI와 실험 미커밋 변경 보존.

기준522 → pytest540 passed(10.18s), Ruff/compileall 통과. 합성52턴/152턴 실제9B 각4사례에서 책/이름 회상, 호칭 반영, 미제공 영화 제목 미생성 확인. 152턴은 원문이 입력에서 제외돼도 별도 증거로 정답을 회상했고 전체 시간 중앙값14.132초. 말투와 부가 정보 오류 가능성은 남는다. 기존 문제 대화의 두 정보 재구성도 읽기 전용으로 확인했다. 웹만 재시작하고 공개 이름/호칭3턴·replay·reset 검증 완료. 파생 기억은 기존 accepted_candidates 수에 포함되지 않는다. 원문 전체 순회 비용과 복잡한 사건 연결은 한계다. [구현·명령·결과](MEMORY_PIPELINE.md). commit/push 없음.

## 2026-09-08 채팅 전송 피드백 타이밍 개선

사용자 입력을 전송하면 세션·이력·채팅 API를 기다리기 전에 사용자 버블을 즉시 추가하고 입력창을 비운 채 잠근다. 유이의 입력 중 표시는 전송 직후가 아니라 650ms 뒤에도 응답을 기다리는 경우에만 나타난다. 빠른 응답에서는 입력 중 표시를 건너뛰며, 실패 시에는 기존과 같이 같은 메시지를 입력창에 복원하고 동일 turn ID 재시도를 유지한다. API·DB·모델 설정과 대화 저장 계약은 변경하지 않았다.

변경 전 기준은 `node --test tests/frontend.test.cjs` 22 passed, `./venv/Scripts/python.exe -m pytest -q` 522 passed, `./venv/Scripts/python.exe -m compileall app` 성공이다. 프런트 회귀 테스트에 즉시 버블/빈 입력창/초기 입력 중 숨김 및 650ms 지연 표시를 추가했다. 변경 후 `node --check frontend/app.js`, `node --test tests/frontend.test.cjs` 22 passed, 전체 pytest 522 passed, compileall 및 `git diff --check`가 통과했다. 격리 HTTP smoke는 현재 기본 2048 context에서 늘어난 프롬프트가 입력 예산을 초과해 채팅 요청이 `INPUT_TOO_LONG`으로 실패했다. 이 UI 변경 전 기준 smoke는 실행하지 않았고 JS/API payload 변경과 무관하므로 기존 문맥 설정 계열의 환경 의존 한계로 기록하며 숨기지 않는다.

## 2026-09-08 동일 모델 2단계 생성 — 구현·공개 적용 완료

EXP-07/Task 11: 같은 9B 모델에 대사 JSON → 고정 대사를 보는 부가 정보 JSON을 순차 요청하고 두 단계 성공 후 기존 원자적 저장을 수행한다. 메타데이터 재시도는 대사를 재생성하지 않는다. canonical API/DB/단일 모델 프로세스를 유지하며 환경 예제와 현재 로컬·공개 설정에 `NPC_GENERATION_MODE=two_stage` 적용. 미설정 또는 명시적 single_pass로 기존 방식 호환. 웹만 재시작했고 모델/터널/관리자는 유지했다.

기준 507 → `./venv/Scripts/python.exe -m pytest -q` 522 passed (10.60s), Ruff/compileall 통과. 같은 합성 4사례로 분석 지시를 3차례 보정했고 최종 8개 호출 모두 최초 형식 유효. 최종 전체 시간 중앙값 5.414초(대사 1.516초, 부가 정보 3.945초). 반복 개발 사례이며 독립 품질 검증은 아니다. 공개 합성 3턴 200/취향 정정 회상/중복 replay/방 reset 통과, 5.922~7.453초. 첫 활성화의 준비 확인은 공개 차단 경로를 사용해 실패했으며 확인 방법 수정 후 재적용했다.

부가 정보의 질문 오분류와 사과 대사의 역할 표현이 남아 있다. 다음은 새로운 표현으로 대사/분류를 나누어 평가하는 작업이다. 기존 미커밋 변경 보존, DB migration 및 commit/push 없음. [구현·설정·검증](TWO_STAGE_GENERATION.md), [실험 계보](EXPERIMENT_LINEAGE.md).

## 2026-09-08 예시 경계와 대사 전용 비교 — 완료

사용자 승인으로 EXP-05(예시 경계/제거)와 EXP-06(전체 출력/대사 JSON/대사 텍스트)을 순서대로 비교한다. 기준 테스트 496 passed, 기존 미커밋 변경 보존. 공개 설정·DB·모델 변경 없이 합성 입력으로 비교하고 계보와 원자료를 기록한다. Task 10: tasks/10_EXAMPLE_AND_REPLY_ABLATION.md.

EXP-05 36회, EXP-06 36회와 다른 표현 12회 모두 최초 형식 유효. 예시 제거는 일부 이름/추측 감소에 도움을 보였으나 예시 혼입의 인과관계는 미확정. 대사 JSON은 다른 표현의 버스 지각 이유와 잘못된 이름 복원에서 전체 JSON보다 적절했고 기본 대사 생성 중앙값 3.99초→1.14초였다. 부가 정보 생성 비용을 뺀 수치이며 일반 텍스트는 말투 이탈도 보였다. 공개는 미변경, 다음은 대사 JSON/부가 정보 분리의 격리 시제품 후보. `./venv/Scripts/python.exe -m pytest -q` 507 passed (10.99s), Ruff/compileall/Git 공백 검사 통과. [전체 결과](EXAMPLE_AND_REPLY_ABLATION.md), [계보](EXPERIMENT_LINEAGE.md). DB/설정 변경 및 push 없음.

## 2026-09-08 반복 억제 비교와 실험 계보 — 완료

사용자 승인으로 docs/EXPERIMENT_LINEAGE.md에 기존 실험의 연결·판단·적용 여부를 모은다. Task 09는 운영 프롬프트를 고정한 4개 샘플링 조건 비교이며 사전 기준은 487 tests passed. 기존 미커밋 변경을 보존하고 운영 설정은 검증 전 바꾸지 않는다. 실행 중 서버의 기본 penalty window는 repeat_last_n=64로 확인했으며 서버 기본값과 앱이 요청에 지정하는 값은 구분한다.

4조건 × 6사례 × 2시드 = 48회 모두 최초 형식 유효, 별도 서버 지원 probe 4회 성공. repeat 단독 해제는 일부 이름 보존에 도움이 됐으나 문맥 실패가 지속되고 반복 탈출은 현재값에서도 성공해 우월성은 불충분했다. 공개 설정 유지. 빈 history의 면접 질문에 과거 시험 사건을 만드는 결과를 근거로 다음 후보는 예시/실제 대화 혼입 분리 검사다. `./venv/Scripts/python.exe -m pytest -q` 496 passed (10.69s), Ruff/compileall/Git 공백 검사 통과. [실험 계보](EXPERIMENT_LINEAGE.md), [비교 결과](SAMPLING_COMPARISON.md). AGENTS.md에 향후 실험마다 계보 갱신 규칙을 추가했다. 운영/DB 변경, commit/push 없음.

## 2026-09-08 역할·말투 프롬프트 비교 — 완료, 운영 교체 보류

입력 점검에 이어 사용자 승인으로 A(현재), B(역할 구분/섹션 정리), C(B+충돌 예시 수정)를 격리 비교한다. 직전 기준 484 tests passed이며 기존 기억 개선의 미커밋 파일을 보존한다. 모델/서버 설정과 저장 동작은 고정하고 개인 대화 대신 합성 다중 턴 문맥을 사용한다. 원래 모델 출력과 서버 보정 후 출력을 따로 기록한다. 효과를 확인하기 전 공개 앱의 캐릭터 설정은 변경하지 않는다.

완료 결과: 기본 60회 + 다른 표현 12회 모두 최초 시도에 형식 유효. C는 메뉴 제안/짧은 확인/시험 실패 예시에서 나아졌으나 새 면접 사례에서는 미제공 노력을 여전히 가정했고 이름을 '유야'로 출력하거나 명시된 수면 시간과 이유를 연결하지 못했다. B/C의 일반적인 우월성을 입증하지 못해 공개 기본 프롬프트는 유지했다. 변경은 실험용 프롬프트/평가 도구/테스트/문서이며 DB·운영 설정 변경 없음. `./venv/Scripts/python.exe -m pytest -q` 487 passed (12.03s), Ruff/compileall/Git 공백 검사 통과. 상세: [IDENTITY_VOICE_COMPARISON.md](IDENTITY_VOICE_COMPARISON.md). 다음 후보는 동일 프롬프트에서 반복 억제 설정만 분리 비교이며 아직 미실행이다.

## 2026-09-08 현재 모델 입력 점검 완료

생성 직전 합성 입력을 실제 DecisionService에서 포착하고 실행 중 llama.cpp 템플릿·토큰화로 점검했다. canonical 경로, system/user/assistant 분리, 사용자 원문 보존을 확인했다. 샘플 1,347토큰으로 입력 잘림 없음. 미제공 상황을 단정하는 고정 예시, 중복 섹션 제목, 서버 취향 회상 보정이 주요 수정/평가 분리 대상이다. 역할 규칙은 이미 전달되고 있으며 오류 원인과 개선 효과는 아직 확정하지 않았다.

`./venv/Scripts/python.exe -m pytest -q` 484 passed (11.10s). 생성은 가로채 합성 응답으로 대체했으며 개인 DB 접근·모델 생성·제품 코드 변경·재시작 없음. 기존 미커밋 기억 개선을 보존했다. 상세 결과와 다음 비교 범위: [PROMPT_INPUT_AUDIT.md](PROMPT_INPUT_AUDIT.md). 새로운 제품 결정은 내리지 않았다.

## 2026-09-08 문맥 기반 기억 선택 — 구현 및 실행 검증 완료

사용자가 승인한 1차 범위는 현재 메시지+최근 문맥으로 기억 선택, 무관한 기억 0개 반환, 명확한 취향 정정 보강이다. 기준 HEAD는 main에 병합된 1efec51이며 a9f6205 이후 누적 변경을 확인했고 작업 시작 시 미커밋 변경은 없다. 기존 저장/권한/한도/문맥 예산과 모델 설정을 보존한다. 별도 모델·임베딩·벡터 DB·프레임워크·DB migration은 추가하지 않는다. 작업 정의: tasks/07_CONTEXT_AWARE_MEMORY.md.

현재 주제 우선 검색, 서버 최근 발언을 이용한 제한적 이어 말하기 검색, 관련 기억 0~3개 선택, 생성 전 반대 취향 제외와 성공 후 취향 갱신을 구현했다. 변경은 app/memory.py, repository.py, main.py, prompt_context.py와 관련 테스트·합성 평가 도구·문서다. 상세: [CONTEXT_AWARE_MEMORY.md](CONTEXT_AWARE_MEMORY.md).

기준 테스트 435 passed → 최종 `./venv/Scripts/python.exe -m pytest -q` 484 passed (9.64s). `./venv/Scripts/python.exe -m ruff check app tests scripts`, `./venv/Scripts/python.exe -m compileall -q app scripts`, `git diff --check` 통과. 합성 기억 선택 집합 일치 12/12, 실제 9B 응답 6/6 형식 유효. 이 결과는 자연스러운 대화 품질을 보장하지 않으며 역할 혼동은 남았다.

웹 프로세스만 재시작하여 공개 테스트 링크에 적용했다. 새로운 검증용 방문자로 녹차 선호 → 부정 정정 → 재확인 3턴 모두 HTTP 200, 정정된 취향 회상과 3턴 저장을 확인한 뒤 해당 대화방만 초기화했다. 기존 사용자 기록·모델·터널은 보존했고 검증 3회는 일일 한도에 포함된다. 브랜치 codex/context-aware-memory에서 작업했으며 아직 커밋·push하지 않았다. 다음 작업은 별도 사례로 검색 누락/오탐을 평가하고 모델의 역할 혼동을 분리 개선하는 것이다.

## 2026-09-08 main 병합 전 Python 3.11 취소 경합 수정

원격 main과 작업 브랜치의 차이는 공유한 3개 커밋이며 별도 main 변경은 없었다. GitHub 3.12 검사는 통과했으나 3.11에서 queue 취소 테스트가 멈췄다. 로컬 Python 3.11 표준 라이브러리 재현에서도 시작 이벤트 완료와 외부 취소가 겹칠 때 취소한 요청이 2초 뒤에도 완료되지 않았다. asyncio.wait_for 대신 asyncio.timeout 범위 안에서 직접 이벤트를 기다리도록 수정했다. 기존 회귀 테스트에 유한 대기 검증을 추가해 같은 문제가 CI를 무한 대기시키지 않도록 했다. DB/배포 설정 변경은 없다.

수정 후 로컬 Python 3.11 재현 통과, `./venv/Scripts/python.exe -m pytest -q` 435 passed (9.79s), `./venv/Scripts/python.exe -m ruff check app tests scripts`, `./venv/Scripts/python.exe -m compileall -q app` 통과. 멈춘 이전 CI는 취소하고 새 커밋으로 두 Python 버전 검사를 다시 수행한다.

## 2026-09-08 GitHub 공유 체크포인트

사용자 요청으로 누적 구현을 현재 `codex/p0-baseline-stabilization` 브랜치에 서버/운영, 프런트, 문서/검증 설정으로 나눠 커밋하여 원격에 공유한다. main 병합이나 실행 환경 변경은 이번 범위에 포함하지 않는다. 실제 .env, .runtime, 대화 DB, 모델 가중치와 임시 공개 URL은 제외한다. 평가 자료는 기존 합성 사례 기반 자료만 포함한다.

push 전 검증: `./venv/Scripts/python.exe -m pytest -q` 435 passed (9.79s), `node --test tests/frontend.test.cjs` 22 passed, `./venv/Scripts/python.exe -m ruff check app tests scripts`, `./venv/Scripts/python.exe -m compileall -q app scripts` 통과. 추가 기능 수정이나 DB migration은 없다. 원격 커밋 일치 여부는 push 후 확인한다.

새 문서까지 포함한 Git 공백 검사는 Markdown 강제 줄바꿈과 평가 TSV의 빈 마지막 열을 공백 오류로 보고했다. 원본 handoff/평가 파일을 변형하지 않고 `.gitattributes`에 해당 형식의 행 끝 공백만 허용했다. 코드 파일의 공백 검사는 유지한다.

## 2026-09-08 관리자 조회·새로고침 복원·대화방 나가기

완료: 서버 기록 50턴 단위 조회/이전 기록 불러오기, 새로고침 후 말풍선/표정 복원, 응답 유실 후 저장된 턴과 pending ID 대조, 별도 확인창을 통한 대화·기억·관계 초기화. 목록 복귀는 유지 동작이다. 초기화는 모든 기존 세션을 폐기하고 큐의 chat을 실행 직전에 재검증한다. 다른 방문자/캐릭터 및 일일 한도는 보존한다. 기존 DB 스키마 변경 없음.

관리자 조회는 공개 앱과 분리된 127.0.0.1:8002 읽기 전용 앱으로 실행 중이다. 방문자별 대화 목록/질문·답변/시각을 조회하며 수동 새로고침과 페이지 탐색을 지원한다. Host/Origin/Fetch-Site/loopback 검사를 적용했고 공개 앱에 관리자 경로를 추가하지 않았다. 개인정보 안내와 나가기 의미를 UI에 명시했다. 방문자는 브라우저 단위이며 기기 간 로그인/동기화, 관리자 원격 접속/편집, 자동 부팅은 범위 밖이다.

변경 파일: app/main.py, repository.py, remote_access.py, 새 app/admin.py, admin/index.html, scripts/serve_admin.py, local_runtime.py, frontend 3개 파일, tests/test_conversation.py, frontend.test.cjs, 현재 상태/결정/API/DB 문서와 CHAT_HISTORY_AND_ADMIN.md.

검증: 기준 `./venv/Scripts/python.exe -m pytest -q` 426 passed → 최종 435 passed (9.52s), `node --test tests/frontend.test.cjs` 18 → 22 passed. `./venv/Scripts/python.exe -m ruff check app tests scripts`, `./venv/Scripts/python.exe -m compileall -q app scripts`, `node --check frontend/app.js` 모두 통과. 새 비동기 복원에 맞춰 기존 프런트 테스트 2개의 대기 시점을 수정했으며 최종 실패 없음. 상세 검증과 운영 명령: [CHAT_HISTORY_AND_ADMIN.md](CHAT_HISTORY_AND_ADMIN.md).

실행 확인: 소유 웹만 재시작, 모델/터널/DB/한도 설정 유지. `scripts/local_runtime.py start-admin --env-file .runtime/public-test.env` 성공. agent-browser로 공개 링크의 합성 1턴 생성→새로고침 복원→관리자에서 동일 질문/답변 조회→나가기 취소 보존→확정 초기화→목록 복귀→새로고침 후 빈 대화를 확인했다. 관리자 새로고침에서도 해당 합성 대화가 사라졌다. 다른 방문자 기록은 삭제하지 않았다. 모바일 390×844 확인창과 320×568 방을 검사했다. 스크린샷/식별자는 무시된 로컬 파일 또는 브라우저 임시 폴더에만 보관한다. 실제 생성 테스트 1회는 일일 한도에 포함된다.

다음 기능: 실제 복수 캐릭터 선택과 캐릭터별 상태 연결. 모델 대화 품질 개선은 별도 과제로 유지한다.

## 2026-09-08 대화 목록과 캐릭터 영상 연결 UI

사용자 요청에 따라 모바일 메신저 목록→유이 방→목록 복귀 흐름과 영상 연결/축소/종료 컨트롤을 구현했다. 변경 파일: frontend/index.html, styles.css, app.js, tests/frontend.test.cjs, PROJECT_STATUS, DECISION_LOG. 기본 진입은 대화 목록이며 hash 경로 `#chat/yui`로 방을 직접 열 수 있다. 같은 페이지에서 이동할 때 방 DOM을 보존하여 말풍선과 초안을 유지한다. 답변 생성 중 목록으로 이동해도 요청을 취소하거나 중복 생성하지 않으며, 응답 도착 시 목록 미리보기/새 답변 표시를 갱신한다.

기본 방은 텍스트 채팅이며 영상 버튼으로 캐릭터 화면을 연다. 실제 이미지 로드 상태에 맞춰 준비/연결/실패를 표시하고, 작게 보기와 빨간 영상 종료 버튼을 제공한다. 영상 종료나 목록 복귀는 캐릭터 영역만 닫으며 채팅 상태/서버 기록을 삭제하지 않는다. 카메라·마이크 권한, 실제 영상 통신, 새 모델 호출은 추가하지 않았다. 화면에 캐릭터 화면임을 명시하고 작동하지 않는 카메라/음소거 버튼은 넣지 않았다. 다른 캐릭터는 준비 중 정보 카드이며 아직 선택·대화할 수 없다. 실제 추가에는 서버 캐릭터 선택과 상태 분리가 필요하다.

검증:

- 변경 전 `node --test tests/frontend.test.cjs`: 15 passed.
- 최종 동일 명령: 18 passed. 영상 연결/축소/종료가 추론 요청을 만들지 않음, 생성 중 목록 이동/미리보기/새 답변/재입장 보존, 직접 경로 및 이미지 실패 상태를 검사했다. 기존 typing/retry/문자열 안전 표시/timeout 테스트 유지.
- `node --check frontend/app.js`, `git diff --check`: 통과. Windows 줄바꿈 안내 외 실패 없음.
- `./venv/Scripts/python.exe -m pytest -q`: 426 passed (11.87s). 최종 이후 변경은 프런트의 이미지 로드 상태 문구와 문서뿐이며 프런트 검사는 다시 통과했다.
- agent-browser로 기존 공개 주소에서 390×844 목록·영상 연결 화면과 320×568 축소 화면을 직접 확인했다. 실제 합성 대화→목록 미리보기 갱신→재입장 말풍선 유지→영상 축소→종료 후 입력창 유지까지 확인했다. 외부 대화 1회는 테스트 한도에 포함된다. 스크린샷은 로컬 브라우저 임시 디렉터리이며 사용자 대화 원문을 저장소에 추가하지 않았다.

정적 파일 갱신이므로 모델/웹 재시작이나 migration 없이 기존 링크에서 새로고침해 사용할 수 있다. 서버/일일 한도/9B 설정은 변경하지 않았다. 새로고침 후 과거 말풍선을 다시 불러오는 기능은 아직 없으며, 서버 기록은 유지된다. 다음은 서버 권한을 검증하는 대화 목록/이력 조회와 실제 복수 캐릭터 연결이다.

## 2026-09-08 모바일 메신저 UI와 입력 중 모션

변경 파일: frontend/index.html, styles.css, app.js, tests/frontend.test.cjs, PROJECT_STATUS, DECISION_LOG. 화면 상단에 유이 얼굴을 고정하고 하단에는 좌측 캐릭터/우측 사용자 말풍선을 누적한다. 말풍선만 스크롤되며 입력창은 하단에 유지한다. 모바일 동적 높이·safe area·작은 높이 대응, 키보드 viewport resize 힌트를 추가했다. 답변 생성 중 세 점 애니메이션은 sending/waiting 상태에만 표시한다. 성공/실패/오프라인에서는 사라진다. 이미지 로드 시 짧게 페이드하며 reduced-motion을 존중한다. 개발/추가 이미지 옵션은 접어둔다.

표시하는 문장은 textContent로 넣고 역할+client_turn_id로 중복 말풍선을 막는다. 기존 pendingTurn/retry와 서버 대화 권한은 유지한다. 새로고침 후의 과거 대화 조회 API는 추가하지 않아 말풍선은 페이지를 연 동안만 누적된다. 서버 기록은 삭제되지 않는다. UI 변경으로 모델/서명 키/일일 한도를 변경하지 않았다.

검증: 변경 전 `node --test tests/frontend.test.cjs` 14 passed. 변경 후 기존 14개에서 입력 중 표시와 종료, 재시도 중 말풍선 중복 방지 검증을 추가하여 통과했다. 추가 다중 턴/textContent 테스트까지 최종 15 passed. 최종 `git diff --check`도 통과했다. `node --check frontend/app.js` 통과. `./venv/Scripts/python.exe -m pytest -q`: 426 passed (9.98s). `agent-browser`로 기존 공개 URL에서 390×844, 320×568 화면을 검사하고 실제 합성 대화 한 번의 입력 중 상태·응답 말풍선·표정·입력 복구를 확인했다. 브라우저 설정 후 최초 CLI 클릭은 PowerShell에서 따옴표 없는 @ref 인자로 실패했고, 인용한 참조로 다시 실행해 정상 확인했다. 페이지/자산은 재시작 없이 반영된다. 실제 휴대폰의 가상 키보드 동작은 실기기에서 추가 확인이 필요하다.

별도 migration 없음. 다음은 새로고침 후 서버 대화 이력을 안전하게 조회·복원하는 기능이다.

## 2026-09-08 공개 테스트 일일 한도 확대

사용자 지정대로 무시된 공개 설정의 NPC_DAILY_VISITOR=300, NPC_DAILY_TOTAL=2000을 적용하고 소유 웹만 재시작했다. 다른 설정은 변경 전 값과 일치함을 검사했다. 현재 모델·터널·DB·오늘 사용량은 유지한다. `.runtime/restart_guest_web.py` 성공, 소유 web/llm/tunnel 실행 확인, 외부 페이지 HTTP 200 확인. 실행 코드 변경이 없어 자동 테스트는 재실행하지 않았다. 별도 migration 없음.

## 2026-09-08 Aggressive 9B Q4_K_M 시험 적용

사용자의 더 큰 Aggressive 모델 시험 승인에 따라 9B Q4_K_M을 저장소 밖에 내려받고 SHA-256을 검증했다. 출처: [HauhauCS 모델](https://huggingface.co/HauhauCS/Qwen3.5-9B-Uncensored-HauhauCS-Aggressive), revision `0a41c68809d375475f954be12ba7c40efa56c2a9`, 파일 `Qwen3.5-9B-Uncensored-HauhauCS-Aggressive-Q4_K_M.gguf`, 5,627,044,224 bytes, SHA-256 `2ca636d9e81d3d23ca9b60c234fe185d30ec082eeba69ce770fdb0c76559a4f5`. 느려진 단일 다운로드를 중단 후 검증된 Range 응답으로 나머지를 받아 전체 해시를 확인했다. 미완성 파일을 모델로 사용하지 않았다.

현재 개발/공개 테스트: 9B Q4_K_M, 문맥 4096, 출력 256, GPU layers auto, parallel 1, batch/ubatch 128, thinking OFF. 소유 모델·웹만 교체하고 터널·서명 키·DB·기존 대화는 유지한다. 4B 파일과 관련 설정/소유 프로세스 인자는 무시된 `.runtime/before-9b.json`에 보존한다. 공유 문서에 로컬 절대 경로나 임시 URL을 넣지 않는다. 기존 9B Q6_K도 삭제하지 않았다.

기준 HEAD는 a9f6205로 동일, 기존 변경 보존. 변경 파일: `scripts/evaluate_dialogue_flow.py`, `.env.example`, AGENTS, README, 현재 런북, PROJECT_STATUS, DECISION_LOG. 애플리케이션의 API/DB 구조는 이번에 변경하지 않았다. 평가 스크립트는 6개 고정 합성 이력으로 이유 설명·오해 수정·주제 전환·맞장구·경계·이름을 확인하며 개인 DB에 접근하지 않는다.

검증 명령과 결과:

- `./venv/Scripts/python.exe -m pytest -q`: 426 passed (9.16s). `./venv/Scripts/python.exe -m ruff check scripts/evaluate_dialogue_flow.py` 및 `./venv/Scripts/python.exe -m compileall -q scripts/evaluate_dialogue_flow.py`: 통과. `git diff --check`: 통과.
- `./venv/Scripts/python.exe scripts/evaluate_dialogue_flow.py --model HauhauCS/Qwen3.5-4B-Uncensored-HauhauCS-Aggressive --output .runtime/flow-4b.json`와 9B/flow-9b.json 비교: 각 6/6 형식 성공, 각 재시도 0. 4B p50 1.547초/최대 2.234초; 9B p50 4.687초/최대 17.188초. 9B 최초 생성은 17.188초, 나머지는 2.219~6.281초. 요청 문맥 예산은 둘 다 4096이고 모델 서버 용량은 4B 8192/9B 4096이었다. 짧은 입력은 모두 잘림 없이 들어간다. 출력/캐시/서버 적재 방식이 다르고 확률적 소표본이므로 엄밀한 모델 우열 시험은 아니다.
- 9B는 반말과 일부 오해 수정/경계 대응이 나았지만 이유 질문에 답하지 않은 사례와 자신을 '유이는 … 좋아할 것 같아'라고 제삼자처럼 언급하는 문제가 남았다. 품질 승자로 확정하지 않고 사용자 비교 시험으로 적용했다. unknown flag 경고 1회는 기존 allowlist 필터가 제거했다.
- `./venv/Scripts/python.exe scripts/evaluate_short_replies.py --output .runtime/short-replies-9b.json`: 10응답, 직전 문자열의 연속 동일 반복 0/10, p50 3.789초/최대 4.969초. 의미 반복이나 일반 대화 이해 전체의 합격 판정은 아니다.
- `.runtime/swap_9b.py candidate` / `activate`: 소유권 검증 후 교체·프로파일 적용. 기동 전 GPU free 3868 MiB, 초기 검사 시 free 약 298 MiB. 전체 GPU 적재나 VRAM 여유 확보를 주장하지 않는다. 자동 배분이며 다른 앱 사용량 변화/장시간 동시 사용은 미검증이다.
- `./venv/Scripts/python.exe .runtime/verify_public_test.py`: 기존 외부 링크 화면·자산·대화 200, 재전송 동일 응답, 타 브라우저 접근 403. 모델 `/props`의 n_ctx 4096과 두 private env의 9B/4096 일치 확인. 외부 합성 요청 1회는 테스트 한도 사용.

Migration 불필요. 되돌릴 때 4B alias/모델 파일/문맥8192/GPU all을 두 private 프로파일에 복원하고 소유 모델·웹을 재시작한다. 현재 PC에서는 무시된 `.runtime/swap_9b.py restore`로 저장된 설정에 복귀할 수 있다. 다음은 사용자의 실제 대화 흐름 평가이며, 결과가 나쁘거나 지연이 부담스러우면 4B 복귀 또는 다른 모델 비교를 진행한다.

## 2026-09-08 짧은 긍정 뒤 반복 응답 보완

최근 대화의 서로 다른 client_turn_id에 같은 응답이 연속 저장된 것을 읽기 전용으로 확인했다. 원문이나 개인 식별자는 이 기록에 복사하지 않는다. 재전송 캐시/화면 재표시 문제가 아니라 생성 결과 반복이었다. 사용자 승인 후 canonical 모델 요청의 누락된 샘플링 설정 전달과 기본 캐릭터의 짧은 긍정 예시를 수정했다.

변경 파일: `app/services/decision_service.py`, `app/characters/default.json`, `tests/test_decision.py`, `scripts/evaluate_short_replies.py`, 현재 런북, PROJECT_STATUS, DECISION_LOG. top_k 20, presence 0.5, frequency 0.3, repetition 1.08은 기존 선언값을 전달한다. llama.cpp는 `repeat_penalty`, vLLM은 `repetition_penalty`로 구분하며 top_k=0도 생략하지 않는다. 최초/재시도에서 동일하게 전송한다. [설치 버전 llama.cpp 소스](https://github.com/ggml-org/llama.cpp/blob/b10830/tools/server/server-task.cpp) 및 로컬 `/completion`의 반환 generation_settings에서 필드와 유효값을 확인했다. 이는 canonical 요청 전송 테스트와 별개로 서버의 파라미터 지원을 확인한 검사다.

`ㅇ`/`ㅇㅇ`/`응`/`응이라고`를 직전 말의 긍정·확인으로 받고 같은 질문을 다시 묻지 않도록 지침과 다중 턴 예시를 추가했다. 모델 응답을 고정 문구로 덮어쓰거나 이미 저장된 사용자 이력을 제거하지 않는다. 컨텍스트 8192, 출력 256, 모델/DB/관계 계산/재전송 계약은 유지한다.

검증 명령 및 결과:

- 변경 전 `./venv/Scripts/python.exe -m pytest -q`: 422 passed (9.02s). 뒤이어 잘못 지정한 Task 파일 읽기가 실패해 전체 셸 명령의 exit는 1이었지만 테스트는 통과했다. 실제 Task 04 파일을 찾아 읽었다.
- 최초 수정 후 전체 테스트: 1 failed, 425 passed. 늘어난 캐릭터 예시가 기존 정체성 테스트의 기본 2048 추정 예산에서 재시도를 넘었다. 해당 테스트를 현재 8192 프로파일로 명시했다. 입력 초과/현재 입력 보존 검사는 별도 유지한다. 2048 fallback+추정 계수로 현재 기본 캐릭터의 모든 재시도가 가능하다는 보장은 하지 않는다.
- 최종 `./venv/Scripts/python.exe -m pytest -q`: 426 passed (9.25s). llama.cpp/vLLM, top_k 0/20, 최초 및 실패 후 재시도에 대한 실제 HTTP 요청 본문 검증 4개 추가.
- `./venv/Scripts/python.exe -m ruff check app scripts tests`: 통과. `./venv/Scripts/python.exe -m compileall -q app scripts`: 통과. `git diff --check`: 통과, 기존 CRLF 안내만 있음.
- `./venv/Scripts/python.exe scripts/evaluate_short_replies.py --output .runtime/short-replies-before.json` 및 after.json/final.json: 정상 시작/반복된 합성 이력에서 각 5턴, 총 10응답. 직전 답변과 완전히 같은 연속 반복은 기준 4/10 → 중간 1/10 → 최종 0/10. 최종 이름 질문 2개 유이 정답, 형식 재시도 0. 중앙값 기준 1.586초/최종 1.625초. 확률적 표본이며 단일 변경의 독립 효과를 입증한 것은 아니다.
- 최종 결과에 이전과 비슷한 위로를 다시 꺼내거나 질문으로 이어가는 경향이 남았다. 0/10은 직전 답변과의 문자열 일치 기준이며 의미 반복이나 모든 과거 대사 재사용이 0이라는 뜻이 아니다. 일반 자연스러움 완성으로 해석하지 않는다.
- `./venv/Scripts/python.exe scripts/benchmark_local.py --limit 20 --output .runtime/repetition-general-check.json`: 최초 형식 20/20, 재시도 0, p50 1.7035초/p95 2.125초. 실행 중 외부 smoke가 일부 겹쳤으므로 정밀 속도 비교는 아니다.
- `./venv/Scripts/python.exe .runtime/restart_guest_web.py`: 소유 웹만 재시작. 바로 수행한 외부 검사는 기동 대기 없이 접근해 502로 실패했으며 재실행 `./venv/Scripts/python.exe .runtime/verify_public_test.py`에서 화면/자산/대화 200, 동일 요청 재생 일치, 타 브라우저 접근 403 확인. 모델·터널·기존 DB 유지, 외부 합성 대화 1회는 테스트 한도에 포함된다.

현재 공개 링크에 적용 완료. 별도 migration/설정 수정 불필요(공개 env에 없는 샘플러 값은 동일한 코드 기본값 사용). 다음은 다양한 짧은 답변·부정·주제 전환·경계 표현의 의미 품질 평가다. 전체 반복 차단을 보장하지 않는다.

## 2026-09-08 입력 문맥 8192와 최근 대화 전달 확대

사용자가 작은 4B 모델에 맞춰 입력 문맥을 넉넉하게 사용할 것을 제안하여 실제 PC에서 8192 프로파일을 검증·적용했다. 모델과 개발/공개 테스트 웹 설정의 `LLAMA_CONTEXT`를 2048→8192로 맞췄다. 출력 256, 여유 64, thinking OFF, parallel 1은 유지한다. 입력 예산은 7872토큰이다. 코드의 설정 미지정 fallback은 2048을 유지하며 `.env.example`에 현재 프로파일을 명시했다.

`app/prompt_context.py`의 최근 4메시지 고정 상한을 제거했다. 서버가 보존하는 최근 12메시지(6턴)를 모두 후보로 전달하고 토큰 예산을 넘을 때만 이전 인용·선택 기억·오래된 완전한 대화 쌍을 줄인다. 정정된 취향 제외, 현재 입력/고정 캐릭터 보존과 토크나이저 장애 처리는 유지한다. 저장 이력의 12메시지 상한과 DB 스키마는 변경하지 않았다.

검증:

- 변경 전 `./venv/Scripts/python.exe -m pytest -q`: 421 passed (9.89s).
- 변경 후 같은 명령: 422 passed (10.65s). 충분한 예산에서 전체 이력 보존, 부족한 예산에서 최신 완전 쌍 보존/원본 불변 테스트 포함. 관련 `pytest -q tests/test_prompt_context.py tests/test_decision.py`: 38 passed.
- `./venv/Scripts/python.exe -m ruff check app scripts tests`: 통과. `./venv/Scripts/python.exe -m compileall -q app scripts`: exit 0.
- `./venv/Scripts/python.exe scripts/benchmark_local.py --limit 5 --output .runtime/context-before.json` 및 after.json: 전후 모두 최초 schema 5/5. 짧은 단일 턴 중앙값 2.203→1.719초, 최대 2.406→2.281초. 표본이 작고 출력 길이/캐시가 달라 속도 향상으로 단정하지 않는다.
- `./venv/Scripts/python.exe .runtime/check_context_capacity.py`: 합성 12메시지 이력, 입력 2459/2450토큰, 잘림·재시도 없음, 첫 약속 장소와 유이 이름 정답. 각각 3.516/1.266초.
- `./venv/Scripts/python.exe .runtime/check_context_capacity_long.py`: 합성 입력 5915/5906토큰, 잘림·재시도 없음, 같은 회상/정체성 확인, 각각 4.672/1.547초. 반복 문장이 포함된 용량 smoke이며 자연스러운 장기 대화 평가가 아니다. 같은 이력의 두 번째 요청은 캐시 효과가 있을 수 있다.
- 모델 `/props`의 실제 `n_ctx=8192` 확인. GPU free는 변경 전 1121 MiB, 변경 후/긴 입력 확인 후 약 1090 MiB. 순간 측정이며 피크나 다른 앱 사용 중 OOM 방지를 보장하지 않는다.
- 소유 모델·웹만 재시작, 터널/서명 키/DB 유지. 최초 준비 검사는 guest 모드에서 제한되는 `/api/ready`를 사용하여 403과 타임아웃이 발생했다. 이는 모델 기동 실패가 아니며 이후 `./venv/Scripts/python.exe .runtime/verify_public_test.py`로 외부 화면·자산·실제 대화 200, 중복 응답 동일, 타 브라우저 403을 검증했다. 합성 외부 1회는 테스트 한도에 포함된다.

변경 파일: app/prompt_context.py, tests/test_prompt_context.py, .env.example, AGENTS.md, README.md, 현재 런북, PROJECT_STATUS, DECISION_LOG. 무시된 두 private env와 합성 측정 파일도 갱신했다. migration 없음. 공개 링크는 그대로다. 다음 작업은 실제 여러 턴의 자연스러움 평가와 샘플링 설정 전달 누락 검증이다. 16K/32K나 출력 상한 확대는 아직 적용하지 않았다.

## 2026-09-08 작은 모델 대화 품질 조사

[조사 보고서](SMALL_MODEL_DIALOGUE_RESEARCH_2026-09-08.md)에 Reddit 실사용 사례, SillyTavern/Letta/Mem0/Outlines/RoleLLM 및 공식 모델 문서를 현재 코드와 대조했다. 최근 원문 이력의 고정 4메시지 상한과 canonical 호출의 일부 샘플링 설정 전달 누락을 확인했다. 캐릭터/예시, 문맥 선택, 작은 출력 schema, 기억, 동일 크기 모델 비교 순서의 실험을 제안한다. 한국어 품질 향상은 아직 실측하지 않았다. 이번 작업은 문서만 변경하며 런타임·모델·서비스·DB를 변경하지 않는다.

## 2026-09-08 정정 — 유이 설정 누락 복구

최종 검증: `./venv/Scripts/python.exe -m pytest -q` 421 passed(10.70s), `./venv/Scripts/python.exe -m ruff check app scripts tests` 통과, `./venv/Scripts/python.exe -m compileall -q app scripts` 통과. 소유 웹만 재시작해 같은 임시 주소에 적용했고 외부 HTTPS에서 '니 이름뭔데' → 200 / '난 유이야. 편하게 유이라고 불러!' 확인. 모델/터널/DB는 유지했다.

사용자 지적 후 git HEAD의 default.json을 대조하여 원래 '유이가하마 유이 계열의 밝고 다정한 고등학생' 설정과 친근함·공감·배려/부드럽고 발랄한 반말/비꼼·냉소·자기비하 금지/불편함에 사과하는 원칙이 있었음을 확인했다. Phase04 프롬프트 축약에서 고유 캐릭터 참조가 누락됐다. 바로 아래의 '이름 미정' 보완은 원본을 확인하지 않은 잘못된 판단이며 폐기한다. 모델이 완전한 유이 설정을 무시했다고 입증한 것이 아니라 모델에 전달할 설정 자체가 빠진 회귀다.

원본 성격·말투 핵심을 복구하고 사용자 의도에 따라 이름을 유이로 명시했다. 현 canonical JSON 계약/점수 규칙/문맥 예산은 유지한다. 다른 이름/이름 미정이라는 과거 대사는 설정을 덮어쓰지 않도록 명시했다. 이름 미정 예시와 평가 기대값도 유이로 수정했다.

tests/test_decision.py에 실제 기본 캐릭터 로드→모델 전송→형식 실패 재시도의 시스템 메시지에 유이 설정이 유지되는 회귀 테스트를 추가했다. 최초 추가 지침은 추정 토큰 모드 재시도 예산을 넘어서 신규 테스트 1개 실패/기존 420개 통과였으며, 성격 정보를 유지하면서 중복 문장을 줄여 해당 30개 테스트를 통과시켰다. 최종 실제 모델의 이름/자기소개 3질문 모두 유이라고 답했다(.runtime/yui-final.json). 기존 대화/점수는 삭제하지 않는다. 일반 대화 품질과 과거 잘못된 이력에서의 일관성은 계속 검증이 필요하다.

## 2026-09-08 이름 질문 품질 오류 보완

사용자가 이름 질문에 부적절한 이름을 답한 사례를 보고했다. 보고된 표현 자체는 새 대화에서 재현되지 않았으나, 편집 전 실제 모델은 '니 이름뭔데'에 '나름은 친구야', '너 이름이 뭐야?'에 '제 이름은 알지 못해'라는 잘못된 응답을 생성했다. 설정에는 고유 이름이 없고 일반적인 성격/이름 창작 금지만 있었다. 정확한 기존 대화 문맥은 확인하지 않았으므로 단일 원인이나 해결 보장을 주장하지 않는다.

default.json에 고유 이름 미정/화면 호칭 NPC와 이름 질문 예시, 평범한 질문에 욕설·비하를 하지 않는 지침을 추가했다. 별도 이름 회귀 평가 5사례를 evaluation/name-regression.json에 기록했다. 고유 이름을 임의로 새로 정하지 않았다.

변경 전후 새 대화 3질문을 실제 모델에 전달했고, 변경 후 이름/자기소개 3개 모두 이름 미정과 NPC 호칭을 안내했다. 웹만 소유권 확인 후 재시작하여 같은 임시 링크에 적용했고 외부 API의 정확한 '니 이름뭔데' 질문도 200 / '아직 이름은 없어. NPC라고 불러줘.'를 확인했다. 링크/모델/DB는 유지했다. 기존 잘못된 대화 이력은 삭제하지 않았다.

`./venv/Scripts/python.exe -m pytest -q`: 420 passed(9.62s). ruff/compile 통과. 최초 테스트 파일명 탐색에서 존재하지 않는 test_decision_service.py를 지정해 수집 실패했고 이후 실제 전체 테스트로 검증했다. 사전/사후 합성 모델 기록은 무시되는 .runtime/name-before.json 및 name-after.json. 일반 대화 품질과 오염된 기존 이력에서의 안정성은 추가 평가 대상이다. 이름 질문 회귀 5개 중 사용자 이름 혼동 2개는 아직 실제 모델 평가 미실시다.

## 2026-09-08 임시 접속 복구

연결 장애 확인 당시 소유 모델/웹/터널 프로세스가 모두 종료되어 있었으며 loopback 8000도 연결 거절이었다. 종료 원인 자체는 확인되지 않았다. 모델을 기존 프로파일로 재시작하고 웹/Quick Tunnel을 새로 연결했다. 새 주소는 무시되는 `.runtime/public-test.json`에 기록한다.

무시되는 임시 실행 스크립트가 재실행 시 기존 public-test.env의 서명 키/테스트 DB 경로/한도를 재사용하도록 수정했다. 기존 대화 및 usage DB를 초기화하지 않았다. 새 호스트에서는 브라우저 쿠키가 자동 이전되지 않으므로 새 방문자로 접속한다.

`./venv/Scripts/python.exe scripts/local_runtime.py start-llm` 성공, `.runtime/start_public_test.py` 성공, `.runtime/verify_public_test.py` 외부 HTTPS 화면/실제 모델 대화 200·중복 응답 일치·다른 브라우저 접근 403 확인. 운영 자동 시작/고정 주소는 아직 구성하지 않았다. 다음은 필요 시 재부팅 후 시작/복구 절차의 정식 구현이다.

## 2026-09-07 임시 외부 테스트 링크 발급 및 검증

사용자가 도메인 없이 접속할 임시 주소 발급을 명시적으로 요청했다. 설치된 cloudflared Quick Tunnel로 guest 웹앱만 공개했다. 주소는 무시되는 `.runtime/public-test.json`에만 기록하고 저장소 문서/설정에는 넣지 않았다. 기존 소유 웹 프로세스를 중지하고 guest 웹으로 전환했으며 기존 llama.cpp 모델은 유지했다. 개발 대화 DB는 보존하고 checkout 밖 새 테스트 DB를 사용한다.

- 공개 HTTPS 경로로 화면/JS/CSS/표정 PNG 200, 익명 쿠키 발급, 세션 생성, 실제 모델 대화 200을 확인했다. 다른 브라우저의 대화 ID 접근은 403, 동일 요청 재전송은 원 응답과 일치했다. 합성 확인 대화 1회가 테스트 일일 한도에서 사용됐다.
- guest 초기 한도: 활동 브라우저 5개/300초, 전체 200회·브라우저 30회/한국 날짜. 운영 설정과 서명 키는 `.runtime/public-test.env`에만 저장했다.
- 시작 확인의 첫 시도는 liveness의 ok 응답을 readiness의 ready와 혼동해 실패했고, 터널/guest 웹을 종료하고 기존 웹을 복구했다. 확인 로직 수정 후 재실행/외부 검증 성공. 모델/개인 대화 손실 없음.
- 사전 `./venv/Scripts/python.exe -m pytest -q tests/test_guest_access.py`: 15 passed. 외부 합성 검증 결과는 `.runtime/public-test-check.json`에 기록한다.
- 외부 접속만 종료: `./scripts/stop-public-test.ps1`. 소유 tunnel만 종료하고 웹/모델은 유지한다. 모두 종료하려면 터널 종료 후 기존 `./scripts/stop-local.ps1` 실행. 터널 종료 후 기존 URL은 접속 불가이며 재발급 시 주소 변경 가능.
- 임시 테스트이며 운영 준비 완료는 아니다. 자동 삭제·재부팅 복구·정규 백업/복원 및 다중 사용자 부하 검증은 남아 있다. 대화는 테스트 DB에 저장되며 자동 삭제되지 않는다.

## 2026-09-07 최신 상태 — 로그인 없는 링크 배포 준비

사용자의 명시적 요청으로 기본 원격 배포를 **guest 공개 링크**로 변경했다. 링크 열기만으로 익명 서명 쿠키가 발급되며, 이메일 인증 없이 브라우저별 대화/관계를 분리한다. 기존 Access 모드는 선택 사항으로 보존한다. 과거 아래의 초대 이메일 기본안은 이 결정으로 대체된다.

- 이번 편집 전 기준 HEAD a9f6205045648e8889a4dbf4190de65e330caaed, pytest 405 passed(8.35s). 기존 미커밋 변경 보존.
- 추가: app/guest_access.py, tests/test_guest_access.py, docs/PUBLIC_LINK_DEPLOYMENT.md. 변경: remote_access/main, remote_preflight/serve_remote, 배포 예시 설정, AGENTS 및 방향/구조/API/계획/상태/결정/런북/README.
- 초기값은 최근 활동 브라우저 5개/TTL 300초, 전체 하루 200회, 브라우저 하루 30회(한국 자정 초기화). 설정으로 변경 가능하다. 모델 생성 동시성은 1개 유지.
- 전체 한도는 쿠키 초기화/앱 재시작에도 유지한다. 모델 실패 시도도 차감하며 이미 저장한 동일 turn의 응답 재전송은 중복 차감하지 않는다. 본인 아닌 대화 ID, 위조/만료 쿠키, 잘못된 Origin/Host를 검증했다.
- 운영 DB 스키마 0001 유지. 운영 DB 옆 `<database>.usage.sqlite3`를 첫 사용 시 생성한다. 두 DB의 백업/복원과 서명 키 관리가 필요하다. 기존 개인 DB와 .env, 실행 중인 모델/웹은 변경하지 않았고 실제 인터넷 공개/커밋/푸시도 하지 않았다.
- 테스트: `./venv/Scripts/python.exe -m pytest -q` → **420 passed (8.83s)**. `./venv/Scripts/python.exe -m pytest -q tests/test_guest_access.py` → 15 passed. `node --test tests/frontend.test.cjs` → 14 passed. `./venv/Scripts/python.exe -m tests.smoke_local` → HTTP/장애 복구/모델 stub/정적 파일 통과, 임시 프로세스 종료. `./venv/Scripts/python.exe -m ruff check app scripts tests`, `./venv/Scripts/python.exe -m compileall -q app scripts`, `git diff --check` 모두 통과(기존 LF/CRLF 안내만 있음).
- 제한: 브라우저별 한도는 사람별 한도가 아니다. 쿠키 삭제로 새 브라우저 이용권을 받을 수 있으나 전체 한도는 우회하지 못한다. 5개 자리는 열린 탭 수가 아니라 최근 대화 활동 기준이다. 자동 대화 삭제/두 DB 백업 관리/운영 서비스 복구/실제 HTTPS 외부 부하 검증은 미완료.
- 다음 작업: 공개 링크 모드의 실제 도메인/Tunnel 설정 및 외부 쿠키/한도 검증. 공개 전 보관·삭제 정책과 기능, 두 DB 복구·운영 복구 및 품질/부하 게이트를 완료한다. 최신 절차는 PUBLIC_LINK_DEPLOYMENT.md.

## 2026-09-07 Phase05 배포 준비 — 인증 경계 구현, 외부 공개 미실시

사용자는 테스트 이후 운영할 배포 기준으로 준비를 요청했으며 도메인/Cloudflare 계정은 아직 없다고 확인했다. 현재 단계는 **원격 인증·사용자 데이터 분리·제한 구현과 배포 설정 준비**다. Phase05 전체 완료나 운영 준비 완료가 아니다. 기존 Phase04 모델 품질 제한도 유지한다.

- 기준 HEAD a9f6205045648e8889a4dbf4190de65e330caaed 동일. 기존 미커밋 작업을 보존했고 이번에도 커밋/푸시/터널 연결을 하지 않았다.
- 편집 전 baseline: `./venv/Scripts/python.exe -m pytest -q` → 375 passed (8.70s).
- 선택적 cloudflare 모드: RS256 서명/issuer/audience/만료 검증, 계정 소유권, 정확한 Host/Origin, API JSON/본문 크기 제한, 사용자별 요청/동시성 제한. 별도 requirements-remote.txt로 로컬 모드에 인증 서비스 의존성을 강제하지 않는다.
- SQLite 스키마 0001 유지. 기존 로컬 대화는 원격 계정에 자동 귀속시키지 않으며 별도 운영 DB 사용이 배포 설정 검사에 필요하다.
- 배포 예시 설정, 읽기 전용 remote_preflight, loopback/단일 worker 인증 웹 실행기, 공개 전 운영 게이트를 추가했다. 실행 중인 로컬 웹/모델 및 개인 .env/DB는 변경하지 않았다. 새 코드는 실행 중인 웹의 다음 재시작부터 적용된다.
- 최종 확인: 전체 Python 405 passed (8.63s). 마지막 헤더 처리 보완 후 원격 30 passed (2.81s), Node 14 passed. lint/compile 및 실제 로컬 HTTP smoke 통과.
- 빈 배포 예시의 preflight는 구성 미완료로 exit 1: 의도된 차단. 외부 실제 계정/도메인 검증, 보관·삭제 기능과 정책, 서비스 자동 복구/재부팅, 다중 사용자 부하/사람 품질 검토는 아직 미완료.
- 다음 작업: 보관·삭제 정책 확정 후 삭제/백업 만료 구현 및 운영 서비스 복구 검증. 계정과 도메인 확보 후 실제 Access/Tunnel 연결·외부망 검증. [운영 런북](REMOTE_DEPLOYMENT_RUNBOOK.md) 참고.

검증 명령:

| 명령 | 결과 |
|---|---|
| `./venv/Scripts/python.exe -m pytest -q` | 405 passed |
| `./venv/Scripts/python.exe -m pytest -q tests/test_remote_access.py` | 최종 30 passed |
| `node --test tests/frontend.test.cjs` | 최종 14 passed |
| `./venv/Scripts/python.exe -m tests.smoke_local` | HTTP liveness/readiness/장애 복구/모델 stub/정적 파일 통과, 임시 서비스 종료 |
| `./venv/Scripts/python.exe -m ruff check app scripts tests` | 통과 |
| `./venv/Scripts/python.exe -m compileall -q app scripts` | 통과 |
| `./venv/Scripts/python.exe scripts/remote_preflight.py --env-file deployment/remote.env.example` | 빈 설정 의도대로 차단, release_ready=false |
| `./venv/Scripts/python.exe scripts/serve_remote.py --env-file deployment/remote.env.example` | 빈 설정 실행 거절, 실제 서버 시작 안 함 |
| `git diff --check` | 오류 없음; 기존 파일 LF/CRLF 안내만 있음 |

## 현재 상태 — 2026-09-07 Phase 04 구현·측정 완료

실사용을 위한 오류·재시도 화면, 문맥 예산, 단순 취향 정정과 인용 회상, 한국어 평가 52사례를 추가했다. **구현과 실측은 완료했으나 말투·경계 존중 등 모델 품질은 미완성**이다. 공개 배포·커밋·푸시는 하지 않았다. 아래 Phase 02/03 기록은 이전 단계의 이력이다.

- 화면은 대기·성공·재시도 가능 오류·입력 오류·오프라인을 구분한다. 오류가 나도 마지막 정상 대사는 유지한다. 같은 메시지 재시도, 420초 제한, 새로고침 후 식별자 보존, 소실 프로필의 명시적 복구를 검증했다.
- 현재 모델의 template/tokenize API로 입력 예산을 확인한다. 2048 - 출력 256 - 여유 64 = 1728토큰이다. 오래된 문맥을 줄이고 현재 입력은 자르지 않는다. 너무 긴 입력은 422, 카운트 서버 장애는 503으로 안내한다. 실제 긴 이력에서 계산한 1460토큰과 모델이 받은 1460토큰이 일치했다.
- 단순 1인칭 취향을 원문으로 추출하고 같은 대상의 선호가 바뀌면 갱신한다. 명시적인 취향 회상은 최신 사용자 발화를 인용한다. schema 0001은 유지하며 개인 DB와 Redis 원본은 삭제하지 않았다.
- 4B 변경 전 50회와 변경 후 50개×2회=100회를 측정했다. 변경 후 100/100 첫 시도 성공, p50 1.524초, p95 2.125초, 대사 중앙값 19자였다. OOM은 관찰되지 않았고 보완 2사례도 성공했다.
- 기존 9B Q6/GPU 12층은 핵심 20사례를 모두 처리했으나 p50 15.039초, p95 22.421초였다. 새 모델 다운로드 없이 비교했고 4B Q4/all GPU로 복구했다. 현재 8000 웹앱과 8001 모델, DB readiness는 정상이다.
- Chrome/Codex/DWM이 열린 상태에서 실행했다. 게임·Unity 동시 부하는 미검증이다. 장치 전체 최고 VRAM 사용량은 4B 6411MiB, 9B 6481MiB로 모델 단독 사용량은 아니다.
- 에이전트의 비블라인드 정성 검토에서 자연스러움은 2.90→3.46/5, 맥락·사실성은 3.50→4.12/5였다. 인간 평가로 주장하지 않는다. 조건을 섞은 100행 검토표와 별도 키를 제공하며 인간 평가는 아직 하지 않았다.

### 변경 파일

app/prompt_context.py, app/services/decision_service.py, app/characters/default.json, app/memory.py, app/repository.py, app/main.py, app/decision.py, app/config.py; frontend/app.js/index.html/styles.css/config.js/config.example.js; scripts/evaluate_model.py/local_runtime.py/doctor.ps1; evaluation/cases.json, tests/와 계획·상태·평가 문서를 변경했다. 기존 Phase 00–03 변경은 보존했다.

### 검증 명령과 결과

| 명령 | 결과 |
|---|---|
| `./venv/Scripts/python.exe -m pytest -q` | 375 passed, 10.89초 |
| `node --test tests/frontend.test.cjs` | 13 passed |
| `./venv/Scripts/python.exe -m ruff check app scripts tests` | 통과 |
| `./venv/Scripts/python.exe -m compileall -q app scripts` | 통과 |
| `./venv/Scripts/python.exe -m tests.smoke_local` | 실제 HTTP + 가짜 모델, 자산·오류 복구 통과 |
| 위 smoke에 `--backend-port 8010 --serve-seconds 600` 추가 | 브라우저 대사·상태·개발 정보·표정·배치 확인 |
| `./venv/Scripts/python.exe scripts/evaluate_model.py --output artifacts/evaluation/phase04-before.json` | 변경 전 50사례 |
| `./venv/Scripts/python.exe scripts/evaluate_model.py --output artifacts/evaluation/phase04-after.json --repeat 2` | 당시 50사례×2회 |
| `./venv/Scripts/python.exe scripts/evaluate_model.py --offset 50 --limit 2 --output artifacts/evaluation/phase04-supplement.json` | 추가 2사례 |
| 기존 9B 실행 후 evaluator에 `--model HauhauCS/Qwen3.5-9B-Uncensored-HauhauCS-Aggressive --offset 30 --limit 20` | 핵심 20사례 비교 |
| `./scripts/doctor.ps1` | 4B 복구 후 database/llm OK, 카운트 모드 llama_cpp |
| `git diff --check` | 공백 오류 없음; LF/CRLF 안내만 출력 |

초기 smoke의 근사 예산 초과와 새 테스트 fixture의 kind 누락은 수정 후 재검증했다. 추가 실모델 API 검사에서는 취향 정정 후 정확한 인용 회상, 과도한 입력의 상태 불변, 동일 turn 재사용을 확인했다. 모든 평가 원문은 합성 대화다.

### 설정과 다음 작업

현재 PC와 .env.example은 NPC_TOKEN_COUNT_MODE=llama_cpp다. 명시적 estimate는 다른 제공자를 위한 근사 모드이며 정확한 상한 보장은 없다. DB 마이그레이션은 필요하지 않다. 브라우저를 새로고침하면 변경된 화면을 사용한다.

다음은 경계 표현·역할 혼동·반말 일관성의 실패 사례를 기준으로 추가 품질 개선과 사용자 검토를 진행하는 것이다. 바로 Phase 05 공개 배포로 넘어가지 않는다. 자세한 내용은 [구현 기록](PHASE04_IMPLEMENTATION.md)과 [평가 보고서](PHASE04_EVALUATION.md), 합성 결과와 검토표는 docs/evaluation/에 있다.

## 이전 단계 기록

## 현재 상태 — 2026-09-07 Phase 02/03 완료

현재 실행 구조는 **FastAPI 웹앱 1개(화면+API) + llama.cpp 모델 1개 + SQLite 파일**이다. Redis는 기본 실행/health에서 제거했으며 선택적 이전 도구로만 남긴다. 아래 이전 기록의 Redis 필수/관계 미구현 표기는 해당 시점의 이력이다.

- 현재 기준 HEAD a9f6205 / branch codex/p0-baseline-stabilization 유지. 기존 변경을 보존했고 이번 변경도 아직 커밋·푸시·공개 배포하지 않았다.
- Phase 02: 규칙 **1.0**, 다섯 수치/실제 delta/이유 코드, 캐릭터 기본값 0/30/30/30/0, legacy 호환 응답과 개발 정보 토글.
- Phase 03: SQLAlchemy/Alembic schema0001, SQLite WAL 트랜잭션, profile/session 영속 연결, 중복 turn 재사용, 큐 활성1/대기8/대기30초, 한 DB에 한 앱 worker, 보수적 발화 인용 기억과 백업/복구 도구.
- 브라우저는 /api/session 후 식별자를 저장하고 메시지마다 client_turn_id를 보존한다. 실패 후 같은 메시지를 재전송해도 중복 누적하지 않는다. 전송 이력은 서버에서만 구성한다.
- Redis 기존 대화 1건 export/dry-run/import 완료. 재실행은 0건 이전/1건 처리 완료로 반환. 백업 원본과 점수·history·flags 일치 검증. Redis 원본 삭제/수정 없음. 이력은 운영 DB에 최근12, 원본 export에는 전체 보존.
- 실제 4B 모델+임시DB 합성 8턴 모두 HTTP200, 1.281~2.563초, 요약 갱신2/기억 후보채택0. 형식/연결 성공이며 품질 합격률로 해석하지 않는다.
- 현재 실제8000 웹앱 재시작 후 database/llm readiness 정상. 모델은 계속 실행 중이며 3060 Ti/4B Q4/all GPU/context2048/output256 설정 유지.

### 수정 파일 범위

핵심은 app/relationship.py, repository.py, storage_schema.py, memory.py, coordinator.py, file_lease.py, main.py, models.py 및 decision/legacy adapter, character 설정이다. migrations/, alembic.ini, frontend/app.js/index.html, scripts/database.py/local_runtime.py/doctor.ps1, 의존성·환경 예제, tests/와 계획/운영 문서를 함께 갱신했다. Phase 00/01의 기존 미커밋 변경도 작업 트리에 남아 있다.

### 최종 실행 검증

| 정확한 명령 (저장소 루트) | 결과 |
|---|---|
| `./venv/Scripts/python.exe -m pytest -q` | **361 passed**, 6.32초 |
| `./venv/Scripts/python.exe -m ruff check app scripts tests` | 통과 |
| `./venv/Scripts/python.exe -m compileall -q app scripts` | 통과 |
| `node --test tests/frontend.test.cjs` | **6 passed** |
| `./venv/Scripts/python.exe -m tests.smoke_local` | 실제 Uvicorn+가짜 모델 HTTP, outage/recovery, 정적 자산 통과 |
| `./venv/Scripts/python.exe scripts/database.py export-redis --file .runtime/backups/phase03-legacy-20260907.json` | 1건 백업, 원본 유지 |
| `./venv/Scripts/python.exe scripts/database.py import-legacy --file .runtime/backups/phase03-legacy-20260907.json` | dry-run 1건 검증 |
| 위 import 명령에 `--apply` 추가 후 두 번 실행 | 1건 이전, 재실행 중복0건 |
| `./venv/Scripts/python.exe scripts/local_runtime.py start-local --reuse-llm` | 단일 worker 정상 기동/재기동 |
| `./scripts/doctor.ps1` | database/llm OK, 소유 웹/모델 RUNNING |

Redis import를 강제로 실패시키는 별도 Python 프로세스에서 기본 앱 startup/chat/restart/readiness를 검증했다. 백업/restore, 초기화/삭제, 동시 다른 세션 중복, commit 후 응답 유실, 큐 포화/timeout, 추론 중 취소 및 DB 쓰기 잠금 부재도 검사했다. 앱 브라우저에서 초기 화면과 기본 숨김 개발 정보 토글이 표시됨을 확인했다. 실제 UI 클릭/대화 흐름은 이번에는 Node 검사로 검증했다.

### 남은 제한과 다음 작업

Phase 04가 다음 작업이다. 우선 품질 기준 12턴의 공감·말투·사실성 문제, 기억 후보 재현율과 정정 충돌, 토큰 예산과 중간 이력 요약 연결, 사용자 초기화/재시도 UX를 다룬다. 현재 짧은 대화용 context2048이라 긴 입력은 실패할 수 있다. 취소가 commit 시작 후라면 이미 저장될 수 있으므로 동일 ID로 확인한다. 프로필은 로컬 식별자이며 공개 서비스 인증은 아니다. 멀티 worker/공개 배포는 미지원이다.

상세 구현·초기 실패 및 해결·품질 기준은 [Phase 02/03 기록](PHASE02_03_COMPLETION.md), 데이터 보관/설정/복구는 [DB 운영](DATABASE_OPERATIONS.md)을 따른다.

## 이전 작업 기록 (아래는 각 단계 당시 상태)

마지막 검토: **2026-09-07 (KST)**  
검토 방식: Git/문서 원본 대조 후 Phase 00 구현, pytest·프런트 자동 검사, 실제 Uvicorn/가짜 LLM HTTP smoke 및 브라우저 확인. 실제 GPU 모델 추론은 미검증.

사용자의 후속 구현 요청에 따라 **Phase 00 완료**. 이전 사전 점검 기록은 [WORK_PREPARATION.md](WORK_PREPARATION.md), 현재 실행 방법은 [README](../README.md), 완료 결과는 아래 8절을 참고한다.

2026-09-07 후속 합의로 **배포 단순화 계획을 갱신**했다 (9절). 이번 갱신은 문서만 변경했다. 현재 실행 구조는 여전히 별도 프런트 서버 + FastAPI + Redis + 모델 서버다.

## 1. Repository baseline

| 저장소 | HEAD | 상태 |
|---|---|---|
| `Newrred/npc-chat` | `a9f6205045648e8889a4dbf4190de65e330caaed` | 개발 기준 |
| `Newrred/heroine` | `f722ae87a82775e3cf12c0f188a71f5165c5686e` | 레거시 프런트 배포본 |

2026-09-07 직접 조회 결과 두 저장소의 원격 HEAD는 위 기준선과 동일했다. 현재 브랜치는 `codex/p0-baseline-stabilization`이며 HEAD는 위 기준선 그대로다. 구현 시작 시 추적 코드 변경은 없었고, `AGENTS.md`, `CODEX_START_PROMPT.md`, `docs/`, `tasks/`는 이미 존재하는 미추적 문서였다. 현재 작업 트리에는 Phase 00 변경과 새 테스트/개발 설정이 있으며 커밋·푸시·배포는 하지 않았다.

## 2. 검증된 현재 구현

| 영역 | 현재 구현 | 주요 파일 |
|---|---|---|
| Backend | 주입 가능한 FastAPI factory, 기존 API와 `/api/live`, `/api/ready` | `app/main.py`, `app/services/health_service.py` |
| LLM | OpenAI-compatible 호출, vLLM/llama.cpp factory | `app/services/llm_service.py`, `llama_cpp_service.py`, `llm_service_factory.py` |
| Character | JSON 기반 캐릭터 prompt sections | `app/character_config.py`, `app/characters/default.json` |
| Structured output | reply, face, internal emotion, affection delta, tags, flags, one-line memory | `app/services/llm_service.py`, `app/models.py` |
| Session | Redis JSON state, TTL, per-session lock | `app/session_store.py` |
| Relationship | `affection_total` 한 개를 LLM delta로 누적 | `app/main.py`, `app/session_store.py` |
| Memory | 최근 history 최대 20메시지 + 덮어쓰기식 `memory_1line` | `app/main.py`, `llm_service.py` |
| Frontend | 단일 `app.js`, 정적 PNG fallback, localStorage session id, 전송 중 중복 submit 차단 | `frontend/` |
| Image | 정적 표정 기본 + 선택적 비동기 ComfyUI 생성/캐시 | `app/services/comfy_service.py` |
| Front deployment | `frontend/`를 GitHub Pages에 배포하는 Action | `.github/workflows/pages.yml` |
| Validation | GPU/Redis 없는 pytest 34개, Node 프런트 검사 5개, Python 3.11/3.12 CI 정의 | `tests/`, `.github/workflows/python-tests.yml` |

## 3. 확인된 구조적 문제

### P0: 해결 완료

- 기본 LLM은 `llama_cpp`, `127.0.0.1:8001/v1`, completion cap 256으로 정리했다. 백엔드는 8000을 유지한다.
- production config의 임시 터널 주소를 제거했다. `frontend/config.js`는 비밀값 없는 로컬 기본값으로 명시적으로 추적하며 예시 파일을 제공한다.
- 정상 UTF-8 프런트를 `app.js`로 통합하고 `app.fixed.js`를 제거했다. 정적 표정 fallback을 자동 검사했다.
- README에 `npc-chat/frontend`를 원본, `heroine`을 레거시로 명시했다.
- pytest, lint, Node 검사와 GitHub Action, 읽기 전용 `scripts/doctor.ps1`을 추가했다.
- `/api/health` 호환 응답을 유지하고, `/api/live`와 timeout이 있는 Redis/LLM `/api/ready`를 추가했다. Redis 장애 중에도 서버는 시작 가능하다.
- 기본 CORS를 프런트의 명시적 로컬 origin 두 개로 제한했다. 기존 `.env`에 지정된 값은 자동 덮어쓰지 않는다.

### P1: 코어 구조 개선

- face enum과 감정 관련 규칙이 여러 파일에 중복돼 drift 가능성이 있다.
- llama.cpp 경로는 guided JSON 없이 텍스트 추출·재시도에 의존한다.
- 응답 길이가 10~50자로 강제돼 매우 짧은 캐릭터 반응을 막는다.
- completion cap은 256으로 축소했지만 실제 모델에서의 출력 길이/성공률 측정은 아직 필요하다.
- 브라우저 `history` 필드는 호환 목적으로 받지만 사용하지 않도록 Phase 00에서 차단했다. 프런트의 필드 전송 제거는 후속 정리 대상이다.
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
- 고정 도메인/접근 통제를 갖춘 원격 배포는 아직 구성하지 않았다.
- structured application error contract가 없다.
- 기본 Redis/LLM readiness 외에 운영 로그, metrics, 백업 정책은 아직 없다.
- 메인 PC에서 게임/디자인 작업과 GPU 경합 시 동작 정책이 없다.

## 4. 아직 검증되지 않은 항목

- 문서의 RTX 4070 Ti / RAM 64 GB 기준 장비가 별도 PC인지 여부. 현재 작업 PC는 RTX 3060 Ti 8 GB / RAM 약 32 GB로 확인됐다.
- 설치된 CUDA toolkit 및 llama.cpp build/모델 실행 호환성
- 사용자의 기존 `.env` 및 실제 모델을 사용하는 통합 실행. 격리된 설정으로 Uvicorn·실제 LLM 어댑터·가짜 모델 endpoint·메모리 저장소·브라우저 연결은 확인했다.
- 선택할 14B GGUF의 정확한 모델·파일 크기·chat template
- 4070 Ti에서 실제 latency, VRAM, schema 성공률
- 현재 GitHub Pages와 quick tunnel URL의 생존 여부
- ComfyUI remote `/generate` API의 실제 구현 여부

## 5. 단계별 상태

| 단계 | 상태 | 완료 조건 |
|---|---|---|
| 00 Baseline stabilization | 완료 (미커밋) | pytest 34개, Node 5개, compile/lint/HTTP·브라우저 smoke 통과 |
| 01 LLM contract/local runtime | 미착수 / 실행 단순화 범위 확정 | same-origin 화면/API, 필수 start/stop, 중앙 schema, local profile 검증 |
| 02 Five-stat relationship | 미착수 | 5수치 결정론 엔진 및 migration 완료 |
| 03 Durable persistence/memory | 미착수 / Redis 전환 게이트 확정 | SQLite 영속성·동시성·중복 처리 검증 후 Redis-free 기본 실행 |
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

## 7. 2026-09-07 작업 준비 결과 (구현 전 기록)

- 문서 원본: `NPC_CHAT_CODEX_HANDOFF_2026-09-03.zip`, SHA-256 `71c4028ea94e8ee4b2e68009c3ab9f4edb2642990deb9107d7930ac046a23ac9`.
- ZIP 내부 checksum 21개 전부 통과. 이번 문서 갱신 전 로컬의 대응 파일 22개가 ZIP과 바이트 단위로 일치했다. 패키지 루트의 README/manifest/master/checksum은 `docs/handoff-package/`에 보관되어 기존 프로젝트 README를 덮어쓰지 않는다.
- 현재 PC: Windows 11 Home `10.0.26200`, Intel i7-11700, RAM 약 31.9 GiB, NVIDIA RTX 3060 Ti `8192 MiB`, 드라이버 `591.86`.
- 기본 Python `3.11.9`, 기존 `venv` Python `3.12.9`. 기존 venv에는 앱 실행 의존성이 있지만 두 Python 모두 pytest가 없다. 저장소에도 테스트 파일/pytest 설정/Python CI가 없다.
- `python -m pytest -q` 및 `./venv/Scripts/python.exe -m pytest -q`: exit 1, `No module named pytest` (기존 환경 제약).
- `python -m compileall app` 및 `./venv/Scripts/python.exe -m compileall app`: exit 0.
- 로컬 기본 포트 `6379` 연결 및 Redis PING 성공. `8000`, `8001`은 점검 시 수신 프로세스가 없었다. `.env`를 읽지 않도록 한 일회성 앱 import 성공.
- fake LLM/메모리 세션을 주입한 TestClient: `/api/health` 200, 빈 메시지 422 및 저장 없음, 정상 채팅 200 및 상태 저장 1회, Comfy disabled 확인. `/api/live`, `/api/ready`는 404로 미구현 확인. 실제 LLM 호출이나 Redis 대화 기록 쓰기는 하지 않았다.
- 일회성 smoke 첫 시도는 `image_source=base`라는 점검 코드의 잘못된 기대 때문에 실패했다. `comfy_service.py`의 OFF 분기를 확인해 기존 계약인 `image_source=none`으로 기대를 수정한 뒤 통과했다. 앱 코드는 변경하지 않았다.
- `frontend/app.js`는 UTF-8 decoding 실패, `app.fixed.js`는 UTF-8 정상. 문서의 프런트 정리 필요성을 재확인했다.
- 다음 시작 가능 작업: `tasks/00_BASELINE_STABILIZATION.md`. 테스트 도구와 fake seam부터 정리할 수 있다. Phase 01 실제 모델 검증은 현재 8 GB GPU 또는 별도 기준 PC의 실행 프로파일 확인이 필요하다.

## 8. Phase 00 완료 결과

### 변경 파일

- Backend: `app/main.py`, `app/config.py`, `app/services/health_service.py` (신규), `app/services/llm_service.py` (기존 lint 오류의 변수명만 정리).
- Frontend: `frontend/app.js`, `frontend/index.html`, `frontend/config.js`, `frontend/config.example.js` (신규), `frontend/app.fixed.js` (삭제).
- Tooling: `.env.example`, `.gitignore`, `requirements-dev.txt`, `pyproject.toml`, `.github/workflows/python-tests.yml`, `scripts/doctor.ps1`.
- Tests: `tests/__init__.py`, `conftest.py`, `fakes.py`, `test_api.py`, `test_health.py`, `test_repository.py`, `frontend.test.cjs`, `smoke_local.py`.
- Docs: `README.md`, 이 문서, `DECISION_LOG.md`, `WORK_PREPARATION.md`, `API_AND_DATA_CONTRACTS.md`, `LOCAL_4070TI_RUNBOOK.md`, `tasks/00_BASELINE_STABILIZATION.md`.

### 실행 결과

기존 venv Python 3.12.9에서 실행했다. 아래 `python` 명령은 해당 venv가 PATH의 첫 위치인 터미널에서 실행했으며, 명시적인 `./venv/Scripts/python.exe`와 같다.

| 명령/검사 | 결과 |
|---|---|
| `./venv/Scripts/python.exe -m pip install -r requirements-dev.txt` | 성공, pytest 8.4.2 / ruff 0.16.6 설치 |
| `python -m pytest -q` | **34 passed** |
| `python -m compileall app` | exit 0 |
| `python -m ruff check app tests` | All checks passed |
| `node --check frontend/app.js` | exit 0 |
| `node --test tests/frontend.test.cjs` | **5 passed**, 실패 0 |
| `python -m tests.smoke_local` | 실제 HTTP live/ready, 장애·복구, 422, 어댑터 채팅, 정적 파일, 종료 검증 통과 |
| `./venv/Scripts/python.exe -m tests.smoke_local --backend-port 8000 --llm-port 8001 --frontend-port 5500 --serve-seconds 240` | 브라우저 QA 서버 및 smoke 통과 |
| 브라우저 UI 점검 | 한글 합성 메시지 전송, 한글 응답, `shy_smile` 이미지 및 호감도 2 표시 확인 |
| `$env:PYTHON_DOTENV_DISABLED='1'; ./scripts/doctor.ps1` | LLM 미실행 시 exit 1 (Redis ok / LLM timeout), 가짜 LLM 기동 중 exit 0 (둘 다 ok) |
| `git diff --check` | 통과 |

기존 pytest 미설치 실패는 개발 의존성 추가로 해결했다. 최초 lint에서 기존 `llm_service.py`의 한 글자 변수 `l`에 E741이 발생했고 변수명만 명확하게 바꿔 해결했다. 새 기능에서 남은 자동 검사 실패는 없다. GitHub CI 정의는 추가했으나 원격 실행은 아직 하지 않았다. Python 3.11은 CI 대상이며 이번 로컬 완료 검증은 3.12에서 수행했다.

### 호환성, 설정 및 다음 단계

- 기존 응답 필드, 단일 호감도 delta 제한, 이미지 OFF 값, 422 동작을 유지한다. 기존 `history` 요청 필드는 계속 유효하지만 내용은 무시한다. 이는 서버 이력 권한을 지키기 위한 명시적인 호환 변경이다.
- Redis 형식과 키를 바꾸지 않았으며 데이터 migration이 없다. 테스트는 영속 대화 쓰기를 하지 않았다. `.env`는 수정하지 않았으므로 기존 포트/CORS/token 값은 필요 시 README와 비교해 수동 갱신한다.
- `api/ready`는 모델 목록을 Pydantic으로 확인하지만 지정 모델 ID 일치, 실제 생성 성공, VRAM 적합성을 보장하지 않는다. Comfy는 readiness에서 제외했다.
- 남은 제한: 실제 모델 미검증, Redis TTL에 따른 상태 소실, 서버 idempotency/정형 채팅 오류/공개 보안 미구현. 이번 단계에서 이들 기능을 구현하지 않았다.
- **다음 작업 `tasks/01_LLM_CONTRACT_AND_LOCAL_RUNTIME.md` 시작 가능.** 후속 계획 개정에 따라 화면/API 통합부터 진행하고 실행기·schema/runtime 검증을 이어간다. 실제 모델 평가 전에는 RTX 3060 Ti 8 GB 또는 별도 기준 장비의 프로파일을 확인해야 한다.

## 9. 실행·배포 단순화 계획 개정 (구현 전)

- 승인 목표: 단일 FastAPI 웹앱 (정적 화면 + `/api`) + 별도 llama.cpp. SQLite는 로컬 파일, 앱은 한 인스턴스/worker. HTTPS/인증은 공개 배포의 추가 진입 계층이다.
- 순서: Phase 01 화면/API 통합 → 필수 통합 start/stop → Phase 03 SQLite 저장·동시성·중복 처리 검증 → Redis 기본 의존성 제거. 이후 Phase 05에 서비스 관리와 공개 보안 적용.
- Redis는 전환 게이트 전까지 유지한다. 이후에도 기존 데이터를 자동 삭제하거나 장애 시 다른 저장소로 자동 전환하지 않는다. 다중 worker/replica는 공유 조정 설계 전까지 기본 지원 범위가 아니다.
- 변경 문서: `AGENTS.md`, `README.md`, `docs/PRODUCT_AND_TECHNICAL_DIRECTION.md`, `TARGET_ARCHITECTURE.md`, `IMPLEMENTATION_PLAN.md`, `LOCAL_4070TI_RUNBOOK.md`, `API_AND_DATA_CONTRACTS.md`, `TEST_AND_ACCEPTANCE_PLAN.md`, `DEPLOYMENT_AND_SCALING_GATES.md`, `DECISION_LOG.md`, 이 파일, `tasks/01_LLM_CONTRACT_AND_LOCAL_RUNTIME.md`, `03_DURABLE_PERSISTENCE_AND_MEMORY.md`, `04_FRONTEND_RELIABILITY_AND_EVALUATION.md`, `05_SECURE_REMOTE_ALPHA.md`.
- 기준 검사: 문서 편집 전 `./venv/Scripts/python.exe -m pytest -q` → 34 passed, `./venv/Scripts/python.exe -m compileall app` → exit 0. 편집 후 문서 15개의 UTF-8/코드 블록/링크 검사, 단계·전환 게이트 교차 검사, 원본 handoff 보존 검사와 `git diff --check`가 통과했다. 문서 외 파일의 SHA-256 지문은 편집 전과 모두 동일했다. 코드 동작이 바뀌지 않아 새 런타임 테스트는 추가하지 않았다.
- 코드·설정·기존 테스트·원본 handoff 보관본은 이번 개정 범위에 포함하지 않는다. 데이터 migration, 프로세스 실행, 커밋·푸시도 수행하지 않는다.

## 10. Phase 01 실행·응답 계약 및 RTX 3060 Ti 검증 (2026-09-07)

사용자 요청에 따라 현재 PC에서 실제 테스트 가능한 프로파일을 우선했다. HEAD는 검토 기준 `a9f6205045648e8889a4dbf4190de65e330caaed`와 같고, 기존 Phase 00 미커밋 변경을 보존한 채 작업했다. 원격 코드 갱신/커밋/푸시/공개 배포는 하지 않았다.

### 완료 범위

- FastAPI가 `/`, index, JS/CSS, 명시적 face PNG만 제공한다. 프런트 기본 URL은 상대 `/api`다. 별도 프런트 프로세스 없이 동작하며 API 404/405, 검증 422, 비공개 경로·traversal 차단을 검증했다.
- `app/decision.py` canonical 스키마와 enum, `decision_service.py`의 주입 가능한 adapter, Pydantic 경계 검증, allowlist, 명시적 schema/json/text/guided_json 모드, 최대 3회 시도 및 실패 분류를 구현했다. legacy를 명시적으로 선택할 수 있다.
- 기존 flat 응답 필드는 유지하고 표정은 `shy_smile`로 정규화한다. canonical 기본 모드에서 관계 delta=0, 기존 총점·메모 유지다. Phase 02 전까지 분류를 점수로 변환하지 않으며 memory 후보 저장도 후속 작업이다.
- `start-llm`, `stop-llm`, `start-local`, `stop-local`, `doctor`, `benchmark-local` PowerShell 도구와 공통 Python 실행기를 구현했다. 숨김 실행, 준비 시간 제한, 단일 worker, 실제 명령 출력, 프로세스 identity, 중복 호출/부분 실패 정리를 검증했다. Redis는 PING만 하며 종료하지 않는다.
- `README`, AGENTS, 로컬 런북, 제품/구조/실행/검증 계획, Task 01, API 계약, DECISION_LOG를 갱신했다. PC별 경로와 설정은 무시된 `.env`에 반영하고 인증값·Redis 설정은 보존했다. `psutil` 의존성을 추가했다.

### 실제 로컬 프로파일과 결과

| 항목 | 실측/설정 |
|---|---|
| CPU / RAM / GPU | i7-11700 / 약 32 GB / RTX 3060 Ti 8192 MiB |
| 드라이버 | 591.86 |
| 모델 | Qwen3.5-9B-Uncensored-HauhauCS-Aggressive-Q6_K.gguf, 약 6.85 GiB (기존 파일) |
| runtime | llama.cpp b10830, commit 465e49b9c, CUDA 12.4, Clang 20.1.8 Windows x86_64 |
| context / max output / parallel | 2048 / 256 / 1 |
| GPU layers / batch / ubatch | 12 / 128 / 128 |
| thinking / fit margin | OFF / 1024 MiB |
| 로딩 직전 free VRAM | 5131 MiB |
| 평가 시작 시 free / 사용 VRAM | 2128 / 6064 MiB |
| 평가 중 peak 사용 VRAM | 6306 MiB |
| 평가 종료 시 free / 사용 VRAM | 1911 / 6281 MiB |
| 합성 사례 | 20개 독립 단일 턴, 실제 모델 호출, Redis 상태 기록 없음 |
| 최초 / 최종 schema 성공률 | 20/20 (100%) / 20/20 (100%) |
| retry 회복 / 전송·파싱 실패 | 0 / 0 |
| 지연 median / p95 | 19.648s / 21.516s |
| 지연 min / max | 13.156s / 25.218s |
| completion token min / max | 90 / 164 |

p95는 nearest-rank 방식으로 저장된 20개 지연에서 계산했다. 초기에 실행된 evaluator의 percentile 인덱스를 바로잡고 같은 측정 자료에서 집계를 갱신했다(추론 재실행 아님). GPU 사용량은 타 앱도 포함하는 장치 전체 값이며 before/after는 모델이 로딩된 상태의 평가 시작/종료 시점이다. 로컬 원자료는 무시된 `artifacts/benchmarks/local-3060ti.json`에 있고 대화/응답 원문은 저장하지 않았다. 출력 길이 상한 256은 이번 사례에서 충분했지만 모든 입력에 대한 보장은 아니다. 여러 사례에서 allowlist 밖 flags가 나와 제거됐으므로 이 수치는 허용 목록 처리 후의 schema 성공률이며 대화 품질 점수는 아니다.

### 실패와 해결 구분

- 기존 Winget llama.cpp Vulkan b8119/ba3b9c884는 auto offload와 12-layer 설정 모두 `GGML_ASSERT(buffer != nullptr)`로 종료했다. 시작기는 자신이 시작한 모델만 정리했다.
- 공식 b10830 CUDA 12.4 배포와 DLL을 SHA-256 대조 후 `.runtime`에 별도 설치하자 로딩·추론이 성공했다. 공식 asset digest: binary `773ec8b12e60f948807b9e3097e1fb7cb4cf16b9a0260cabb23426e81e44266f`, DLL `8c79a9b226de4b3cacfd1f83d24f962d0773be79f1e7b75c6af4ded7e32ae1d6`.
- 초기 직접 adapter 진단은 기존 `.env` endpoint 설정으로 전송 실패했다. 이 PC용 로컬 8001 설정을 반영한 뒤 실제 평가 20개에는 해당 실패가 없었다.
- 원래 14B Q4는 모델 파일이 없고 현재 PC 기준도 아니므로 사용자 지시에 따라 향후 프로파일로 분리했다. 현재 단계 실패나 미수행 필수 게이트로 계산하지 않는다.

### 검증 명령과 결과

- 수정 전 `./venv/Scripts/python.exe -m pytest -q`: Phase 00 34 passed, 화면 통합 slice 후 53 passed.
- 최종 `./venv/Scripts/python.exe -m pytest -q`: 97 passed. GPU 없는 schema/adapter/HTTP/static/lifecycle/lease 검사.
- `./venv/Scripts/python.exe -m compileall app scripts`: exit 0.
- `./venv/Scripts/python.exe -m ruff check app tests scripts`: 통과.
- `node --check frontend/app.js`, `node --test tests/frontend.test.cjs`: 구문 통과, 5 passed.
- `./venv/Scripts/python.exe -m tests.smoke_local`: 실제 Uvicorn + fake OpenAI 모델 + fake store, same-origin assets/chat, 404/405/422, 장애/복구 통과. 임시 서비스 종료.
- `./venv/Scripts/python.exe -m tests.smoke_local --backend-port 8002 --serve-seconds 180`: 브라우저에서 한국어 답변, `shy_smile` PNG 실제 로딩, 입력 복구 확인. 브라우저의 `/api/unknown` 직접 탐색은 클라이언트에서 차단됐으나 해당 404는 HTTP 테스트로 검증했다.
- `./scripts/start-local.ps1` 두 번: 최초 준비 통과, 두 번째 기존 프로세스 재사용. 실제 모델/웹앱 모두 loopback 준비 완료.
- `./scripts/doctor.ps1`: 모델 파일·실행 파일·소유 프로세스 확인, Redis/LLM 모두 ok, exit 0 (실행 중 검사).
- `./scripts/benchmark-local.ps1 --limit 20`: 위 20개 통과, exit 0.
- `./scripts/stop-local.ps1` 두 번: 모두 exit 0. registry 비움, 8000/8001 종료, 기존 Redis 6379 계속 LISTENING. 테스트 후 GPU를 점유하는 프로젝트 모델을 남기지 않았다.
- `git diff --check`: 통과(Windows CRLF 전환 안내만 있음). 문서 UTF-8/링크 및 민감 로컬 파일 ignore 검사 통과.

### 남은 한계와 다음 작업

현재는 기능 검증용으로 한 응답 약 20초의 부분 GPU offload 프로파일이다. 20개 독립 턴의 schema 검증이며 100턴 내구성/대화 품질/장기 기억 평가는 아니다. 2048 문맥에서는 긴 입력/이력이 넘칠 수 있고 최대 최근 4개 메시지만 모델에 전달한다. 토큰 기반 문맥 관리, 제한 큐/idempotency, SQLite, 전체 오류 request ID, 공개 보안은 미완료다. 데이터 migration은 이번 작업에 없다. 코드 변경은 아직 커밋하지 않았다.

**다음 단계: [Task 02](../tasks/02_RELATIONSHIP_ENGINE.md)의 결정론 관계 계산을 구현한다.** 실행은 [현재 로컬 런북](LOCAL_DEVELOPMENT_RUNBOOK.md)을 따른다.

## 11. 응답 지연 개선 검증 시작 (2026-09-07)

- 사용자 피드백: 응답이 느림. 기존 9B Q6_K는 GPU 12층/CPU 혼합이며 이전 20-case 중앙값 19.648초다. 현재 기동 프로세스에서도 동일 설정을 확인했다. 시작 시 free VRAM은 약 995 MiB로 추가 offload 여유가 적었다.
- 변경 전 `./venv/Scripts/python.exe -m pytest -q`: 97 passed. HEAD는 기준과 동일하며 기존 변경은 보존한다.
- 같은 제작자의 4B Q4_K_M (약 2.52 GiB)을 저장소 밖에 내려받아 GPU 전체 offload 후보로 비교한다. 새 모델 자동 다운로드를 시작 스크립트에 추가하지 않는다. 기존 9B 파일은 보존하고 모델 관련 기존 설정만 무시된 `.runtime/profile-before-speed.json`에 기록했다.
- benchmark에 `--model` alias 인자를 추가해 `.env`를 변경하기 전에 후보를 테스트할 수 있게 했다. `pytest -q tests/test_local_runtime.py` 13 passed, 해당 스크립트 lint 통과.
- 배포 원본: https://huggingface.co/HauhauCS/Qwen3.5-4B-Uncensored-HauhauCS-Aggressive , revision `c09cdbcdb1fefad6d335809d445621b5f5ba0c6e`; Q4_K_M asset SHA-256 `79e28ecacf84e75b6056cf4059636d435aa9eb67795780f7b7dbc7d32a962741`.
- 최종 선택과 비교 결과는 아래 완료 기록으로 확정한다.

### 응답 지연 개선 완료

현재 `.env`의 모델 파일/alias/GPU layer를 검증된 4B Q4_K_M / all로 바꾸고 웹앱을 재시작했다. 변경 전 앱이 실행 중이었으므로 작업 후에도 실행 상태로 복원했다. 기존 9B GGUF, Redis 서비스 및 기존 대화 데이터는 보존한다. 4B 가중치는 저장소 밖 Downloads 하위에 저장했고 SHA-256 검증을 통과했다. 코드 및 문서만 Git 변경 대상으로 남긴다.

| 비교 | 기존 9B Q6_K / GPU 12층 | 4B Q4_K_M / GPU 전체 (최종) |
|---|---:|---:|
| 사례 수 | 20 | 20 |
| 최초 / 최종 schema 통과 | 20/20 / 20/20 | 20/20 / 20/20 |
| 중앙값 | 19.648s | 1.172s |
| p95 | 21.516s | 1.563s |
| output cap / context | 256 / 2048 | 256 / 2048 |

초기 4B 비교(프롬프트 변경 전)도 20/20 통과, 중앙값 1.390s였다. 작은 모델의 반말 지침 유지를 돕기 위해 스키마 뒤에 캐릭터 지침을 배치하고 기존 반말 규칙을 예시로 재강조한 후 최종 20개를 다시 실행했다. 최종 결과는 캐시가 준비된 상태이며 초기 4B 첫 요청은 2.860s였다. 기존 9B와 GPU의 타 앱 부하는 같지 않으므로 정밀한 동일 환경 A/B 측정이라고 주장하지 않는다.

4B 로딩 직전 free VRAM 3801 MiB. 최종 평가 시작 free 959 MiB, peak 전체 사용 7239 MiB, 종료 free 968 MiB였다. 이는 모델 단독이 아닌 장치 전체 사용량이다. 현재 타 앱까지 포함하면 VRAM 여유는 약 1 GB이므로 큰 모델용으로 `all`을 일반화하지 않는다.

변경 파일: `.env.example`, `app/services/decision_service.py`, `app/characters/default.json`, `scripts/benchmark_local.py`, AGENTS, README, 현재 런북, 제품/구조/구현/검증 계획, Task 01, DECISION_LOG, PROJECT_STATUS. 무시된 로컬 `.env`는 모델 관련 3개 값만 갱신했다.

검증:
- `./scripts/benchmark-local.ps1 --model HauhauCS/Qwen3.5-4B-Uncensored-HauhauCS-Aggressive --output artifacts/benchmarks/local-3060ti-4b-speed-final.json --limit 20`: 20/20, 재시도 0, exit 0. 이전 비교 원자료도 별도 보존.
- `./venv/Scripts/python.exe -m pytest -q`: 97 passed.
- `./venv/Scripts/python.exe -m ruff check app tests scripts`: 통과.
- `./venv/Scripts/python.exe -m compileall -q app scripts`: exit 0.
- `./scripts/start-local.ps1`, `./scripts/doctor.ps1`: exit 0, Redis/LLM ready, 8000 웹앱 및 8001 모델 실행 중.
- 실제 FastAPI factory + 실제 4B adapter + 격리 fake store로 POST `/api/chat`: HTTP 200, 1.594초, 한국어 반말 응답과 happy 표정, delta 0. 기존 Redis 데이터는 쓰지 않았다.
- 실제 3턴 문맥 확인은 성공 응답을 반환했지만 일부 존댓말 혼용 및 이전 대화에 없던 내용 추가를 관찰했다. 스키마 통과가 의미/말투 품질을 보장하지 않는다. 더 작은 모델의 품질 동등성이나 100턴 안정성은 미검증이다.

추가 migration이나 인증 변경은 없다. 빠른 개발 테스트용 기본값으로 적용했으며 장기 문맥/말투 품질은 Phase 04 평가 대상으로 남긴다. 다음 기능 작업은 Task 02 관계 계산이다. 커밋/푸시/공개 배포는 하지 않았다.
