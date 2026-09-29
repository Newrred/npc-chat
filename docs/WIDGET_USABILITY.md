# 위젯 크기·위치·답장 알림

Task39, 데스크톱 앱1.2.0. 위젯 `⋯` 또는 오른쪽 클릭으로 메뉴를 연다.

## 사용법

- 오른쪽 아래 `◢`를 드래그하면 75~160% 범위에서 크기가 바뀐다. 메뉴의 작게/보통/크게는 80/100/130%다.
- **얼굴만 보기**는 카드/이름/상태를 접고 얼굴과 답장 배지를 남긴다. 얼굴 클릭은 채팅 열기, 얼굴 드래그는 이동이다. 오른쪽 클릭 메뉴는 계속 사용할 수 있다.
- **항상 위에 표시**, 크기, 보기 모드, 모니터와 위치는 재실행 후 유지한다.
- 채팅창을 숨기거나 최소화한 동안 새 응답이 완료되면 위젯에 **새 답장**이 표시된다. 클릭하면 해당 캐릭터 채팅을 열고 배지를 지운다. 채팅창을 직접 활성화해도 읽음 처리한다.
- 위젯 자체를 숨겼다면 강제로 다시 띄우지 않고 트레이 설명에 새 답장 상태를 표시한다. 소리나 답변 본문 팝업은 없다.
- 화면 배치가 바뀌면 작업 영역 안으로 위치를 맞춘다. **화면 안으로 위치 복구**는 주 화면으로 되돌린다.

## 저장과 모니터 처리

기존 AppData `widget.json`을 버전 있는 설정으로 확장했다. 이전 `[Left, Top]` 좌표는 처음 읽을 때 유지해 표시한 뒤 새 형식으로 전환한다. 대화 DB는 변경하지 않는다. 설정은 임시 파일을 거쳐 교체하며 잘못된 JSON/미지원 버전은 기본 설정으로 복구한다. 저장 권한 오류는 위젯 상태의 도움말로 알린다.

창 크기는 WPF 논리 단위로 유지한다. 모니터 선택과 위치는 PerMonitorV2 창의 실제 픽셀 작업 영역을 사용하며, 해당 영역에서 위젯이 이동 가능한 범위의 비율로 저장한다. 모니터가 없어지면 주 모니터로 복구한다. DPI 변경 이후 위치를 다시 맞추고 장치 변경 이벤트 구독은 창 종료 시 해제한다. 작업 영역보다 위젯이 큰 극단적 환경에서는 상단을 보이게 놓으며 크기를 줄일 수 있다.

관련 API 동작은 [Microsoft High DPI 문서](https://learn.microsoft.com/en-us/windows/win32/hidpi/high-dpi-desktop-application-development-on-windows)와 WPF의 DPI 변경 흐름을 대조했다. 실제 혼합 DPI/모니터 분리·연결 검증은 아직 완료하지 않았다.

## 알림 경로

프런트가 채팅 API의 유효한 새 답변을 화면에 추가한 경우에만 `npc-reply-committed` 이벤트를 보낸다. 저장 이력 로딩과 실패 응답은 알림을 만들지 않는다. WebView2 연결은 캐릭터 식별자와 turn UUID만 전달하고 답변 본문은 전달하지 않는다. 네이티브는 허용된 출처·캐릭터·UUID를 검사하고 최근256개의 중복 알림을 제거한다. 위젯의 미확인 알림은 실행 중에만 유지하고 별도로 영구 저장하지 않는다.

## 검증

- 기준 53c444a 및706 Python tests. 최종 `./venv/Scripts/python.exe -m pytest -q`: **706 passed**.
- `node --test tests/frontend.test.cjs tests/inspector.test.cjs`: **31 passed**. 새 응답 식별자만 전달, 실패/과거 이력 무알림 포함.
- `desktop`에서 `../.runtime/dotnet/dotnet.exe run --project WidgetChecks/WidgetChecks.csproj -c Release`: **11 checks passed**. 음수 모니터 좌표, 제거된 모니터, 큰 창, 잘못된 크기, 설정 저장/복원, 이전 좌표 이관, 손상/누락 설정 포함.
- `./scripts/build-desktop.ps1`: publish 통과. 최초 빌드의 Guid.TryParse discard와 이벤트 인자 이름 충돌을 수정 후 통과했다.
- `./venv/Scripts/python.exe -m ruff check app tests scripts`, `./venv/Scripts/python.exe -m compileall -q app scripts`, `git diff --check`: 통과.
- `NpcChat.Desktop.exe --smoke-widget --data-dir <별도 폴더>`: 가짜 모델을 이용한 실제 WebView 전송/숨긴 채팅창 새 답장/위젯 배지/열기 후 제거/과거 이력 무알림/표정/403/종료 검증. 개발 실행을 같은 폴더로 두 번 실행해 130%·얼굴 보기·항상 위 OFF 복원을 확인했고 동봉 패키지도 통과했다.
- 증거는 ignored `.runtime/widget-ui-smoke` 및 `.runtime/portable-widget-smoke`의 JSON과 `widget-unread.png`에 보존한다. 개인 대화는 테스트에 사용하지 않았다.

물리적으로 서로 다른 배율의 모니터 이동/분리, 실제 마우스 드래그 감각과 작은 크기 가독성은 사용자 장비에서 추가 확인할 항목이다. 이번 변경은 모델 품질 실험이 아니며 실제 LLM 호출을 추가하지 않는다.
