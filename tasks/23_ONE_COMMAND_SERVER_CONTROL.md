# Task 23 — 서버 원클릭 관리

상태: 2026-09-11 완료.

## 목표

현재 공개 테스트 구성을 사용자가 한 명령으로 시작·종료·재시작·상태 확인할 수 있게 한다.

## 사용자 명령

```powershell
.\server.ps1 start
.\server.ps1 stop
.\server.ps1 restart
.\server.ps1 status
```

## 범위

- 기존 `.runtime/public-test.env`의 모델·DB·한도·비밀값 재사용
- start: 모델 → Quick Tunnel → 공개 웹 → 관리자 순서
- stop: 관리자 → 터널 → 웹 → 모델 전체 종료
- 이미 실행 중인 start와 이미 종료된 stop은 안전하게 반복 가능
- status는 모델·웹·관리자·터널 및 현재 공개 주소만 표시하고 비밀값은 출력하지 않음
- 부분 시작 실패 시 이번 명령이 시작한 구성요소만 롤백
- 기존 세부 start/stop 스크립트는 유지

## 검증

- URL 추출·HTTP 준비 실패·실행 상태 단위 테스트
- 실제 status → 반복 start → stop → 반복 stop → start → status
- 공개 페이지, 로컬 web live, 관리자 ready, 모델 alias 확인
- 전체 테스트·Ruff·compile·diff 검사

## 결과

- 실제 전체 stop 뒤 포트와 등록 프로세스가 모두 정리됐고 반복 stop도 성공했다.
- 실제 start와 restart 뒤 모델·공개 웹·검사창·Quick Tunnel이 모두 준비됐으며 공개 페이지 HTTP 200을 확인했다.
- 관련 테스트 20개와 전체 테스트 591개가 통과했다.
- Ruff, Python compileall, PowerShell 구문 검사가 통과했다.
