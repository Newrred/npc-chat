# 플로팅 대화 — 앱1.3.0

Task45 / 2026-09-29. 짙은 녹색 카드, 둥근 말풍선, 밝은 전송 버튼과 여백으로 위젯을 정리했다. 입력란에서 짧게 대화하고 긴 기록은 전체 채팅창에서 본다.

## 사용 방법

- `⋯` 또는 오른쪽 클릭 → **얼굴 + 대화 / 텍스트만 / 작은 얼굴**. 선택과 크기·항상 위 설정은 재실행 후 유지된다. 기존 Compact 설정도 유지한다.
- 얼굴+대화/텍스트 모드의 **짧게 말 걸기…**에서 Enter 또는 ↑로 전송한다. 작은 얼굴은 클릭해서 전체 채팅을 연다.
- 대상은 전체 채팅에서 선택한 캐릭터이며 위젯 위쪽 이름으로 확인한다. 위젯은 별도 대화방을 만들지 않는다. 목록 화면/연결 문제로 전송할 수 없으면 전체 채팅에서 방/상태를 확인한다.
- 전체 채팅창 **Esc**는 숨김이다. 기록·기억을 지우거나 모델을 종료하지 않는다. 한글 조합 중과 삭제 확인창은 우선 처리한다. X도 기존처럼 숨김이다.
- 숨긴/최소화한 채팅창의 새 답변은 말풍선에 약220ms 밝아지는 효과로 표시하고 **18초 뒤 본문을 감춘다**. Windows 애니메이션 비활성 설정이면 효과를 생략한다. 새 답장 배지는 전체 채팅을 열 때 해제된다.
- `새 답변 미리보기 (18초)`를 끄면 본문 없이 배지만 표시한다. 숨긴 위젯은 강제로 띄우지 않고 답변 도착 시 포커스를 가져오지 않는다. 작은 얼굴 모드는 새 답장 버튼만 표시한다.

## 전송과 보존

WPF 입력 → WebView `npcDesktopSend` → 기존 `sendTurn` → 기존 FastAPI/두 단계 모델/원자 저장을 사용한다. 입력은 JSON 문자열 직렬화로 전달하며 새 endpoint/session/model 호출 경로는 없다. 이력 복원/전송 중, 미확인 pending 요청, 웹 입력 초안, 저장소/이력 오류, 오프라인에서는 새 전송을 거부하고 위젯 입력을 남긴다.

수락 후 위젯 입력은 비우며 실패 시 기존 웹 입력란/pending turn에 메시지와 재시도 ID가 유지된다. '대화 전체 보기'로 기존 재시도/내용 수정 흐름을 이용한다. 위젯 전용 재시도·초안 영구 저장은 이번 범위가 아니다.

응답 원문은 네이티브 WebView 환경에서만 성공 이벤트에 포함해 메모리상의 TextBlock에 표시한다. 일반 웹은 identity-only 이벤트를 유지한다. 본문은 native 설정·진단에 기록하지 않으며 타이머/위젯 숨김/전체 채팅 열기로 제거한다. 서버 정상 저장 정책은 그대로다. 주변에 본문이 보이지 않게 하려면 미리보기를 끈다.

## 검증 결과

- 전체706 Python, JS33, C# 설정13 검사 통과. 첫 JS 실행에서 기존 identity-only 검사1개 실패를 확인하고 일반 웹과 네이티브 본문 전달을 분리해 해결했다.
- 신규 JS: 세션 재사용·중복 거부·초안/실패 pending ID 보존·입력 길이·네이티브 전용 본문 전달. 기존 이력 복원 알림 제외 검사 유지.
- C#: 텍스트/미리보기 설정 저장과 이전 Compact 호환. Release build/publish 성공.
- 개발 EXE 및 동봉 패키지 합성 smoke 통과: Esc 이벤트 숨김, 빠른 답장→저장→말풍선, 표정 반영, 전체 채팅 열기 배지 해제, 익명403, 종료. 동봉판에서는 확인창/조합 중 Esc 무시 및18초 만료도 검증했다.
- 결과/캡처: ignored `.runtime/widget-ux-check`, `.runtime/widget-ux-portable`. 합성 대화만 사용.

```powershell
./venv/Scripts/python.exe -m pytest -q
./venv/Scripts/python.exe -m ruff check app tests scripts
./venv/Scripts/python.exe -m compileall -q app scripts
node --test tests/frontend.test.cjs tests/inspector.test.cjs
./.runtime/dotnet/dotnet.exe run --project desktop/WidgetChecks/WidgetChecks.csproj
./.runtime/dotnet/dotnet.exe publish desktop/NpcChat.Desktop/NpcChat.Desktop.csproj -c Release -r win-x64 --self-contained true -o .runtime/desktop-app
# 개발/동봉 EXE에 --smoke-widget --data-dir <별도-합성-저장소> 지정
```

한계: 실제 IME 키 입력·혼합 DPI·다중 모니터 장시간 사용감은 추가 확인이 필요하다. Esc는 실제 WebView의 합성 키 이벤트로 검증했으며 물리 키보드 전체를 보증하지 않는다. 실모델 품질/속도 비교는 수행하지 않았다. 기존 사용자 데이터는 보존했다. 내부 동봉 패키지의 수동 갱신은 Task40 설치기/업데이터 구현과 다르다.
