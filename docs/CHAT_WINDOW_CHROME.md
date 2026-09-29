# 자체 채팅 상단바 — 앱1.4.0

Task46 / 2026-09-29. Windows 기본 제목 표시줄을 얇은 NPC CHAT 상단바로 교체했다. 배경/구분선/버튼과 웹 채팅의 헤더·말풍선·입력창을 연한 녹색 계열로 맞췄다. 일반 브라우저/모바일 스타일은 유지한다.

- 상단 빈 영역 드래그로 이동, 더블클릭으로 최대화/복원. 창 가장자리에서 크기 조절. WPF WindowChrome이 OS 창 동작을 담당한다.
- 오른쪽 버튼: 최소화, 최대화/복원, 닫기. 닫기는 기존처럼 숨김이며 모델 종료/기록 삭제가 아니다. Esc 동작도 유지한다.
- C# ChatShell은 창 제어만 담당하고 대화는 기존 WebView2/FastAPI 경로를 사용한다. 네이티브에서만 `desktop-shell` 클래스를 붙여 웹 스타일을 조정한다.
- 작업용 smoke/fake 실행에서는 표시 전부터 항상 위를 강제로 끈다. 다른 수동 검증은 `--no-topmost`를 사용한다. 저장된 사용자 Topmost 선호를 수정하지 않는다. 사용자 지시를 AGENTS.md에도 기록했다.

## 검증 및 한계

기준 관련9 Python tests 통과. 변경 후 관련35 Python/33 JS/13 C# 검사, Release publish와 diff 검사 통과. 네이티브 smoke에서 실제 버튼 Click 이벤트를 통해 최소화·최대화·복원·닫기/재열기와 크기 변경 후 WebView 배치를 확인하고, 기존 빠른 답장/Esc/미리보기/종료도 검증했다. 캡처는 ignored `.runtime/chat-chrome-check-3`에 있다.

첫 smoke는 일부 캡처 후 최종 결과 없이 종료되어 통과로 인정하지 않았다(원인 미확정). 두 번째는 maximize→restore 검사 실패를 확인했다. 비동기 SystemCommands 전송 대신 WPF WindowState를 직접 바꾸도록 수정한 뒤 세 번째 전체 smoke가 통과했다. 실제 마우스로 드래그/리사이즈, Windows Snap 및 혼합 DPI/작업 표시줄 배치는 수동 추가 검증 대상이다. 전체706 Python tests는 직전 Task45 결과이며 이번에 재실행한 것은 관련35개다. 모델 비교/개인 데이터 migration은 없다.

```powershell
./venv/Scripts/python.exe -m pytest -q tests/test_desktop.py tests/test_desktop_package.py tests/test_desktop_diagnostics.py
node --test tests/frontend.test.cjs tests/inspector.test.cjs
./.runtime/dotnet/dotnet.exe run --project desktop/WidgetChecks/WidgetChecks.csproj
./.runtime/dotnet/dotnet.exe publish desktop/NpcChat.Desktop/NpcChat.Desktop.csproj -c Release -r win-x64 --self-contained true -o .runtime/desktop-app
# EXE --smoke-widget --data-dir <별도-합성-저장소>
git diff --check
```

사용자는 기존 바로가기를 다시 실행하면 된다. 별도 설정/DB 변경이 없다. 다음은 실제 사용감 확인이며 설치·라이선스 후속 Task41~44는 별도 대기다.

최종 동봉판 `.runtime/chat-chrome-portable` smoke도 종료코드0과 모든 결과 파일을 확인했다. 시작 시 topmost가 꺼져 있는 검사까지 포함한다. 개발/동봉 실행 파일1.4.0과 전용 CSS를 갱신했으며 `python scripts/verify_desktop_package.py <패키지>` 결과 valid=true, changed_or_missing=[]였다. 개인 AppData는 수정하지 않았다.
