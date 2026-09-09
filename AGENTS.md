# AGENTS.md — NPC Chat Repository Instructions

## Mission

기존 `npc-chat` 프로토타입을 로컬 우선 캐릭터 챗봇으로 안정화한다. 사용자는 짧은 한국어 대화를 주고받으며, 캐릭터의 표정·감정 태그와 5개 관계 수치 변화를 경험한다. 현재 구현을 보존하면서 테스트 가능한 작은 단위로 발전시킨다.

## Source-of-truth order

1. 이 `AGENTS.md`
2. `docs/PRODUCT_AND_TECHNICAL_DIRECTION.md`
3. `docs/PROJECT_STATUS.md`
4. `docs/TARGET_ARCHITECTURE.md`
5. `docs/API_AND_DATA_CONTRACTS.md`
6. `docs/IMPLEMENTATION_PLAN.md`
7. 현재 지정된 `tasks/*.md`
8. 기존 `README.md`

## Baseline

- Primary repository: `Newrred/npc-chat`
- Reviewed baseline: `main@a9f6205045648e8889a4dbf4190de65e330caaed`
- Legacy frontend repository: `Newrred/heroine@f722ae87a82775e3cf12c0f188a71f5165c5686e`
- `heroine` is not a second product. Treat it as a historical deployment copy.

If repository HEAD differs from the reviewed baseline:

1. Inspect the actual diff.
2. Update `docs/PROJECT_STATUS.md` before changing code.
3. Preserve newer working behavior unless it conflicts with a confirmed decision.
4. Do not reset, force-push, or discard user changes.

## Confirmed technical decisions

- 2026-09-09 local inspector: explicit NPC_DEBUG_TRACE=1 captures private request/output diagnostics in a separate local sidecar, 1 hour/100 executions, default OFF. Current testing explicitly enabled. Never expose inspector on public app or commit traces. See docs/LOCAL_INSPECTOR.md.

- 2026-09-08 memory pipeline: recent model history comes from committed turns, not the 6-turn compatibility cache. Deterministic source-backed views derive explicit name/preferred address and attributed recommendations/proposals/cancellations; keep them separate from user memory candidates. Reserve compact evidence before old dialogue. No new model call/schema migration. Actor statements are not verified real-world completion. See docs/MEMORY_PIPELINE.md.

- 2026-09-08 user approved same-model two-stage generation: reply-only JSON, then metadata analyzing the frozen final reply, then one atomic commit. Current trial and env examples use NPC_GENERATION_MODE=two_stage; absent setting or explicit single_pass preserves rollback. Keep one model process and one queue; no early reply streaming. Metadata retries must not regenerate the successful reply. See docs/TWO_STAGE_GENERATION.md.

- Keep FastAPI as the backend.
- Keep the frontend deployable as static HTML/CSS/JavaScript.
- Default deployment target: one FastAPI web app serving both static frontend and `/api`, plus a separate model process. Keep modules separate inside the app; separate frontend hosting is optional.
- Implement the simplification in order: same-origin frontend/API, unified start/stop, SQLite durability and concurrency/idempotency validation, then remove Redis from the default runtime.
- The Redis-free target is one app instance with one worker. Do not scale to multiple workers/replicas without shared coordination and persistence validation.
- Keep LLM inference as a separate OpenAI-compatible process.
- Primary local reference runtime is `llama.cpp`; vLLM support remains optional.
- Current development target is the user's Intel i7-11700 / approximately 32 GB RAM / RTX 3060 Ti 8 GB desktop (confirmed 2026-09-07).
- Current user trial (2026-09-08): Qwen3.5-9B-Uncensored-HauhauCS-Aggressive Q4_K_M, context 4096, GPU layers auto, output 256, parallelism 1, batch/ubatch 128, thinking disabled. This is a heavier-model trial, not a proven quality winner. Preserve the faster 4B Q4_K_M / context 8192 / GPU all profile for rollback and the existing 9B Q6_K for comparison. 14B Q4 on 4070 Ti is deferred.
- Retained history is selected by token budget instead of a fixed four-message prompt window. Tune from measured semantic quality, schema success, and latency; do not equate fewer exact duplicates with coherent dialogue.
- Current local prompt budgeting uses NPC_TOKEN_COUNT_MODE=llama_cpp (apply-template/tokenize), reserving output plus 64 tokens. Never silently truncate the current user message or fall back to estimated counting on an outage.
- Static expression assets are the default. ComfyUI remains optional and OFF in the core milestone.
- The backend is authoritative for history, relationship state, flags, and memory.
- Relationship dimensions are `affection`, `trust`, `comfort`, `interest`, and `irritation`.
- The model classifies the interaction; deterministic server code computes relationship deltas.
- Redis may hold ephemeral session/lock/cache state. Durable relationship and memory state must not depend on an expiring Redis key.
- Task 03 migration, queue, duplicate-turn, restart and rollback gates passed on 2026-09-07. SQLite is now the default durable store; Redis is optional for legacy import/export only. Never silently fall back or delete legacy source during cutover. See docs/DATABASE_OPERATIONS.md.
- Do not expose the llama.cpp port directly to the internet.
- User approved a temporary domain-free public test link on 2026-09-07. Quick Tunnel is allowed for this temporary test only; keep its URL in ignored local runtime files, never in committed configuration. Fixed-domain requirements remain for ongoing production operation.
- 2026-09-07 user decision: default remote deployment is a public link with automatic signed guest cookies, no email/login steps. Keep Cloudflare Access as an optional mode. Enforce server-side visitor and durable daily quotas; cookie reset must not reset the global daily cap. A guest identifies a browser, not a verified person.

