# 운영 계측과 독립 대화 평가

## 목적과 경계

Task28은 대화 원문을 상시 남기는 검사 추적과 운영 계측을 분리한다. 운영 계측은 기본 OFF이며 `NPC_METRICS_ENABLED=1`일 때만 회전 JSONL에 기록한다. 메시지·답변·기억 내용·사용자/프로필/세션/turn ID·주소·키·DB 경로는 기록하지 않는다. 로컬 검사창의 상세 추적은 기존처럼 `NPC_DEBUG_TRACE=1`인 개발 환경에서만 사용한다.

기동 시 `runtime_manifest` 한 건을 기록한다. 실제 적용된 모델 별칭, 생성 방식, context/output 한도, tokenizer 방식, sampling, queue 설정, 검색기/입력 구성 버전과 캐릭터 프롬프트 지문을 허용 목록으로 저장한다. URL·origin·키·로컬 경로는 제외한다.

각 채팅 요청은 임의의 계측 ID로만 연결하며 다음을 기록한다.

- 대기열 시간·깊이, 소유권/중복 조회, quota, 저장소 load, 기억 recall, 이미지, commit, 전체 시간
- reply/metadata별 입력 준비·모델 추론·전체 시간, 입력/출력 token, tokenizer 요청 횟수
- 시도 횟수, 형식/전송 실패 수, 문맥 축약 여부, grounded recall 여부
- llama.cpp가 실제 제공하는 `timings`, `cache_n`, `cached_tokens`; 없는 값은 만들지 않는다
- success/rejected/failed/cancelled, 구조화 오류 코드, replay 여부

## 설정과 확인

```dotenv
NPC_METRICS_ENABLED=0
NPC_METRICS_PATH=.runtime/metrics/requests.jsonl
NPC_METRICS_MAX_BYTES=5000000
NPC_METRICS_BACKUP_COUNT=3
```

서버 재시작 뒤 집계한다.

```powershell
./venv/Scripts/python.exe scripts/summarize_metrics.py .runtime/metrics/requests.jsonl
```

회전 파일까지 합치려면 보존된 파일을 함께 넘긴다. 성공 요청의 p95와 전체 성공률은 별개다. 소표본 p95는 수용량 근거로 사용하지 않는다. JSONL은 `.runtime` 아래에 두며 Git에 포함하지 않는다.

## 합성 평가 세트

`docs/evaluation/dialogue-suite-v1.json`은 실제 사용자 대화를 포함하지 않는 48개 사례다. 추천과 이유, 짧은 맞장구, 화자/정체성, 취향 정정, 사건·취소·주제 전환, 기억 부재, 경계, 유이/띳띠 말투를 각각 6개씩 포함한다. development 24개로 변경을 조정하고 holdout 24개는 후보가 고정된 뒤 한 번 확인한다. 긴 사례는 서로 다른 합성 일상 대화 24쌍을 사이에 둔다.

```powershell
./venv/Scripts/python.exe scripts/evaluate_dialogue_suite.py --validate-only
./venv/Scripts/python.exe scripts/evaluate_dialogue_suite.py `
  --split development --env-file .runtime/public-test.env `
  --output .runtime/dialogue-suite-development-v1.json
```

holdout은 조정 중 실수로 사용하지 않도록 `--unlock-holdout`을 추가해야 실행된다. 결과의 자동 문자열 검사는 빠른 이상 탐지용이며 품질 점수가 아니다. 사람은 각 사례의 `rubric`에 따라 형식·주체·근거·내용·자연스러움·캐릭터 일관성을 따로 판단한다. 현재 runner는 선택된 기억을 생성기에 직접 제공하므로 **최종 입력 이후의 답변 활용**을 본다. 원문 존재→후보 생성→검색 선택→최종 입력 포함 단계는 저장소·검색 회귀 테스트와 검사 추적으로 별도 판정하며, 이 결과를 검색 정확도로 해석하지 않는다.

## 되돌리기와 한계

`NPC_METRICS_ENABLED=0`으로 계측 파일 기록을 끌 수 있다. API, DB schema, 모델 호출 수와 응답 내용은 바뀌지 않는다. 파일 쓰기 실패를 별도 원격 모니터링으로 전송하지 않으며, 한 앱 인스턴스·한 worker 전제를 유지한다. 여러 인스턴스로 확장하기 전에는 공용 수집과 파일 충돌 정책이 필요하다.
