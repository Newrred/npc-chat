# Task 05 — Secure Remote Alpha

2026-09-07 사용자 변경 요청: 기본은 **링크 접속 즉시 이용하는 guest 모드**다. 이메일 로그인은 선택적 cloudflare 모드로 보존한다. 서명된 익명 쿠키로 브라우저별 대화 분리, 최근 활동 이용자 수 및 전체/브라우저별 일일 한도를 적용한다. 실제 동시 GPU 생성 확대는 이번 작업 범위가 아니며 1개를 유지한다. PUBLIC_LINK_DEPLOYMENT.md 참고.

2026-09-07 상태: **진행 중 / 배포 준비**. 선택적 Access JWT 인증, 계정 소유권, Origin/Host/요청 제한, 구성 preflight와 실행기 구현. 도메인/계정 미보유로 실제 터널 연결은 미실시. 보관·삭제 정책/기능, 운영 서비스 복구, 외부 접속·부하·품질 검증은 남아 있다. 상세: docs/REMOTE_DEPLOYMENT_RUNBOOK.md, docs/PROJECT_STATUS.md.

Prerequisite: local daily-use path is stable and measured.

## Objective

Expose the app for owner-only or invited remote use without exposing the model server or relying on temporary tunnel URLs.

## Required work

### Network boundary

- Use a named/fixed tunnel or equivalent reverse proxy.
- Default to one protected HTTPS origin for the FastAPI web app (static frontend + `/api`). Keep the model and DB files private.
- Keep llama.cpp on 127.0.0.1:8001.
- Remove all quick-tunnel assumptions from documentation and deployment config.

### Access control

Choose and document one entry mode:

- owner-only Cloudflare Access, or
- invited user authentication.
- public link with automatically issued signed guest cookies and durable aggregate daily limits (user-selected default).

Do not put a reusable secret in static JavaScript.

### Limits

- per-user/session requests per minute
- maximum concurrent active turn per session
- global bounded queue
- input/output caps
- explicit 429/503 errors

### Frontend deployment config

- Ship frontend and API together as one versioned web application; default API URL is relative `/api`.
- Separate frontend hosting is optional. Only for that mode, generate the non-secret API URL from deployment variables and configure exact CORS.
- No hardcoded machine-specific URL in source.
- same-origin authentication and, for cookie authentication, CSRF protection; CORS does not replace authentication
- cache behavior that does not pin obsolete config indefinitely

### Observability and operations

- request id
- structured status/error logs
- no raw message body by default
- readiness dependency status
- queue/latency/error counters
- startup and recovery runbook
- SQLite backup and restore
- clear UI when home server is offline
- service supervision for owned web/model processes: ordered start/stop, bounded readiness, restart backoff, logs and recovery after reboot
- one application instance/worker is the supported default; no replica/worker increase without shared lock/queue/rate-limit and persistence validation
- keep SQLite in persistent local storage outside replaceable application/static files; test backup/restore across an application upgrade

### Security tests

- unauthorized access denied
- CORS rejects unexpected origin
- default single-origin page, assets and authenticated API work through the same entry point
- rate limit works
- prompt injection cannot alter server-owned state/schema
- direct LLM port not externally reachable
- duplicate turn remains idempotent across network retries

## Acceptance criteria

- remote access works through a stable endpoint.
- no model endpoint or Redis port is public.
- access control is enforced before chat requests reach the app.
- security and failure checks are documented with results.
- public alpha is not claimed unless privacy/retention decisions are completed.
- Default deployment needs no separate frontend server or Redis; confirm Task 03 cutover gates passed first.