## Engineering constraints

- Prefer incremental refactoring over a rewrite.
- Keep each PR/commit phase-scoped and reversible.
- Preserve current API behavior until a compatibility path and tests exist.
- Centralize enums and schemas; do not duplicate face/emotion lists across modules.
- Use Pydantic for external and LLM output validation.
- Add dependency injection or test seams before adding complex behavior.
- All score updates must be bounded, deterministic, idempotent, and unit-tested.
- Never trust `history`, score totals, flags, or memory supplied by the browser.
- Add a client turn id before allowing retries that can mutate state twice.
- Do not log full private conversation content by default.
- Do not add a cloud dependency to complete a local milestone.

## Security and repository hygiene

Never commit:

- `.env` or local config with credentials
- `*.gguf`, model directories, generated images, or caches
- `trycloudflare.com` temporary URLs
- API keys, tunnel tokens, Redis credentials, or private user data

Required safeguards before public exposure:

- exact CORS origins
- selected access boundary: signed guest cookies for the approved public-link mode, or Cloudflare Access for the optional restricted mode
- request and concurrency limits
- structured error responses
- fixed/named tunnel or equivalent reverse proxy
- backend readiness checks
- content retention policy and backup behavior

## Required workflow for every task

1. Read this file and the task document.
2. Inspect actual code and current git status.
3. Record baseline commands and failures before editing.
4. Make the smallest coherent change that satisfies the task.
5. Add or update automated tests.
6. Run relevant test, lint, and smoke commands.
7. Update `docs/PROJECT_STATUS.md` and `docs/DECISION_LOG.md` when facts or decisions change.
8. Report modified files, behavior changes, commands run, results, known limitations, and the next unblocked task.

Do not silently skip a failing test. Distinguish failures introduced by the change from pre-existing or environment-dependent failures.

## Default verification commands

For dialogue-quality experiments, maintain `docs/EXPERIMENT_LINEAGE.md`: record the experiment ID and parent, hypothesis, fixed and changed variables, evidence links, failures/limitations, adoption decision, and the next question. Add the planned entry before running the experiment and update it when complete. Preserve rejected variants and synthetic results; never include private conversations or secrets. Keep format success, memory retrieval, dialogue quality, and latency separate.

Discover and use the repository's actual tooling. Until a project-specific command replaces these, the expected baseline is:

```bash
python -m pytest -q
python -m compileall app
```

For a local smoke test:

```bash
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Then verify liveness/readiness and one chat request with a fake or real OpenAI-compatible LLM endpoint. Do not make real-model tests mandatory in CI.

## Definition of done

A task is complete only when:

- acceptance criteria in its task file pass;
- tests cover both success and failure paths;
- no secret or machine-specific path is committed;
- old state can be migrated or safely ignored without data corruption;
- user-visible behavior and configuration are documented;
- `docs/PROJECT_STATUS.md` reflects the actual repository state;
- the final report includes exact commands and results.

## Final report format

```text
Scope completed
Files changed
Behavior changed
Tests/commands run and results
Migration/configuration required
Known limitations
Recommended next task
```
