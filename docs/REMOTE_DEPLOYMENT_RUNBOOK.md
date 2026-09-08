# 테스트 이후 배포 준비와 공개 전 검증

**후속 사용자 결정:** 기본 배포는 로그인 없는 공개 링크(guest)로 변경됐다. 최신 절차는 [PUBLIC_LINK_DEPLOYMENT.md](PUBLIC_LINK_DEPLOYMENT.md)를 따른다. 아래 Access 구성은 선택적 이메일 로그인 모드의 문서로 보존한다. guest 호스트에는 Access 로그인 보호를 적용하지 않는다.

2026-09-07: 사용자 요청은 테스트 이후 운영할 배포 기준으로 준비하는 것이다. 도메인과 Cloudflare 계정은 아직 없다. 실제 인터넷 공개, 계정 생성, 유료 구매, 터널 생성은 수행하지 않았다. 첫 배포의 접근 정책은 **초대 사용자 한정이라는 임시 기본안**이며 누구나 가입하는 서비스는 별도 결정이 필요하다.

## 현재 준비한 범위

- Windows의 단일 FastAPI 웹앱 + 별도 llama.cpp + SQLite 유지. Docker 전환 불필요.
- `NPC_ACCESS_MODE=cloudflare`에서 전체 웹 화면/정적 파일/API를 Access JWT 서명·issuer·audience·만료 검증으로 보호한다. 이메일 헤더나 브라우저 profile ID를 인증으로 취급하지 않는다. 익명 예외는 내용 없는 `/api/live`, `/api/health`뿐이다.
- 로그인 issuer/subject에서 서버가 사용자 프로필을 도출한다. 다른 사용자의 profile/session, 로컬 기존 프로필은 403. 세션 생성/채팅/이미지 상태에 동일한 소유권 경계를 적용한다. 같은 계정은 브라우저를 바꾸어도 같은 관계·기억을 사용한다.
- 원격 요청은 client_turn_id 필수. 중복 요청의 저장 결과 재사용은 유지한다.
- 변경 요청에 정확한 HTTPS Origin과 JSON을 요구한다. Host도 고정 주소와 일치해야 한다. CORS는 인증을 대체하지 않는다.
- 사용자당 기본 20회/분(세션 생성과 채팅 포함), 처리 중/대기 중 채팅 1개, 전체 기존 큐 8개, 입력 본문 16 KiB. 429에는 Retry-After가 있다. 한 worker 기준의 메모리 제한이며 재시작하면 요청 횟수 창은 초기화된다.
- 서명 검증 동시 4개, 키 조회 timeout 3초, 본문 각 수신 대기 10초 제한. 공개 인터넷의 악성 트래픽은 Access 및 edge 제한에서도 차단해야 한다.
- 원격 응답 no-store, request ID, 프레임 삽입 차단. 애플리케이션 기본 원격 로그는 상태/소요시간/요청 ID만 기록한다. 이메일·JWT·본문·query는 기록하지 않는다.
- 로컬 모드는 기존 동작과 모델 연결을 유지한다. 운영 모드로 기존 개인 대화를 자동 이전하지 않는다. 스키마는 0001 그대로다.

## 준비물과 설정

1. Cloudflare에서 사용할 도메인과 Zero Trust 계정을 준비한다.
2. Access의 Self-hosted 애플리케이션을 먼저 생성하고 정확한 호스트 전체를 보호한다. 초대된 이메일만 Allow하며 Bypass/Everyone 규칙을 사용하지 않는다. Team issuer와 Application AUD를 확보한다.
3. `deployment/remote.env.example`을 무시되는 개인 설정 파일(예: `.runtime/deployment.env`)로 복사하고 빈 값을 채운다. 비밀값을 채팅·Git·JS에 넣지 않는다.
4. 운영 DB는 코드 checkout 밖의 영속 디렉터리를 지정한다. 개발 DB와 별도 파일을 쓰고 기존 개인 DB를 복사하지 않는다. 해당 폴더와 백업은 운영 Windows 계정만 읽을 수 있도록 제한한다.
5. 배포 전 의존성 설치와 구성 검사:

```powershell
./venv/Scripts/python.exe -m pip install -r requirements-remote.txt
./venv/Scripts/python.exe scripts/remote_preflight.py --env-file .runtime/deployment.env
```

구성 검사는 읽기 전용이며 비밀을 출력하지 않는다. 빈 예시 파일은 exit 1로 거절되는 것이 정상이다. `configuration_ready=true`는 설정 검사 통과만 의미하고, `release_ready`는 외부 검증 전 항상 false다. 모델 바이너리/GGUF 내용·버전 호환성은 이 검사만으로 보장하지 않는다.

## 연결과 실행 순서

