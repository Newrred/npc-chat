# 공통 설치기 — 내부 시험판

2026-10-05 Task48: 설치기0.2/앱1.5 보라색 설치 마법사, 설치 폴더·바탕화면 바로가기 선택, 완료 후 실행 선택, 오류/취소/재시도를 추가했다. 설치 원본 누락은 시작 전에 안내하며 실제 주소가 없는 다운로드 옵션은 비활성화한다. [새 UI·검증·배포 산출물](SETUP_WIZARD.md). 아래 Task42 수치는 당시 기록이다.

2026-09-30 / Task42 / 설치기0.1.0, 설치 대상 앱1.4.0.

2026-10-02 정밀 검증: 앱 payload 압축·성공 후 캐시 정리·취소 staging 정리·동명 바로가기 보존을 보강했다. 새 ZIP6.77GB(기존7.89GB), 실물 한글/공백 경로 설치 및 무결성 검사 통과. 현재 높은 GPU 부하에서 설치 후 실제9B 채팅은 시간 초과로 실패했으며 설치 성공과 구분한다. [검사·실측·남은 제한](INSTALLER_REVIEW_20261002.md).

## 사용 방식

- 오프라인: `NPCChatSetup-offline.zip`을 전부 풀고 `NPCChatSetup.exe` 실행 → 설치 → 앱 실행. 옆의 `payloads` 폴더가 필요하다. Python/.NET SDK를 별도로 설치하지 않는다.
- 다운로드: 실제 HTTPS 주소를 넣어 빌드한 `NPCChatSetup-online.exe` 하나 실행 → 앱/모델 다운로드 → 동일한 검증과 설치. 아직 호스팅 주소가 없어 실제 다운로드 배포본은 생성하지 않았다.
- 기본 설치 위치는 `%LOCALAPPDATA%/Programs/NpcChat/releases/<release-id>`. 기존 대화·브라우저 세션·위젯 설정은 `%LOCALAPPDATA%/NpcChatDesktop`에 그대로 둔다.
- 일반 설치는 선택한 경우 바탕화면 바로가기를 만든다. 같은 이름의 다른 대상 바로가기는 보존한다. UI 테스트 모드는 격리 폴더에만 테스트 바로가기를 만들며 개인 데이터에 접근하지 않는다. 설치 창은 항상 위에 고정하지 않는다.

두 공급원은 파일 준비 → SHA256/크기 검증 → 별도 staging 추출 → 모델 복사 → 전체 패키지 검증 → release 이동 → current 기록 순서를 공유한다. 취소/전송 중단 시 캐시를 보존하고 재시도한다. HTTP Range를 지원하지 않는 서버의200응답은 처음부터 다시 받는다. 경로 탈출·중복 파일·연결 경로·manifest 변경·손상 파일은 거부한다.

## 빌드

```powershell
./venv/Scripts/python.exe scripts/build_installer.py --package <검증된-폴더형-패키지> --output <새-출력-폴더> --release-id 1.4.0-20260930
# 다운로드판도 만들려면 다음 두 옵션을 추가한다.
# --app-url https://호스트/app.zip --model-url https://호스트/model.gguf
```

출력의 `app.zip`과 `model.gguf`를 해당 HTTPS 주소에서 제공해야 한다. 로그인·토큰 없는 직접 다운로드 주소를 사용한다. 일반 호스트 리디렉션은 거부하며 설치기0.2는 HF 원본의 제한된 HTTPS CDN 이동만 허용한다. 설치기 안에 파일 hash/크기가 고정되므로 같은 URL의 파일을 임의 교체하면 실패한다. `bootstrap`은 빌드 중간 산출물이며 배포하지 않는다. 외부 업로드는 수행하지 않았다.

10월2일 압축 빌드 기준, 오프라인 운반 ZIP과 압축을 푼 원본 외에도 설치 디스크에 약15GB의 여유 공간이 필요하다. 새 설치가 성공하면 해당 payload 캐시를 정리하며 실패/취소 시에는 이어받기 캐시를 보존한다. 현재 시도의 staging은 정상적인 실패/취소 시 정리하지만, 강제 종료로 남은 옛 staging은 자동 삭제하지 않는다. 설치된 앱 자체는 약7.75GB이며 모델을 줄이지 않았다.

