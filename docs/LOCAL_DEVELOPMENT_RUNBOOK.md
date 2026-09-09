# Current local development runtime

2026-09-08 반복 응답 보완: canonical 모델 요청에도 `NPC_TOP_K`, `NPC_PRESENCE_PENALTY`, `NPC_FREQUENCY_PENALTY`, `NPC_REPETITION_PENALTY`를 전달한다. 현재 값은 20/0.5/0.3/1.08이다. llama.cpp의 요청 필드는 `repeat_penalty`이며 vLLM에는 `repetition_penalty`를 사용한다. 고정 답변 대체나 대화 초기화는 하지 않는다. 합성 반복 회귀 확인: `./venv/Scripts/python.exe scripts/evaluate_short_replies.py --output .runtime/short-replies-check.json`. 실제 모델을 사용하는 선택적 검사이며 개인 DB를 읽거나 쓰지 않는다.

2026-09-07 사용자 요청에 따라 이 PC를 개발 기준으로 사용한다. 4070 Ti/14B Q4는 추후 별도 평가 대상이다.

| 항목 | 현재 테스트 설정 |
|---|---|
| 장비 | i7-11700, RAM 약 32 GB, RTX 3060 Ti 8 GB |
| 모델 | 사용자 비교 테스트: Qwen3.5-9B-Uncensored-HauhauCS-Aggressive-Q4_K_M.gguf, 약 5.24 GiB. 4B 파일/설정 보존 |
| 실행 파일 | 공식 llama.cpp b10830 / CUDA 12.4 Windows x64 |
| 문맥 / 응답 | 9B 시험: 4096 / 최대 256 토큰. 4B 복귀 시 8192 |
| 동시 처리 | 모델 parallel 1, FastAPI 1 worker |
| GPU 층 / batch / ubatch | auto / 128 / 128; 9B는 전체 GPU 적재를 가정하지 않음 |
| 사고 출력 | `--reasoning-budget 0`, `enable_thinking=false` |
| 메모리 검사 | 시작 전 free VRAM 최소 2048 MiB, fit margin 1024 MiB |
| 선택 기능 | ComfyUI OFF; 모델 자동 다운로드 없음 |

VRAM 검사는 출발 조건이지 OOM 방지 보장이 아니다. 다른 앱의 사용량이 변하므로 실행마다 확인한다. 9B Q8 모델은 이번 기본값으로 쓰지 않는다. 현재 Vulkan b8119는 이 모델 로딩 중 `GGML_ASSERT(buffer != nullptr)` 오류가 반복돼 공식 CUDA 빌드로 교체 검증했다. 기존 Winget 설치는 보존한다.

## 최초 준비와 실행

개발 의존성을 설치하고 `.env.example`을 참고해 로컬 `.env`에 실행 파일과 GGUF의 절대 경로를 지정한다. 모델은 저장소 밖에 둔다. 비밀값·실제 PC 경로는 Git에 올리지 않는다.

```dotenv
LLAMA_SERVER_PATH=llama-server.exe
LLAMA_MODEL_PATH=<absolute path to existing GGUF>
LLAMA_CONTEXT=4096
LLAMA_GPU_LAYERS=auto
NPC_MODEL=local-model
NPC_BASE_URL=http://127.0.0.1:8001/v1
NPC_MAX_TOKENS=256
NPC_OUTPUT_CONTRACT=canonical
NPC_JSON_MODE=schema
```

