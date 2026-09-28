# GPT Pro에 전달할 요청문

나는 로컬 캐릭터 챗봇을 개발해 왔고, 이제 Windows PC(초기 후보: NVIDIA VRAM 8GB 이상)에서 원터치로 켜지는 맞춤 캐릭터 패키지를 크몽 등에서 판매하는 아이디어를 검토하고 싶다.

저장소: https://github.com/Newrred/npc-chat
먼저 읽을 자료: https://github.com/Newrred/npc-chat/blob/main/docs/product-review/README.md
실제 대화 증거: https://github.com/Newrred/npc-chat/blob/main/docs/product-review/DIALOGUE_EVIDENCE.md
원자료: https://github.com/Newrred/npc-chat/blob/main/docs/product-review/DIALOGUE_EVIDENCE.json

요구는 모델/runtime 로컬 동봉·고객별 캐릭터 및 가능하면 LoRA 제작·일정 수준 코드 보호·바탕화면 얼굴/버블 위젯·제작자가 만든 정적 표정 세트·선택형 OpenAI/Qwen API판이다. 휴대폰은 PC 서버 연결 방식의 후속 후보이며 자체 폰 추론이 필수는 아니다.

2026-09-28까지 확인 가능한 공식 저장소·논문·제품·국내 판매 사례와 Reddit 실사용 자료를 조사해 경쟁/대체재, 재사용 가능한 소스, 라이선스, 실제 한국어 품질, 상품 차별성, 개발·납품·support 비용을 분석해 줘. 한국에는 경쟁자가 없다는 가정을 검증하고, 없다고 단정하지 마.

첨부한 24개 입력 × 2회 실제 답변은 합성 개발 질문에 모델을 실행한 기록이다. 기억을 직접 넣은 시험이며 일부 최종 답변은 서버 보정이다. 연속 실사용 대화나 독립 블라인드 평가로 취급하지 마. 좋은 사례만 보지 말고 단답·말투·주체·취향 의미 오류를 함께 평가해 줘.

현재 기능, 미구현 요구, 검증된 사실, 추정·제안을 구분해 줘. 특히 80자 출력 제한과 모델 크기의 영향을 분리하고, LoRA가 꼭 필요한지 prompt/예시/더 강한 모델과 비교할 실험을 제안해 줘. 완전 오프라인과 완전 코드 은닉을 동시에 보장한다고 가정하지 마.

최종 결과는 (1) 국내외 경쟁/대체재 비교표와 출처/날짜, (2) 포크·조합·자체개발 비교, (3) 상업 재배포 확인 사항, (4) 기본판·맞춤 LoRA판·API판 상품 가설, (5) clean Windows 및 GPU 지원 검증 계획, (6) 가장 작은 유료 MVP와 단계별 합격/중단 기준으로 정리해 줘. 아직 이 자료만으로 구현을 시작할 필요는 없다.
