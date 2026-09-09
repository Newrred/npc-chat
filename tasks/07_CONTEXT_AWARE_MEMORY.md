# Task 07 — Context-aware memory retrieval

Scope approved 2026-09-08: lexical retrieval using current input and bounded recent server history, zero results without evidence, conservative preference correction. No embeddings, extra model calls, event/mood schema, dynamic example selection, or general contradiction inference.

Completed 2026-09-08. Full suite: 484 passed; lint/compile checks passed. Synthetic exact-set retrieval: 12/12; real-model valid responses: 6/6, with remaining role confusion recorded separately. Public API preference correction/recall succeeded across three synthetic turns; the isolated room was reset afterward. No schema migration. See docs/CONTEXT_AWARE_MEMORY.md for evidence and limitations.

Acceptance:
- Explicit current topic wins. Recent context is a fallback only for recognizable continuations; assistant-only claims cannot establish a memory subject.
- Use at most the last four server messages; no browser history trust. Match simple Korean particle variants without claiming general semantic/coreference understanding.
- Return zero to three relevant memories, ranked by direct evidence before recency/importance. No unrelated fill. Ambiguous indirect references abstain.
- A supported direct user preference correction suppresses contradictory old memory/history/summary before generation and updates the same subject atomically after successful generation. Questions, quotations and third-person statements cannot overwrite the user's preference.
- Preserve old DB compatibility, owner/character isolation, replay, rollback, bounded prompt counting and no private-content default logging.
- Isolated tests cover direct/continuation/topic shift/ambiguous/missing matches, same-turn correction, failure rollback and restart. Compare synthetic retrieval fixtures against the old selector. Real-model quality is measured separately from retrieval correctness.
