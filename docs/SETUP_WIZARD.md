# 설치 마법사 0.2 / 앱1.5

2026-10-05 후속 설치기0.3: [시작 메뉴·Windows 등록·선택적 제거 구현과 검증](WINDOWS_UNINSTALL.md). 기존0.2 산출물에는 이 기능이 없으므로 새0.3 EXE를 사용한다.

후속: 사용자 제공 Drive app.zip을 연결한 단일 EXE와 실제 온라인 설치 검증은 [Drive 온라인 설치 기록](DRIVE_ONLINE_INSTALLER.md)을 따른다. 아래 호스팅 대기 항목은 Task48 당시 상태다.

2026-10-05 사용자 요청: 새 앱과 같은 보라색 아이콘/자체 상단바, 설치 위치와 바로가기 선택, 앱·런타임·모델 설치, 완료 후 실행.

## 사용 흐름

1. 오프라인 ZIP 전체를 풀고 `NPCChatSetup.exe` 실행한다. 옆 `payloads` 폴더를 유지한다.
2. 전용 설치 폴더를 직접 입력하거나 찾아보기로 선택한다. 기본은 사용자별 Programs/NpcChat이다. 기존 다른 버전이 있으면 새 전용 폴더를 선택해야 한다. 이번 버전은 자동 업데이트를 구현하지 않는다.
3. 바탕화면 바로가기 생성 여부를 선택한다. 동봉 파일이 완비되어 있으면 오프라인이 기본이며, 실제 HTTPS 주소가 포함된 빌드에서만 다운로드 옵션을 선택할 수 있다. 파일 크기 확인은 사전 안내이며 설치 중 SHA256 검증을 별도로 수행한다.
4. 설치 중 현재 파일의 복사/다운로드 진행률과 검증 단계를 표시한다. 검증/압축 해제는 미정 진행 막대로 표시하며 전체 설치 진행률로 오해시키지 않는다. 닫기나 취소는 진행 중 작업을 안전하게 취소한 뒤 설정 화면으로 돌아간다.
5. 완료 화면에서 앱 실행 체크를 선택하고 완료를 누른다. 실행 요청 실패 시 완료 화면을 유지하고 재시도할 수 있다. 프로그램 실행 요청 성공과 실제 모델 준비 완료는 구분한다.

대화·기억·브라우저 식별자·위젯 설정은 변경하지 않는다. 바탕화면에 같은 이름의 다른 대상 바로가기가 있으면 덮어쓰지 않고 완료 화면에 설명한다. 설치 폴더 열기 및 완료 후 실행으로 새 앱에 접근할 수 있다.

## 구현 파일

- `desktop/NpcChat.Setup/SetupWindow.xaml(.cs)`: 자체 상단바, 설정/진행/완료 및 오류/취소/재시도, 폴더 선택, 저장 공간 안내, 바로가기/실행 선택.
- `SetupOptions.cs`: 설치 루트·보호 경로·기존 데이터/버전·공급원 사전 검사. 사전 검사는 파일을 만들지 않는다.
- `App.xaml.cs`: 기존 설치 엔진과 HTTP/로컬 공급원 연결, 미리보기/격리 UI 검증 실행.
- `NpcChat.Setup.csproj`, `SetupShortcut.cs`: 앱과 같은 EXE/창/바로가기 아이콘, 설치기0.2.0.
- `SetupUiChecks.cs`, `desktop/SetupChecks`: 실제 WPF 버튼/창 상태·오류/취소·실물 설치 및 앱 실행 검사와 핵심 회귀 검사.

## 검증

작업 전 설치 핵심64개/Python 관련25개 통과. 작업 후 핵심92개, 전체Python726개, Ruff/compileall 및 WPF 빌드(경고0/오류0) 통과. 실제 배포 산출물의 UI 검증 결과는 아래 후속 기록을 따른다.

```powershell
.runtime\dotnet\dotnet.exe run --project desktop/SetupChecks -c Release
venv\Scripts\python.exe -m pytest -q
venv\Scripts\python.exe -m ruff check app scripts tests
venv\Scripts\python.exe -m compileall -q app scripts
venv\Scripts\python.exe scripts/build_installer.py --package <앱1.5 동봉 폴더> --output .runtime/setup-wizard-20261005 --release-id 1.5.0-20261005
# 최종 ZIP을 새 폴더에 해제한 후:
NPCChatSetup.exe --ui-test <존재하지 않는 격리 폴더>
```

