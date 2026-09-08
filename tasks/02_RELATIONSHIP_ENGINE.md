# Task 02 — Five-Stat Relationship Engine

Status: implemented and validated 2026-09-07. See docs/PHASE02_03_COMPLETION.md and docs/PROJECT_STATUS.md for evidence and limitations.

Prerequisite: canonical LLM decision contract from Task 01.

## Objective

Replace model-controlled single affection delta with a deterministic five-dimension relationship system while maintaining a safe migration path.

## Required work

### Domain model

Implement:

```text
RelationshipState
RelationshipDelta
RelationshipResult
```

Dimensions:

```text
affection
trust
comfort
interest
irritation
```

- totals 0..100
- per-turn deltas -3..+3
- character-config initial values
- validation at every persistence/API boundary

### Engine

- Implement the base matrix and modifiers in `API_AND_DATA_CONTRACTS.md`.
- Input: current state, canonical interaction, recent successful interaction events.
- Output: delta, next state, reason codes.
- No randomness.
- Repeated invocation with identical input returns identical result.
- Engine has no network or database side effects.

### Chat flow

- Call LLM for decision.
- Call relationship engine after successful validation.
- Apply changes only inside the successful turn transaction boundary.
- On LLM/parse/persistence failure, do not mutate state.
- Add `client_turn_id` support or temporary server idempotency seam if Task 03 transaction storage is not yet present.

### Migration compatibility

- Map legacy `affection_total` to `affection`.
- Use character defaults for other dimensions.
- Continue returning legacy `affection_total`/`affection_delta` while old frontend requires them.
- Mark compatibility fields deprecated in docs.

### Prompt

- Inject all five current values and a compact relationship stage/summary as trusted server context.
- Do not inject raw reason codes unless useful.
- Do not allow user text to masquerade as state.

### Frontend debug

- Show values and per-turn deltas behind a debug toggle or development panel.
- Do not finalize whether all scores are permanently visible to users.

## Required tests

- every base interaction type
- intensity 0..3
- clamp at lower/upper totals
- teasing low/high comfort
- irritation >=70 modifier
- repeated positive interaction attenuation
- legacy migration
- identical input determinism
- failed turn leaves state unchanged
- duplicate application prevention seam

## Acceptance criteria

- no code path accepts LLM-provided final delta as authoritative.
- all five totals are returned in the new API shape.
- legacy frontend still works through compatibility fields.
- relationship engine has complete unit coverage for documented rules.
- `PROJECT_STATUS` contains the implemented rule version.
