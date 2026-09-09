# Task16 — Input/output separation and memory decision evidence
User requests clearer inputs/outputs, visible metadata analyzer prompt, actual selection criteria and accepted/rejected user memory evidence. Add opt-in trace from real retrieval/commit decisions; preserve algorithms and public contracts. Separate model candidates from server preference rule and derived name/events. Commit event only after transaction success. Old traces explicitly lack this detail. Verify behavior parity, failure paths, UI and real local smoke. Baseline555 tests.


Completed: 562 pytest,5 UI tests, real two-turn local model memory acceptance/retrieval smoke, browser analyzer view verified. Synthetic room reset. See docs/LOCAL_INSPECTOR.md for full commands, limitations and corrected old test event-order assumption.
