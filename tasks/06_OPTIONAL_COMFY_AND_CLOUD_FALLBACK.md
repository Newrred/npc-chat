# Task 06 — Optional ComfyUI and Cloud Fallback

Status: gated; do not execute automatically.

## Entry conditions

- local chat, relationship, persistence, and secure remote path are complete
- measured user experience shows a need
- GPU/resource and cloud cost limits are approved

## Track A — ComfyUI

Goals:

- generated portrait never blocks text chat
- explicit queue, timeout, cancellation, cache, and retry behavior
- GPU coexistence policy with the 14B model
- persistent or disposable image policy
- generated image provenance/status visible in debug

Required review of current implementation:

- in-memory cache/status loss on restart
- background task shutdown/cancellation
- remote `/generate` API contract
- per-session cache key and retention
- image URL trust and expiry
- 12 GB VRAM contention

Prefer a separate worker or remote GPU over running full image generation concurrently with a near-VRAM-capacity LLM on the same 4070 Ti.

## Track B — Cloud fallback

Goals:

- fallback only after local readiness failure or queue policy
- same canonical schema and relationship engine
- serving backend recorded per turn
- explicit cost and request limits
- no silent model behavior mismatch
- health-based circuit breaker and manual disable switch

## Acceptance criteria

- text chat remains functional when image generation fails.
- fallback cannot apply one user turn twice.
- monthly spending cap and observability exist before enabling cloud calls.
- evaluation confirms fallback model is contract-compatible.
