# Task 03 — Durable Persistence and Memory

Status: implemented and validated 2026-09-07. See docs/PHASE02_03_COMPLETION.md and docs/PROJECT_STATUS.md for evidence and limitations.

Prerequisite: Task 02 relationship domain and tests.

## Objective

Persist relationship, flags, turns, summary, and selected memories independently of Redis TTL and make turn processing idempotent.

Updated 2026-09-07: after persistence and concurrency validation, make SQLite plus in-process coordination the default runtime. One web app instance/worker plus the model process is the target. Redis stays active until the replacement passes all gates below; disabling its default use does not delete legacy data.

## Required work

### Database foundation

- Add SQLAlchemy 2.x and Alembic.
- Default local database: SQLite file under an ignored runtime data directory.
- Define a repository protocol so PostgreSQL can replace SQLite later.
- Add backup/export documentation before destructive migration.

### Minimum tables

- profiles
- character_relationships
- turns or relationship_events
- memories
- processed client turns/idempotency records

Use normalized columns for five scores. JSON may be used for small metadata but not as a substitute for all queryable state.

### Transaction boundary

One successful chat turn must atomically persist:

- user/assistant turn
- canonical expression and interaction
- relationship delta and resulting totals
- flags
- accepted memory candidates
- rolling summary when updated
- processed `client_turn_id`

If commit fails, return an error and leave no partial mutation.

### Single-worker coordination and Redis transition

- Store profile/session mappings, recent turns and all durable state in SQLite. Use a local disk file, not a network-shared DB file.
- Serialize turns for the same profile/character even across different browser sessions. Use bounded-lifetime in-process locks and a bounded global inference queue with one active generation.
- Do not hold a SQLite write transaction while awaiting the model. Commit state and the processed-turn record together in a short transaction.
- Enforce duplicate protection with a DB uniqueness constraint scoped to the durable owner/character and `client_turn_id`. Same ID and payload reuses the committed response; changed payload under the same ID is rejected.
- Include the minimum browser turn-ID generation/preservation needed to use this contract before cutover. Full retry/offline UX remains Task 04; do not enable retries that generate a fresh ID for the same turn.
- Cover concurrent duplicate submissions, timeouts/cancellation and lost responses after commit. Uncommitted queued work may be lost on restart; retry must use the same client turn ID and cannot apply committed state twice.
- Configure finite queue length/wait time and explicit full/timeout responses. Inactive users must not leave an unbounded number of locks/caches in memory.
- Update the managed launcher to enforce one app instance/worker. Multiple workers/replicas require a separate shared-coordination design and tests before becoming supported.
- Keep current Redis behavior during implementation/migration. Only after the tests below pass, switch the default startup/config/doctor/readiness to SQLite+LLM, with no Redis service required.
- Redis can remain an explicit optional adapter for legacy migration or future shared coordination. Do not silently fall back between stores on an outage and do not build an unneeded distributed mode in this task.

### Memory v1

Implement:

- recent turn window
- rolling summary with a strict size budget
- memory candidates of limited kinds
- normalization and duplicate detection
- importance/confidence bounds
- retrieval of a small relevant set for prompt construction

Do not implement embeddings/vector DB in this task. Deterministic lexical/recency/importance selection is sufficient.

### Legacy migration

- Migrate existing Redis affection/flags/memory/history when present.
- Migration must be idempotent.
- Preserve source until durable commit succeeds.
- Provide a dry-run or clear log summary.
- Gate the cutover on a documented backup/restore procedure. Do not delete source Redis records when disabling the dependency; do not roll back to stale Redis after SQLite has accepted new turns without an explicit restore/migration plan.

## Required tests

- fresh profile creation
- restart persistence
- Redis expiry independence
- duplicate `client_turn_id`
- concurrent duplicate turn, same ID/different payload rejection, response lost after commit then retry
- same profile/character via different sessions, queue saturation, cancellation/timeout without partial state
- bounded lock/cache cleanup and rejection of unsupported managed multi-worker startup
- transaction rollback at injected failure points
- legacy migration once and repeat
- memory dedupe and size cap
- profile reset/delete behavior at repository layer
- Redis-free normal startup, chat, restart and readiness; SQLite unavailable readiness failure
- optional Redis disabled is not a readiness failure and no Redis connection is attempted in default mode

## Acceptance criteria

- relationship survives backend and Redis restart.
- same client turn never changes state twice.
- all persistence tests use temporary isolated databases.
- Alembic upgrade from empty DB succeeds.
- documented backup/restore procedure exists.
- All persistence/concurrency/idempotency gates pass **before** Redis is removed from the default dependencies.
- `start-local`, `stop-local`, `doctor`, configuration, dependencies and README agree on the Redis-free one-worker default. Optional adapters must not make Redis mandatory for a clean default installation.
