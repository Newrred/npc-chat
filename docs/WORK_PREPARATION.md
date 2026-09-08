# 작업 준비 기록

확인일: 2026-09-07 (KST)

이 문서는 **구현 전 사전 점검 기록**이다. 이후 사용자 요청으로 Phase 00을 완료했으며 현재 상태와 검증 결과는 [PROJECT_STATUS.md](PROJECT_STATUS.md) 8절, 실행 방법은 [README](../README.md)을 따른다. 아래의 미설치/미구현 항목은 점검 당시 사실이다.

## 완료 범위

사용자 요청에 따라 전달 ZIP, 현재 작업 트리, 연결된 GitHub 저장소를 비교했다. 코드와 문서 원본이 모두 현재 기준과 같아 추가 다운로드/병합이 필요하지 않았다. 이번 변경은 이 문서, `PROJECT_STATUS.md`, `DECISION_LOG.md`이며 앱 동작·설정·의존성은 변경하지 않았다. 커밋/푸시는 수행하지 않았다.

문서 내부의 구현 시작 프롬프트는 다음 작업에 사용할 자료다. Phase 00 전체를 이번 준비 작업의 완료 범위로 간주하지 않는다.

## 최신성 및 문서 배치

| 비교 대상 | 결과 |
|---|---|
| 로컬 HEAD / `origin/main` / 원격 main | `a9f6205045648e8889a4dbf4190de65e330caaed`로 동일 |
| 현재 브랜치 | `codex/p0-baseline-stabilization` |
| 원격 heroine HEAD | `f722ae87a82775e3cf12c0f188a71f5165c5686e`, 문서 기준선과 동일 |
| 전달 ZIP SHA-256 | `71c4028ea94e8ee4b2e68009c3ab9f4edb2642990deb9107d7930ac046a23ac9` |
| ZIP checksum 검증 | 21개 항목 전부 통과 |
| 문서 반영 상태 | 갱신 전 22개 대응 파일 모두 원본과 동일 |
| 시작 시 추적 파일 변경 | 작업 트리/인덱스 모두 없음 |
| 시작 시 미추적 문서 | `AGENTS.md`, `CODEX_START_PROMPT.md`, `docs/`, `tasks/` |

패키지 `AGENTS.md`, `CODEX_START_PROMPT.md`, `docs/`, `tasks/`는 같은 상대 위치에 있다. 패키지 루트의 `README.md`, `MANIFEST.md`, `NPC_CHAT_CODEX_MASTER_HANDOFF.md`, `SHA256SUMS.txt`는 `docs/handoff-package/`에 있다. 기존 프로젝트 `README.md`와 패키지 README는 서로 다른 문서다.

`docs/handoff-package/SHA256SUMS.txt`는 원본 ZIP용 기록이다. 작업하면서 갱신되는 상태/결정 문서의 최신 checksum 목록이 아니므로 원본 checksum을 다시 생성하지 않는다.

## 실제 환경과 기준선 결과

| 항목 | 확인 결과 |
|---|---|
| OS | Windows 11 Home 10.0.26200 |
| CPU / RAM | Intel i7-11700 / 약 31.9 GiB |
| GPU / 드라이버 | RTX 3060 Ti, 8192 MiB / 591.86 |
| Python | 기본 3.11.9, 기존 venv 3.12.9 |
| 기존 venv 의존성 | FastAPI 0.135.1, Uvicorn 0.41.0, OpenAI 2.21.0, HTTPX 0.28.1, python-dotenv 1.2.2, Redis 7.4.0, Pydantic 2.12.5 |
| pytest | 기본 Python과 기존 venv 모두 미설치; 저장소 테스트도 없음 |
| 서비스 | 기본 로컬 Redis 6379 연결/PING 성공; 8000/8001 수신 없음 |

문서의 i7 / RAM 64 GB / RTX 4070 Ti는 제품 기준 장비다. 현재 PC 실측과 일치하지 않으며, 이 점검은 모델 적합성이나 속도 검증이 아니다. 모델 다운로드와 GPU 실행은 수행하지 않았다.

실행한 주요 명령과 결과:

| 명령 | 결과 |
|---|---|
| `git status --short --branch` | 기존 Phase 00 브랜치, 미추적 문서 확인 |
| `git ls-remote --symref origin HEAD` | 기본 브랜치 main 및 기준 커밋 확인 |
| `git ls-remote --heads origin` | 공개된 원격 branch 목록에서 main 확인 |
| `git fetch origin` | 성공 |
| `git rev-list --left-right --count HEAD...origin/main` | `0 0` |
| `git diff --exit-code HEAD origin/main` | exit 0, 차이 없음 |
| `git ls-remote https://github.com/Newrred/heroine.git HEAD` | 위 레거시 커밋 확인 |
| `python -m pytest -q` | exit 1, No module named pytest |
| `./venv/Scripts/python.exe -m pytest -q` | exit 1, No module named pytest |
| `python -m compileall app` | exit 0 |
| `./venv/Scripts/python.exe -m compileall app` | exit 0 |
| `nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv,noheader` | 위 GPU/메모리/드라이버 확인 |