## 범위와 제한

신규 설치와 동일 release 재시도만 지원한다. 다른 버전 업데이트는 명시적으로 거부한다. 손상된 기존 release의 자동 수리, 제거 UI/Windows 앱 목록 등록, 데이터 백업/복원, 자동 업데이트는 후속 Task43/44다. current는 현재 release 문자열이며 고정 Launcher는 아직 없다. 바로가기는 해당 release EXE를 직접 가리킨다.

코드 서명/판매 배포 승인, GPU·드라이버·VC++ 자동 설치, 깨끗한 Windows 검증은 완료하지 않았다. 모델/이미지 등 권리 검토가 끝나기 전 내부 시험용만 빌드한다. hash 검증은 배포자 서명을 대체하지 않는다. 기존4070Ti ZIP 구동 확인은 이 새 설치기의 검증이 아니다.

## 검증 및 실패 기록

- `./venv/Scripts/python.exe -m pytest -q`: 722 passed (Task42 최초 구현 후).
- `./.runtime/dotnet/dotnet.exe run --project desktop/SetupChecks -c Release`: 공급원 수정 후26 checks passed. 신규 설치/동일 버전 재시도/활성화 직전 중단 복구/버전 변경 거부/경로 검사/손상/취소/HTTPS206이어받기·200재시작·잘못된 범위/로컬 복사 재개를 포함한다. HTTPS 응답은 합성이며 실제 호스팅 검증이 아니다.
- 초기 테스트 예외 분류 누락 및 WPF 네임스페이스 컴파일 오류는 수정 후 통과했다.
- 최종 관련 검사: `./venv/Scripts/python.exe -m pytest -q tests/test_build_installer.py tests/test_package_notices.py tests/test_desktop_package.py` →24 passed. 앞선 명령에서 파일명을 `test_package_desktop.py`로 잘못 지정해 수집 실패했으며 올바른 이름으로 재실행했다.
- `./venv/Scripts/python.exe -m ruff check app tests scripts`, `./venv/Scripts/python.exe -m compileall -q app scripts`, `git diff --check` 통과.
- **폐기한 접근:** self-contained EXE 뒤에 payload를 붙인7,888,794,179bytes 파일은 실제 실행 시 Windows가 `not a valid application for this OS platform`으로 거부했다. 작은 설치기 미리보기는 성공했지만 대형 EXE의 성공 근거가 되지 않았다. 최종 빌더는 이 형식을 만들지 않고 ZIP64 운반 파일을 만든다.
- 최종 `NPCChatSetup-offline.zip`: 7,888,794,545bytes, SHA256 `c70c1156da420fdbc856ded41ecac3fed331f444ffab76e81b93a83b7fbc94fb`. ZIP64 실제 추출/CRC 통과.
- 추출한 설치기의 `--install-test <한글·공백이-있는-새-폴더>` →exit0, `install-test.json` success=true/executable=true. 실제 앱/모델 전체 hash를 설치 엔진이 검증했다. 개발 PC의 격리 경로이며 깨끗한 Windows 검증이 아니다.
- 설치된 `NpcChat.Desktop.exe --smoke-widget --data-dir <새-합성-데이터-폴더>` →exit0. chat/nativeFace/anonymousBlocked/hideRestore, 숨긴 창 답장/읽음 해제/과거 이력 알림 제외 검사 통과. 실제 WebView2와 FastAPI를 사용하고 LLM 응답은 합성이다. topmost OFF이며 개인 데이터 접근 없음. GPU 실모델 재실행 검증으로 간주하지 않는다.
- 추출한 `NPCChatSetup.exe --preview <새-PNG>` →exit0. 오프라인 설명/설치·취소 버튼/고정 해제 창 렌더링을 확인했다. 일반 설치의 바탕화면 바로가기 생성은 개인 바로가기를 바꾸지 않기 위해 실물 테스트에서 실행하지 않았다.

테스트 실행은 `NPCChatSetup.exe --install-test <존재하지-않는-새-폴더>`이다. 성공하면 그 폴더의 `install-test.json`에 결과를 쓴다. 테스트 UI는 `--preview <새-PNG>`로 검증한다. 둘 다 사용자의 정상 설치/바로가기/대화를 바꾸지 않는다.
