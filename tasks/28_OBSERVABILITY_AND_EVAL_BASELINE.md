# Task 28 — 유효 설정·단계별 계측·독립 평가 기준선

## 목표

대화 원문과 사용자 식별자를 저장하지 않으면서 현재 실행 설정과 요청 단계별 지연·성공·실패를 재현 가능하게 기록하고, 후속 metadata 문맥 A/B에 사용할 독립 합성 평가 세트를 만든다.

## 기준선

- 시작 HEAD: `main@3d03a4f`
- 작업 전 관련 테스트: 81 passed
- 전체 직전 기준: 613 passed
- 현재 구조: 9B 동일 모델 two-stage, 단일 worker/생성 슬롯, SQLite

## 범위

- 비밀값·주소·경로를 제외한 유효 설정 manifest
- queue, repository load, recall, LLM prepare/infer, commit, total 단계 지연
- 모델 단계별 토큰·재시도·형식/전송 실패·문맥 축약·provider 지원 수치
- 성공·replay·거절·실패·취소를 같은 schema로 기록
- 크기 제한 회전 JSONL과 오프라인 p50/p95 집계
- 개발/holdout으로 분리한 합성 평가 세트와 구조 검사
- 현재 공개 시험 환경에서 계측 활성화 및 smoke

## 제외

- 대화 원문, 답변, 기억 내용, 사용자·세션·turn ID의 운영 계측 저장
- 외부 모니터링 서버
- metadata 문맥 축약 자체
- 모델·샘플링·DB schema 변경
- 실제 사용자 대화의 평가 자료 편입

## 완료 조건

- manifest와 요청 JSONL에 비밀값·원문·사용자 식별자가 없다.
- 성공과 실패 요청에서 가능한 단계 지연과 최종 상태가 남는다.
- 회전·집계·평가 세트 검증이 자동 테스트된다.
- 전체 테스트와 실제 로컬/공개 smoke가 통과한다.

## 완료 결과

- 비개인 manifest, 성공·실패·거절·취소·replay terminal record, 단계별 지연·token·provider 수치, 회전 JSONL과 오프라인 집계를 구현했다.
- 48개 합성 세트를 development/holdout 24개씩 고정하고 긴 합성 이력과 6축 사람 rubric을 포함했다. development 기준선만 실행했고 holdout은 보존했다.
- development 24개/48호출은 최초 형식 성공, parse·transport 실패0, 전체 중앙2.532초·표본 p95 3.891초였다. 내용상 경계3건 실패 등은 별도 기록했다.
- 현재 공개 시험 구성에서 계측을 활성화하고 서버를 재시작했다. 새 합성 방문자로 공개 채팅 1턴 200 및 방 reset 200을 확인했다. JSONL에는 manifest+turn 2건만 있으며 합성 원문·답변과 사용자/세션/turn ID가 없었다. 공개 guest 모드의 `/api/ready` 403은 설계된 비공개 경계이며 `/api/live`, 공개 화면·채팅과 로컬 모델/검사창은 정상이다.
- 최종 Python 623 tests, 프런트·검사창 28 tests, Ruff/compileall/JavaScript/diff 검사 통과. 전체 첫 실행은 기존 queue 테스트 대역이 새 시작 콜백 인자를 받지 못해 1 failed/622 passed였고 대역을 실제 계약에 맞춰 수정했다. 평가 CLI 첫 실행은 import 경로 누락으로 모델 호출 전 중단됐으며 회귀 테스트를 추가했다.
- DB migration, 모델·프롬프트·API 응답·호출 수 변경 없음. 공개 smoke가 일일 전체/방문자 quota 각 1회를 사용했으며 합성 대화는 즉시 삭제했다.
