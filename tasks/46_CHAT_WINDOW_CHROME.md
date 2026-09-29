# Task46 — 채팅창 자체 상단바

사용자 승인: Windows 기본 제목 표시줄을 간결한 앱 상단바로 교체하고 콘텐츠와 통일한다. WPF/WebView2/서버 구조는 유지한다. Task40/45 미커밋 변경을 보존한다.

기준: 앱1.3.0, 관련 Python9 tests 통과. 이동/크기 조절은 WPF WindowChrome으로 유지한다. 최소화·최대화/복원·닫기(숨김), Esc 기존 동작과 데스크톱 전용 웹 스타일을 구현한다. 실제 native smoke에서 창 버튼/복원/채팅/숨김을 확인한다. 혼합 DPI/Windows Snap 실사용은 별도 수동 게이트.

완료: 앱1.4.0, 관련35 Python/33 JS/13 C# 및 publish. native 초기 중단/복원 실패 뒤 수정·전체 통과. 작업 창 topmost OFF 사용자 지시도 반영했다. [명령·결과·한계](../docs/CHAT_WINDOW_CHROME.md).
