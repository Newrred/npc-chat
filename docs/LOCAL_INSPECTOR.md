# 로컬 모델 검사 창

## 2026-09-09 Task16 — 입력/출력과 기억 판단 추적

입력 파란 영역/출력 주황 영역으로 구분한다. 전체 흐름과 단계별 보기 모두 실제 시스템 지시문을 펼쳐 보여주고 출력 JSON 스키마는 별도로 접는다. 분석 단계는 분석기 규칙/완성된 대사/서버 기억/최근 대화를 구분한다. 검색됐으나 해당 단계 입력에 포함되지 않은 기억도 비교해 표시한다.

명시적 opt-in 진단에서만 memory_retrieval을 기록한다. 일반 기억의 실제 검색 단어, 현재 입력/가장 가까운 사용자 발언/취향 범주 검색 경로, 후보별 일치 단어·취향 모순·선택 여부, 순위 규칙을 담는다. 이름·호칭은 최신 명시적 발언, 사건은 질문 범주/제목 단어 기준의 최근3개라는 파생 경로를 설명한다. 검색/저장 알고리즘 자체는 바꾸지 않았다. 입력 예산의 요약→이전 대화→일반 기억 제외 순서도 표시한다.

memory_committed는 실제 DB transaction 성공 후 기록한다. 현재 사용자 원문, 모델 후보/서버 취향 규칙의 후보 생성 경로, 원문 근거/종류 규칙/중복 병합/최대2개 한도 검사, 쓴 기억, 보관50개 제한 제외키, 원문에서 파생한 이름·호칭/사용자·캐릭터 사건을 담는다. 이름·사건은 별도 memory 테이블 쓰기가 아니라 저장 대화에서 파생한다. 롤백에는 commit 진단을 내지 않는다. 이전 턴에는 상세 이유가 없다고 명시하고 현재 기억으로 과거 판단을 재구성하지 않는다. 기존1시간/100회 비공개 trace 보관 정책 유지.

검증: 기준555 passed(13.39s) → `./venv/Scripts/python.exe -m pytest -q` 562 passed(16.02s). `node --test tests/inspector.test.cjs` 5 passed, `node --check admin/inspector.js`, `./venv/Scripts/python.exe -m ruff check app tests scripts`, `./venv/Scripts/python.exe -m compileall -q app scripts`, `git -c core.safecrlf=false diff --check` 통과. 새7개 Python 사례는 진단 유무 저장/검색 결과 동등성, 문맥 검색/모순 제외, commit 이후 파생 정보, rollback 미기록을 검증한다. 기존 테스트 하나의 ‘첫 이벤트는 context_selected’ 가정을 이벤트명 검색으로 갱신했다. 새 UI검증은 후보 생성 경로/제외 이유/이름 파생/구기록 안내다. skip 없음.

웹만 재시작, 모델·터널·관리자 유지. 별도 guest 실제 모델2턴에서 취향1개 저장→다음 질문에서1개 검색→질문 후보0개 저장 확인 후 해당 합성 방 reset. 사용자 테스트방은 변경하지 않음. 브라우저에서 펼친 분석기 프롬프트와 출력 구분/구기록 안내 확인. 모델 품질 개선 실험이 아닌 관측 기능이며 private 내용 커밋 없음. 변경: app/memory.py, conversation_memory.py, repository.py, admin/inspector.js·html, tests/test_memory_audit.py·test_debug_trace.py·inspector.test.cjs 및 문서. DB migration/추가 설정/commit/push 없음. 다음은 실제 실패 턴의 검색·분석·저장 중 어느 단계가 문제인지 이 기록으로 비교하는 것이다.


## 2026-09-09 Task15 — 프롬프트 편집·시간순 검사 완료

캐릭터 소개/말투 규칙을 편집하고 ‘이 설정으로 테스트’로 이후 자기 테스트방 요청에 적용한다. 공유 캐릭터 파일은 변경하지 않으며 기본값 복원 가능. 적용본은 이 브라우저 localStorage에 남고, 미적용 편집은 전송하지 않는다. 실패한 메시지 재시도는 당시 편집본/turn ID를 유지한다. 적용해도 기존 대화·기억은 유지되므로 독립 비교는 새 테스트방으로 시작한다. 요청별 편집본과 버전은 기존 비공개 진단 보관 정책(1시간/100회)에 따라 기록한다.

