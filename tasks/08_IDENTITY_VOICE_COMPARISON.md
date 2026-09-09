# Task 08 — Identity / voice comparison

Completed 2026-09-08. 60 main comparisons and 12 follow-up generations were valid on first attempt. C improved some example-aligned responses but failed to generalize and showed remaining identity/context/voice issues. Keep production prompt unchanged; preserve experimental variants and raw reports. 487 tests passed, lint/compile passed. See docs/IDENTITY_VOICE_COMPARISON.md.

Approved 2026-09-08: compare current prompt A, identity/section cleanup B, and corrected voice examples C. Preserve the bright, kind Yui persona. No mood system, dynamic retrieval, schema changes or new production model calls.

Acceptance: versioned prompt snapshots; identical synthetic conversation contexts and paired generation seeds; fixed model/settings; record raw and final replies, override marker, validity, latency and tokens; review role/context/voice separately without treating keyword flags as ground truth. Preserve partial reports on failure. Keep existing runtime until comparative evidence supports a change. Report uncertainty and all regressions. No private DB access or production quota charge.