1. 배포 버전의 테스트/품질 검토와 아래 공개 게이트를 끝낸다. 운영 중인 개발 프로세스를 포트 번호로 강제 종료하지 않는다. 필요한 경우 소유권을 확인하는 기존 stop-local로 종료한다.
2. 준비된 llama.cpp를 loopback 8001에서 먼저 실행하고 모델 ID와 GPU 설정을 확인한다. 모델 파일, 경로, API key는 개인 설정으로 관리한다. 현재 PC 기준은 4B Q4 / context 2048 / parallel 1 / output 256 / full GPU이며 동시성 확대는 별도 측정 후 결정한다.
3. 인증된 웹앱을 실행한다. 이 실행기는 기존 개발 `.env`를 불러오지 않고 지정한 배포 설정만 사용하며, loopback 8000 / worker 1 / proxy headers 비신뢰를 강제한다.

```powershell
./venv/Scripts/python.exe scripts/serve_remote.py --env-file .runtime/deployment.env
```

4. Cloudflare named tunnel의 고정 호스트를 `http://127.0.0.1:8000`에 연결한다. 공개 Host를 유지하고 Access의 **Protect with Access**도 활성화한다. 모델 8001, DB, 다른 포트를 route로 등록하지 않는다. 공유기 포트 개방은 하지 않는다.
5. 테스터 브라우저는 같은 호스트에서 화면과 `/api`를 사용한다. 별도 Pages 프런트나 JS API key는 필요 없다. 이전 계정의 브라우저 저장값이 남으면 403 후 **현재 계정으로 연결** 버튼으로 로컬 식별자만 정리한다. 서버 기록은 삭제하지 않는다.

`serve_remote.py`는 전경 실행기이며 운영 서비스 관리자나 모델 실행기를 대체하지 않는다. 현 시점에는 자동 부팅/재시작 서비스가 설치되지 않았다. 로그아웃/재부팅 후에도 운영할 경우 서비스 계정, Windows 작업 스케줄러 또는 서비스 관리자 설정과 복구 시험을 완료해야 한다. 개발용 start-local은 인증된 readiness를 호출할 수 없으므로 원격 실행에 사용하지 않는다.

## 실제 공개 전 필수 게이트 — 아직 미완료

- 외부망에서 로그인 전 화면/API 거절, 허용 이메일 접속, 거절 이메일 차단, 로그아웃/만료/재로그인 확인.
- 두 실제 계정의 관계·기억·재시도 결과 분리, 다른 계정 ID의 접근 거절, 중복 turn 한 번만 저장.
- 브라우저 Origin 및 429/503 동작, 터널 단절/PC 오프라인 안내, 모델 포트 외부 접근 불가.
- 모델→웹→터널 순서 시작, 터널→웹→모델 순서 종료. 비정상 종료 시 제한된 재시도와 지수 지연을 적용하는 운영 서비스 관리 및 재부팅 리허설. 포트의 다른 프로세스를 종료하지 않는다.
- queue 대기시간·오류율·GPU 메모리·응답 p95 측정. 현재 1개 생성 동시성 유지. 이전 1인 합성 평가를 다중 사용자 용량 보장으로 쓰지 않는다.
- 운영 DB 온라인 백업 후 별도 경로 복원, 이전 앱 버전과 데이터 복구 리허설. `scripts/database.py backup/restore` 사용; 실제 운영 파일은 중지·검증 없이 덮어쓰지 않는다.
- 데이터 보관/삭제 정책 확정 및 UI 고지, 삭제 실행 도구와 백업 만료 구현. 현재는 **자동 보관 만료나 사용자 삭제 기능이 없다**. 권고 초안은 마지막 활동 후 30일 삭제, 백업 7일 보관이지만 사용자 승인 전 실행하지 않는다. 삭제 시 history·memory·관계·turn 캐시·백업 모두를 대상으로 하고 복원 후 삭제 데이터가 부활하지 않도록 검증한다.
- 운영자 연락처, 대화가 저장됨과 AI 응답임을 알리는 안내, 모델 배포/이용 조건 확인, Phase04 말투·경계 존중 실패 사례의 사람 검토.

이 게이트와 실제 접속 증거가 없으면 Phase05 완료 또는 공개 서비스 준비 완료로 표시하지 않는다. 초대 테스트를 넘는 누구나 가입하는 서비스는 가입/탈퇴/복구, 악용 대응, 운영 시간/SLO, 비용 한도와 부하 측정에 따른 전용 GPU 서버 검토가 추가로 필요하다. 현 코드의 단일 worker/SQLite를 임의로 복제하지 않는다.

## 공식 근거

- [Cloudflare self-hosted application: Access를 먼저 구성하고 origin token 검증](https://developers.cloudflare.com/cloudflare-one/access-controls/applications/http-apps/self-hosted-public-app/)
- [Cloudflare JWT 검증: 서명, issuer, audience와 공개 키](https://developers.cloudflare.com/cloudflare-one/access-controls/applications/http-apps/authorization-cookie/validating-json/)
- [PyJWT 검증과 JWKS API](https://pyjwt.readthedocs.io/en/latest/api.html)
