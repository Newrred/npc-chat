# NPC Chat 독립 폴더 패키지

Task37, 2026-09-29. 내부 검증용이며 판매/공개 배포 승인본이 아니다.

앱1.4.0: [자체 상단바와 창 제어](CHAT_WINDOW_CHROME.md). 작업용 smoke/fake 실행은 항상 위 OFF이며 일반 사용자 설정을 덮어쓰지 않는다.

Task45 업데이트: 앱1.3.0에서 얼굴+대화/텍스트/작은 얼굴을 선택하고 플로팅 입력으로 대화한다. 새 답변 미리보기는18초 후 감추며 메뉴에서 끈다. 전체 채팅 Esc는 기록을 유지한 채 숨긴다. [사용법·검증](FLOATING_CHAT_UX.md).

Task40에서 [실제 의존성/고지 조사](DESKTOP_DEPENDENCIES.md) 및 [설치·업데이트·제거 설계](DESKTOP_INSTALLATION_PLAN.md)를 완료했다. 아래 폴더형 실행 방식은 그대로이며 설치기·업데이터는 아직 미구현이다.

Task39 업데이트: 앱1.2.0에서 위젯 오른쪽 아래를 드래그하거나 `⋯`/오른쪽 클릭 메뉴로 크기를 바꾼다. **얼굴만 보기**와 **항상 위**는 재실행 후 유지한다. 얼굴 보기에서는 얼굴을 드래그해 이동한다. 모니터별 위치를 기억하고 화면 배치 변경 시 복구하며, 메뉴의 **화면 안으로 위치 복구**로 주 화면에 돌려놓을 수 있다. 숨긴 채팅에 새 답변이 도착하면 위젯 배지를 누르거나 채팅창을 활성화해 확인한다. 실제 혼합 DPI 모니터 이동은 추가 검증이 필요하다.

Task38 업데이트: 앱1.1.0에서 위젯 `⋯` 또는 트레이 → **실행 상태 / 문제 해결**을 열 수 있다. 시작 실패 시 자동으로 안내 창이 나오며 원인 조치 후 **다시 시도**한다. **진단 파일 저장**은 대화·경로·키·원문 로그 없이 단계/오류 코드/경과시간/앱·OS 버전만 저장한다. 다른 PC에서 실행이 안 되면 이 파일을 이용해 점검한다. 최종706 Python tests, 실패→재시도→채팅, 실제 모델 부모 종료 정리를 검증했다. manifest는 재생성되는 Python 캐시를 제외하고 원본 파일을 검사한다.

## 실행과 종료

폴더 전체를 보존하고 `NpcChat.Desktop.exe`를 실행한다. 모델이 준비되면 얼굴 위젯에서 대화하기를 누른다. 채팅 X는 숨김이며 트레이/위젯 메뉴의 **완전히 종료**가 모델까지 종료한다. 8001/8003 포트를 다른 서버가 쓰고 있으면 먼저 해당 서버를 정상 종료해야 한다.

현재 패키지는 Windows x64 / NVIDIA GPU용이다. Python 설치, .NET SDK 설치, pip 명령, 웹 주소 입력 없이 실행하도록 구성한다. CUDA 추론 DLL, Python embedded, .NET, 고정 WebView2, 모델, 정적 얼굴을 폴더에 포함한다. NVIDIA 그래픽 드라이버와 Windows 시스템 구성요소는 운영체제 전제 조건이다. 이 PC에서의 검증이 다른 PC 호환성 검증을 대신하지는 않는다.

대화와 위젯 위치는 `%LOCALAPPDATA%/NpcChatDesktop`에 저장된다. 폴더를 옮겨도 같은 Windows 사용자의 기록은 유지된다. 검증 명령은 `--data-dir`로 별도 폴더를 사용한다. 실행 중 폴더를 이동/삭제하지 않는다. 업데이트는 종료 후 새 폴더로 교체하며 사용자 AppData는 보존한다. 제거는 종료 후 프로그램 폴더 삭제이며, 대화 데이터 삭제는 AppData를 따로 지워야 한다.

## 포함 범위와 경계

- `runtime/python`: Python 3.12.10 embedded + 현재 검증 버전으로 고정한 32개 Python 배포 패키지. 개발 venv와 전역 Python은 사용하지 않는다. 사용자 site/PYTHONPATH/.pth 자동 로딩을 끈다.
- `runtime/webview2`: Fixed Version 153.0.4234.48 x64. 설치된 Edge/WebView2 대신 이 폴더를 명시한다.
- `runtime/llama`: 현재 검증된 llama.cpp CUDA12 추론 엔진과 DLL.
- `models/model.gguf`: 현재 Aggressive9B Q4_K_M 모델의 독립 복사본.
- `desktop-package.json`: 상대 경로와 허용된 추론 설정만 포함한다. `.env`를 복사하거나 읽지 않는다. 자식 프로세스에는 OS 필수 환경만 전달한다.
- `package-manifest.json`: 포함 파일의 크기와 SHA-256. 배포 서명이 아니라 파일 동일성 점검용이다.
- 소스는 아직 읽을 수 있다. 압축/폴더 패키징을 소스 은닉으로 취급하지 않는다.

