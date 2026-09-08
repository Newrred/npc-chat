# NPC Chat

기본 원격 배포는 [로그인 없는 공개 링크](docs/PUBLIC_LINK_DEPLOYMENT.md)다. 익명 쿠키로 대화를 분리하고 활동 이용자 수와 일일 한도를 적용한다. Cloudflare Access 이메일 로그인은 선택 모드이며 실제 외부 공개는 아직 하지 않았다.

원격 배포 준비: [운영 런북](docs/REMOTE_DEPLOYMENT_RUNBOOK.md). 현재 로컬 모드는 유지하며, 원격 모드는 추가 인증 의존성과 별도 개인 배포 설정이 필요하다. 도메인 연결/실제 외부 검증 및 보관·삭제/운영 복구 게이트 전에는 공개 배포 완료로 취급하지 않는다.

캐릭터와 짧은 한국어 대화를 주고받는 로컬 우선 챗봇이다. FastAPI 백엔드, 정적 HTML/CSS/JavaScript 프런트, 별도 OpenAI-compatible LLM 프로세스로 구성한다.

**`Newrred/npc-chat`이 유일한 개발 기준 저장소이며 `npc-chat/frontend`가 프런트 원본이다.** `Newrred/heroine`은 레거시 배포 복사본이다. 그 저장소에서 병행 기능 개발을 하지 않는다.

현재 **Phase 04 신뢰성 구현·모델 평가 완료**: FastAPI 한 주소에서 화면/API를 제공하고 다섯 관계 수치와 기억을 SQLite에 저장한다. 기본 실행에는 Redis가 필요 없다. [현재 상태](docs/PROJECT_STATUS.md), [로컬 실행](docs/LOCAL_DEVELOPMENT_RUNBOOK.md), [백업/복구](docs/DATABASE_OPERATIONS.md)를 참고한다.

## 구성과 포트

| 구성 | 기본 주소 | 역할 |
|---|---|---|
| FastAPI 웹앱 | `http://127.0.0.1:8000` | 화면, 정적 표정, API 및 서버 세션 상태 |
| llama.cpp | `http://127.0.0.1:8001/v1` | 별도 로컬 모델 프로세스 |
| SQLite | `.runtime/data/npc-chat.sqlite3` | 관계·이력·기억·중복 방지, 별도 서버 없음 |

ComfyUI는 기본 OFF이며 readiness 필수 의존성이 아니다. 선택적 Comfy 연동은 `/generate`를 제공하는 기존 어댑터 계약을 전제로 하며, stock ComfyUI API와 직접 호환된다는 뜻이 아니다.

## Python 환경 준비

Python 3.11 또는 3.12를 사용한다. 저장소 루트 PowerShell에서:

```powershell
if (-not (Test-Path venv/Scripts/python.exe)) { python -m venv venv }
./venv/Scripts/python.exe -m pip install -r requirements-dev.txt
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
```

서버 실행만 필요하면 `requirements.txt`를 설치한다. `.env`가 이미 있으면 예제로 덮어쓰지 말고 다음 항목을 비교·수정한다. 환경 변수는 `.env`보다 우선한다.

```dotenv
NPC_LLM_BACKEND=llama_cpp
NPC_BASE_URL=http://127.0.0.1:8001/v1
NPC_MODEL=local-model
NPC_MAX_TOKENS=256
HEALTH_TIMEOUT_SEC=2
CORS_ORIGINS=http://127.0.0.1:5500,http://localhost:5500
NPC_DATABASE_PATH=.runtime/data/npc-chat.sqlite3
COMFY_ENABLED=false
COMFY_CONNECT=false
```

`NPC_MODEL`은 실제 `/v1/models`에 있는 ID나 서버 alias와 일치시킨다. `NPC_API_KEY`는 해당 로컬 서버 설정에 맞춘다. vLLM이 필요하면 `NPC_LLM_BACKEND=vllm`, 해당 버전에서 지원하는 `NPC_JSON_MODE` (`guided_json` 또는 `json`/`text`)와 모델 ID를 명시한다. `NPC_CHARACTER_ID` 기본값은 `default`다.

현재 개발 장비는 RTX 3060 Ti 8 GB / RAM 약 32 GB다. 2026-09-08 사용자 요청으로 Aggressive 9B Q4_K_M / 문맥 4096 / GPU layers auto를 비교 테스트 중이다. 응답 최대 256, 동시 처리 1, thinking OFF, batch/ubatch 128이다. 빠른 4B Q4_K_M / 문맥 8192 / GPU all 설정과 기존 9B Q6_K는 보존한다. 저장된 최근 12개 메시지를 토큰 예산 안에서 전달한다. 9B의 대화 품질 우위는 아직 확정하지 않았다. 14B Q4는 추후 검증한다.

## 로컬 실행

`.env`에 `LLAMA_SERVER_PATH`와 `LLAMA_MODEL_PATH`를 설정한다. SQLite 스키마는 시작 시 준비한다. 자동 설치/모델 다운로드는 없다.

