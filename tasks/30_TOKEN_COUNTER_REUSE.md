# Task 30 — TokenCounter 연결 재사용·요청 내부 캐시

## 목표

llama.cpp의 정확한 apply-template/tokenize 검증을 유지하면서 TokenCounter의 매 호출 HTTP client 생성을 제거하고, 한 생성 요청 안에서 완전히 같은 메시지 계산만 재사용해 준비 지연을 줄일 수 있는지 측정한다.

## 기준선

- 시작 HEAD: `main@0c29016`
- 전체 직전 기준: 627 Python tests, 프런트·검사창 28 tests
- 현재 TokenCounter 호출마다 새 `httpx.Client`, apply-template 1회, tokenize 1회
- 정상 two-stage 한 턴은 서로 다른 reply/metadata prompt이므로 기본 4 HTTP 요청

## 고정 조건

- 정확한 llama.cpp apply-template/tokenize 결과와 장애 시 명시적 실패
- 9B 모델, two-stage full metadata context, prompt/schema/sampling
- API, DB, 모델 생성 호출 수와 응답
- 요청 밖으로 원문 메시지 캐시를 보존하지 않음

## 완료 조건

- TokenCounter가 HTTP 연결을 재사용하고 명시적으로 닫힌다.
- 캐시는 한 최상위 요청 scope 안의 동일 메시지에만 적용되고 scope 종료 시 지워진다.
- 서로 다른 prompt는 합치지 않고 최종 token 검증을 생략하지 않는다.
- 합성 전후 benchmark, 단위/전체 테스트, 실제 full 공개 smoke로 채택 여부를 기록한다.

## 완료 기록

2026-09-22 완료. 연결 재사용과 요청 범위 SHA-256 cache를 구현하고 exact token 결과 불변을 확인했다. 정상 reply/metadata는 서로 달라 tokenizer HTTP 4회를 유지하지만 client는 1개이며, development 24개의 prepare 중앙값은 0.578→0.297초였다. 전체 모델 응답 중앙값은 샘플링 변동으로 2.531→3.546초여서 전체 속도 개선으로 주장하지 않는다. 전체 629 Python tests, 프런트·검사창 28 tests 및 정적 검사를 통과했다. 공개 합성 2턴에서 첫 턴 이후 reply prepare도 0초로 측정됐고 즉시 reset했다. 상세는 `docs/TOKEN_COUNTER_REUSE.md`, EXP-22 참고.
