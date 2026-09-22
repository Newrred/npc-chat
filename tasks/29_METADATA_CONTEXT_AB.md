# Task 29 — metadata 전용 문맥 A/B

## 목표

같은 9B two-stage 구조에서 reply 입력은 고정하고 metadata 단계에만 필요한 문맥을 줄여, 분류·기억 후보·주체·표정 정확성을 해치지 않으면서 지연과 입력 token을 줄일 수 있는지 검증한다.

## 기준선

- 시작 HEAD: `main@2c3613b`
- 관련 테스트: 38 passed
- EXP20 development 24개: 48호출 형식 성공, 전체 중앙 2.532초, metadata 중앙 1.617초
- A: 기존 full metadata context
- B: 현재 사용자 발언, 확정 reply, 관계/flags, 직전 완전 대화 최대 2쌍, 선택된 profile/episode 근거

## 고정 조건

- 9B Q4_K_M, context 4096, output 256, 현재 sampling/thinking OFF
- reply 프롬프트·history·기억·품질 재시도 로직
- metadata 모델·schema·지시·재시도·최종 atomic commit
- API와 DB schema, 모델 프로세스와 호출 수
- development 24개 사용, holdout 24개 미사용

## 완료 조건

- full이 기본값으로 남고 compact는 명시적 설정으로 되돌릴 수 있다.
- current user와 frozen reply는 절대 제거되지 않는다.
- compact가 오래된 일반 이력/요약/일반 memories를 metadata 입력에서 제외하고 최근 완전 쌍과 source-backed 근거만 유지한다.
- metadata 형식, interaction, memory candidate, flags, face/emotion 결과를 A/B에서 비교할 수 있다.
- 전체 회귀와 실제 모델 development 비교 후 채택 여부를 문서화한다.

## 완료 결과

- full/compact 설정과 고정 reply metadata-only 평가 경로를 구현했다. reply 입력·생성은 변경하지 않는다.
- 관련 단위검증 42개 통과 후 development 24쌍/metadata 48호출을 실행했다. 양쪽 모두 최초 형식 성공, parse·transport 실패0.
- compact의 prompt 중앙은 3.5 token만 감소했고 metadata 전체 중앙은 2.062→2.094초로 개선되지 않았다. 긴 24쌍 이력 1건은 659 token·약0.36초 감소했다.
- compact interaction 분류 비열화가 확인되어 운영 미채택. 기본과 공개 시험은 full 유지한다.
- 원시 기억 후보는 많았지만 서버 원문 검증 후 양쪽 모두 0건 수용이었다. 후보 원시 품질은 별도 과제다.
- 최종 전체 627 Python tests, 프런트·검사창 28 tests, Ruff/compileall/JavaScript/diff 검사 통과. 공개 설정에 full을 명시하고 재시작해 화면/live/합성 chat/reset 200, manifest의 full·two_stage와 reply/metadata 두 단계를 확인했다. 합성 대화는 즉시 삭제했고 quota 1회를 사용했다.
