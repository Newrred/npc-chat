# NPC Chat 1.5 — 보라색 브랜드와 컴팩트/확장 채팅

2026-10-03 사용자 승인 시안의 1번 흰색 캐릭터 말풍선 심볼, 컴팩트 기본/라이트 확장 방향을 적용했다. 다크 시안은 이번 구현 범위가 아니다.

## 변경 파일과 동작

- `frontend/brand.svg`: 직접 작성한 벡터 마크. AI 생성 비교 시트는 커밋하지 않는다. `scripts/build-brand.ps1`로 네이티브 PNG/7개 크기 ICO를 재현한다. 서비스/API 키 불필요.
- `frontend/index.html`, `violet.css`, `app.js`: 보라색 헤더/말풍선/입력창, 대화 목록 브랜드, 실제 캐릭터 프로필, 관계 패널. 기본 440×740 창에서 하단 관계 정보, 760px 이상에서는 오른쪽 사이드바. 넓게 펼치기 버튼은 네이티브 창을 960px까지 확장하고 다시 접는다. 화면 재로드 없이 초안/대화를 보존한다.
- 추천 문구는 빈 입력창에만 넣으며 자동 전송하거나 기존 초안/실패 재시도를 덮어쓰지 않는다. 표정 보기·캐릭터 선택·설정·기록 삭제 확인·재시도는 기존 흐름을 유지한다.
- `app/repository.py`: 기존 인증된 history 응답에 현재 서버 관계 5개 수치 `relationship`를 추가한다. 페이지별 과거 수치가 아닌 현재 상태이며 기존 `items` 계약은 보존한다. 브라우저는 정수 0~100만 표시하고 다른 캐릭터로 이동하거나 기록 복원이 실패하면 이전 패널을 비운다. `NPC_RELATIONSHIP_DISPLAY=hidden`은 패널도 숨긴다.
- `app/web.py`, `scripts/package_desktop.py`: 브랜드 SVG/테마 CSS만 명시적으로 공개·패키징한다.
- `desktop/NpcChat.Desktop/{App.xaml.cs,ChatShell.xaml,ChatWindow.cs,WidgetWindow.xaml,NpcChat.Desktop.csproj,Assets/*}`: 앱1.5.0, EXE/트레이/상단바 아이콘과 위젯 라이트 테마. topmost 테스트 규칙 유지.
- `IdentitySmoke.cs`, Python/JS tests: 실제 창 전환·초안·최소 크기·표정·설정·캐릭터 분리와 서버 값 복원 검증.

## 명령과 결과

PowerShell, 저장소 루트 기준. 수정 전 `venv\Scripts\python.exe -m pytest -q` 723개, `node --test tests/frontend.test.cjs` 28개 통과.

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/build-brand.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/build-desktop.ps1
venv\Scripts\python.exe -m pytest -q
node --test tests/frontend.test.cjs tests/inspector.test.cjs
venv\Scripts\python.exe -m pytest -q tests/test_conversation.py tests/test_web.py tests/test_desktop_package.py
venv\Scripts\python.exe -m ruff check app scripts tests
venv\Scripts\python.exe -m compileall -q app
# desktop 디렉터리에서:
..\.runtime\dotnet\dotnet.exe run --project WidgetChecks/WidgetChecks.csproj -c Release
```

전체 Python726개, 최종 관련42개, JS36개, C#13개, lint/compile/publish 통과. 처음 아이콘 빌드 명령은 Windows PowerShell 실행 정책으로 거부되어 위 명령의 프로세스 범위 옵션으로 실행했다. 시스템 정책 변경 없음.

실제 개발 빌드 및 최종 동봉 설치 폴더의 `NpcChat.Desktop.exe --smoke-widget --no-topmost --data-dir <격리 폴더>` 각각 exit0. 실제 WPF/WebView2/FastAPI/SQLite와 합성 모델로 다음을 확인했다.

- 채팅 전송, 표정·빠른 답장·미리보기 만료, Esc와 최소화/최대화/숨김/복원.
- 보라색 테마 로드, 컴팩트↔확장 버튼 실제 네이티브 크기 변경, 초안 보존.
- 360×480 최소 창의 입력창 접근 및 표정/설정 화면, 캐릭터 전환 시 관계 분리와 기록 복원.
- 익명 API 차단, topmost OFF, 종료 후 프로세스 등록 `{}`와 소유 프로세스 종료.

증거: ignored `.runtime/violet-ui-check-1` 및 `.runtime/violet-installed-check`의 `identity-smoke.json`, `smoke.json`, `widget-smoke.json`, `identity-*.png`, `widget.png`, `chat-titlebar.png`. 캡처는 실제 런타임 출력으로 시안 이미지와 구분한다.

최종 설치 패키지는 `venv\Scripts\python.exe scripts/verify_desktop_package.py <새 release>` 결과 `valid=true`, `changed_or_missing=[]`, manifest3270개. `git diff --check` 통과(기존 CRLF 변환 경고만 존재).

## 이 PC 적용 및 복원

기존 사용자별 설치 경로 아래 `releases/1.5.0-violet-20261003`를 별도로 구성했다. 기존1.4.0 폴더와 개인 AppData는 보존했다. 같은 볼륨의 모델·런타임 약7.55GB는 하드 링크로 공유하고 변경하는 앱/소스 파일은 별도 복사본이다. 공유 의존성은 제자리 수정하지 않는다. 이번 절차는 로컬 내부판 적용이며 자동 업데이트 제품 기능이 아니다.

최종 설치본 smoke/manifest 확인 후 바탕화면 `NPC Chat.lnk`의 대상/아이콘과 설치 `current.json`을 새 release로 전환했다. 이전 바로가기/current 파일은 ignored `.runtime/violet-rollback`에 보관했다. 다른 D드라이브 구형 portable 바로가기는 변경하지 않았다. 포인터 교체 첫 .NET 호출은 빈 backup 경로 오류로 실패했고, 준비된 JSON을 `os.replace`로 원자 교체한 뒤 읽기 검증했다. 바로가기 대상 EXE 버전1.5.0을 확인했다.

데이터 migration·모델 설정 변경 없음. 복원이 필요하면 기존1.4.0 실행 파일을 사용하거나 백업 바로가기/current를 복원한다. Git commit/push 및 운반용 설치 ZIP 재생성은 하지 않았다.

## 한계와 다음 작업

실제9B 추론 품질/속도는 이번 UI 검증에서 재측정하지 않았다. 합성 모델 smoke를 실제 모델 성공으로 해석하지 않는다. 혼합 DPI·물리 IME·Windows Snap 장시간 사용감과 깨끗한 PC 설치는 추가 검증 대상이다. 다음은 사용자가 이 PC의 새 `NPC Chat` 바로가기로 실제 대화 사용감을 확인하고, 확정한1.5 UI를 새 배포 패키지에 포함하는 일이다.
