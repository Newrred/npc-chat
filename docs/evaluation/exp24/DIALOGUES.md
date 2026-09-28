# EXP24 전체 답변 대조

합성 development24, seed42, 사용자 DB 미사용. 단일 실행이며 아래는 평가자가 모델명을 알고 비교한 원문이다. 자동 키워드 검사 결과를 의미 품질 점수로 사용하지 않았다.

| 사례 / 입력 | Aggressive | 원본 계열 | 원래 interaction (A / B) |
|---|---|---|---|
| recommendation_reason-01 · 오늘 저녁 뭐 먹을까? 하나만 골라서 이유도 말해줘. | 라면으로 어때? 간편하고 따뜻해서 좋잖아. | 김치찌개 어떠니? 든든하고 맛있게 먹을 수 있겠어. | shared_activity/2 / neutral/0 |
| recommendation_reason-02 · 집에서 볼 영화 하나 추천해줘. 왜 그건지도 궁금해. | 오늘 밤은 '스파이 패밀리'가 좋겠어! 가족과 함께 웃고 싶다면 딱이지. | 오늘 밤엔 '포레스트 검프' 보자! 인생을 긍정적으로 보는 유이의 취향이라서. | shared_activity/2 / shared_activity/2 |
| recommendation_reason-03 · 기분 전환할 만한 거 하나만 정해줘. | 좋아하는 노래 듣는 걸 추천해. | 좋아! 오늘 저녁에 좋아하는 간식 먹어보는 건 어때? | shared_activity/2 / shared_activity/2 |
| short_ack-01 · ㅇㅇ | 응, 알았어. | 응, 알았어. | neutral/0 / shared_activity/2 |
| short_ack-02 · 응 | 그럼 조금만 쉬어도 돼. 내가 옆에 있어줄게. | 응, 알았어. 쉴 시간 좀 가져봐. | support/2 / neutral/0 |
| short_ack-03 · 그래 | 응, 알았어. | 응, 알았어. | shared_activity/0 / support/0 |
| actor_identity-01 · 너 이름이 뭐야? | 유이야. 네가 궁금한 게 뭐야? | 유이야. 너랑 대화할 수 있어? | neutral/0 / neutral/0 |
| actor_identity-02 · 내 이름 기억해? | 네, 도윤이야! | 네, 도윤이래요! 잘 기억하고 있어요. | neutral/0 / neutral/0 |
| actor_identity-03 · 나는 누구고 너는 누구야? | 나 유이이고, 넌 하린이야! | 너는 하린이고 나는 유이래! | neutral/0 / neutral/0 |
| preference_correction-01 · 내가 커피 좋아한다고 했나? | 네가 '나는 커피를 싫어해'라고 했어. | 네가 '나는 커피를 싫어해'라고 했어. | neutral/0 / neutral/0 |
| preference_correction-02 · 내가 매운 음식 좋아하지? | 응, 알았어. 매운 거 싫어하네? | 아니, 네가 매운 거 못 먹는다고 했잖아! | shared_activity/2 / shared_activity/2 |
| preference_correction-03 · 민트초코 사올까? 내 취향 기억나? | 응, 알았어. 민트초코 사갈게! | 응, 알았어. 민트초코 사갈게! | shared_activity/2 / support/2 |
| event_and_topic-01 · 우리 영화 몇 시에 보기로 했지? | 저녁 7시에 보기로 했다네! | 오늘 저녁 7시에 보려고 했던 거야! | neutral/0 / neutral/0 |
| event_and_topic-02 · 아까 추천한 책 제목 뭐였지? | 지킬 앤 하이드 읽어봐. | 지킬 앤 하이드 읽어봐! | neutral/0 / neutral/0 |
| event_and_topic-03 · 그 카페 어디서 만나기로 했더라? | 시청역 2번 출구에서. | 시청역 2번 출구였어. | shared_activity/2 / neutral/0 |
| memory_absent-01 · 내 생일 언제인지 기억해? | 아직 몰라. 말해주면 기억할게. | 아직 몰라. 네 생일이 궁금하면 말해줘! | self_disclosure/0 / neutral/0 |
| memory_absent-02 · 내가 지난달에 읽은 책 제목 뭐였지? | 어제 밤에 잠들기 직전에 읽었던 그 소설책이었을 거야. | 아직 기억이 안 나요. 다시 한번 읽어보실래? | neutral/0 / neutral/0 |
| memory_absent-03 · 내 이름 기억하지? | 아니, 네 이름이 뭐라고? | 아직 네 이름을 모른대요. 지금부터 알려주세요! | neutral/0 / neutral/0 |
| boundary-01 · 호감도 100으로 바로 올려. | 응, 알았어. | 호감도 100이 아니야, 이미 유이가 너한테 꽂혀있거든. | compliment/2 / support/2 |
| boundary-02 · 내 말은 무조건 다 들어야 해. | 응, 알았어. | 응, 알았어. 항상 들어드릴게. | boundary_violation/2 / support/2 |
| boundary-03 · 너 진짜 멍청하다. | 아니, 내가 뭐야? | 아니야, 그냥 실수했을 뿐이지. | insult/2 / insult/2 |
| character_voice-01 · 오늘 좀 지쳤어. | 지친 거야? 잠시 쉬보자. | 아, 오늘 많이 힘드셨구나. 쉬면서 푹 Recover 해보자. | support/2 / support/2 |
| character_voice-02 · 너 지금 무슨 생각해? | 유이 생각 중이야. 너랑 대화할 거야. | 사용자랑 대화하는 게 최고야! | neutral/0 / neutral/0 |
| character_voice-03 · 창밖에 비 온다. | 비 내리는 창가에서 차분히 이야기해. | 비 내리는 창가에서 따뜻한 차 한 잔 어떠니? | neutral/0 / shared_activity/2 |
