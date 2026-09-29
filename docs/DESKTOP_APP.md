# Windows 데스크톱 위젯 시제품

앱1.4.0은 [간결한 자체 상단바](CHAT_WINDOW_CHROME.md)를 사용한다. 작업용 실행에서는 항상 위를 끈다.

최신 앱1.3.0의 텍스트 모드·빠른 답장·말풍선·Esc 숨김은 [플로팅 대화 안내](FLOATING_CHAT_UX.md)를 참고한다.

현재 위젯1.2.0의 크기/얼굴 보기/위치 저장/답장 알림은 [위젯 사용 안내](WIDGET_USABILITY.md)를 우선한다. 아래는 최초 Task36 개발 시제품 기록이다.

후속 Task37에서 [모델·런타임 동봉 폴더 패키지](PORTABLE_DESKTOP.md)를 만들었다. 아래 개발 시제품 실행 방식은 유지하며, 독립 폴더 실행과 남은 배포 게이트는 후속 문서를 우선한다.

2026-09-29, Task36. C# / WPF / .NET 10 네이티브 창과 트레이를 사용한다. 기존 채팅 화면만 WebView2로 표시하며 FastAPI와 llama.cpp의 대화 처리 구조는 유지한다. Windows 바탕화면에 떠 있는 위젯이며 Windows의 뉴스·위젯 보드 확장은 아니다.

## 사용하기

1. 빌드 시 만든 바탕화면 **NPC Chat** 아이콘을 실행한다. 모델 준비가 끝나면 대화 버튼이 활성화된다.
2. 얼굴이나 **대화하기**를 누르면 채팅창이 열린다. 기존 캐릭터 선택과 대화 기능을 사용한다. 답변 표정과 선택 캐릭터가 위젯 얼굴에도 반영된다.
3. 위젯 상단을 끌어 이동한다. `⋯` 메뉴에서 항상 위 표시와 숨기기를 선택한다.
4. 채팅창 X는 숨기기다. 알림 영역의 트레이 아이콘에서 다시 열 수 있다.
5. 위젯 메뉴 또는 트레이의 **완전히 종료**를 누르면 이 앱이 시작한 웹 서버와 모델도 종료된다.

별도 웹 서버를 미리 실행하지 않는다. 모델 8001 또는 전용 앱 8003 포트가 이미 사용 중이면 시작을 중단하며 다른 서버를 임의 종료하거나 인수하지 않는다. 공개 터널과 inspector는 실행하지 않는다.

## 저장과 실행 경계

- `%LOCALAPPDATA%/NpcChatDesktop`에 대화 DB(`data/chat.sqlite3`), WebView2 브라우저 저장소, 위젯 위치, 소유 프로세스 기록/로그를 둔다. 기존 웹 테스트 DB는 그대로이며 자동 복사하지 않는다.
- `.env`의 기존 모델 경로와 추론 설정을 읽는다. 앱 전용 DB·인증·계측 OFF 설정은 자식 프로세스에만 적용한다. 원본 `.env`는 수정하지 않는다.
- 전용 앱은 loopback에만 열고 실행마다 무작위 토큰을 요구한다. Host/Origin도 검사한다. WebView2는 같은 출처 요청에만 토큰을 붙이고 외부 탐색·새 창·다운로드·권한을 차단한다.
- 웹→네이티브 메시지는 허용된 캐릭터 얼굴 경로와 입력 중 상태만 처리한다. 임의 파일 접근이나 명령 실행 API는 없다.
- 네이티브 앱의 stdin 파이프가 끊어져도 감독 프로세스가 소유 서버를 정리한다. 감독 프로세스까지 강제 종료하거나 OS가 멈추는 모든 상황에서 즉시 정리를 보장하지는 않는다. 다음 실행은 자기 기록만 복구한다.

## 개발 환경과 빌드

SDK는 .NET **10.0.401**, WebView2 NuGet은 **1.0.4258.31**로 고정했다. SDK는 공식 Microsoft 배포 ZIP의 SHA-512를 공식 release metadata와 대조한 뒤 저장소의 ignored `.runtime/dotnet`에 설치했다. 전역 SDK를 교체하지 않았다. 현재 PC의 WebView2 Runtime 153.0.4234.48을 확인했다.

