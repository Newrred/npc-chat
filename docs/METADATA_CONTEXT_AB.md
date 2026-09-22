# EXP-21 metadata 전용 문맥 A/B

## 결론

compact는 운영에 채택하지 않는다. 공개 시험 설정은 `full`을 유지한다. 짧은 대화가 대부분인 development 세트에서는 입력과 지연이 거의 줄지 않았고, 일부 interaction 분류가 나빠졌다. 긴 이력에서만 분명한 token 절감이 있었으므로 향후 실제 긴 문맥 비율과 metadata 분류 기준을 보강한 뒤 조건부 경량화를 다시 검토할 수 있다.

## 조건

- 모델/설정: 현재 9B Q4_K_M, context 4096, output 256, 현재 sampling, thinking OFF
- 세트: dialogue-suite-v1 development 24개, holdout 미사용
- A `full`: 기존 reply와 동일한 전체 token-budget context
- B `compact`: 현재 입력·고정 reply·관계/flags·최근 완전 대화 2쌍·선택 profile/episode만 유지
- reply 생성, 프롬프트, schema, DB/API, 모델 호출 수는 비교 대상에서 제외

처음에는 전체 two-stage를 full/compact로 각각 실행했으나 확률적인 reply 차이가 metadata 결과까지 바꾸어 인과 비교에 부적합했다. 최종 비교는 EXP20의 같은 합성 reply를 고정하고 각 사례의 full/compact 실행 순서를 교차했다. 24사례×2조건, metadata 48호출이다.

## 결과

| 항목 | full | compact |
|---|---:|---:|
| 최초 형식 성공 | 24/24 | 24/24 |
| parse / transport 실패 | 0 / 0 | 0 / 0 |
| prompt token 중앙 | 903.5 | 900.0 |
| prompt token 평균 | 956.9 | 925.4 |
| prompt token 최대 | 1,739 | 1,080 |
| prepare 중앙 | 0.329초 | 0.329초 |
| infer 중앙 | 1.726초 | 1.742초 |
| infer 표본 p95 | 2.593초 | 2.297초 |
| metadata 전체 중앙 | 2.062초 | 2.094초 |
| 서버 최종 수용 기억 사례 | 0/24 | 0/24 |

평균 token 감소 대부분은 24쌍의 긴 이력이 있는 `event_and_topic-03` 한 건에서 나왔다. 이 사례는 1,739→1,080 token, infer 2.656→2.296초였다. 나머지 짧은 사례의 중앙 절감은 3.5 token뿐이라 고정 schema·지시가 차지하는 비용에 비해 작았다.

같은 답변인데도 확률적 metadata는 완전 일치 2/24, interaction 일치 17/24, face 일치 19/24, internal emotion 일치 17/24였다. 차이가 난 interaction 7건을 지시와 문맥으로 검토했다.

- `그래`로 우산 제안을 수락한 사례는 full의 `shared_activity`가 compact의 `neutral`보다 적절했다.
- 장소·책·취향을 확인하는 질문은 neutral이어야 한다. 장소 질문에서는 compact가 맞았지만 책 질문에서는 full이 맞았고 취향 질문은 양쪽 모두 틀렸다.
- `오늘 좀 지쳤어`는 사용자 자기 공개다. full의 `self_disclosure`가 compact의 `support`보다 적절했다.
- 무조건 복종 요구는 `boundary_violation`이어야 하나 양쪽 모두 놓쳤고 compact는 `support`로 분류해 더 부적절했다.
- 짧은 피곤 확인 응답은 양쪽 모두 명확한 정답으로 보기 어려웠다.

원시 memory candidate는 full 12사례, compact 11사례에서 나왔지만 질문·답변·바꾼 표현이 대부분이었다. 서버 원문 검증을 통과한 후보는 양쪽 모두 0건이어서 이번 비교에서 실제 저장 차이는 없었다. 원시 후보 품질 문제는 별도 개선 대상이며 compact 채택 근거가 아니다.

## 채택과 되돌리기

`NPC_METADATA_CONTEXT_MODE=full`이 기본이며 공개 시험도 full을 유지한다. compact 구현은 명시적 실험/향후 긴 문맥 비교용으로 남긴다. 설정 한 줄로 전환·복귀할 수 있고 API·DB migration은 없다. 다음 속도 후보는 문맥 삭제보다 TokenCounter 연결 재사용/요청 내부 중복 count 제거를 독립 비교하는 것이다. 정확한 최종 token 검증은 유지한다.

원자료: `docs/evaluation/metadata-context-ab-v1.json`. 실제 사용자 대화, 사용자 DB, 공개 API와 quota는 사용하지 않았다.
