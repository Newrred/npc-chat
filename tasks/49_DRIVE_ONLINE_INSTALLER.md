# Task49 — Google Drive 앱과 HF 모델 온라인 설치

사용자가 제공한 Drive app.zip 공유 링크를 연결한다. 기존 Task48 UI와 동봉 설치는 보존한다. 기준 설치 검사92개 통과. 공유 링크를 고정 공개 다운로드 URL로 변환하되 일반 query token 허용으로 확장하지 않는다. HTML 확인/할당량 페이지는 파일로 저장하지 않고 오류 안내하며 기존 캐시를 유지한다.

수용 기준: Drive 실제 전체 app.zip과 HF 실제 전체 모델 다운로드, 고정 SHA256 검증, 격리 신규 설치, 설치 앱 합성 smoke, 온라인 선택 UI 확인. 실제 모델 성능·제거/업데이트·일반 판매 배포 승인은 범위 밖이다. 개인 데이터/기존 설치/바로가기를 변경하지 않는다.

전체 다운로드/해시/manifest/격리 설치 exit0, cache/staging 정리 확인. 설치94개/Python733개/lint/compile/publish 및 온라인 창 캡처 통과. [명령·산출물·후속 실행 증거](../docs/DRIVE_ONLINE_INSTALLER.md).

설치 앱 합성 위젯/채팅 smoke exit0로 범위 완료. 실제 추론 성공과 구분한다.