검사 기본 화면은 ① 서버 입력 준비 → ② 모델 대사 생성(입력+출력) → ③ 같은 모델 부가정보 분석(입력+출력) → ④ 서버 검증·저장이다. 단계별 재시도도 표시한다. 현재 기억 보관함은 별도 현재 상태 조회다. 모델 입력을 시스템 지시문/서버 문맥/최근 대화로 나누어 읽을 수 있게 했으며 앞의 두 부분은 실제로 같은 system 메시지에 포함된다. ‘기록 전체 JSON’은 입력뿐 아니라 시각·설정·출력 등 진단 기록 전체라는 설명을 추가했다.

로컬 bridge가 DB 옆 *.inspector.key로 서명한 일시적 요청 헤더를 발급한다. 서명은 세션/프로필/turn/message/편집본에 결합되고10분 후 만료된다. 웹은 서명 검증 후 서비스의 얕은 복사본에만 캐릭터 초안을 주입한다. 모델 클라이언트/큐는 공유하고 글로벌 설정은 변경하지 않는다. 프롬프트도 중복 요청 digest에 포함되어 같은 ID의 다른 편집본은409다. 기존 guest 소유권·큐·일일 한도·원자적 저장을 유지한다. 공개 JSON의 임의 prompt 필드는 사용하지 않는다. 키는 gitignore되며 비공개로 취급한다. 대사 규칙과 캐릭터 소개만 편집 가능하고 출력 계약/토큰 예산/분석 규칙은 서버에 유지한다. 편집 시험에서만 분석기의 캐릭터 지칭을 일반화하여 기존 유이 이름과 충돌하지 않게 했다. two_stage 모드에서 지원한다.

검증: 기준552 passed(11.79s) → 전체 `./venv/Scripts/python.exe -m pytest -q` 555 passed(11.62s). `node --test tests/inspector.test.cjs` 4 passed, `node --check admin/inspector.js`, `./venv/Scripts/python.exe -m ruff check app tests scripts`, `./venv/Scripts/python.exe -m compileall -q app scripts`, `git -c core.safecrlf=false diff --check` 통과. 추가3개 Python 검증: 서명 위조/만료/대상 변경, 두 단계 입력 반영, 실제 guest bridge 기본 설정 격리/재전송/변경409/비정상 편집422/공개 위조403. UI 검증은 편집 후 실패 재전송 시 원래 편집본 유지·4단계 순서 포함. 테스트 첫 실패2건은 ‘하나’가 기존 문장 ‘가능하나’와 겹친 검증 문자열 문제로 더 구체적인 문자열로 수정. UI 문구 교체 중 구문 오류는 node 검사로 발견·수정. skip 없음.

웹/관리자 재시작, 모델/터널 유지. 최초 준비 상태 조회는 guest 자격 없이 /api/ready를 조회해403으로 실패했으며 /api/live200, 관리자 ready200, 실제 브라우저1턴 생성·commit·두 단계 편집본 캡처로 동작 확인. 화면에서 기본 설정 복원 완료. 확인용1턴은 기존 테스트방에 남았다. 모델의 언어 혼입은 여전하며 이 작업은 모델 품질 개선 채택 실험이 아니다. 새 DB schema migration/추가 결제/commit/push 없음. 초안이 길면 기존 토큰 예산 오류가 발생할 수 있으며 자동으로 사용자 입력을 잘라내지 않는다. 다음 과제는 동일한 초기 대화 상태로 프롬프트 후보들을 비교하는 품질 실험이다.


## 2026-09-09 가독성 개선·통합 테스트 채팅 (Task14)

검사 창을 ‘대화 실험실’로 바꿨다. 넓은 화면은 왼쪽 테스트 채팅/오른쪽 검사, 좁은 화면은 위아래 배치다. 기억을 종류·값·근거 발언 카드로 표시하고 프롬프트는 사용자/캐릭터 역할별 카드, 시스템 설정은 접어서 표시한다. 원본 JSON은 별도 펼치기에 보존한다. 검색된 기억 수와 실제 최근 단계 입력에 포함된 기억 수를 구분한다. 보관함도 일반 사용자 기억/이름·호칭/사건 수를 구분한다.

