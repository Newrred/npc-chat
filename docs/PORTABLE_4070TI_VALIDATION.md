# 4070 Ti 패키지 실행 검증 — 2026-09-29

사용자가 옮긴 `NPCChatPortable-20260929.zip`을 저장소 밖의 새 폴더에 풀어 앱 1.4.0과 동봉 9B Q4_K_M 모델을 검증했다. 기존 파일 덮어쓰기, 모델 교체, 개발 `.env` 변경, 기본 사용자 AppData 접근은 하지 않았다. 모든 채팅 입력은 검증용 합성 입력이며 테스트 DB는 별도 `--data-dir`에 저장했다.

## 환경과 범위

- Windows 11 Pro 10.0.26200, Intel i7-10700F, RAM 63.9 GiB.
- RTX 4070 Ti, VRAM 12282 MiB, NVIDIA driver 610.62.
- 설치된 VC++ x64 Redistributable 14.51.36247.0. 이 버전에서 실행됐다는 증거이며 최소 지원 버전 검증은 아니다.
- 패키지 설정 유지: Aggressive 9B Q4_K_M, 문맥 4096, GPU layers auto, 응답 최대 256, two_stage, metadata full.
- Python·.NET 개발 도구가 이미 설치된 PC다. 깨끗한 Windows/개발 도구 미설치 게이트는 미완료다. 실행 경로 관찰로 동봉 Python·llama·WebView2 사용은 확인했다.
- 별도 계획인 14B 모델의 4070 Ti 적합성/품질 평가는 수행하지 않았다.

## 결과

| 검사 | 결과 |
|---|---|
| ZIP 해제 | 새 폴더에 해제, 압축 내 5693개 항목, 비압축 약 7.77 GB |
| manifest 무결성 | 3225개 대상 파일, `valid=true`, 변경/누락 없음 |
| 핵심 소스 비교 | supervisor/config/verifier/frontend/main의 텍스트가 main@2015558과 일치; 줄바꿈 차이는 제외 |
| 실제 네이티브 첫 실행 | `--smoke-real --no-topmost`, 종료 코드 0; 시작부터 채팅·종료까지 20.66초 |
| 네이티브 재실행 | 종료 코드 0, 16.30초; 기존 assistant 1개 복원 후 새 답변 생성 |
| 실제 창과 서버 | 실제 모델 답변, smiling 표정, 인증 없는 요청 403, 채팅창 숨김/복원 통과 |
| 동봉 런타임 | 관찰된 Python/llama-server/WebView2 실행 파일이 모두 패키지 내부; WebView2 153.0.4234.48 |
| 개발 환경 간섭 | Windows TEMP에서 실행; 잘못된 NPC_BASE_URL/PYTHONPATH/HTTP_PROXY/HTTPS_PROXY를 전달한 상태에서도 위 검사 통과 |
| 연속 요청 | 별도 동봉 supervisor/API에서 5턴 모두 HTTP 200; 실제 추론 사용 |
| 중복 요청 | 동일 turn ID 재요청 HTTP 200, 응답 동일, 0.016초 |
| 종료 | 각 supervisor 종료 코드 0, 소유 registry `{}`; 최종 패키지 프로세스 및 8001/8003 listener 없음 |

연속 5턴의 클라이언트 왕복 시간은 **2.469 / 2.375 / 2.000 / 2.234 / 2.391초**, 중앙값 **2.375초**였다. 이 값은 two_stage 처리와 저장을 포함한 짧은 합성 입력의 전체 HTTP 시간이다. 순수 토큰 생성 속도나 3060 Ti 대비 성능 비교로 해석하지 않는다. 동봉 supervisor를 별도로 시작한 검사에서는 준비 완료까지 8.453초였다.

5턴은 인사 → 산책 언급 → 직전 활동 회상 → 음악 분위기 추천 → 인사 순서였다. 회상 질문에는 `산책하고 왔다고 했잖아!`라고 응답했다. 이는 해당 짧은 사례의 관찰이며 장기 기억/대화 품질 검증이 아니다.

네이티브 검사에서 1초 간격으로 관찰한 GPU 전체 메모리 사용 최고값은 **8029 MiB(약 7.84 GiB)**, 연속 요청 직후 7722 MiB, 최종 종료 후 2498 MiB였다. 다른 앱의 GPU 사용량을 포함하며 샘플 사이의 순간 최고값은 보장하지 않는다. OOM이나 추론 오류는 이번 요청에서 관찰하지 않았다.

## 남은 항목

- 네트워크를 실제 차단하지 않았다. 두 네이티브 실행에서 동봉 `msedgewebview2.exe`의 외부 TCP 443 연결을 각각 관찰했다. 목적/페이로드는 조사하지 않았으며 대화 전송 여부도 판단하지 않는다. **오프라인 검증 통과로 표시하지 않는다.**
- 깨끗한 Windows, VC++ 미설치 환경, 장시간 사용, 재부팅/절전, 실제 혼합 DPI 조작은 미검증이다.
- 14B Q4 비교, 라이선스/재배포 권리, 설치기/서명/업데이트 검증은 별도다.

## 재현과 증거

패키지 폴더에서 동봉 Python으로 `scripts/verify_desktop_package.py .`를 실행하고, EXE에 `--smoke-real --no-topmost --data-dir <별도 테스트 폴더>`를 지정했다. 같은 테스트 폴더로 두 번째 실행해 복원을 확인했다. 개발 저장소 밖의 패키지를 사용했으며 패키지 내용은 수정하지 않았다.

로컬 증거는 Git 제외 경로 `.runtime/portable-4070ti/`의 `first-start.json`, `restart.json`, `requests.json`, `real/smoke.json`, `real/chat.png`, 각 runtime registry에 보존했다. 로컬 검사 도구는 `.runtime/test_portable_4070.py`, `.runtime/check_portable_requests.py`다. 실행 파일 경로와 개인별 로컬 경로가 들어가는 원자료는 커밋하지 않는다. 변경은 이 검증 기록과 관련 상태 문서뿐이며 앱 코드 변경은 없다.
