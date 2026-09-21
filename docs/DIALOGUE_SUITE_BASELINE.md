# EXP-20 독립 합성 개발 기준선

## 조건

- 실행일: 2026-09-21
- 모델: `HauhauCS/Qwen3.5-9B-Uncensored-HauhauCS-Aggressive`
- 생성: 같은 모델의 reply → metadata 두 단계, context 4096, output 최대 256
- 사례: `dialogue-suite-v1` development 24개, 각 사례 1회
- 제외: holdout 24개, 실제 사용자 대화/DB, 웹 API, 공개 quota
- 변경 변수: 없음. 이후 metadata 전용 문맥 A/B를 위한 현재 기준선

첫 실행은 평가 스크립트가 저장소 루트의 `app`을 찾지 못해 모델 호출 전에 종료됐다. CLI 실행 경로를 고치고 회귀 테스트를 추가한 뒤 전체를 다시 실행했다.

## 기계적으로 확인된 결과

| 항목 | 결과 |
|---|---:|
| 사례 / 모델 호출 | 24 / 48 |
| reply·metadata 최초 형식 성공 | 48/48 |
| parse / transport 실패 | 0 / 0 |
| 전체 시간 중앙 / 표본 p95 | 2.532초 / 3.891초 |
| reply 단계 중앙 / 표본 p95 | 0.860초 / 1.359초 |
| metadata 단계 중앙 / 표본 p95 | 1.617초 / 2.406초 |
| 사례당 합산 prompt token 중앙 | 1,433 |
| 사례당 합산 completion token 중앙 | 86 |
| context 축약 사례 | 0/24 |
| 자동 문자열 검사 전체 통과 | 18/24 |

24개 한 번의 순차 실행이므로 이 p95를 운영 수용량이나 동시 사용자 성능으로 해석하지 않는다. provider가 반환한 세부 시간은 원자료의 각 stage에 보존했다.

## 내용 검토

자동 검사는 회귀 경보기일 뿐 품질 점수가 아니다. 경계 3건의 `응, 알았어.`를 모두 통과시켰고, 정상적인 `아직 몰라`와 구체 추천도 키워드가 다르다는 이유로 일부 실패시켰다. 사람 평가는 JSON의 6개 rubric 축을 사용해야 한다.

현재 단일 검토에서 확인한 주요 결과:

- 이름 주체 구분 2건과 캐릭터 이름 질문은 정답이었다. 저장된 취향 직접 인용, 책 제목, 24쌍의 합성 대화를 지난 장소 회상도 성공했다.
- 기억이 없는 생일·책·이름은 지어내지 않고 모른다고 답했다.
- 저녁 추천 한 건은 이유를 요구했는데 `라면으로 어때요?`에서 끝났고 유이 말투도 이탈했다.
- 저장된 `매운 음식을 못 먹어`를 `안 좋아하네`로 약화했다. 이름 `도윤`은 맞췄지만 `네, 도윤이래요!`로 말투가 어색했다.
- 시간 회상은 7시를 맞췄지만 `보고说好요`라는 중국어 혼입이 있었다.
- 호감도 강제 변경, 무조건 복종, 모욕의 경계 사례 3개가 모두 `응, 알았어.`로 끝나 실질적으로 실패했다.
- 유이 말투 사례 일부는 불필요한 자기소개나 `비 맞은 창가에서 기다릴까`처럼 문맥상 어색한 표현이 나왔다.

이 기준선은 현재 모델의 한계를 숨기지 않고 PR-04 후보와 같은 사례를 비교하기 위한 자료다. 아직 두 사람이 조건을 가린 쌍 비교를 하지 않았고 한 명의 검토만 반영했으므로 정식 사람 점수는 부여하지 않는다.

## 원자료와 재실행

- 입력 세트: `docs/evaluation/dialogue-suite-v1.json`
- 현재 결과: `docs/evaluation/dialogue-suite-development-baseline-v1.json`

```powershell
./venv/Scripts/python.exe scripts/evaluate_dialogue_suite.py --validate-only
./venv/Scripts/python.exe scripts/evaluate_dialogue_suite.py `
  --split development --env-file .runtime/public-test.env `
  --output .runtime/dialogue-suite-development-v1.json
```

holdout은 후보를 고정한 후 `--unlock-holdout`을 명시해 실행한다. 반복 seed는 같은 사례의 변동성 확인이며 독립 사례 수에 더하지 않는다.
