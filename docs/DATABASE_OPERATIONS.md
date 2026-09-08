# SQLite 운영과 백업/복구

기본 파일은 `.runtime/data/npc-chat.sqlite3`이며 NPC_DATABASE_PATH로 변경한다. 저장소 루트에서 실행한다. 로컬 디스크만 지원하고 네트워크 공유 경로는 사용하지 않는다. schema 0001은 앱 시작 또는 아래 upgrade로 준비한다. 이미 존재하는 DB의 스키마 변경 전에는 백업한다.

```powershell
./venv/Scripts/python.exe scripts/database.py status
./venv/Scripts/python.exe scripts/database.py upgrade
./venv/Scripts/python.exe scripts/database.py backup --file .runtime/backups/manual-01.sqlite3
```

backup은 SQLite 온라인 backup API를 사용하므로 앱 실행 중에도 일관된 복사본을 만든다. 기존 대상 파일은 덮어쓰지 않는다. WAL 파일을 제외하고 DB 파일만 수동 복사하지 않는다.

## 기존 Redis 이전

먼저 stop-local로 앱 쓰기를 중지한다. Redis 서비스와 원본은 그대로 둔다. export/import는 기본 DB의 앱 잠금을 확보해야 한다. 내보낸 파일에는 개인 대화가 포함되므로 Git 무시된 .runtime에 둔다.

```powershell
./scripts/stop-local.ps1
./venv/Scripts/python.exe -m pip install -r requirements-redis.txt
./venv/Scripts/python.exe scripts/database.py export-redis --file .runtime/backups/legacy-01.json
./venv/Scripts/python.exe scripts/database.py import-legacy --file .runtime/backups/legacy-01.json
./venv/Scripts/python.exe scripts/database.py import-legacy --file .runtime/backups/legacy-01.json --apply
./scripts/start-local.ps1
```

apply 없는 import는 임시 DB에서 검증한다. 실제 import는 기존 SQLite를 먼저 백업하고 세션별 원자적 이전을 수행한다. 중간 실패 시 원본을 보존하며 같은 파일로 재실행하면 완료된 항목을 건너뛴다. 기존 affection은 0..100으로 제한하고 다른 수치는 캐릭터 기본값을 사용한다. history는 최근 12메시지, 메모는 400자만 운영 DB에 옮기며 원본 전체는 export에 보존한다. Redis TTL로 이미 사라진 데이터는 복구할 수 없다.

## 복구

```powershell
./scripts/stop-local.ps1
./venv/Scripts/python.exe scripts/database.py restore --file .runtime/backups/manual-01.sqlite3 --apply
./scripts/start-local.ps1
./scripts/doctor.ps1
```

restore는 백업 integrity/schema를 확인하고 현재 DB를 before-restore 파일로 보존한 다음 SQLite backup API로 복원한다. 앱 실행 중 복원은 거부한다. 복원 시점 이후 대화는 복구된 DB에 포함되지 않지만 before-restore에 남는다. SQLite가 새 대화를 받은 뒤 오래된 Redis를 바로 기본 저장소로 되돌리지 않는다. 알려진 SQLite 백업 복원 또는 명시적인 별도 데이터 이전이 필요하다.

## 데이터 수명과 범위

프로필 관계/turn/중복 처리 기록은 TTL 없이 유지한다. 기억은 50개, 순환 요약 400자, 최근 prompt용 이력은 12메시지로 제한한다. 전체 turn 기록은 사용자 삭제 전까지 보관하며 DB/백업 크기는 대화량에 따라 증가한다. 저장소 reset/delete는 테스트되어 있지만 공개 API/화면은 후속 작업이다. reset/delete 후에도 이전 완료 receipt는 남는다. 백업 삭제/보관 기간은 사용자가 정하며 자동 삭제하지 않는다.

같은 DB에 앱 프로세스 하나/worker 하나만 허용한다. 큐 포화는 429, 대기 시간 초과와 DB 장애는 503이다. 둘 다 저장된 client_turn_id로 재시도한다. 다른 DB 파일을 쓰는 별도 앱까지 전역 제어하는 도구는 아니다.

## 2026-09-08 사용자 대화방 나가기와 조회

대화방 나가기는 확인 후 profile/character의 turns, memories, sessions를 한 트랜잭션에서 지우고 관계·요약·flags를 초기화한다. profile 자체와 legacy import 영수증, 별도 usage DB는 유지한다. 예외 발생 시 전체 롤백하며 오래된 session은 다시 사용할 수 없다. 다른 캐릭터/방문자에는 적용하지 않는다. 스키마 변경은 없다. 기존 백업에는 이전 내용이 남을 수 있으며 현재 DB의 논리적 삭제가 저장 장치의 안전한 소거를 뜻하지 않는다.

관리자 조회 앱은 기존 DB를 mode=ro 및 query_only=ON으로 열며 DB를 생성하거나 migration/쓰기 lease를 획득하지 않는다. 공개 웹 프로세스와 동시 조회가 가능하다. 운영 명령/사용자 복원 API: CHAT_HISTORY_AND_ADMIN.md.