이 패키지에는 개인 대화 DB, API 키, 공개 터널 정보, 원본 개발 `.env`를 포함하지 않는다. 합성 채팅 smoke fixture만 검증용으로 포함한다. 공개 판매 전 모델·원본 캐릭터/이미지·각 런타임의 재배포 권리와 고지, 코드 서명 및 지원 Windows/드라이버 범위를 별도로 확정해야 한다. 특히 현재 캐릭터 자산을 상품화 승인 자산으로 간주하지 않는다.

## 빌드

`scripts/build-desktop.ps1`로 실행 파일을 먼저 publish한다. `scripts/package_desktop.py`에 `--output`, `--python-zip`, `--model`, `--llama`, `--webview`, `--publish` 경로를 명시한다. 기존 출력 폴더가 있으면 덮어쓰지 않고 실패한다. Python ZIP SHA-256을 고정 확인하고, 의존성은 `desktop/requirements-runtime.lock`의 버전으로 wheel 설치한다. 전체 파일 hash 계산을 마친 후 manifest를 생성한다. 빌드 중 오류가 난 폴더는 실행/배포 완료본으로 취급하지 않는다.

런타임은 개발 환경의 보안 최신 버전을 자동 선택하지 않는다. 재현성 있는 내부 검증 버전이며 외부 배포 전 Python과 고정 WebView2의 보안 업데이트 검토 및 회귀 검증이 필요하다. 실행 시 업데이트를 다운로드하지 않는다. 폴더 재배치는 테스트하지만 깨끗한 별도 PC와 네트워크 차단 환경 검증은 별도 항목이다.

공식 근거: [Python embedded 배포](https://docs.python.org/3.12/using/windows.html#the-embeddable-package), [Python 3.12.10 배포](https://www.python.org/downloads/release/python-31210/), [Microsoft WebView2 Fixed Version 배포](https://learn.microsoft.com/microsoft-edge/webview2/concepts/distribution).

## 검증 상태

완료: 원본 저장소 밖으로 폴더를 이동하고 작업 디렉터리를 Windows TEMP로 바꾼 상태에서 실행했다. 잘못된 NPC_BASE_URL, NPC_ACCESS_MODE, PYTHONPATH, WebView2 경로 및 HTTP_PROXY를 전달해도 fake 채팅과 실제9B 채팅이 성공했다. 프로세스 실행 파일을 관찰해 Python·llama-server·WebView2 모두 이동한 패키지 내부 경로임을 확인했다. 실모델 입력 `안녕`에 `안녕! 유이랑 친하게 지내자.`가 표시되었고 smiling 표정 반영, 익명 요청403, 창 숨김/복원, 종료 후 소유 프로세스 기록이 빈 상태임을 확인했다. 이는 1턴 실행 검증이며 대화 품질 개선 결과는 아니다.

검증 중 발견한 문제와 수정:

- embedded Python `_pth`의 상위 경로에 Windows 역슬래시를 사용해 모듈 검색 경로를 바로잡았다.
- 네이티브 smoke 도구의 HTTP 검사가 외부 프록시 환경변수를 따르던 문제를 고쳐 loopback 직접 연결로 고정했다.
- 환경 격리 시 NVIDIA NVML이 필요로 하는 ProgramFiles 계열 Windows 환경변수도 보존하도록 수정했다. 첫 실제 모델 실행 실패 뒤 재검증은 성공했다.

자동 검증: 전체688 Python tests, 화면29 tests, Ruff/compileall, .NET publish 통과. 패키지 신규8개 tests는 상대 경로·금지 설정·개인 파일 제외·덮어쓰기 차단·hash 변조/누락 검출을 다룬다. 기존 desktop9개 tests도 유지한다. 기본 프로젝트 DB 및 모델 설정은 변경하지 않았다.

사용한 명령:

```powershell
./venv/Scripts/python.exe -m pytest -q
./venv/Scripts/python.exe -m ruff check app tests scripts
./venv/Scripts/python.exe -m compileall -q app scripts
node --test tests/frontend.test.cjs tests/inspector.test.cjs
./scripts/build-desktop.ps1
# 패키지 폴더에서 별도 테스트 저장 경로를 지정
./NpcChat.Desktop.exe --smoke --data-dir <테스트-폴더>
./NpcChat.Desktop.exe --smoke-real --data-dir <테스트-폴더>
./runtime/python/python.exe scripts/verify_desktop_package.py .
```

검증 캡처/결과는 개발 저장소의 ignored `.runtime/portable-fake-check-2`, `.runtime/portable-real-chat-2`에 보관하며 패키지에 넣지 않는다. 완성 폴더 약7.8GB이며 GGUF가 약5.6GB다. 실사용 기록은 별도 AppData이므로 검증 대화가 기본 채팅방에 나타나지 않는다.

다음 게이트: 깨끗한 Windows/4070Ti PC에서 첫 실행·드라이버·VC++ 구성요소·네트워크 차단·장시간 사용을 검증한다. 이후 재배포 고지/자산 권리와 보안 업데이트 기준을 확정하고 설치 프로그램·서명·업데이트/제거 UI를 추가한다. 현재 단계는 설치 마법사가 없는 폴더형 실행 패키지다.
