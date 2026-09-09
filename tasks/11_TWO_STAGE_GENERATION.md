# Task 11 — Same-model two-stage generation

User approved 2026-09-08: use the same model sequentially for reply and metadata. Preserve one model process and single app queue. First generate reply-only JSON without fixed examples; then classify the user interaction and the frozen final assistant reply into canonical metadata. Metadata cannot rewrite the reply. Grounded recall correction, when applicable, occurs before metadata so face/emotion see the displayed reply.

Acceptance: compatible canonical API; one atomic commit after both stages; replay cannot generate twice; each stage has bounded retries, metadata retries never regenerate reply; model/tokenizer/DB failures cannot leave partial history/relationship/memory; original user input and frozen reply cannot be silently truncated; Pydantic schemas reuse canonical fields; no default private-content logging. Record per-stage timing/attempts and total. Preserve single-pass rollback via config. Test fake success/failure/replay and live synthetic same-model calls before activating the existing web process. No model reload, second model, schema migration or frontend streaming in this scope.

Baseline is 507 passing tests and the existing uncommitted experiment/memory changes; preserve them. Track EXP-07 in the lineage.

Completed 2026-09-08: 522 tests passed, Ruff/compileall passed, live synthetic two-stage calls and public 3-turn correction/replay/reset passed. Web activated in two_stage mode without changing model/tunnel/admin processes. No DB migration. Metadata semantic errors remain; see docs/TWO_STAGE_GENERATION.md for results, activation check correction, rollback and next evaluation.
