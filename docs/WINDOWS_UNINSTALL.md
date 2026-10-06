# Windows 등록·선택적 제거 (설치기0.3 / 앱1.5)

## 동작

설치 완료 시 현재 사용자 시작 메뉴의 `NPC Chat (설치 식별자)` 폴더와 HKCU의 Windows 설치된 앱 목록에 등록한다. 다른 사용자·관리자 권한·시작 프로그램 등록은 사용하지 않는다. 설치 위치별 식별자로 다른 설치를 덮어쓰지 않는다. 제거 명령은 설치 루트의 `NPCChatUninstall.exe --uninstall <루트>`다. 등록 실패 시 앱 파일은 남기되 성공으로 표시하지 않고 같은 설치에서 재시도한다.

제거기는 새 보라색 UI를 사용한다. 기본은 **대화 기록·설정 보존 / 모델 보존**이다. 대화 삭제 선택 시 현재 사용자의 기본 `NpcChatDesktop` 데이터 전체(대화·기억·관계·브라우저 식별 정보·설정·백업·runtime)를 삭제한다는 확인을 다시 받는다. 다른 설치와 공유하는 데이터임을 명시한다. 임의 `--data-dir` 폴더는 탐색하거나 삭제하지 않는다. 모델 보존 시 설치 루트 `retained-models/<sha256>.gguf`로 이동한다. 보존 모델의 자동 재사용은 아직 구현하지 않았다.

제거기는 설치기의 같은 self-contained 바이너리를 별도 이름으로 복사한다. 설치 중 약140MB가 추가된다. 실행 중인 자신도 삭제할 수 있도록 임시 폴더 복사본에서 제거 UI를 실행하고, 종료 후 숨겨진 PowerShell helper가 정확히 복사본 EXE와 빈 임시 폴더만 지운다. recursive shell deletion은 사용하지 않는다.

기존0.2 설치기는 자동으로 바뀌지 않는다. 새0.3 설치기로 동일 release의 설치 폴더를 선택하면 검증 후 등록을 추가할 수 있다. 다른 release로 자동 업데이트하는 기능은 아직 없다. 앱/모델 payload는 바뀌지 않아 Drive app.zip 재업로드가 필요 없다.

## 삭제 범위와 실패 처리

- 임베디드 release와 설치 소유 정보의 루트/버전/manifest hash를 대조하고, 제거 EXE hash 및 manifest hash를 검사한다.
- 소유 manifest 파일과 해당 `.py` 소스에 대응하는 CPython `__pycache__`만 제거한다. 설치 목록에 없는 개인 파일/폴더는 보존한다.
- 데이터 경로와 설치 경로가 겹치거나 junction/symlink가 있으면 사전 거부한다. 소유 파일/선택한 데이터의 잠금을 삭제 전에 검사한다.
- 앱의 기본 데이터 singleton과 같은 mutex를 잡고 설치 잠금도 사용한다. 실행 중이면 트레이에서 완전히 종료하라는 안내를 내고 재시도할 수 있다. 다른 프로세스를 강제로 종료하지 않는다.
- 시작 메뉴·바탕화면 바로가기는 실제 대상이 이번 앱일 때만 제거한다. 설치 위치가 일치하는 Windows 등록만 제거한다.
- 제거는 전체 rollback 트랜잭션이 아니다. 사전 검사 이후 외부 프로세스가 파일을 잠그거나 I/O 오류가 생기면 일부 제거 상태가 남을 수 있으며 실패를 표시한다. 가능한 동안 소유 정보/제거기를 남겨 재시도하게 한다.

## 변경 파일

`desktop/NpcChat.Setup/WindowsInstall.cs`: 소유 정보, 등록, 보존/삭제, 경로·잠금 검사.
`UninstallWindow.xaml(.cs)`, `UninstallHost.cs`: 제거 UI·데이터 확인·임시 실행/자체 정리.
`App.xaml.cs`, `SetupWindow.xaml.cs`, `SetupOptions.cs`, `SetupShortcut.cs`, `NpcChat.Setup.csproj`: 설치 연동 및0.3 버전.
`UninstallUiChecks.cs`, `SetupUiChecks.cs`, `desktop/SetupChecks`: 합성 선택·등록·제거/실물 흐름 검증.

