# Codex Start Prompt

아래 내용을 `Newrred/npc-chat` 저장소를 연 Codex 작업에 그대로 전달한다.

---

당신은 이 저장소의 구현 담당자다. 먼저 저장소 루트의 `AGENTS.md`와 아래 문서를 우선순위대로 읽어라.

1. `docs/PRODUCT_AND_TECHNICAL_DIRECTION.md`
2. `docs/PROJECT_STATUS.md`
3. `docs/TARGET_ARCHITECTURE.md`
4. `docs/API_AND_DATA_CONTRACTS.md`
5. `docs/IMPLEMENTATION_PLAN.md`
6. `tasks/00_BASELINE_STABILIZATION.md`

이번 작업에서는 **`tasks/00_BASELINE_STABILIZATION.md`만 수행**한다. 관계 엔진, 장기 기억, 공개 배포 등 이후 단계까지 한 번에 구현하지 마라.

시작 전에 다음을 수행하라.

- 현재 브랜치, HEAD, working tree를 확인한다.
- 문서 기준선 `a9f6205045648e8889a4dbf4190de65e330caaed`와 다르면 차이를 검토하고 `docs/PROJECT_STATUS.md`에 기록한다.
- 현재 애플리케이션의 실행/테스트 가능 여부를 먼저 확인한다.
- 사용자 작업을 덮어쓰거나 강제 reset하지 않는다.

작업 원칙:

- `npc-chat`을 유일한 기준 저장소로 유지한다.
- `heroine`은 레거시 배포본으로만 취급한다.
- 기존 FastAPI + 정적 프런트 구조를 유지한다.
- API 호환성을 깨는 변경은 이번 단계에서 하지 않는다.
- 임시 Cloudflare URL, 모델 파일, `.env`, 키를 커밋하지 않는다.
- 실제 LLM이 없어도 테스트 가능한 fake/stub 경로를 마련한다.
- 변경과 함께 테스트, README, `PROJECT_STATUS`를 갱신한다.

완료 후 다음 형식으로 보고하라.

1. 발견한 현재 상태와 기준 문서의 차이
2. 변경한 파일
3. 변경한 동작
4. 실행한 명령과 결과
5. 아직 검증하지 못한 환경 의존 항목
6. 다음 작업으로 `tasks/01_LLM_CONTRACT_AND_LOCAL_RUNTIME.md`를 시작해도 되는지

---