첫 메시지 또는 ‘테스트 대화 연결’로 **이 로컬 브라우저 전용 guest 대화방**을 연다. 기존 공개 사이트 브라우저와는 별도 guest이므로 원래 방문자 방에 전송하지 않는다. 다른 방을 살펴보고 있어도 채팅 전송 대상은 자기 테스트 방으로 고정하며 검사 선택을 그 방으로 연결한다. 새로고침하면 테스트 세션과 최근100턴을 복원한다. 서버 원문은 그대로이며100턴은 채팅창 표시 한도다. 실패 시 같은 client_turn_id를 유지하고 다시 전송한다. ‘테스트 방 나가기’는 해당 테스트 대화·기억·진단 기록을 초기화한다. 연결 재시도는 별도 버튼으로 가능하다.

관리자는 guest 모드의 NPC_PUBLIC_ORIGIN이 설정됐을 때만 /api/test/session, /api/test/chat, /api/test/reset POST와 /api/test/conversation GET을 제공한다. 쓰기는 정확한 localhost Origin·Host·JSON·16KB 본문 제한을 요구한다. 원격 URL이나 관리자가 선택한 임의 방문자에 대한 쓰기를 제공하지 않는다. 고정 127.0.0.1:8000의 기존 웹 API로만 연결하고 해당 웹 앱의 guest 소유권·큐·일일 한도·중복 처리·reset을 그대로 적용한다. Cloudflare Access/local 모드에는 현재 bridge를 활성화하지 않는다. 로컬 테스트 쿠키는 upstream이 발급한 서명 guest를 HttpOnly/SameSite=Strict, /api/test 경로의 localhost 쿠키로 전달하며 공용 사이트 쿠키를 가져오지 않는다. DB 본체를 직접 수정하지 않고 모델/웹 생성 로직도 바꾸지 않았다. 관리자 API를 외부에 공개해서는 안 된다.

검증: 기준545 → 전체 `./venv/Scripts/python.exe -m pytest -q` 552 passed(11.89s), `./venv/Scripts/python.exe -m ruff check app tests scripts` 및 `./venv/Scripts/python.exe -m compileall -q app scripts` 통과. `node --check admin/inspector.js`, `node --test tests/inspector.test.cjs` 3 passed. 추가된 bridge7개 검증에는 경로/Origin/본문 크기/쿠키 분리/장애·429 전달과 실제 guest 앱을 통한 다른 방문자 접근 차단·재전송·한도·reset이 포함된다. UI3개는 안전한 텍스트 카드/자기 방 고정 및 동일 요청 재시도/실제 포함 기억 파싱을 검사한다. 최초 통합 테스트의 mock 응답 stream 타입 오류를 수정했다.

관리자만 재시작하고 실제 브라우저에서 테스트2턴, 이름 근거 카드, 대사 입력, 검사 자동 연결, 새로고침 후 대화 복원을 확인했다. 확인용 테스트 대화2턴은 화면을 살펴볼 수 있도록 남겼다. 첫 실제 모델 답변에는 다른 언어 혼입이 있었으며 UI 구현의 품질 개선으로 모델 오류까지 해결했다고 주장하지 않는다. 변경 파일: admin/inspector.html·inspector.js, app/admin.py·inspector_chat.py, scripts/serve_admin.py, tests/test_inspector_chat.py·inspector.test.cjs. 새 DB migration/모델 재시작/추가 환경 설정 없음. commit/push 없음.

아래 Task13 기록 중 ‘관리자 GET·HEAD만 허용’은 현재 일반 조회 경로에 해당하며, 위의 좁은 테스트 bridge 쓰기 예외가 추가됐다.

2026-09-09 Task13. http://127.0.0.1:8002/inspector 에서 대화방과 처리(turn)를 선택한다. 기존 관리자 상단의 ‘모델 검사 창 열기’ 링크로도 연다. 1초 자동 갱신과 새 처리 따라가기를 켜고 다른 창에서 대화하면 모델 요청 중에도 입력을 확인할 수 있다. 지난 처리를 선택하면 따라가기가 꺼진다.

## 화면 구분