## 명령과 검증

```powershell
.runtime/dotnet/dotnet.exe run --project desktop/SetupChecks -c Release
.runtime/dotnet/dotnet.exe build desktop/NpcChat.Setup/NpcChat.Setup.csproj -c Release
.runtime/dotnet/dotnet.exe publish desktop/NpcChat.Setup/NpcChat.Setup.csproj -c Release -r win-x64 --self-contained true -o .runtime/setup-lifecycle-20261005/bootstrap -p:InstallerManifestPath=<온라인 release.json 절대 경로>
venv/Scripts/python.exe -m pytest -q
venv/Scripts/python.exe -m ruff check app scripts tests
venv/Scripts/python.exe -m compileall -q app scripts
NPCChatSetup.exe --ui-test <새 격리 설치/UI 폴더>
NPCChatSetup.exe --uninstall-ui-checks <새 격리 데이터 선택 검증 폴더>
NPCChatSetup.exe --register-test <검증된 격리 설치 루트>
NPCChatUninstall.exe --uninstall <격리 설치 루트> --uninstall-smoke <새 증거 폴더>
```

기준94개 → 설치/제거147개 검사 통과. 네 보존 조합, 잠긴 파일·앱 mutex·변조 manifest/루트·데이터 경로 중복·실제 junction 거부, 외부 파일 보존, 생성 캐시 제거, 실제 임시 registry/shortcut 등록·해제 포함. 전체Python733개(16.36초), Ruff/compileall, WPF 빌드 경고0/오류0 및 publish 통과.

`.runtime/lifecycle-setup-ui-20261005/ui-test.json` passed=true, 실제 동봉 설치와 Windows 등록/시작 메뉴/제거기 생성 검사, 취소/오류 재시도, 설치된 앱 합성 smoke exit0. `.runtime/lifecycle-data-ui-20261005/ui-checks.json` passed=true: 실제 WPF 체크박스/제거 동작에서 주입한 확인 결과가 거절이면 파일 보존, 승인일 때만 격리 데이터/모델 삭제. 확인 버튼 자체는 테스트 seam으로 대체했으며 Windows MessageBox 수동 클릭 검증은 아니다. 모든 검증 창 topmost OFF.

첫 실물 제거에서 manifest 밖 CPython 캐시가 남아 소스별 생성 캐시 정리를 추가했다. 첫 임시 실행 정리에서 EXE는 지워졌지만 helper의 작업 폴더 때문에 빈 폴더가 남아, helper 작업 폴더를 Temp 상위로 변경했다. 이 최초 실행을 완전 정리 통과로 간주하지 않는다. 최종 재검증 결과는 후속 기록을 따른다.

## 한계와 다음 작업

최종 산출물: `.runtime/setup-lifecycle-20261005/NPCChatSetup.exe`, 139,854,924 bytes, SHA256 `0981ba934617346b7b92b4f891a8cf74c774c361ae990490b76d9ce1cc43b55f`.

최종 실물 제거 재검증: `.runtime/lifecycle-final-uninstall-20261005/result.json` passed=true/topmost=false/keepData=true/keepModel=true. `.runtime/setup-lifecycle-20261005/removal-evidence.json`: 설치 루트에 retained-models의 동일 모델 파일 하나만 남음, registered=false. 실제 사용자 시작 메뉴의 해당 식별자 폴더도 제거됨. 새 임시 제거 EXE·폴더는 종료 후 정리됐다. 최초 실패에서 남은 빈 임시 폴더는 별도 시험 잔재이며 최종 정리 성공과 구분한다. 합성 앱 종료 후 processes.json도 비어 있음.

내부 시험용이며 코드 서명·새 Windows 설치 환경·자동 업데이트는 미완료다. 실제 모델 추론은 이번 검증 범위가 아니다. 기본 실제 대화 데이터와 기존 사용자 설치/바로가기를 삭제하거나 전환하지 않았다. 다음은 보존 모델 재사용, 업데이트/복구 설계 및 깨끗한 Windows에서 설치·제거 시험이다.
