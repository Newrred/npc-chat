# Task 01 — LLM Contract and Local Runtime

Prerequisite: Task 00 accepted.

Implemented and locally validated 2026-09-07 on the user-confirmed RTX 3060 Ti profile. See docs/PROJECT_STATUS.md section 10 for 97 offline tests, 20/20 real-model cases, lifecycle checks and limitations. Deliver the following in small ordered changes: (1) same-origin web hosting, (2) unified lifecycle with the model launch helpers, (3) remaining canonical contract/runtime evaluation. Redis remains required until Task 03 passes its replacement gate.

## Objective

Create one canonical LLM decision contract and verify the existing 9B Q6_K GGUF profile on the RTX 3060 Ti 8 GB desktop without coupling CI to the real model.

Also simplify local deployment to one web entry point and one start/stop entry point, while keeping inference in a separate process and preserving the current Redis data.

## Required work

### Same-origin web application — first implementation slice

- Serve the existing static HTML/CSS/JavaScript and face assets from FastAPI; open the web app at `127.0.0.1:8000`.
- Use relative `/api` URLs by default. Keep separate static hosting as an explicit optional mode with exact CORS origins; no mandatory frontend build framework or separate web server.
- Keep `/api/chat`, `/api/image/status`, live/ready and API 404/error behavior intact. Static fallback must not turn unknown `/api` paths into an HTML success response.
- Serve only the frontend directory. `.env`, SQLite, model files, logs and repository metadata must not be reachable through static paths or traversal.
- Keep source modules separate; serving frontend and API together must not merge domain responsibilities.
- Add real HTTP/browser smoke for page, face asset, same-origin chat and failed requests; test unknown API/static paths and traversal rejection.

### Canonical domain schema

- Centralize FaceType, InternalEmotion, InteractionType.
- Normalize legacy `shy smile` to `shy_smile` at boundaries.
- Implement Pydantic models matching `docs/API_AND_DATA_CONTRACTS.md`.
- Permit reply length 1..80 characters.
- Reject extra keys and out-of-range intensity/memory values.
- Keep a compatibility adapter for the old flat LLM output during migration if required.

### LLM adapter

- Keep OpenAI-compatible transport.
- Represent backend capability explicitly: schema/guided JSON supported or fallback text parsing.
- Disable thinking through backend-appropriate options when supported.
- Use bounded retries and classify transport vs parse failures.
- Avoid app-global hard coupling that prevents fake injection.
- Keep model id, URL, token cap, timeout, temperature, and backend in config.

### Prompt/output

- Update character prompt to request only canonical LLM decision fields.
- Do not ask the model for relationship totals or final deltas.
- Add flag allowlist to character config; unknown flags are discarded and logged as structured diagnostics.
- Reduce completion token default to 256 or lower only after measured schema success.

### Local scripts

Add or complete:

```text
scripts/start-llm.ps1
scripts/stop-llm.ps1
scripts/start-local.ps1
scripts/stop-local.ps1
scripts/doctor.ps1
scripts/benchmark-local.ps1
```

Requirements:

- model path is an argument or environment variable
- bind to 127.0.0.1:8001
- context default 2048 on this PC (user-directed change 2026-09-07); 4096 and 14B Q4 are deferred profiles
- parallel default 1
- free VRAM check before start
- no auto-download and no model file in repository
- print the exact effective command

`start-local.ps1` / `stop-local.ps1` are **required**, not optional recommendations:

- Reuse the model helpers; do not maintain two different sets of model launch flags. Model settings stay configurable and secrets are redacted from diagnostics.
- In the transitional Redis profile, check an existing Redis or start only a documented project-owned local service. No silent data reset, install or download. Clearly report missing prerequisites.
- Check ports and duplicate instances, start the model, wait with bounded readiness, then start the web app with one worker. Expose one browser URL; a separate frontend process is not needed.
- Track only processes started by this invocation using PID plus verified process identity. On partial failure or stop, clean up only owned processes; never stop an unrelated process merely because its name or port matches.
- Preserve a pre-existing/shared Redis or model process when stopping. Repeated start/stop must be safe and stopping before start must be a no-op or readable result.
- Normal operation is one application instance/worker. Do not enable multiple workers or reload in the managed operating profile. Keep Windows background helpers hidden.
- Test lifecycle success, missing executable/model, port collision, readiness timeout, partial failure cleanup, repeated invocation and preservation of unrelated processes using fake executables/endpoints without a GPU.
- Automatic launch on Windows boot and public hosting remain outside this task; production service supervision is Task 05.

### Evaluation

- Add fake adapter tests.
- Add a real-model evaluation command that is opt-in.
- Record exact GPU/model/llama.cpp/runtime facts in `PROJECT_STATUS`.
- Run at least 20 representative prompts for the first runtime check; the full 50-case suite is Task 04.

## Acceptance criteria

- CI passes without GPU.
- One FastAPI URL serves frontend, assets and API without a separate frontend server; legacy API tests still pass.
- Required unified start/stop scripts pass success and failure-path lifecycle tests; current Redis state is preserved.
- Local launch and README describe the transitional Redis dependency rather than claiming the two-process end state already exists.
- all canonical schema tests pass.
- old and new response handling cannot produce an invalid face value.
- real local profile either passes 20 prompts or is honestly documented as blocked with the exact failure.
- first-pass and retry schema rates are recorded.
- actual VRAM before/peak/after and latency are recorded when real-model run is possible.
- no relationship totals are model-generated in the new contract.

## Non-goals

- persistent five-stat totals
- score balancing
- public deployment
- Comfy generation

Follow-up 2026-09-07: user-reported latency prompted a 4B Q4_K_M full-GPU speed profile. Final 20/20 schema pass and median 1.172s; see PROJECT_STATUS section 11 for configuration, quality limitations, and preserved 9B fallback.
