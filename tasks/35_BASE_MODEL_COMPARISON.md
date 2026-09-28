# Task35 — 원본 계열 vs Aggressive 9B 비교

2026-09-28 계획. 부모 EXP23/상품화 리뷰. 작업 트리 Task34 변경을 보존한다.
가설: 동일 9B라도 Aggressive 변형 대신 원본 계열을 사용하면 주체/요청 이행/metadata 오류가 줄 수 있다.

- 기존 development24 사례, seed42, 동일 프롬프트/2단계/full/4096/출력256/temperature0.4 및 현재 sampler를 고정한다.
- 현재 Aggressive Q4_K_M과 Qwen/Qwen3.5-9B를 기반으로 한 Unsloth Q4_K_M을 비교한다. 후자는 공식 Qwen 직접 배포 파일이 아닌 별도 양자화이며 양자화 제작 방식 차이가 남는다.
- 파일 revision/SHA256, 런타임/프롬프트/평가 입력 hash, 실측 runtime 조건을 남긴다. 모델 파일과 개인 데이터는 Git에 넣지 않는다.
- DB/웹앱/공개 터널을 사용하지 않고 모델 프로세스만 순차 실행한다. 종료 후 시작 전 중지 상태로 복원한다.
- 원래 모델 metadata와 Task34 guard 적용 결과를 분리한다. 선택 기억은 주입되므로 검색 품질 평가는 아니다.
- 형식/재시도, 답변 내용, 관계 분류, 지연을 별도로 보고하며 문자열 검사 통과율을 의미 품질로 보지 않는다.
- 우선24개씩 한 seed의 탐색 비교다. holdout은 열지 않는다. 기본 모델 전환은 추가 검증 후 판단한다.

실행 중 확인한 한계: 두 GGUF의 내장 chat template SHA256이 다르다. 앱의 messages와 sampler는 고정하지만 각 파일의 기본 template을 유지한 패키지 비교로 해석한다. 모델 변형/양자화/template 중 어떤 요소가 차이를 일으켰는지 분리하지 못한다. 시작 전 GPU 여유도 Aggressive3446MiB/원본4812MiB로 달랐고 auto offload이므로 지연 우열의 인과 판단은 하지 않는다.

완료: 각24개/총48개 결과를 docs/evaluation/exp24에 보존. 형식·전송 실패0, 각48생성. 상세 판단은 docs/BASE_MODEL_COMPARISON.md. 기본 교체 미채택. 평가용 모델을 종료하고 기존 설정을 보존했다. 전체671 tests/lint/compile 통과. 다음은 고정 대사 metadata 분류 지침/대조 예시 비교다.
