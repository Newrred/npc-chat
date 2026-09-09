# 활성 화제 기반 기억 검색 — EXP-12

2026-09-09 Task19 구현. 현재 SQLite 원문 파생 뷰와 두 단계 생성 구조를 유지하면서, 생략 질문의 검색 범주를 최근 사용자 발화의 활성 구간에서만 정한다. 새 모델 호출, embedding, DB 스키마, 환경 변수는 없다.

## 동작

- `그만하자`, `다른 이야기`, `주제를 바꾸자`, `말고`, 명시적 취소를 만나면 그 앞 사용자 화제를 검색 단서에서 제거한다.
- 경계 문장 뒤에 새 내용이 있으면 그 부분부터 새 활성 구간으로 사용한다.
- `그거/그게 뭐였지` 계열에서 책·영화가 명시되지 않아도 `작품`, 추천/선택/골라준 대상이라는 지칭이 있으면 가장 최근의 출처 있는 추천 하나를 선택한다.
- `어딜/어디로`는 활성 구간에 날짜·시각·만남·이동 제안 단서가 있고 부정 이동이 없을 때만 약속 사건을 찾는다.
- 명시적 취소 사건은 앞선 약속 사건을 폐기한다. 이후 새 제안이 있으면 앞선 취소도 폐기한다.
- 연결 근거가 없으면 사건 기억을 선택하지 않는다. 이름·호칭 파생 및 기존 사용자 memories 검색은 유지한다.

이것은 전체 대화 의미를 이해하는 상태 머신이 아니다. 규칙에 없는 표현, 여러 추천을 한 문장에 함께 가리키는 표현, 풍자·간접 부정은 모호할 수 있다. 사건은 발화 출처이며 실제 일정 이행을 증명하지 않는다.

## EXP-12 결과

EXP-11과 동일한 합성 4사례, 동일 모델/설정/seed 109·211을 사용했다. 변경 전 결과는 보존된 EXP-11 baseline과 비교했고 변경 후만 다시 실행했다. 8실행/16턴/32모델 호출, 예외·재시도·형식 실패 0.

| 사례 | 변경 전 검색 | 변경 후 검색 | 변경 후 대사 |
|---|---:|---:|---|
| 영화 선택 → 작품 지칭 → “그거 뭐였지?” | 대상 0/2 | 리틀 포레스트 2/2 | 정확한 제목 1/2; 다른 1건은 “요즘 유행하는 영화”로 제목 미사용 |
| 책 선택 → 도서관 → “그게 뭐였지?” | 모모 2/2 | 모모 2/2 | 정확한 제목 2/2, 변화 없음 |
| 영화 화제 종료 → 책상 정리 → 생략 질문 | 지난 영화 오선택 2/2 | 사건 0/2 | 지난 영화 혼입 0/2. 한 답변은 “아까 말한 거야”로 모호해짐 |
| 영화 약속 취소 → “어딜?” | 사건 0/2 | 사건 0/2 | 두 조건 모두 집에서 쉰다고 답함 |

검색 목표는 영화 누락과 종료된 화제 오선택에서 각각 2/2 개선됐다. 그러나 선택된 증거를 9B가 답변에 반드시 사용하는 것은 아니다. 기억 검색 성공과 대사 품질을 별도로 평가해야 한다. 취소 사례는 최근 입력에 취소 문장이 남은 통제 조건이라 장기 취소 상태 전체를 검증하지 않는다.

첫 턴 reply+metadata 단계 합 중앙값 2.7495초, 최대 3.563초. 두 번째 턴 중앙값 2.9375초, 최대 4.828초. 변경 전과 순차 실행 시점이 달라 속도 우열로 사용하지 않는다. 앱 큐·HTTP·DB 왕복이 포함된 부하 측정도 아니다.

## 검증과 재현

초기 관련 테스트에서 취소 뒤 새 제안과 이전 취소가 함께 선택되는 실패 1건을 발견했다. 새 제안이 이전 취소를 폐기하도록 수정하고 다시 검증했다. 실패를 skip하거나 기준을 완화하지 않았다.

```text
./venv/Scripts/python.exe -m pytest -q
  편집 전: 571 passed in 12.07s
./venv/Scripts/python.exe -m pytest -q tests/test_conversation_memory.py tests/test_search_cues.py
  최초: 1 failed, 28 passed (취소 뒤 새 제안 처리)
./venv/Scripts/python.exe -m pytest -q tests/test_conversation_memory.py tests/test_search_cues.py tests/test_memory_api.py tests/test_memory_audit.py
  수정 후: 40 passed in 1.26s
./venv/Scripts/python.exe scripts/evaluate_search_cues.py --env-file .runtime/public-test.env --case active_topic --output docs/evaluation/active-topic-retrieval-v1.json
  8실행/16턴/32호출, 오류 0
./venv/Scripts/python.exe -m pytest -q
  최종: 574 passed in 12.01s
./venv/Scripts/python.exe -m ruff check app tests scripts
  All checks passed
./venv/Scripts/python.exe -m compileall -q app scripts
  통과
```

[합성 원자료](evaluation/active-topic-retrieval-v1.json). 실제 사용자 대화, 키, 임시 공개 주소는 포함하지 않는다.

## 적용 및 다음 단계

규칙 검색은 기본 `source_views`에 적용한다. EXP-10의 모델 생성 `search_cues`는 계속 운영 OFF다. 다음 품질 개선은 검색된 단 하나의 명확한 추천 제목을 회상 질문에서 모델이 사용하도록 입력 지시 또는 제한된 근거 답변 방식을 비교하는 것이다. 모델 출력 강제는 이번 범위에 포함하지 않았다.

공개 테스트 웹과 로컬 관리자만 소유권 기록으로 재시작했다. 모델·터널·기존 SQLite는 유지했다. 새 합성 게스트 방에서 페이지/세션/실제 채팅/reset이 모두 HTTP 200이고 답변이 비어 있지 않음을 확인했다. 합성 방은 reset했으며 일일 전역 요청 카운트 1회는 정상적으로 소비됐다. 공개 모드에서 `/api/ready`가 403인 것은 readiness 비공개 정책이며, 앱 startup 완료 로그·공개 채팅·모델 endpoint·관리자 readiness로 실행 상태를 교차 확인했다.
