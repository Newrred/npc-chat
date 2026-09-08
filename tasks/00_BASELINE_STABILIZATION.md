# Task 00 — Baseline Stabilization

Priority: P0  
Allowed scope: repository/config/testability cleanup only  
Do not implement five-stat relationship or durable memory in this task.

Status: **Completed, 2026-09-07 (uncommitted)**. Python tests 34 passed, frontend tests 5 passed, lint/compile/HTTP and browser smoke passed. Completion evidence and limitations: [PROJECT_STATUS](../docs/PROJECT_STATUS.md), section 8. Real-model evaluation remains Task 01.

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
