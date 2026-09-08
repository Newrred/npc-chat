# 대화 복원·나가기·관리자 조회 (2026-09-08)

## 이용자 동작

- 같은 브라우저에서 새로고침하면 서버의 최근 50턴을 불러온다. 더 오래된 기록은 `이전 대화 더 보기`로 50턴씩 조회한다. 프롬프트에 넣는 최근 기록 제한과는 별개다.
- 상단 뒤로가기는 목록 이동이며 기록·관계·초안을 유지한다.
- `대화 설정 → 대화방 나가기 → 기록 삭제하고 나가기`는 해당 방문자/캐릭터의 저장된 턴, 기억, 요약, 플래그와 관계를 초기화한다. 다른 방문자/캐릭터와 일일 사용량은 유지한다.
- 모든 기존 세션을 폐기하므로 오래 열린 탭은 새로고침/현재 대화로 연결이 필요하다. 오래된 초기화 요청을 재전송해도 새 대화가 삭제되지 않는다.
- 초기화 응답이 유실되면 삭제 완료 여부를 단정하지 않고 새로고침으로 확인하도록 안내한다. 오래된 세션에는 403/404를 반환한다.
- 브라우저의 저장된 식별자와 서명 쿠키로 대화를 구분한다. 기기 간 자동 동기화/회원 로그인은 없다. 쿠키나 사이트 데이터를 삭제하거나 임시 주소가 바뀌면 기존 기록을 자동 복구한다고 보장하지 않는다.
- 테스트 대화가 서버에 저장되고 운영자가 확인할 수 있음을 대화 설정에 알린다.

## 관리자

관리 PC에서 `http://127.0.0.1:8002`를 연다. 방문자별 캐릭터/대화 횟수/마지막 시각 목록과 질문·답변·시각을 조회하며, 목록 100개/기록 50턴 단위로 더 볼 수 있다. 방문자는 익명 브라우저 구분이며 실제 사람이나 PC를 식별하지 않는다. 자동 실시간 갱신 대신 새로고침 버튼을 사용한다. 관리자 삭제/편집 기능은 없다.

```powershell
./venv/Scripts/python.exe scripts/local_runtime.py start-admin --env-file .runtime/public-test.env
./venv/Scripts/python.exe scripts/local_runtime.py stop-admin
```

선택한 환경의 `NPC_DATABASE_PATH`가 기존 DB 파일이어야 한다. 비밀 설정을 관리자 페이지에 전달하지 않는다. 공개 웹과 별도 프로세스이며 loopback 8002에만 바인딩한다. 공개 터널은 계속 8000만 연결한다. 정확한 Host, 로컬 접속 주소, Origin/Fetch-Site 검사로 외부 접속과 브라우저를 통한 우회 읽기를 차단한다. DB는 SQLite `mode=ro`/`query_only=ON`, 응답은 no-store다. 로그인 없이 이 PC를 사용하는 사람이 조회할 수 있으므로 외부 관리자 접근은 지원하지 않는다.

공통 실행기가 소유 프로세스를 기록하며 `stop-local`은 관리자도 종료한다. 포트나 프로세스 이름으로 다른 프로그램을 종료하지 않는다. 관리자 자동 부팅은 추가하지 않았다.

## API와 저장

- `GET /api/conversation?session_id=…&profile_id=…&before=…&limit=50`: 소유권 검증 뒤 `{items:[{turn_id,user_message,reply,face,created}],before}`. limit 1–100. before는 이전 페이지가 반환한 가장 오래된 턴 ID이며 생성시각+ID로 안정 정렬한다. 페이지는 오래된 순이다. 삭제된 커서는 409.
- `POST /api/conversation/reset` JSON `{session_id,profile_id}`: 소유권/Origin 검증과 기존 직렬 실행 큐를 거쳐 원자적 초기화. 성공 `{closed:true}`. 반복된 오래된 요청은 403/404. 큐에서 실행 직전 chat 세션도 재검증하여 폐기된 요청의 재저장을 막는다.
- 읽기/나가기는 일일 생성 한도를 차감하거나 복원하지 않는다. 원격 요청 속도 제한은 적용된다.
- DB 스키마 변경/마이그레이션은 없다. 기존 turns 테이블을 읽는다. legacy import 영수증은 유지하여 오래된 데이터를 자동 재수입하지 않는다.
- 초기화는 현재 DB의 논리적 삭제다. 기존 백업/SQLite 파일의 안전한 물리적 소거를 뜻하지 않는다. 백업 보관·폐기는 기존 DATABASE_OPERATIONS 정책을 따른다.

## 검증

기준 Python 426개에서 435개, 프런트 18개에서 22개로 확대해 통과했다. 기록 페이지/동일시각 정렬/재시작 복원, 다른 방문자 접근 거부, 초기화 후 과거 세션/대기 요청 거부, 트랜잭션 롤백, 일일 한도 유지, 관리자 외부 접근 차단/DB 없음, 응답 유실 후 복원, 초기화 취소/실패를 검사했다. 프런트 초기 테스트 2개는 새 비동기 기록 복원을 기다리도록 수정했고 재검증했다.

```powershell
./venv/Scripts/python.exe -m pytest -q
node --test tests/frontend.test.cjs
./venv/Scripts/python.exe -m ruff check app tests scripts
./venv/Scripts/python.exe -m compileall -q app scripts
node --check frontend/app.js
```

위 명령 모두 통과. 실사용 데이터 삭제 없이 격리 DB/합성 대화로 검증한다.
