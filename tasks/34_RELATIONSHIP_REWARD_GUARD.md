# Task34 — 명시적 관계 조작 요구의 긍정 보상 방지

근거: 상품화 리뷰 및 `docs/product-review/DIALOGUE_EVIDENCE.json` boundary-01/02.
기준: main ddad67b, 수정 전 전체 629 tests 통과.

## 범위와 완료 조건

- 명확한 단독 점수 변경/무조건 복종 요구가 긍정 상호작용으로 잘못 분류돼도 관계 보상은 0이다.
- 단어 포함만으로 차단하지 않는다. 부정·인용·질문·조건·일반 칭찬/지지에는 적용하지 않는다.
- 원래 모델 분류와 적용 분류/이유를 로컬 trace로 구분한다. 대사/표정/기억 및 모델 호출 수는 보존한다.
- 실제 SQLite 저장과 동일 turn 재전송에서 보정 분류/수치가 일관된다.
- 프롬프트/모델 변경은 별도 비교로 남긴다. 범용 의미 분류나 모든 우회 차단을 주장하지 않는다.
- 단위·HTTP/SQLite 회귀, 전체 pytest, lint, compile, fake-model smoke 검증.

## 완료 결과

41개 신규 회귀 및 전체670 tests 통과. 두 기록 사례의 잘못된 보상 제거, 일반 발화 보존, 원본/보정 trace, SQLite recent 저장과 동일 turn replay 검증. lint/compile/diff check 통과. smoke는 기본2048 추정 예산에서 INPUT_TOO_LONG 실패, 프로세스에 LLAMA_CONTEXT=8192를 지정하여 HTTP 및 장애복구 통과. 실제 서비스 설정/DB 변경 없음. 모델 분류 품질·대화 품질 자체는 재측정하지 않았다. 다음 단계는 원본/변형 모델 비교이며 이 과제의 완료 범위에 포함하지 않는다.