`--ui-test`는 개인 바탕화면 대신 지정 검증 폴더에 바로가기를 생성한다. 경로 오류/취소/전송 실패는 합성 실패를 사용하고, 재시도 설치는 실제 동봉 payload와 검증을 수행한다. 완료 버튼은 실제 설치 앱의 `--smoke-widget --no-topmost --data-dir <격리 폴더>`를 실행한다. 모델 응답만 합성이며 실제 WPF/WebView2/FastAPI/SQLite를 사용한다. 캡처와 결과 JSON은 검증 폴더에 보존한다.

## 산출물 기록

- 최종 권장본 `.runtime/setup-wizard-final-20261005/NPCChatSetup-offline.zip`: 6,765,264,331 bytes, SHA256 `c89b2a29fdecc7ec0607c504ee53dd934f92aa997cc4175ee0765b0bc79fa4bd`. 전체 ZIP CRC 통과. `ready/NPCChatSetup.exe`는 옆 payloads와 함께 바로 실행할 수 있다. 최종 publish 및 실제 창 preview exit0, 캡처 `installer.png` 확인. 모델 URL만 고정되어 있고 app URL은 미설정이다.
- 아래 최초 ZIP에서 전체 해제 후 `--ui-test` exit0. `.runtime/setup-wizard-ui-check-20261005/ui-test.json`: 잘못된 경로 거부, 닫기 취소, 실패 후 재시도, 실제 설치, 바로가기 생성/선택 해제, 앱 실행 실패 후 재시도/선택 해제, topmost OFF 모두 통과. 설치 앱의 합성 채팅 smoke exit0, cache/staging 및 소유 프로세스 목록 비어 있음. 기본 사용자 데이터와 바로가기는 변경하지 않았다.
- 최종본은 아래 설치 검증본에 제한된 HF redirect 처리를 추가한 것이다. 변경한 다운로드 경로는92개 검사와 실제 HF 부분 다운로드로 검증했다. 최종본의 전체 재설치 및 실제 모델 추론은 반복하지 않았다.
- `.runtime/setup-wizard-20261005/NPCChatSetup-offline.zip`: 6,765,261,907 bytes, SHA256 `493cb7dd48bcfcd646975309c86d14a2f4dd0c2b6af3ea96e6fd0db6f0d972e8`.
- 앱 payload1,079,371,075 bytes, 모델5,627,044,224 bytes(이전과 동일). 새 설치 공간은 빈 캐시 기준 약14.99GB이며 운반 ZIP/압축 해제 원본은 별도다.
- ZIP 전체를 `.runtime/setup-wizard-extracted-20261005`로 해제하면서 모든 파일 CRC를 검증했다. `NPCChatSetup.exe`와 `payloads/app.zip`, `payloads/model.gguf` 구성을 확인했다.
- 온라인 산출물은 생성하지 않았다(`online_created=false`). 고지40개 포함, 내부 시험용 배포 제한 유지.
- `.runtime/setup-wizard-20261005/preview-no-payload.png` 실제 렌더링 확인: 원본이 빠진 EXE의 설치 시작 비활성화·안내 정상.

## 별도 후속 범위

다운로드형은 실호스팅 주소가 아직 없어 실제 온라인 배포 검증 전이다. 사용자 요청 없이 업로드하지 않는다. 시작 메뉴/Windows 설치 앱 목록·제거기, 버전 업데이트/복구, 코드 서명, 깨끗한 Windows·혼합 DPI 검증과 판매 권리 검토는 이 설치 UI 완료와 구분한다. 모델은 그대로이며 새 UI가8GB VRAM 실측 성능을 보증하지 않는다.

## 온라인 설치 준비

