# Future RTX 4070 Ti Reference Runbook

현재 PC의 실행 방법은 [LOCAL_DEVELOPMENT_RUNBOOK](LOCAL_DEVELOPMENT_RUNBOOK.md)을 따른다. 이 파일의 4070 Ti/14B Q4 프로파일은 추후 검증용이며 현재 개발 기본값이 아니다.

상태: Codex가 실제 PC에서 검증하고 명령을 조정해야 하는 기준 절차.

2026-09-07: Phase 00 실행/테스트 절차는 [README](../README.md)에 반영됐다. 현재 작업 PC는 RTX 3060 Ti 8 GB / RAM 약 32 GB다. 아래 4070 Ti/14B 절차는 실제 모델 검증 전의 기준 계획이며 그대로 검증 완료된 실행 프로파일이 아니다. 기존 `.env`는 덮어쓰지 않는다.

## 1. 목적

목표 기본 실행은 아래처럼 웹앱과 모델 두 프로세스를 유지하고 SQLite를 웹앱의 로컬 파일로 사용한다. Phase 01에서 웹 제공/실행기를 통합하고 Phase 03에서 Redis 전환 게이트를 통과한다.

```text
llama.cpp server : 127.0.0.1:8001
FastAPI web app  : 127.0.0.1:8000 (static frontend + /api, one instance/worker)
SQLite           : local data file (Phase 03)
Redis            : transitional dependency until Phase 03; optional afterward
```

초기 단계에서는 ComfyUI를 실행하지 않는다.

현재 Phase 00 실행 방법은 README의 별도 프런트 5500/Redis 구조다. 이 런북의 아래 수동 명령은 전환기 참고이며 통합 스크립트가 이미 구현됐다는 뜻이 아니다. 별도 정적 호스팅은 목표 기본 실행의 필수 요소가 아니다.

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

Phase 03 완료 전의 전환기용 절차다. SQLite·동시성·중복 요청·재시작 검증 후에는 기본 `start-local`/`doctor`/readiness가 Redis 없이 동작해야 한다. 기존 데이터나 공유 Redis 프로세스를 자동 삭제/중지하지 않는다.

Docker 사용 시 Redis만 container로 실행할 수 있다.

```powershell
docker run --name npc-chat-redis `
  -p 127.0.0.1:6379:6379 `
  -v npc_chat_redis_data:/data `
  -d redis:7-alpine redis-server --appendonly yes
```

Phase 01 실행기는 기존 Redis를 확인하거나 문서화된 프로젝트 전용 서비스만 관리한다. 필요하면 Compose 또는 동등한 도구를 사용하되 Docker를 기본 앱/모델 실행의 필수 조건으로 새로 추가하지 않는다.

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
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
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

현재 Phase 00의 수동 실행 순서:

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

Phase 01 통합 실행기의 필수 목표:

- `start-local.ps1`: 설정/포트/중복 기동 확인 → 전환기 Redis 확인 → 모델 준비 확인 → 단일 worker 웹앱 시작 → 같은 origin의 화면/API 안내.
- `stop-local.ps1`: 자신이 시작한 웹앱과 모델만 종료. 기존 공유 프로세스는 유지한다. PID 재사용까지 고려한 소유권 확인, 반복 호출, 일부 기동 실패 정리가 필요하다.
- Phase 03 전환 후에는 Redis 확인을 SQLite 준비 확인으로 대체한다. 기본 실행은 두 핵심 프로세스이며 데이터 파일은 유지한다.
- Phase 05에서는 이 순서와 준비 확인을 서비스 관리자에 연결해 재시작·로그·장애 복구를 관리한다. HTTPS/인증 진입 계층은 별도 배포 구성이다.

## 9. Main-PC coexistence policy

초기에는 Windows 부팅 시 자동 실행하지 않는다. 명시적인 start/stop script로 운영한다.

- 게임, 3D, 영상, Stable Diffusion 작업 전 llama.cpp를 종료한다.
- LLM startup script는 free VRAM을 검사하고 부족하면 시작을 거부하거나 경고한다.
- inference 중 GPU OOM이 발생하면 백엔드는 상태를 변경하지 않고 503을 반환한다.
- 메인 PC 작업 중 클라우드 fallback은 Phase 06 이전에 구현하지 않는다.

Phase 01에서 필수 구현/완성할 scripts (doctor는 Phase 00에 구현됨):

```text
scripts/doctor.ps1
scripts/start-llm.ps1
scripts/stop-llm.ps1
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
