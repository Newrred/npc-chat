# EXP-11 — 검색 단서 추가 검증

부모 EXP-10. 2026-09-09 완료. 기존 구현·모델·설정 고정, 새로운 표현 4사례 × OFF/ON × seed 109/211. 각 실행 2턴, 총 16실행/32턴/64모델 호출. 실제 사용자 DB 접근·운영 설정 변경 없음.

## 결과

| 사례 | 기존 검색 | 단서 ON | 판단 |
|---|---|---|---|
| 영화 선택 후 “그거 뭐였지?” | 제목 회상 0/2, 기억 0개 | 동일, 단서가 두 seed 모두 없음 | EXP10의 단서 누락 재현 |
| 도서관에서 찾겠다고 한 뒤 “그게 뭐였지?” | 모모 회상 2/2 | 모모 회상 2/2 | 추가 이득 없음. 기존 검색도 최근 발화의 도서관을 단서로 사용 |
| 영화 이야기를 그만하고 책상 정리로 전환 후 생략 질문 | 지난 영화 기억 선택 2/2 | 지난 영화 기억 선택 2/2; 영화 단서 잔류 2/2 | 검색의 관련성 실패. 최종 답변은 두 조건 모두 책상 정리 맥락 유지 |
| 영화 약속 취소 후 “어딜?” | 기억 0개, 집에서 쉰다는 답변 2/2 | 동일, 단서 없음 | 취소한 영화 약속을 현행으로 말하지 않음. 다만 쉬겠다는 내용은 사용자 원문보다 강한 추정 |

모든 대응 쌍에서 첫 답변과 최종 답변 문자열이 각각 동일했다. 영화 제목 미회상은 검색 실패와 구분해서 판정했다. 책 회상은 검색 단서 확장의 효과로 계산하지 않는다.

## 원인 교차 확인

`app/conversation_memory.py`의 `source_views`는 정확히 “그거 뭐였지/그게 뭐였지”인 질문에서 최근 4개 메시지의 책/소설/도서/영화 단어를 확인한다. “영화 얘기는 그만하자”도 영화 검색을 활성화한다. 부정·화제 종료 의미는 여기서 구분하지 않는다. 따라서 화제 전환 실패는 단서 ON에만 생긴 문제가 아니다.

`app/search_cues.py`의 원문 검증은 인용이 실제 존재하는지를 확인한다. 과거 영화 인용은 출처 검증을 통과하지만 현재 관련성을 보장하지 않는다. 새 모델 호출 없이 단서를 얻을 수 있다는 EXP10 결과는 유지되지만 안정적인 기억 선택은 입증되지 않았다.

## 형식과 시간

예외 0/16, 두 단계 각 1회씩 총 64호출, 재시도 없음. 첫 턴의 reply+metadata 단계 시간 합 중앙값 OFF 3.2025초 / ON 2.9220초, 최댓값 OFF 4.219초 / ON 4.749초. 작은 순차 표본이며 실행 순서가 고정되어 있어 ON이 빠르다는 근거로 쓰지 않는다. 실제 앱 큐 대기·DB·전체 HTTP 응답 지연은 측정하지 않았다.

## 한계 및 판정

운영 채택 보류 유지. 새로운 문장에서도 누락·화제 잔류가 확인되었다. 특정 영화/시간 키워드를 더 추가하기보다 현재 화제에 대한 관련성 판단과 검색 단서 유지/폐기 기준을 다음 검증 대상으로 삼는다.

이 실험은 원문을 두 번째 모델 입력에서 의도적으로 제외한 통제 실험이다. 자연스러운 토큰 밀림·긴 세션·DB 저장/취소 처리 전체를 검증한 것은 아니다. 특히 취소 문장은 최근 입력에 남아 있고 검색 저장소 fixture는 최초 추천 턴만 포함한다. 그러므로 취소 사례 성공을 장기 기억의 취소 상태 저장 성공으로 해석하지 않는다. 4사례와 2seed의 수동 정성 판정이며 일반 대화 품질 통계가 아니다.

## 재현 및 변경 파일

변경: `scripts/evaluate_search_cues.py`에 validation 사례 추가, 본 보고서와 원자료, EXPERIMENT_LINEAGE/PROJECT_STATUS/DECISION_LOG 업데이트. 서비스 구현 변경 없음. 마이그레이션·설정 변경 필요 없음.

실행 명령과 결과:

```text
./venv/Scripts/python.exe scripts/evaluate_search_cues.py --env-file .runtime/public-test.env --case validation --output docs/evaluation/search-cues-validation-v1.json
  완료: 16실행, 32턴, 64호출, 예외 0 (다시 실행할 때 새 output 경로 사용)
./venv/Scripts/python.exe -m pytest -q tests/test_search_cues.py tests/test_two_stage.py
  17 passed in 2.50s
./venv/Scripts/python.exe -m ruff check scripts/evaluate_search_cues.py
  통과
./venv/Scripts/python.exe -m compileall -q scripts/evaluate_search_cues.py
  통과
```

[합성 원자료](evaluation/search-cues-validation-v1.json). 개인 대화·비밀값은 포함하지 않는다.