설치한 빌드는 `--fit`, `--fit-target`, `--reasoning-budget`, `--log-disable`을 지원해야 한다. 실행기는 시작 전에 확인하며 기존 시스템 설치를 자동 업데이트하지 않는다. CUDA 빌드와 CUDA DLL은 [공식 b10830 배포](https://github.com/ggml-org/llama.cpp/releases/tag/b10830)에서 받았고 GitHub asset SHA-256과 대조했다. 현재 PC의 전용 실행 파일은 무시된 `.runtime` 아래에 있으며 `.env`가 이를 가리킨다.

```powershell
./venv/Scripts/python.exe -m pip install -r requirements-dev.txt
./scripts/doctor.ps1
# SQLite는 시작 시 준비되며 Redis 서비스는 필요 없음:
./scripts/start-local.ps1
# http://127.0.0.1:8000
./scripts/stop-local.ps1
```

기본 저장소는 SQLite이며 Redis 연결을 시도하지 않는다. 이전/백업/복구는 [DB 운영](DATABASE_OPERATIONS.md)을 따른다.

```powershell
./scripts/start-llm.ps1
./scripts/benchmark-local.ps1
./scripts/stop-llm.ps1
```

인자는 공통 Python 실행기로 전달한다. 9B 시험 예: `--model <path> --context 4096 --gpu-layers auto --max-tokens 256`. 모델/API alias는 `NPC_MODEL`로 통일한다. 이미 실행 중이면 같은 프로세스를 재사용하므로 설정 변경은 종료 후 다시 시작한다. 모델을 자동 교체하지 않는다. 설정 미지정 fallback은 2048이며 실제 프로파일은 개발 `.env`와 별도 배포 env에 명시한다. 모델과 웹의 alias/문맥 설정을 함께 변경해야 한다. 4B 복귀 시 기존 파일/alias와 context 8192/GPU all을 사용한다.

## 프로세스 소유권과 복구

`.runtime/processes.json`에 PID, 생성 시간, 실행 파일, 실행 인자를 기록한다. 종료할 때 전부 대조한다. 포트나 이름만 일치하는 다른 프로세스는 종료하지 않는다. OS 파일 잠금으로 실행기 중복 진입을 차단한다. 포트 충돌·준비 시간 초과·부분 기동 실패 시 해당 호출이 시작한 프로세스만 정리한다. start/stop은 반복 호출할 수 있다.

Windows 가상환경 실행기는 등록된 `venv\Scripts\python.exe` 아래에 실제 시스템 Python 자식을 만들 수 있다. 종료기는 먼저 등록된 부모 신원을 검증하고, 그 시점에 확인한 자식 트리도 각각의 생성 시간·실행 파일·인자와 다시 대조한 뒤 함께 종료한다. `stop-local.ps1`은 관리자·웹·프로젝트 소유 모델을 모두 종료한다. `stop-public-test.ps1`은 외부 공개 주소만 닫기 위한 명령이라 tunnel만 종료하고 로컬 웹·모델은 유지한다. 완전히 끄려면 public stop 후 local stop을 실행한다.

외부에서 시작한 모델을 쓸 때는 `start-local.ps1 --reuse-llm`을 명시한다. 모델 목록에 설정 alias가 있는지 확인하지만 이 외부 프로세스의 문맥/GPU 설정까지 검증하지는 않는다. 외부 모델은 registry에 등록하거나 종료하지 않는다. `start-llm`으로 등록한 프로젝트 모델은 `stop-local`도 종료한다. 웹앱이 실행 중이면 `stop-llm`은 순서 보호를 위해 거절하며 `stop-local`을 사용한다.

기동 로그는 `.runtime/llm.log`, `.runtime/web.log`다. 모델의 상세 로그와 HTTP access log는 기본 비활성이다. 강제 종료/PC 재부팅 이후 stale PID는 다른 프로세스와 동일인으로 취급하지 않는다. 개발 실행기는 Windows 서비스/부팅 자동 시작/공개 배포용 supervisor를 대체하지 않는다.

## 응답 계약과 평가

기본 `canonical`은 Pydantic 검증을 사용한다. `schema`는 llama.cpp의 schema response format, `guided_json`은 이를 지원하는 vLLM 버전용이다. 서버가 기능을 지원하지 않으면 명시적으로 `json` 또는 `text`를 선택한다. 인증 오류나 schema 지원 오류에 자동으로 다른 backend/계약을 쓰지 않는다. 전송 및 파싱 시도는 합쳐 최대 3회다. 설정 오류(400/401 등)는 바로 실패한다.

`legacy`는 출력 모양만 호환하며 모델의 delta는 버린다. canonical 분류를 규칙 1.0으로 계산해 SQLite 트랜잭션에 저장한다. 최근 이력 12개를 보관하고 전부 모델 문맥 후보로 사용한다. 실제 토큰 예산을 넘으면 오래된 인용·선택 기억·오래된 대화 쌍 순으로 줄인다. 고정 캐릭터와 현재 입력을 조용히 자르지 않으며 필수 입력이 한도를 넘으면 422로 수정을 안내한다. 출력 256+여유 64를 예약하므로 8192 프로파일의 입력 예산은 7872토큰이다.

단일 worker, 활성 추론 1개/대기 8개/최대 대기 30초를 사용한다. commit 전 취소는 상태를 바꾸지 않으며 응답 유실은 같은 client_turn_id로 다시 확인한다. 실제 프로필/turn이 남는 DB는 .runtime/data에 있으므로 필요한 시점에 백업한다.

`benchmark-local`은 실제 8001 모델에 합성 사례 20개를 순서대로 보낸다. Redis/대화 데이터에 쓰지 않으며 출력은 무시된 `artifacts/benchmarks/local-3060ti.json`에 저장한다. 원문 대신 성공 여부·시도 수·토큰·지연·GPU 측정만 남긴다. `--limit`은 진단용으로 20 미만 실행할 수 있지만 전체 평가로 계산하지 않는다. GPU 값은 장치 전체 사용량이며 타 앱을 포함한다. before/after는 모델 로딩 전후가 아니라 평가 시작/종료 시점이다. 모델 로딩 직전 값과 빌드 정보는 PROJECT_STATUS에 함께 기록한다.

정적 프런트 별도 호스팅이 필요하면 `frontend/config.js`의 URL과 정확한 CORS origin을 지정한다. 기본 개발에는 별도 프런트 프로세스가 없다. 인터넷 공개는 Phase 05의 인증·HTTPS·요청 제한·백업 검증 후 진행한다.

## 속도 우선 프로파일 개정 이력 (2026-09-07, 현재 9B 시험 이전)

기존 9B Q6_K / GPU 12층 프로파일은 중앙값 약 19.6초로 느려, 같은 제작자의 [4B Q4_K_M 모델](https://huggingface.co/HauhauCS/Qwen3.5-4B-Uncensored-HauhauCS-Aggressive)을 별도 다운로드해 비교했다. 현재 작은 모델을 기본으로 사용하며 기존 9B GGUF는 보존했다. 모델 원본 revision 및 SHA-256, 최종 속도와 VRAM은 PROJECT_STATUS section 11에 기록한다.

`all`은 4B 모델용 설정이다. 9B로 되돌릴 때는 GPU layers를 12로 함께 바꿔야 한다. CLI 자체의 환경변수 미지정 fallback은 안전하게 기존 12를 유지한다. 현재 PC `.env`와 공유 `.env.example`은 작은 모델에 맞춘다. 기존 PC의 모델 관련 설정만 `.runtime/profile-before-speed.json`에 보관했으며 인증값과 Redis 설정은 변경하지 않았다.

짧은 합성 사례의 속도/형식 검증이며, 작은 모델은 말투 일관성과 문맥 정확도가 약할 수 있다. 별도 3턴 점검에서 존댓말 혼용 및 이전 발화에 없던 내용을 덧붙이는 사례를 관찰했다. 기본 반말 지침을 프롬프트 끝에 다시 명시했지만 이 문제가 해결됐다고 판정하지 않는다. 장기 대화 품질 평가는 Phase 04에서 수행한다.


## Phase 04 — 오류 처리와 문맥 설정 (2026-09-07)

화면의 오류/대기 안내는 마지막 NPC 대사와 분리된다. 실패 후에는 같은 메시지 다시 보내기로 확인한다. 새로고침해도 turn ID와 프로필이 유지된다. 자동 재전송은 하지 않는다. 422 입력 오류는 내용 수정, 없는 프로필은 새 대화 시작으로 복구한다. 이 버튼은 기존 서버 기록을 삭제하지 않는다.

로컬 기본 설정에 `NPC_TOKEN_COUNT_MODE=llama_cpp`를 사용한다. 현재 실행 모델의 `/apply-template`와 `/tokenize`로 출력 여유를 제외한 문맥 한도를 확인한다. 긴 현재 입력을 몰래 자르지 않고 422로 안내한다. 다른 제공자용 `estimate`는 근사값이므로 해당 제공자의 tokenizer 검증이 별도로 필요하다.

개발 정보에는 관계값/변화/이유 코드/지연이 표시된다. frontend/config.js의 `NPC_RELATIONSHIP_DISPLAY`는 debug(기본 숨김 토글) 또는 hidden이다. `NPC_REQUEST_TIMEOUT_MS`는 기본 420000이며 timeout 후에도 같은 ID로 확인한다.

단순한 사용자 취향 정정은 최신 원문으로 교체한다. 명시적 취향 회상은 저장한 발화를 직접 인용해 모델의 긍정/부정 뒤집기를 방지한다. 복잡한 기억과 말투 품질은 아직 한계가 있다. 구현/검증은 PHASE04_IMPLEMENTATION.md, 실측은 PHASE04_EVALUATION.md 문서를 참고한다.
