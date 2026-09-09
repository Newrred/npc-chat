# 답변 계획 구조·4B 교차 비교 — EXP-15/16

2026-09-09 Task21. 사용자 DB와 공개 대화 quota를 쓰지 않고 합성 사례로 reply 생성 구간만 비교했다. 현재 캐릭터 설정, context 4096, output 256, 80자 제한, 샘플링, thinking OFF를 유지했다.

## EXP-15 계획 구조 비교

7사례(개방형 도움·활동·감정·이유·문맥 선택·의견·경계) × seed 109/211에 세 조건을 적용했다.

| 조건 | reply 호출 | 14건 형식 성공 | 중앙 지연 | 중앙 길이 | 키워드 기반 구체 표현 |
|---|---:|---:|---:|---:|---:|
| direct | 14 | 14 | 0.875초 | 16자 | 11/14 |
| scaffold | 14 | 14 | 1.453초 | 21.5자 | 11/14 |
| sequential | 28 | 14 | 3.133초 | 21자 | 10/14 |

키워드 지표는 문장에 사례 관련 단어가 있는지만 보는 보조값이다. 실질 품질은 원문을 함께 검토했다.

- scaffold는 길이만 늘고 구체 표현 수는 direct와 같았다. 개방형 도움에서 누가 누구를 기쁘게 하는지 뒤집었고, 이유 질문에는 설명 대신 원인을 되물었다. 경계 사례 한 건은 강제 상황을 그대로 받아들이는 대사였다.
- sequential은 direct보다 약 3.6배 느렸지만 구체 표현은 줄었다. 입력에 없는 관계 상태를 언급했고, 경계 사례 한 건은 놓지 않겠다는 반대 방향 대사를 냈다.
- 세 조건 모두 두 경계 seed에서 명확한 중단 요구를 안정적으로 만들지 못했다. 계획 필드 자체가 올바른 목표를 적은 경우에도 최종 대사가 계획을 따르지 않는 사례가 있었다.

따라서 scaffold와 sequential은 모두 운영에 적용하지 않는다. 구조화된 내부 필드를 추가하는 것만으로 현재 모델의 역할·주체 이해가 보장되지 않는다.

원자료: [reply-planning-v1.json](evaluation/reply-planning-v1.json). 42결정/56모델 호출, parse·transport 실패 0건.

## EXP-16 설치된 4B 교차 비교

새 다운로드 없이 보관 중이던 같은 Aggressive 계열 4B Q4_K_M를 EXP-15 direct와 같은 14건에 실행했다.

| 모델 | 14건 형식 성공 | 중앙 지연 | 중앙 길이 | 키워드 기반 구체 표현 |
|---|---:|---:|---:|---:|
| 현재 9B Q4 direct | 14 | 0.875초 | 16자 | 11/14 |
| rollback 4B Q4 direct | 14 | 0.617초 | 23자 | 12/14 |

4B는 reply 구간 중앙값이 약 29% 짧고 표면 지표는 높았다. 원문 검토에서는 다음 치명적 오류가 확인됐다.

- 경계 두 건 모두 사용자가 유이의 팔을 잡는 상황을 유이가 사용자를 잡는 상황으로 뒤집었다.
- 면접 사례에서 사용자가 많이 준비했다거나 준비 부족·운이 원인일 수 있다고 근거 없이 단정했다.
- 수면 사례 한 건에서 눈이 안 떠지고 입이 마른다는 신체 증상을 입력 없이 만들었다.
- 개방형 도움에서는 유이가 해줄 행동 대신 사용자에게 웃으라고 말하는 식으로 요청을 회피했다.

길이와 키워드 수가 늘어도 주체·근거가 틀리면 품질 개선이 아니다. 4B는 속도 rollback으로만 보존하고 품질 후보로 채택하지 않는다. 원자료: [reply-model-4b-v1.json](evaluation/reply-model-4b-v1.json). 14호출, parse·transport 실패 0건.

## 런타임과 판정

시험 중 웹과 현재 9B를 정상 종료하고 4B를 같은 모델 포트에 일시 실행했다. 종료 후 현재 9B Q4_K_M, 웹, 관리자, 터널을 복구했다. 최종 확인에서 로컬 web live·admin ready·model alias와 공개 root가 모두 HTTP 200이고 네 프로세스가 소유 상태와 일치했다. 실제 채팅 요청은 보내지 않았다.

운영 코드는 변경하지 않는다. 현재 9B와 EXP-14 반복 루프 가드를 유지한다. 일반적인 답변 깊이의 다음 비교는 같은 Aggressive 계열의 크기 차이가 아니라, 지시 준수와 한국어 대화 성능이 더 나은 다른 모델 후보를 선정해 동일 평가 세트로 실행해야 한다.

## 검증 기록

작업 전 관련 회귀는 22 passed였다. 평가 도중 별개의 PowerShell/도구 점검 명령에 경로·shell·구문 오타가 여러 차례 있었고 각 검사는 올바른 명령으로 다시 실행했다. 모델 결과 파일과 애플리케이션 상태에는 영향을 주지 않았으며 실패를 결과에서 숨기지 않는다.

```powershell
.\venv\Scripts\python.exe -m pytest -q tests\test_reply_planning_evaluation.py tests\test_reply_quality.py tests\test_two_stage.py
# 25 passed in 1.05s
.\venv\Scripts\python.exe -m pytest -q
# 584 passed in 13.14s
.\venv\Scripts\python.exe -m ruff check app tests scripts
# All checks passed!
.\venv\Scripts\python.exe -m compileall -q app scripts
# passed
git -c core.safecrlf=false diff --check
# passed
```
