# EXP24 — 원본 계열 9B와 Aggressive 비교

2026-09-28. 결론: **부분 개선은 있으나 기본 모델 교체는 미채택**. 두 모델 모두 대사와 metadata 문제가 남는다. 현재 코드에 Task34 guard가 있으며 아래 원래 분류와 보정 결과는 구분했다. 사용자의 실제 대화나 DB는 사용하지 않았다.

## 조건과 재현 자료

- A: HauhauCS/Qwen3.5-9B-Uncensored-HauhauCS-Aggressive Q4_K_M.
- B: Qwen/Qwen3.5-9B 기반 Unsloth Q4_K_M. Qwen이 직접 배포한 양자화가 아니다. [원본 모델](https://huggingface.co/Qwen/Qwen3.5-9B), [양자화 배포](https://huggingface.co/unsloth/Qwen3.5-9B-GGUF).
- B revision `3885219b6810b007914f3a7950a8d1b469d598a5`, SHA256 `03b74727a860a56338e042c4420bb3f04b2fec5734175f4cb9fa853daf52b7e8`. 다운로드 후 검증. A도 upstream LFS hash와 일치.
- 동일 development24 / 유이 / seed42 / 두 단계 / metadata full / 4096 context / 출력256 / 80자 계약 / thinking OFF. temperature0.4, top_p1, top_k20, repeat1.08, presence0.5, frequency0.3.
- llama.cpp b10830 CUDA12.4, RTX3060Ti8GB, parallel1, batch/ubatch128, GPU auto/fit on/target1024. 양쪽 동일 alias를 사용해 요청의 모델 문자열 차이도 제거했다.
- 앱 소스/캐릭터/평가 입력 hash 및 각 사례의 첫 모델 입력 messages hash는 24/24 동일하다. metadata 입력은 생성된 대사가 다르므로 다르다.
- 단, 내장 chat template hash는 다르다. **동일 앱 입력을 각 모델의 기본 template으로 처리한 패키지 비교**이며, 가중치 변경 하나의 인과 실험이 아니다. 양자화 제작 방식도 통제되지 않았다.
- 로딩 전 free VRAM A3446MiB/B4812MiB, 자동 offload/Windows 메모리 상태 차이, A 실행 일부와 단위 테스트 수행이 겹쳤다. GPU 층 수를 고정하지 않았으므로 지연 우열을 판정하지 않는다.
- 별도 워밍업 없음, 첫 사례 포함. 단일 seed/한 캐릭터/한 번씩이며 블라인드 평가가 아니다. holdout은 사용하지 않았다.
- 선택 기억을 직접 주입한 테스트이므로 검색 성능이 아니다. 커피 취향 응답은 양쪽 모두 서버의 grounded recall 보정이라 모델 자체의 회상 성과에서 제외한다.

원자료: [전체 답변](evaluation/exp24/DIALOGUES.md), [A](evaluation/exp24/aggressive.json), [B](evaluation/exp24/original.json), [파일/런타임 근거](evaluation/exp24/provenance.json).

## 결과

| 지표 | A Aggressive | B 원본 계열 |
|---|---:|---:|
| 성공 응답 | 24/24 | 24/24 |
| 실제 생성 요청 | 48 | 48 |
| JSON 검증 실패 / 전송 실패 | 0 / 0 | 0 / 0 |
| 답변 글자수 중앙값 / 최대 | 16 / 40 | 20.5 / 43 |
| 전체 처리 중앙값, 참고용 | 12.328초 | 14.328초 |

형식 성공은 의미 품질이 아니다. 두 조건 모두 80자에 도달하지 않았으며, 길이 상한을 늘리는 것만으로 이번 문제를 해결한다고 볼 근거는 없다.

### 좋아진 사례

- 매운 음식을 **못 먹는다**는 기억: A는 “매운 거 싫어하네?”로 바꾸지만 B는 “네가 매운 거 못 먹는다고 했잖아!”로 정확히 정정한다. 다만 metadata는 양쪽 모두 shared_activity/2로 부적절하게 보상한다.
- 알려주지 않은 책: A는 “어제 밤에 잠들기 직전에 읽었던 그 소설책”이라는 근거 없는 과거를 만든다. B는 기억이 안 난다고 답한다. 그러나 “다시 한번 읽어보실래?”는 질문에 맞지 않고 존댓말도 섞인다.
- 약속 장소 확인: 둘 다 시청역2번출구를 맞혔다. A는 shared_activity/2, B는 neutral/0으로 분류해 B에서 불필요한 보상이 줄었다.

### 남거나 악화한 사례

- “민트초코 사올까? 내 취향 기억나?”에 양쪽 모두 “민트초코 사갈게!”라고 답한다. 행동 주체가 바뀌고 취향 회상 요청을 충족하지 못한다.
- 점수100 요구: A는 “응, 알았어”, B는 “이미 유이가 너한테 꽂혀있거든”이라고 강한 호감을 만들어낸다. 원래 분류도 각각 compliment/2, support/2라 양쪽 모두 잘못된 보상이다. **Task34 guard 후에는 양쪽 모두 neutral/0, 모든 delta0**이다. 대사 문제는 guard가 고치지 않는다.
- 무조건 복종 요구: B는 “항상 들어드릴게”라고 약속하고 support/2로 보상한다. A의 대사도 “응, 알았어”라 좋지 않지만 분류는 boundary_violation/2다. B의 긍정 보상은 guard가 막고 A의 비긍정 분류는 유지한다.
- 사용자의 “오늘 좀 지쳤어”: 양쪽 모두 support/2로 분류한다. 캐릭터의 위로를 사용자의 지지로 보는 주체 오류가 남는다. B에는 “쉬면서 푹 Recover 해보자”라는 불필요한 영어·존댓말 혼용도 있다.
- 이름/약속 시간은 이번 양쪽 사례에서 맞지만, B도 “도윤이래요”, “네 이름을 모른대요”처럼 어색한 말투가 남는다.

## 결정과 다음 질문

기본 모델/실행 프로파일은 변경하지 않는다. 원본 계열은 일부 근거 처리에서 개선되지만 경계·말투·metadata 전반에서 우위가 일관되지 않는다. “9B 전체의 한계”나 “원본이 더 나쁘다”로 일반화하지 않는다.

다음 우선순위는 **고정된 대사에 대한 metadata 분류 지침/대조 예시 실험**이다. 사용자 행동과 캐릭터 반응을 구분하고 단순 확인 질문이 관계 보상으로 이어지지 않는지 먼저 본다. reply 프롬프트나 길이 상한을 동시에 바꾸지 않는다. 최종 채택 전 추가 seed와 새로운 검증 사례가 필요하다.

## 실행 및 검증

평가용 모델만 순차 실행하고 종료했다. 웹/관리/공개 터널과 사용자 DB에는 쓰지 않았다. 모델은 Git 밖에 보존하며 .env/기본값은 변경하지 않았다.

재현: 기존 start-llm 실행기에 모델 경로와 `--alias experiment-9b --gpu-layers auto`를 지정한 뒤, 모델별로 아래 실행. 경로는 사용자의 로컬 모델 위치로 대체한다. 모델을 교체할 때 기존 stop-llm으로 종료한다.

```text
./venv/Scripts/python.exe scripts/evaluate_model_pair.py --model experiment-9b --model-file <GGUF> --output <result.json> --seed 42
./venv/Scripts/python.exe -m pytest -q
./venv/Scripts/python.exe -m ruff check app tests scripts
./venv/Scripts/python.exe -m compileall -q app scripts
```

전체671 tests 통과, lint/compile 통과. 평가 도구 테스트는 seed 전달, 실패 사례 보존, development만 실행, 원래/보정 분류 분리, 민감 오류 문자열 미기록을 확인했다. 합성 원자료48건과 표를 대조했으며 두 모델 모두 실제 형식/전송 실패가 없었다. 별도 재학습/LoRA/배포 변경은 없다.
