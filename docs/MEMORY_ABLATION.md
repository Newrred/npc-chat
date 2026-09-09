# EXP-09 — 이력과 검색 기억 효과 비교

합성 영화 ‘월터의 상상은 현실이 된다’, 저녁8시 만남 제안. 운영 사용자DB 읽기/쓰기 없이 기존 DecisionService와 source_views 사용. seed109/211, 현재9B/4096/두 단계 및 기본 캐릭터 설정 고정. 직접 순차 모델 호출이므로 앱 큐/DB durability 평가는 아니다. 원문 이력 제거는 통제 조건이며 자연 토큰 초과를 재현한 실험은 아니다. 암시적 질문의 직전 ‘응, 빨리 가자!’는 세 조건 공통으로 고정했다.

|질문|이력만|실제 검색 기억만|둘 다 없음|
|---|---|---|---|
|영화 제목이 뭐였지?|두 seed 모두 정확한 제목|두 seed 모두 대상 영화 회상. seed109는 ‘된다’를 ‘돼’로 바꿔 제목 완전 일치는 아님|인터스텔라 환각 / 제목 미응답 및 같이 봤다는 미제공 사실|
|8시 언급 후 ‘어딜?’|두 seed 모두 영화관|검색0개, 두 seed 모두 집 제안|동일하게 집 제안|

형식:12/12 정상,24모델 호출(각 두 단계1회). 검색:명시적 질문 기억1개, 암시적 질문0개. 원문을 제거한 조건에서 실제 recent messages에 영화 제목이 없음을 검증했다. 검색기억 조건은 system source_backed_context에만 영화 근거 포함. 속도 중앙값:이력만3.26s/검색만3.08s/없음2.84s, 각4회로 성능 우열 주장은 불가. 의미 판정은 대상을 회상했는지와 제목 철자 일치를 구분한다.

결론: 관련 기억이 검색되면 원문 대화 없이도 답변에 도움을 줄 수 있다. 그러나 ‘어딜?’은 현 검색기가 약속을 고르지 못한다. 사용자가 관찰한 영화관 답변은 이력 유지로 설명되며 장기 기억 검색 성공 사례로 볼 수 없다. 기억 없는 조건에서 모름을 인정하지 않는 생성 오류도 남는다. 두 seed/두 질문뿐이며 일반화·장기 운영 검증 아님. 구조/운영 설정 채택 변경 없음. 다음 질문은 암시적 시간/목적지 발언에서 최근 사건을 과잉 검색 없이 고를 수 있는가다.

명령: `./venv/Scripts/python.exe scripts/evaluate_memory_ablation.py --env-file .runtime/public-test.env --output docs/evaluation/memory-ablation-v1.json`. `./venv/Scripts/python.exe -m ruff check scripts/evaluate_memory_ablation.py`, `./venv/Scripts/python.exe -m compileall -q scripts/evaluate_memory_ablation.py`, `git -c core.safecrlf=false diff --check` 통과. 초기Ruff 세미콜론1건 수정. 실제 모델 실패 없음. 분석기의 허용되지 않은flag는 기존 서버 필터가 제거(로그1회). 재시작/DB 변경/commit/push 없음.

원자료: [memory-ablation-v1.json](evaluation/memory-ablation-v1.json). 원자료는 합성 입력/출력이며 private 대화/credentials 없음.
