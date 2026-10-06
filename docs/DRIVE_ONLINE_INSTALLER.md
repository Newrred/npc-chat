# Drive + Hugging Face 온라인 설치 검증 (2026-10-05)

2026-10-06 인수인계: 사용자 요청으로 공개 배포 URL/hash를 `desktop/releases/1.5.0-20261005.internal.json`에 추가했다. 아래 `.runtime`에만 보존한다는 문장은 최초 시험 당시 상태다. [다른 PC 재개](HANDOFF_20261006.md).

후속 [설치기0.3](WINDOWS_UNINSTALL.md)에 시작 메뉴/설치된 앱 등록과 선택적 제거를 추가했다. 앱·모델 원본은 동일하며 아래0.2 EXE 대신 새 산출물을 사용한다.

## 범위와 변경

Task48 설치 UI를 유지하며 사용자 제공 Drive 앱 공유 링크를 연결했다. `scripts/build_installer.py`는 정확한 drive.google.com/file/d/ID/view 공유 주소와 알려진 공유 query만 고정 drive.usercontent.google.com 다운로드 주소로 변환한다. 임의 query token 허용으로 확장하지 않는다. `Installer.cs`는 HTML 확인/권한/할당량 응답을 파일로 쓰기 전에 거부하고 기존 이어받기 캐시를 보존한다. 기존 HTTPS/크기/SHA256/압축 경로/설치 manifest 검증은 유지한다.

공개 링크와 release 설정은 ignored `.runtime`에만 보존한다. 공유 파일은 app.zip 1,079,371,075 bytes, SHA256 `adc3a6114632f9b2739d819aebd7c8419b3126eaf420a6ec1e9175d59b81c14a`이다. 모델은 Task48에서 확인한 HF 고정 commit의 동일9B Q4_K_M이다.

## 산출물

`.runtime/setup-online-drive-20261005/NPCChatSetup.exe`: 139,822,156 bytes, SHA256 `94aa5d9c342c782b602842757001dd625645618ddb779e254500643eea42fda8`.

옆에 payloads 폴더 없이 단일 EXE로 실행한다. 기본 설치 위치에 다른 버전이 있으면 비어 있는 전용 설치 폴더를 선택한다. 기존 다른 대상의 바로가기는 덮어쓰지 않는다. 임베디드 URL만 새로 연결했으며 앱/model hash는 기존 검증 산출물과 동일하다. 재압축으로 이미 업로드한 app.zip을 바꾸지 않았다.

## 실행 명령과 증거

```powershell
.runtime/dotnet/dotnet.exe run --project desktop/SetupChecks -c Release
venv/Scripts/python.exe -m pytest -q tests/test_build_installer.py
venv/Scripts/python.exe -m pytest -q
venv/Scripts/python.exe -m ruff check app scripts tests
venv/Scripts/python.exe -m compileall -q app scripts
.runtime/dotnet/dotnet.exe publish desktop/NpcChat.Setup/NpcChat.Setup.csproj -c Release -r win-x64 --self-contained true -o .runtime/setup-online-drive-20261005/bootstrap -p:InstallerManifestPath=<온라인 release.json 절대 경로>
NPCChatSetup.exe --preview <online-preview.png 절대 경로>
NPCChatSetup.exe --install-test <새 격리 설치 폴더>
.runtime/dotnet/dotnet.exe run --project desktop/SetupChecks -c Release -- --hf-probe <Drive 직접 다운로드 URL> <기존 app.zip 경로>
```

기준92개 → 설치 검사94개 통과. Python 관련15개, 전체733개(17.46초), Ruff/compileall 통과. publish 성공. 실제 온라인 선택 창 preview exit0 및 캡처 확인. `--hf-probe`는 명칭과 달리 같은 다운로드 helper의 일반 URL/로컬 파일 대조 검사이며, Drive의 끝1MiB206 응답/전체 크기/원본 바이트 일치 passed=true.

전체 다운로드 설치 검증은 `.runtime/setup-online-drive-install-20261005`에 격리한다. 개인 AppData/기존 설치/바탕화면 바로가기를 수정하지 않는다. 이 모드는 실제 EXE의 설치 엔진을 실행하며 클릭 UI 흐름 검증은 Task48 기록을 따른다.

최종 실제 `--install-test` exit0. 빈 캐시/동봉 payloads 없음 상태에서 Drive 앱1,079,371,075 bytes와 HF 모델5,627,044,224 bytes를 전부 새로 받아 SHA256 검증→압축 해제→설치 manifest 전체 검증→활성화까지 통과했다. `install-test.json` success=true/id=1.5.0-20261005/executable=true. 설치 후 cache/staging 비어 있음. 전송 중 캐시 파일을 추가로 읽으려는 관찰은 배타적 파일 잠금으로 PermissionError가 났으나 설치 실패가 아니며 설치기를 중단하지 않았다.

## 한계

설치된 `releases/1.5.0-20261005/NpcChat.Desktop.exe --smoke-widget --no-topmost --data-dir <격리 smoke 폴더>` exit0. `.runtime/setup-online-drive-smoke-20261005/smoke.json`: chat=true, 표정 shy_smile, anonymousBlocked=true, hideRestore=true. 실제 WPF/WebView2/FastAPI/SQLite를 실행했으며 모델 응답은 합성이다. 사용자 대화 데이터는 사용하지 않았다.

Drive 공유 권한 변경이나 제공 서버 다운로드 제한이 생기면 설치가 실패할 수 있다. 다운로드 확인/권한 페이지를 우회하거나 로그인하지 않는다. 현재 링크의 확인 없는 공개 파일 응답을 실측한 것으로 모든 Drive 링크의 동작을 보증하지 않는다. 설치기와 배포 파일은 내부 시험용이다. 업데이트·제거 등록·코드 서명·깨끗한 Windows·실제 모델 성능은 이 연결 검증 범위 밖이다.