추가로 PowerShell here-string을 `./venv/Scripts/python.exe -`에 전달하여 ZIP checksum/파일 바이트 대조, 패키지 버전 조회, UTF-8 검사, 포트 검사, 앱 import/Redis PING 및 TestClient smoke를 실행했다. `.env` 읽기는 일회성 프로세스에서 `PYTHON_DOTENV_DISABLED=1`로 비활성화하고, 로컬 테스트 설정과 Comfy OFF를 명시했다.

격리된 smoke 결과:

- 실제 모델 대신 고정 응답 fake LLM, Redis 대신 메모리 fake session store를 주입했다.
- `/api/health`: 200 및 `{"status":"ok"}`.
- 빈 `message`: 422, 저장 횟수 0.
- 정상 합성 메시지: 200, 저장 횟수 1, `affection_total=1`.
- Comfy OFF: `comfy_status=disabled`, `image_source=none`, `image_url=null`.
- `/api/live`, `/api/ready`: 각각 404. 아직 구현되지 않은 것이 현재 기준선이다.
- 실제 LLM 요청, 영속 세션 쓰기, 외부 배포는 수행하지 않았다. 이 검사는 Uvicorn/브라우저 종단 간 검증이나 저장된 pytest suite를 대신하지 않는다.

실패 기록: pytest 부재는 기존 환경 문제다. 초기 파일 검사도 손상된 `app.js`의 UTF-8 디코딩과 터미널 인코딩 때문에 중단됐으나, 오류를 명시적으로 처리해 다시 검사했다. 첫 smoke의 `image_source=base` 기대는 잘못된 점검 가정이었다. 실제 OFF 분기를 읽어 `none`으로 고친 후 smoke가 통과했다. 제품 코드를 수정해 실패를 숨기지 않았다.

## 문서와 현재 구현의 차이

1. `.env.example`과 `app/config.py`의 LLM 기본 포트 8000이 백엔드와 겹친다. 기본 backend/model/token 설정도 목표 로컬 프로파일과 다르다.
2. `frontend/app.js`는 바이트 2655에서 UTF-8 디코딩이 실패한다. `app.fixed.js`는 UTF-8 정상이며 `index.html`이 실제로 로드한다.
3. `frontend/config.js`는 ignore 목록에 있지만 이미 Git 추적 중이며 임시 터널 주소가 있다. 같은 도메인 예시가 `.env.example`, `app/config.py`에도 있다. 점검 문서에 실제 임시 주소는 복사하지 않았다.
4. `/api/health`는 상수 응답이다. startup은 Redis PING을 수행하지만 LLM 준비 상태는 확인하지 않는다.
5. 기본 검증 오류는 422다. 목표 문서의 400과 구분하여 Phase 00 호환 테스트는 기존 계약을 따른다.
6. 실제 상태는 LLM이 제안한 단일 호감도 delta, Redis TTL, 초기 client history 수용이다. 5개 결정론 수치와 SQLite 영속성은 목표 설계다.

## 다음 작업 준비

다음 구현 파일: [00_BASELINE_STABILIZATION.md](../tasks/00_BASELINE_STABILIZATION.md).

1. 기존 venv를 활용해 개발 의존성과 pytest 설정을 명시하고 fake LLM/session 테스트부터 추가한다. 실제 Redis/GPU/인터넷 없이 성공·실패 경로가 검증되어야 한다.
2. 백엔드 8000 / LLM 8001, 명시적인 로컬 CORS, Comfy OFF 예시를 정리한다. 기존 `.env`는 덮어쓰지 않는다.
3. 정상 `app.fixed.js`를 기준으로 프런트 실행 파일을 하나로 정리하고, 공개 가능한 config 예시 및 정적 표정 fallback을 검증한다.
4. 기존 `/api/health`를 보존하면서 liveness/readiness와 시간 제한을 추가한다.
5. Python CI, 읽기 전용 환경 점검 스크립트, 실행 README를 추가하고 Task 00 수용 조건 전체를 검증한다.

Phase 00은 현재 하드웨어와 모델 선택이 확정되지 않아도 시작 가능하다. Phase 01 모델 평가 전에 기준 PC 또는 8 GB 장비용 별도 프로파일을 확인해야 한다. Phase 00 완료 전에는 다음 단계 완료를 선언하지 않는다.

이번 준비에 필요한 데이터 migration이나 로컬 설정 변경은 없다. 준비 변경을 검토할 때 미추적 문서는 일반 `git diff`에 나타나지 않는 점에 유의한다.
