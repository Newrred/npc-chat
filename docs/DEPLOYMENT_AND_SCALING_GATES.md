# Deployment and Scaling Gates

2026-09-07 target update: one FastAPI web app (frontend + API), one separate model process, SQLite local file, one app instance/worker. HTTPS/access control is an additional deployment boundary. This target becomes Redis-free only after Phase 03 validation; the current Phase 00 runtime still uses Redis and a separate static server.

## Stage A — Local development

Users: developer only  
Runtime: localhost  
Required:

- llama.cpp bound to 127.0.0.1
- FastAPI bound to 127.0.0.1
- Phase 01~02: transitional Redis; Phase 03 onward: SQLite and in-process bounded queue/locks, Redis optional
- Phase 01 onward: same-origin frontend/API and required unified start/stop
- Comfy OFF
- automated tests and local runbook

No tunnel is required.

## Stage B — Personal remote access

Users: owner only  
Required before entry:

- Phase 00~04 complete
- named/fixed tunnel
- Cloudflare Access or equivalent identity gate
- exact CORS origin
- no direct LLM exposure
- safe restart and readiness
- deploy the web frontend/API as one unit; service-supervised model and app lifecycle
- state backup

A temporary `trycloudflare.com` URL is not an acceptable 24/7 endpoint.

## Stage C — Small private beta

Users: invited testers  
Required:

- per-user or per-session authentication
- rate limit and single-session concurrency control
- terms/notice for stored conversations
- delete/reset relationship function
- structured logs without raw content by default
- queue depth and latency visibility
- clear offline state when the home PC is unavailable

## Stage D — Public alpha

Required:

- durable user identity and access revocation
- abuse and prompt injection testing
- privacy/retention policy
- backup and restore drill
- uptime expectation and maintenance behavior
- capacity test using measured tokens/sec and concurrency
- public-safe character/IP configuration
- cloud or second-node failure strategy if uptime is promised

## Stage E — Cloud fallback or dedicated server

Do not enter based on assumed user counts. Use measured triggers.

Possible triggers:

- main PC must remain available for work/games and LLM interruption is frequent
- queue p95 exceeds the product threshold during real usage
- local machine unavailability causes unacceptable failed sessions
- cloud serverless monthly spend is consistently above the amortized cost of a dedicated node
- one GPU cannot meet measured concurrency after batching/queue controls

## Capacity policy for the current PC

Initial service mode:

```text
one local model
one app instance / one worker
one parallel slot
one active generation per session
bounded queue
short response cap
```

Before increasing `parallel`, measure VRAM and latency. 12 GB VRAM should not be assumed to support multiple long-context slots safely.

Before increasing application workers/replicas, replace in-process-only coordination with a validated shared design. Evaluate Redis for shared locks/queues/rate limits and PostgreSQL when measured write contention or multi-host storage requires it. Neither is automatically required by public exposure alone, and adding Redis alone does not establish distributed correctness.

## Failure and availability disclosure

When the home PC or LLM is unavailable:

- frontend must show an explicit offline/unavailable state
- do not fabricate a reply
- do not mutate relationship or memory
- retry must reuse the same `client_turn_id`

Cloud fallback is optional. It must not silently use a different model without recording the serving backend and validating compatible behavior.

## Hardware purchase gate

Do not purchase a dedicated sub-1,000,000 KRW server until at least one is true:

1. the main PC cannot be kept available for the intended use;
2. local LLM materially interferes with normal work or gaming;
3. measured remote usage justifies always-on hardware;
4. serverless/cloud cost and usage data show a credible local payback;
5. the product has passed relationship, persistence, and quality validation.

The existing RTX 4070 Ti machine remains the development and validation baseline.
