# 패키지 고지 수집 — Task41

2026-09-30. **자동 수집/누락 보고 완료, 권리 검토·판매 배포 승인은 미완료.** 완전한 전이 의존성 SBOM 또는 법률 검토 도구가 아니다.

`scripts/package_desktop.py`가 패키지 복사 후 `licenses/`를 생성하고 마지막 파일 manifest에 함께 포함한다. 기존 Python/모델/엔진/정적 자산 실행 구조는 바뀌지 않는다.

## 생성 항목

- `licenses/THIRD-PARTY-NOTICES.md`: 수집된 원문으로 가는 상대 링크와 미해결 항목.
- `licenses/files/…`: 패키지에 실제 존재하는 LICENSE/COPYING/NOTICE 등 원문 사본. 파일 이름/배치가 다른 고지는 누락 가능성이 있어 수동 검토를 대체하지 않는다.
- `licenses/inventory.json`: Python 이름/버전/선언 라이선스, 원문 상대 경로/hash, lock hash, 주요 앱·Python·모델·엔진·WebView 파일 hash, 미확정 권리 상태. 빌더 경로에서는 소스 Git commit/dirty 여부를 기록한다. 절대 경로·환경 변수·개인 대화는 기록하지 않는다.

Python wheel metadata를 lock과 비교해 누락/추가/버전 불일치를 보고한다. 고지 부재도 보고하며 내부 빌드에는 허용한다. 고지 목록은 파일 존재 확인이며 그 라이선스 의무를 모두 충족한다는 뜻이 아니다. 모델/자산 및 .NET/CUDA/WebView 약관은 검토 대기로 명시한다. 실제 파일 hash는 로컬 산출물 식별이며 upstream revision과의 일치 검증이 아니다.

`--distribution internal`이 기본이다. `--distribution release`는 모델 복사/출력 폴더 생성 전에 오류로 차단한다. **현재는 모든 release 빌드를 차단**하며 수동 승인 문자열로 우회하는 기능도 없다. 추후 고정된 upstream 출처/원문 고지/자산 권리 증빙을 검토하는 release 승인 계약을 별도 구현해야 한다.

기존 출력 폴더 덮어쓰기, 고지 입력의 링크/junction·경로 탈출, 중복 package/lock은 거부한다. 고지 출력은 신규 폴더만 허용한다. 빌드 중 중단된 폴더는 완료본으로 사용하지 않는다. 프로그램 실행이나 대화 저장 기능은 변경하지 않는다.

## 기존 패키지 읽기 전용 점검

```powershell
./venv/Scripts/python.exe scripts/package_notices.py --package <패키지폴더> --output <새로운-검사폴더> --lock desktop/requirements-runtime.lock
```

출력 폴더를 패키지 밖으로 지정하면 기존 패키지를 수정하지 않는다. CLI는 현재 저장소 commit을 기존 패키지의 출처라고 추정하지 않으므로 source commit은 null이다. 새 패키지의 출처는 빌더 호출 때 기록한다. 생성된 고지 파일은 실행하지 않는다.

## 검증 결과

2026-09-30 기존 로컬1.4.0 패키지 읽기 전용 점검: Python32개 lock 일치, 고지40개 수집. `release_allowed=false`, 권리/약관 검토6개 미해결 분류. 이 결과는 사용자4070Ti PC의 파일을 직접 검사한 것은 아니다. 출력은 ignored `.runtime/package-notices-20260930`에 있다. 마지막 보강 전 생성된 이 실물 보고서에는 lock_sha256이 없으며 최종 코드의 lock hash와 링크 경계 보강은 회귀 검사로 확인했다.

전체715 Python tests 통과. 최종 경계/lock hash 보강 후 관련17 tests 재실행 통과, Ruff/compileall 통과. 신규9개는 고지 원문/hash, 버전·파일 누락, 원문 고지 복사, 덮어쓰기 차단, 경로 탈출/junction, release 사전 차단, 중복lock, 빌더→고지→최종manifest 연결을 검증한다. 빌더 통합은 합성 실행 파일/모델과 pip 대역으로 수행했다. 실제 전체7.8GB 새 패키지 재빌드나 모델 실행은 하지 않았다.

```powershell
./venv/Scripts/python.exe -m pytest -q
./venv/Scripts/python.exe -m pytest -q tests/test_package_notices.py tests/test_desktop_package.py
./venv/Scripts/python.exe -m ruff check app tests scripts
./venv/Scripts/python.exe -m compileall -q app scripts
git diff --check
```

다음은 Task42 설치 트랜잭션(새 폴더 준비·파일 검증·중단 복구)이다. 내부용 설치 개발은 가능하며 판매 배포 승인은 별도다. 권리 원문 보완과 upstream provenance 검토는 병행해 남겨둔다.
