# TokenCounter 연결 재사용 실험

## 결론

GPT Pro 검토의 제안대로 llama.cpp의 `/apply-template`과 `/tokenize` 정확 검증은 유지하면서 `TokenCounter`의 HTTP 연결을 서비스 생명주기 동안 재사용한다. 한 최상위 생성 요청 안에서 완전히 같은 `messages`를 다시 세는 경우에만 SHA-256 키로 결과를 재사용하고, 요청이 끝나면 키와 값 모두 버린다. 정상 two-stage의 reply와 metadata 입력은 서로 다르므로 합치지 않으며 실제 공개 smoke에서도 한 턴당 tokenizer HTTP 요청은 4회였다.

이번 변경은 **입력 준비 구간 최적화**로 채택한다. 개발 세트의 총 prepare 중앙값은 0.578초에서 0.297초로 줄었지만, 확률적인 모델 생성 시간이 커져 전체 decision 중앙값은 2.531초에서 3.546초로 늘었다. 따라서 답변 전체가 항상 빨라졌다고 판단하지 않는다.

## 구현 경계

- `TokenCounter`가 하나의 `httpx.Client`를 지연 생성하고 앱 종료 때 닫는다.
- 캐시는 `ContextVar` 기반 최상위 `decide` 범위에만 존재한다. metadata 내부 호출은 같은 범위를 이어 쓴다.
- 캐시 키에 원문을 보관하지 않고 직렬화한 메시지의 SHA-256 digest만 사용한다.
- 성공한 정확 계산만 캐시한다. tokenizer 장애는 기존 `TOKENIZER_UNAVAILABLE`로 실패하며 추정값으로 후퇴하지 않는다.
- 서로 다른 reply/metadata 메시지, 다음 채팅 요청, 다른 실행 간에는 token 수를 공유하지 않는다.
- 비개인 지표에 `tokenizer_cache_hits`를 추가해 HTTP 요청 감소와 캐시 적중을 분리한다.

## 통제 측정

같은 로컬 llama.cpp와 메시지를 사용한 합성 측정이다. 시간은 해당 PC의 로컬 왕복이며 모델 생성은 포함하지 않는다.

| 조건 | 논리 요청 | client 생성 | tokenizer HTTP | cache hit | 경과 | token 결과 |
|---|---:|---:|---:|---:|---:|---|
| 변경 전, 같은 입력 2회/요청 | 20 | 40 | 80 | 0 | 12.003초 | 모두 35 |
| 변경 후, 같은 입력 2회/요청 | 20 | 1 | 40 | 20 | 0.582초 | 모두 35 |
| 변경 전 모사, reply/metadata 다른 입력 | 20 | 40 | 80 | 0 | 11.744초 | 25/28 |
| 변경 후, reply/metadata 다른 입력 | 20 | 1 | 80 | 0 | 0.388초 | 25/28 |

서로 다른 정상 입력의 HTTP 횟수는 그대로이고 결과도 같았다. 즉 정상 two-stage에서 주효한 변경은 중복 생략이 아니라 연결 재사용이다. 요청 내부 캐시는 retry나 동일 검증이 실제로 반복될 때만 작동한다.

## 실제 9B 개발 세트

EXP-20의 development 24개와 같은 모델·full metadata·4096/256 설정을 사용했다. 전후 모두 24/24가 첫 시도에 형식 성공했고 parse/transport 실패는 없었다. 출력은 샘플링되므로 대화 품질 A/B나 전체 지연의 엄밀한 paired 비교로 사용하지 않는다.

| 지표 | 변경 전 p50 / p95 | 변경 후 p50 / p95 |
|---|---:|---:|
| reply prepare | 0.281 / 0.326초 | 0.297 / 0.329초 |
| metadata prepare | 0.289 / 0.312초 | 0.000 / 0.016초 |
| 합계 prepare | 0.578 / 0.610초 | 0.297 / 0.341초 |
| decision 전체 | 2.531 / 3.753초 | 3.546 / 4.510초 |

변경 후 모든 정상 턴은 tokenizer HTTP 4회, request-scope cache hit 0회였다. 첫 reply 준비에서 client와 연결을 만든 뒤 metadata 및 다음 턴은 같은 연결을 재사용했다.

## 공개 smoke

재시작한 full/two-stage/llama_cpp 구성에서 새 합성 방문자로 연속 2턴을 보낸 뒤 즉시 reset했다. 화면·live·session·chat 2회·reset이 모두 200이었다. 첫 턴은 reply/metadata prepare 0.297/0.000초, 다음 턴은 0.000/0.015초였고 양쪽 모두 tokenizer 요청 4회, cache hit 0회였다. 전체 응답은 12.844/5.453초로 모델 inference 변동이 준비 구간 절감보다 컸다. 공개 quota 2회를 사용했으며 합성 대화는 삭제했다.

## 한계와 다음 판단

- localhost에서 새 client 생성 비용이 크게 나타난 합성 수치를 인터넷 환경의 절대 속도로 일반화하지 않는다.
- 실제 답변 시간의 대부분은 현재 9B의 두 번 생성이다. 이 변경만으로 체감 지연을 안정적으로 낮추지는 못한다.
- cache hit 0은 실패가 아니다. reply와 metadata의 정확한 입력이 다르기 때문에 의도한 결과다.
- 다음 기본 우선순위는 고정 주소, guest 지속성, DB 백업·복구, 자동 복구와 1→2→3→5명 부하 게이트다.