```powershell
./scripts/start-local.ps1
# 브라우저: http://127.0.0.1:8000
./scripts/stop-local.ps1
```

모델만 실행/종료하려면 `start-llm.ps1` / `stop-llm.ps1`을 사용한다. 도구는 자신의 PID와 생성 시간/실행 파일/인자를 확인한 프로세스만 종료한다. 외부 모델을 사용하려면 `--reuse-llm`을 명시하며 해당 모델과 Redis는 종료하지 않는다. 실패하면 그 호출이 시작한 프로세스만 정리한다. 설정을 바꾼 뒤에는 stop/start한다.

수동 웹앱 실행도 가능하다: `./venv/Scripts/python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000`. 프런트 서버는 필요하지 않다.

`frontend/config.js`는 비밀값 없는 로컬 기본 설정으로 **의도적으로 Git 추적**한다. `config.example.js`가 기준 예시다. 기본 `NPC_API_BASE_URL`은 빈 문자열로 같은 주소의 `/api`를 사용한다. 별도 호스팅 시 API 주소를 수정하고 백엔드 `CORS_ORIGINS`에 정확한 프런트 origin을 지정한다. 프런트 설정에는 API 키나 인증 정보를 넣지 않는다.

`index.html`은 `config.js`와 단일 실행 파일 `app.js`를 로드한다. 이전 `app.fixed.js`는 제거했다. 정적 표정은 `frontend/faces/{slug}.png`에서 제공하고 공백을 underscore로 바꾼다. 이미지가 없으면 대체 표정과 `neutral`, 마지막으로 placeholder를 사용한다. 생성 이미지 실패도 정적 표정으로 돌아간다.