저장소 루트 PowerShell에서:

```powershell
./scripts/build-desktop.ps1 -Shortcut
./scripts/start-desktop.ps1
# 모델 없이 UI 개발용
./scripts/start-desktop.ps1 -Fake
```

결과는 `.runtime/desktop-app/NpcChat.Desktop.exe`다. .NET 런타임은 self-contained publish로 동봉된다. **아직 판매 가능한 독립 설치 패키지는 아니다.** 이 실행 파일은 현재 저장소의 Python venv, 서버 코드, llama.cpp, 모델, 얼굴 자산 및 설치된 WebView2 Runtime에 의존한다. 실행 파일만 다른 PC로 복사하면 동작하지 않는다. SDK 설치는 개발용이며 최종 실행에 SDK 자체가 필요한 것은 아니다.

## 검증 결과

| 검사 | 결과 |
|---|---|
| `./venv/Scripts/python.exe -m pytest -q` | 680 passed (신규 desktop 9개 포함) |
| `./venv/Scripts/python.exe -m ruff check app tests scripts` | 통과 |
| `./venv/Scripts/python.exe -m compileall -q app scripts` | 통과 |
| `node --test tests/frontend.test.cjs tests/inspector.test.cjs` | 29 passed |
| .NET Release build / self-contained publish | 오류 0, 경고 0 |
| 네이티브 `--smoke --data-dir <별도 테스트 폴더>` | 가짜 모델로 실제 채팅 전송, 얼굴 연동, 인증 없는 요청 403, 숨김/복원, 종료 확인 |
| 같은 테스트 폴더로 재실행 | 이전 답변 1개 복원 후 새 답변 확인 |
| 게시된 EXE smoke | 종료 코드 0, 채팅·얼굴·인증·복원 성공 |
| `--verify-real --data-dir <별도 테스트 폴더>` | 현재 9B 모델 준비, WebView2 초기화, 종료 성공; 실모델 대사 생성은 이 검사에 포함하지 않음 |
| 준비 전 취소 및 네이티브 부모 종료 | 소유 서버 기록이 없거나 비어 있음; 준비 전 취소는 START_CANCELLED/종료 코드 1 |

실행 증거와 캡처는 ignored `.runtime/desktop-smoke-2`, `.runtime/desktop-exe-smoke`, `.runtime/desktop-real-check`에만 보존한다. 첫 시도에서 숨긴 창의 WebView2 초기화가 멈춰, 비활성 표시 후 초기화하는 순서로 수정했다. 조기 취소 검사도 처음에는 반드시 기록 파일이 있어야 한다고 잘못 가정했으며, 프로세스 생성 전 취소 시 파일 자체가 없는 정상 경우를 포함해 재검증했다.

## 남은 범위

다중 모니터·서로 다른 DPI와 실제 사용 중 장시간 안정성은 수동 검증이 필요하다. 위치 복원은 현재 주 화면 작업 영역에 맞춘다. 트레이 두 번째 실행은 안내를 표시하며 첫 창을 자동 활성화하지 않는다. 이번 변경은 모델 품질 개선, LoRA 선택/학습, 휴대폰 연결, 소스 은닉 또는 오프라인 동봉 설치본을 구현하지 않는다.

위 문단은 Task36 당시의 남은 범위다. 이후 Task37에서 런타임·모델·자산 동봉 폴더 패키지, Task38에서 시작 진단/재시도, Task39에서 위젯 사용성을 구현했다. Task40에서 [의존성·라이선스 현황](DESKTOP_DEPENDENCIES.md)과 [설치·업데이트·제거·복구 설계](DESKTOP_INSTALLATION_PLAN.md)를 정리했다. 설치기 구현, 재배포 고지 완성, 권리 확정 및 깨끗한 Windows 검증은 아직 남아 있다. 대화 품질/LoRA 실험은 별도로 계속한다.