- 이번에 선택한 기억: 생성 전 검색 결과, 원문 이력 메시지 수, 요약, 관계. 검색 결과 전체가 최종 입력에 남는다는 뜻은 아니다.
- 현재 저장·파생 기억: 기존 memories 테이블의 사용자 기억, 원문 기반 이름/호칭, 최근50개 추천/제안/약속/취소 사건. 과거 선택 턴 당시가 아닌 **현재 DB** 기준이다.
- 1차/2차 입력: 각 시도 직전 실제 OpenAI SDK 요청 arguments. 토큰 조절 후 messages(system/user/assistant), 스키마/생성 설정, 토큰 수/예산/문맥 제외 여부를 표시한다. extra_body는 SDK에서 HTTP JSON 최상위로 합쳐진다. 모델 서버 내부 채팅 템플릿 렌더링 문자열은 캡처하지 않는다.
- 모델 출력·저장 결과: 원시 출력/finish_reason, 실패·재시도, 최종 commit 이후 응답. 출력 도착과 저장 완료는 별도 이벤트이며 기존 대사 보정 전후도 비교할 수 있다. 시간은 단계 시작부터의 누적 elapsed_sec다.

## 활성화와 보관

`NPC_DEBUG_TRACE=1`을 실제 웹 실행에 사용한 환경 파일에 지정하고 웹을 재시작한다. 예제 기본값은0이며 이번 사용자 테스트의 루트 .env 및 공개 시험 환경에만1을 적용했다. 끄려면0으로 바꾸고 웹을 재시작한다. 창의 자동 갱신 체크는 조회만 멈추며 서버 캡처를 끄지는 않는다.

진단은 앱 DB 옆 `<database>.debug.sqlite3`에 저장한다. 일반 로그나 공개 응답에 프롬프트를 넣지 않는다. API키/Authorization 헤더/환경 파일은 캡처하지 않는다. 모든 대화방의 활성화 이후 처리에 적용되며 테스트가 끝나면 끄는 용도다. 보관은 최근1시간, 최대100회 처리(재전송 포함)로 조회/쓰기 때 정리한다. 프로세스가 멈춰 있으면 디스크 정리도 다음 조회/쓰기까지 지연된다. SQLite 삭제는 보안 삭제를 보장하지 않는다. 방 초기화/프로필 삭제는 해당 진단도 정리한다. 진단 파일 쓰기 실패는 채팅을 실패시키지 않는다.

관리자 프로세스의 loopback/정확한 Host·Origin/GET·HEAD 경계를 유지한다. 공개 앱에는 inspector 경로를 추가하지 않는다. 원문은 외부로 보내지 않고 JSON을 textarea.value/textContent로 표시한다. 브라우저 응답은 no-store다. 기존 추적 이전 요청의 정확한 프롬프트는 소급 복원하지 않는다. 현재 기억은 기존 대화에서도 볼 수 있다.

## 검증과 범위

기준540 tests. 요청 arguments를 실제 mock HTTP body와 교차 비교, 형식 오류/재시도, OFF 시 파일 미생성, 100회/1시간 한도, 실패 정보 최소화, DB 기억 자료형, 진단 장애 시 채팅 지속, 관리자 경계/공개 비노출/reset을 검증했다. 초기에 함수 이름 변경 위치 오류로32개 테스트가 실패하여 수정했고, SDK extra_body 병합을 반영해 정확한 요청 비교 테스트를 수정했다. skip한 테스트는 없다.

최종 결과: pytest545 passed(10.97s), Ruff/compileall/JS 구문 검사 통과.

최종 명령: `./venv/Scripts/python.exe -m pytest -q`, `./venv/Scripts/python.exe -m ruff check app tests scripts`, `./venv/Scripts/python.exe -m compileall -q app scripts`, 추출한 inspector JS의 `node --check`. 실제 공개 합성 1턴에서 대사/부가정보 요청과 최종 응답 일치, 로컬 기억 조회, 공개 inspector 비노출을 확인하고 테스트 방/진단을 초기화했다. 브라우저에서 페이지 로드·연결 상태·기억 탭 전환을 확인했다.

변경: app/debug_trace.py, config.py, main.py, services/decision_service.py, repository.py, admin.py, admin/inspector.html, 관리자 링크, tests/test_debug_trace.py 및 문서. 모델 설정/프롬프트 내용/DB 본체 스키마는 변경하지 않았다. 웹/관리자만 재시작하며 모델/터널 유지. 아직 commit/push하지 않았다.

현재 조회는 원문 파생 계산 및 제한된 진단 레코드를 읽으므로 큰 DB에서는 비용이 증가한다. 다음 과제는 실제 실패 턴을 이 창으로 식별하고 합성 회귀 사례로 변환하는 것이다.