사용자는 (1) 모델 저장소 URL과 정확한 단일 GGUF 파일명 (2) 앱 payload `app.zip`을 올릴 HTTPS 저장소/직접 다운로드 URL을 준비한다. 공개된 기존 모델 파일을 선택할 수 있으므로 반드시 모델을 재업로드할 필요는 없다. 다른 모델을 선택하면 단순 URL 교체로 끝나지 않으며 모델 설정·동작 검증·payload manifest/hash를 다시 만든다. 설치기는 선택한 파일의 정확한 byte 크기와 SHA256을 고정한다.

Hugging Face 링크 예시(실제 주소 아님): `https://huggingface.co/OWNER/REPO/resolve/COMMIT_SHA/model-name.gguf`. `blob` 페이지가 아니라 파일 다운로드 주소이며 `main` 대신 확정 commit을 사용한다. 임시 CDN 주소를 복사해 배포 설정에 넣지 않는다. 접근 승인/gated/private 모델은 별도 사용자 인증 흐름이 필요하므로 현재 무인 다운로드 설치의 범위 밖이다. 개발자 개인 토큰을 EXE에 넣거나 사용자에게 공유하지 않는다.

사용자가 제공한 [9B Q4_K_M 파일](https://huggingface.co/HauhauCS/Qwen3.5-9B-Uncensored-HauhauCS-Aggressive/blob/main/Qwen3.5-9B-Uncensored-HauhauCS-Aggressive-Q4_K_M.gguf)은 기존 동봉 모델과 크기5,627,044,224 bytes 및 SHA256 `2ca636d9e81d3d23ca9b60c234fe185d30ec082eeba69ce770fdb0c76559a4f5`가 일치한다. 재업로드 없이 사용할 수 있다. 모델 다운로드 주소는 `https://huggingface.co/HauhauCS/Qwen3.5-9B-Uncensored-HauhauCS-Aggressive/resolve/0a41c68809d375475f954be12ba7c40efa56c2a9/Qwen3.5-9B-Uncensored-HauhauCS-Aggressive-Q4_K_M.gguf`로 고정했다.

자동 redirect는 계속 OFF이며 설치 엔진이 HF 원본에 한해서 HTTPS 기본 포트의 HF/CDN 허용 목록으로 최대4회 이동한다. Range를 유지하고 외부 호스트/HTTP/사용자정보/루프는 거부한다. 실제 C# 다운로드 경로로 끝부분1MiB를 받아206/전체 크기/동봉 파일 바이트 일치를 확인했다. 전체5.63GB 신규 다운로드 검증은 아니며 임시 CDN 서명 URL은 저장하지 않는다.

검증 명령: `.runtime/dotnet/dotnet.exe run --project desktop/SetupChecks -c Release -- --hf-probe <위 고정 resolve URL> <동봉 모델 경로>`. 결과 passed=true, bytes=1048576, total=5627044224, host=us.aws.cdn.hf.co, range=true.

남은 준비물은 `.runtime/setup-wizard-20261005/app.zip`(1,079,371,075 bytes)을 제공할 공개 HTTPS 직접 다운로드 주소다. 로그인/만료 토큰 없는 고정 버전 주소를 사용하고 파일을 재압축하거나 교체하지 않는다. 현재 일반 호스트 redirect는 거부하므로 앱 호스팅 URL의 응답도 확인해야 한다. Google Drive 공유 페이지를 직접 다운로드 URL로 취급하지 않는다. 앱 주소 확보 후 두 URL을 포함한 온라인 EXE를 빌드하고 전체 신규 다운로드 설치를 검증한다.

준비 순서: 모델 페이지/파일 선택 → 현재 모델과 일치·사용 조건/고지 확인 → 앱 버전의 app.zip 업로드 → 안정적인 두 주소 확보 → 설치기 다운로드 호환/재개 검증 → 두 URL을 넣어 빌드 → 로그인 없는 환경에서 신규 다운로드 설치 검증. 공개 업로드는 별도 사용자 지시 후 수행한다.

공식 참고: [Hub 파일 다운로드](https://huggingface.co/docs/huggingface_hub/en/package_reference/file_download), [버전 지정 다운로드](https://huggingface.co/docs/huggingface_hub/en/guides/download), [gated 모델 인증](https://huggingface.co/docs/hub/models-gated). 확인일2026-10-05.