## Health와 API 호환성

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/live
Invoke-RestMethod http://127.0.0.1:8000/api/ready
$body = @{ message = "안녕, 오늘 어땠어?"; comfy_on = $false } | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/api/chat -ContentType "application/json; charset=utf-8" -Body ([System.Text.Encoding]::UTF8.GetBytes($body))
```

- `/api/live`와 기존 `/api/health`: 프로세스 응답 확인, 200 `{"status":"ok"}`.
- `/api/ready`: SQLite 스키마/읽기와 LLM `/models`를 병렬 확인. 모두 정상이면 200, 장애면 503. 각 의존성은 `ok`, `unavailable`, `timeout`으로 표시한다. URL·키·예외 본문은 반환하지 않는다.
- `HEALTH_TIMEOUT_SEC`는 의존성별 기본 2초이며 0.1~10초로 제한한다. Comfy는 확인하지 않는다. LLM 모델 목록 확인은 모델 ID 일치·추론 성공·VRAM 적합성까지 보장하지 않는다.
- 의존성이 중단돼도 서버가 시작되어 live/ready를 확인할 수 있다. 채팅에는 정상 Redis와 LLM이 필요하다.
- 기존 채팅/이미지 응답 필드와 빈 메시지의 422 검증 응답은 유지한다. `shy smile` 입력은 `shy_smile`로 정규화한다. canonical 모드는 관계 엔진 구현 전까지 affection_delta=0으로 기존 총점·메모를 보존한다. `history` 필드는 호환을 위해 받지만 내용은 사용하지 않는다. 서버 이력만 모델에 전달한다.
- 전송 중 입력과 버튼을 잠근다. 자동 재시도는 없으며 서버 idempotency는 후속 단계다. canonical 모델의 전송 실패는 503, 응답 검증 실패는 502로 분류한다. 전체 오류 규격과 request ID는 후속 단계다.
- Comfy OFF의 API 값은 `comfy_status=disabled`, `image_source=none`, `image_url=null`이다. 프런트가 자체 정적 이미지를 표시한다.

## 검증

활성화된 가상환경에서는 아래 명령의 `./venv/Scripts/python.exe`를 `python`으로 바꿀 수 있다. Node.js 20 이상은 프런트 검사에 사용한다.

```powershell
./venv/Scripts/python.exe -m pytest -q
./venv/Scripts/python.exe -m compileall app
./venv/Scripts/python.exe -m ruff check app tests scripts
node --check frontend/app.js
node --test tests/frontend.test.cjs
```

pytest는 로컬 `.env`를 읽지 않고 fake 모델/세션 및 모의 HTTP 응답을 사용한다. 실제 GPU, Redis, 인터넷을 요구하지 않는다. GitHub Action은 Python 3.11/3.12에서 위 검사를 실행한다.

추가 로컬 HTTP smoke:

```powershell
./venv/Scripts/python.exe -m tests.smoke_local
```

일시적인 loopback 포트에 가짜 OpenAI-compatible 서버와 실제 FastAPI/Uvicorn을 띄운다. 실제 LLM 어댑터 호출, 준비 상태의 장애·복구, 정적 파일을 확인하고 종료한다. 세션은 메모리 fake store라 기존 Redis 데이터를 쓰지 않는다. 이것은 모델 성능 검증이 아니다.

브라우저 수동 검증용으로만 합성 응답 서버를 잠시 유지하려면:

```powershell
./venv/Scripts/python.exe -m tests.smoke_local --backend-port 8000 --llm-port 8001 --serve-seconds 120
```

해당 포트가 비어 있어야 하며 지정 시간이 지나면 종료한다. 운영 앱에는 fake 모드를 노출하지 않는다.

환경 점검:

```powershell
./scripts/doctor.ps1
```

기존 `venv`, `.venv`, PATH Python 순으로 선택한다. `-Python`으로 실행 파일을 지정할 수 있다. Python/패키지/GPU, 기본 포트와 현재 설정의 Redis·LLM을 읽기 전용으로 확인한다. 설치나 서버 실행, 모델 로드, 대화 저장을 하지 않는다. 의존성 누락·LLM 포트 충돌·서비스 준비 실패이면 exit 1이다. 서버를 시작하지 않은 상태의 exit 1은 예상 가능한 환경 결과다.

## 저장과 배포 경계

이번 단계의 데이터 migration은 없다. 기존 Redis 키와 TTL 설정을 유지한다. TTL 만료 뒤 브라우저 history로 대화를 복원하지 않으며 영속 기억은 Phase 03에서 구현한다.

GitHub Pages Action은 계속 `frontend/`만 배포한다. 로컬 기본 주소를 배포한 페이지는 원격 백엔드 배포 완료를 의미하지 않는다. 원격 사용 전 고정 주소, 접근 통제, 정확한 CORS, 요청 제한과 보존 정책 등 [보안 게이트](docs/DEPLOYMENT_AND_SCALING_GATES.md)를 충족해야 한다. LLM 포트를 직접 외부에 공개하지 않는다.

`.env`, 키, 모델, 로컬 DB, 생성 이미지, 개인 대화는 커밋하지 않는다. 새 모델/DB/검사 산출물은 `.gitignore`로 제외한다. 현재 제공된 정적 표정 자산은 유지한다.


## 관계와 재시도 (Phase 02/03)

/api/session에 빈 JSON 또는 기존 session_id/profile_id를 보내 대화 식별자를 먼저 저장한다. /api/chat은 식별자와 client_turn_id, message, comfy_on을 받는다. 같은 ID/내용 재시도는 저장한 응답을 반환하며 내용 변경은 409다. 기존 ID 없는 flat 요청은 일회성 호환 경로이며 재시도 중복 보장을 받지 못한다.

응답 relationship에 다섯 values/delta, reason_codes, rule_version이 있다. 기존 affection_total/delta는 호환용 deprecated 별칭이다. 화면의 개발 정보 체크박스에서 확인한다. 모델은 분류만 하며 서버가 규칙 1.0으로 계산한다. 실패 후 입력과 turn ID를 보존하므로 같은 메시지를 다시 전송하면 된다. 웹앱은 반드시 worker 1개로 실행한다.

정확한 구현 범위·검증·품질 제한은 [Phase 02/03 완료 기록](docs/PHASE02_03_COMPLETION.md)을 참고한다.


## Phase 04 — 오류 처리와 문맥 설정 (2026-09-07)

화면의 오류/대기 안내는 마지막 NPC 대사와 분리된다. 실패 후에는 같은 메시지 다시 보내기로 확인한다. 새로고침해도 turn ID와 프로필이 유지된다. 자동 재전송은 하지 않는다. 422 입력 오류는 내용 수정, 없는 프로필은 새 대화 시작으로 복구한다. 이 버튼은 기존 서버 기록을 삭제하지 않는다.

로컬 기본 설정에 `NPC_TOKEN_COUNT_MODE=llama_cpp`를 사용한다. 현재 실행 모델의 `/apply-template`와 `/tokenize`로 출력 여유를 제외한 문맥 한도를 확인한다. 긴 현재 입력을 몰래 자르지 않고 422로 안내한다. 다른 제공자용 `estimate`는 근사값이므로 해당 제공자의 tokenizer 검증이 별도로 필요하다.

개발 정보에는 관계값/변화/이유 코드/지연이 표시된다. frontend/config.js의 `NPC_RELATIONSHIP_DISPLAY`는 debug(기본 숨김 토글) 또는 hidden이다. `NPC_REQUEST_TIMEOUT_MS`는 기본 420000이며 timeout 후에도 같은 ID로 확인한다.

단순한 사용자 취향 정정은 최신 원문으로 교체한다. 명시적 취향 회상은 저장한 발화를 직접 인용해 모델의 긍정/부정 뒤집기를 방지한다. 복잡한 기억과 말투 품질은 아직 한계가 있다. [구현 기록](docs/PHASE04_IMPLEMENTATION.md)과 [평가 보고서](docs/PHASE04_EVALUATION.md)를 참고한다.
