# Task 04 — Frontend Reliability and Model Evaluation

Status: implementation and measured evaluation completed 2026-09-07. See docs/PHASE04_IMPLEMENTATION.md and docs/PHASE04_EVALUATION.md. Remaining semantic quality issues are explicitly recorded; this is not public-release approval.

Prerequisite: durable chat flow.

## Objective

Make the static frontend reliable for daily personal use and produce measured evidence for the chosen local model.

## Required work

### Backend-authoritative client

- Stop sending history or state as authoritative request data.
- Generate and retain `client_turn_id` for retries.
- Build on Task 03's minimum turn-ID contract; do not defer safe duplicate protection until this UX task. Preserve Task 01's same-origin `/api` default.
- Prevent double submission while a turn is active.
- Reuse the same id on network retry; generate a new id only for a new user message.

### UX states

Implement explicit states:

```text
idle
sending
waiting_for_model
success
retryable_error
non_retryable_error
offline
```

- Never show a fabricated character response on failure.
- Show static face immediately after a valid response.
- Comfy status remains secondary.
- Keep a hidden/debug panel for raw emotion, reason codes, latency, and five score deltas.

### Expression assets

- Validate all canonical face files at build/test time.
- Keep fallback chain to neutral.
- Remove obsolete spelling aliases from user-facing output while accepting legacy input.

### Relationship UI

Implement a configuration-controlled choice:

- debug-only exact values, default for development
- optional user-facing bars/labels later

Do not make hidden exact score visibility a permanent product decision without updating `DECISION_LOG`.

### Evaluation suite

- Expand to at least 50 representative Korean cases.
- Run the exact chosen model profile.
- Record:
  - schema first-pass/retry rates
  - latency p50/p95
  - output length distribution
  - face/emotion distribution
  - VRAM and OOM behavior
  - manual naturalness scores
  - failure examples
- Compare at least one smaller or alternative model only if readily available; do not auto-download large models without user direction.

### Main-PC operation

- Verify stop/start scripts.
- Confirm behavior while common GPU applications are open.
- Document the condition that should block model startup based on free VRAM.

## Acceptance criteria

- duplicate clicks/retries do not duplicate state.
- offline LLM produces clear retryable UI and no score change.
- all canonical face assets have a valid fallback.
- 50-case evaluation report is stored in docs/artifacts without private conversations.
- quality and latency gates in `TEST_AND_ACCEPTANCE_PLAN` are evaluated with measured results.
