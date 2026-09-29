# 동봉 의존성·라이선스 현황

2026-09-29 / Task40 / 코드 기준56ba7ea, 앱1.2.0 동봉 산출물 확인. **조사 결과이며 판매·재배포 승인서 또는 완성된 THIRD-PARTY-NOTICES가 아니다.** 라이선스 표시가 있다고 원본 고지 보존·변경 표시·소스 제공 등 조건까지 충족된 것은 아니다.

## 실제 런타임과 남은 확인

| 구성 | 현재 확인 | 고지/출처 상태와 다음 조치 |
|---|---|---|
| Python embedded | 3.12.10 x64; builder가 공식 ZIP SHA-256 고정 | runtime/python/LICENSE.txt 있음. 포함 third-party 구성까지 해당 배포본의 고지를 보존 |
| Python wheels | lock과 설치 metadata 32/32 버전 일치 | 아래32개 모두 적어도1개의 고지 후보 파일 존재. 범위별 의무 및 전문 내용 검토는 미완료 |
| .NET / WPF | self-contained Microsoft.NETCore.App 및 Microsoft.WindowsDesktop.App 10.0.12 | runtimeconfig 확인. 패키지 최상위에 LICENSE/NOTICE 없음. 해당 runtime pack의 고지 수집 필요; SDK 전체를 동봉하지 않음 |
| WebView2 SDK | Microsoft.Web.WebView2 1.0.4258.31 | NuGet lock 버전/hash 확인. SDK 라이선스와 Runtime 조건을 따로 수집 |
| WebView2 Runtime | Fixed153.0.4234.48 x64 | 하위 LICENSE 파일3개와 라이선스 표시 도구 발견. 이것만으로 Microsoft Fixed Runtime 배포 조건 전문 포함을 확인한 것은 아님 |
| llama.cpp | 기존 빌드 기록 b10830 / CUDA12 | 공식 b10830 LICENSE는 MIT. 실제 llama 폴더에는 LICENSE-LLVM-OpenMP만 있어 엔진 자체 LICENSE 보완 필요 |
| OpenMP / CUDA DLL | libomp.dll, cudart64_12.dll, cublas64_12.dll, cublasLt64_12.dll | OpenMP 고지 있음. CUDA 약관/배포 archive 출처와 DLL별 대응 미완료. NVIDIA 드라이버는 패키지에 넣지 않음 |
| GGUF 모델 | Qwen3.5-9B-Uncensored-HauhauCS-Aggressive Q4_K_M → models/model.gguf | 업로더 model card는 Apache-2.0, 기초 Qwen3.5-9B LICENSE도 Apache-2.0. 로컬 파일과 업스트림 고정 revision/hash의 대응·원문 고지·변경 이력 아직 미확정 |
| 유이·띳띠 이미지/캐릭터 | 현재 PNG·캐릭터 설정 동봉 | 상업 재배포 권리 증빙 미확인. 내부 시험용으로 분류하고 판매본은 권리 확보한 오리지널 자산 또는 승인 자산으로 교체 |
| 프로젝트 자체 코드 | FastAPI·정적 UI·C#·실행 scripts | 저장소 최상위 LICENSE 미발견. 외부 코드 도입 이력과 자체 제품 이용 조건 정리 필요. 공개 저장소라는 사실은 권리 정리를 대신하지 않음 |
| Windows / NVIDIA driver / VC++ | 사용자 OS 구성요소 | 별도 PC 최소 버전·필수 VC++ 확인 대기. CUDA Toolkit 전체를 사용자에게 요구하는 설계가 아님 |

현재 생성기는 llama 폴더에서 DLL/server/LICENSE*만 복사한다. README/NOTICE/개별 라이선스가 다른 이름이면 누락될 수 있다. Python wheel 안의 native binary 및 WebView/.NET/추론엔진 전이 의존성까지 조사한 완전 SBOM은 아직 아니다. 사용하지 않는 추론 보조 DLL도 복사되는 현상을 확인했지만 이번에는 삭제하지 않았다.

DLL 파일 버전 원문은 cudart `6,14,11,12040`, cublas `6,14,11,1245`였다. 이 숫자를 CUDA Toolkit 릴리스로 단정하지 않는다. 원본 다운로드 artifact와 배포 기록에서 정확한 CUDA 버전을 확인한 후 그 버전의 EULA를 적용해야 한다.

## Python 목록 (실제 파일 기반)

선언값은 License-Expression을 우선하고 없으면 classifier/License metadata를 사용했다. 'BSD License'처럼 세부 형식이 없는 값은 추측해 채우지 않았다. 파일 수는 LICENSE/COPYING/NOTICE 이름 후보 수이며 의무 충족 판정이 아니다. 각 파일의 패키지 상대 경로·SHA-256은 [검증 스냅샷](DESKTOP_DEPENDENCY_SNAPSHOT.json)에 있다. 개인 경로나 대화는 없다.

| 패키지 | 버전 | metadata 선언 | 고지 후보 파일 수 |
|---|---|---|---:|
| alembic | 1.19.2 | MIT | 1 |
| annotated-doc | 0.0.4 | MIT | 1 |
| annotated-types | 0.7.0 | MIT License | 1 |
| anyio | 4.12.1 | MIT | 1 |
| certifi | 2026.1.4 | Mozilla Public License 2.0 (MPL 2.0) | 1 |
| charset-normalizer | 3.4.4 | MIT | 1 |
| click | 8.3.1 | BSD-3-Clause | 1 |
| colorama | 0.4.6 | BSD License | 1 |
| distro | 1.9.0 | Apache Software License | 1 |
| fastapi | 0.135.1 | MIT | 1 |
| greenlet | 3.5.5 | MIT AND PSF-2.0 | 2 |
| h11 | 0.16.0 | MIT License | 1 |
| httpcore | 1.0.9 | BSD-3-Clause | 1 |
| httpx | 0.28.1 | BSD License | 1 |
| idna | 3.11 | BSD-3-Clause | 1 |
| jiter | 0.13.0 | MIT License | 2 |
| Mako | 1.4.1 | MIT | 1 |
| MarkupSafe | 3.0.3 | BSD-3-Clause | 1 |
| openai | 2.21.0 | Apache Software License | 1 |
| psutil | 7.2.2 | BSD-3-Clause | 1 |
| pydantic | 2.12.5 | MIT | 1 |
| pydantic_core | 2.41.5 | MIT | 1 |
| python-dotenv | 1.2.2 | BSD-3-Clause | 1 |
| requests | 2.32.5 | Apache Software License | 1 |
| sniffio | 1.3.1 | MIT License; Apache Software License | 3 |
| SQLAlchemy | 2.0.52 | MIT | 1 |
| starlette | 0.52.1 | BSD-3-Clause | 1 |
| tqdm | 4.67.3 | MPL-2.0 AND MIT | 1 |
| typing-inspection | 0.4.2 | MIT | 1 |
| typing_extensions | 4.15.0 | PSF-2.0 | 1 |
| urllib3 | 2.6.3 | MIT | 1 |
| uvicorn | 0.41.0 | BSD-3-Clause | 1 |

`certifi`와 `tqdm`의 MPL 계열, greenlet의 복합 라이선스, sniffio의 복수 선언은 각각 실제 원문을 확인해야 한다. 전체 제품이 같은 라이선스라고 단정하거나 단순히 '전부 MIT'로 표기하지 않는다. 로컬 모드에 OpenAI Python SDK가 포함된 것은 의존성 목록이며 클라우드 호출 필수라는 뜻이 아니다.

## 판매 배포 전 해소할 항목

1. 빌드 시 `licenses/<component>/`에 정확한 배포본의 원문/NOTICE를 보존하고 THIRD-PARTY-NOTICES 인덱스를 생성한다. 해시와 출처 revision을 함께 남긴다. 누락은 release 빌드 실패로 처리한다.
2. 내부 시험 자산과 판매 자산을 분리한다. 모델/캐릭터 권리 상태 unknown이면 외부 배포판 빌드를 차단하되 내부 시험판은 그 상태를 명시한다.
3. DLL 재배포 허용 목록과 버전별 NVIDIA/Microsoft 약관을 대조한다. 모델 로컬 hash를 고정된 업스트림 artifact와 연결한다. model card 라이선스 표시는 파일 provenance 검증을 대신하지 않는다.
4. 자체 이용 약관·제3자 고지·라이선스별 소스 제공 의무 여부를 검토한다. 설치 동의 화면을 추가하는 것만으로 누락된 권리가 해결되지 않는다.
5. Python/.NET/WebView2/엔진 보안 업데이트 담당과 재검증 절차를 정한다. 지금 버전을 보안 최신이라고 보증하지 않는다. 고정 Runtime의 업데이트 책임은 제품 측에 있다.

## 공식 근거 (2026-09-29 확인)

- [Python 배포 및 포함 구성 라이선스](https://docs.python.org/3.12/license.html): 실제 동봉 버전의 LICENSE.txt도 보존한다.
- [.NET runtime MIT](https://github.com/dotnet/runtime/blob/main/LICENSE.TXT): 최신 링크는 방향 확인용이며 배포본10.0.12 고지를 별도로 수집한다.
- [llama.cpp b10830 LICENSE](https://github.com/ggml-org/llama.cpp/blob/b10830/LICENSE): MIT 원문, OpenMP/CUDA까지 대체하지 않는다.
- [WebView2 Runtime 배포](https://learn.microsoft.com/en-us/microsoft-edge/webview2/concepts/distribution): Fixed Runtime 동봉과 업데이트 관리. 배포 설명을 약관 전문으로 취급하지 않는다.
- [NVIDIA CUDA EULA](https://docs.nvidia.com/cuda/eula/index.html): 재배포는 지정 구성요소와 조건에 따라 검토한다. 현재 DLL에 맞는 보관 버전 약관 연결은 남아 있다.
- [Aggressive 모델 카드](https://huggingface.co/HauhauCS/Qwen3.5-9B-Uncensored-HauhauCS-Aggressive/blob/main/README.md), [기초 모델 LICENSE](https://huggingface.co/Qwen/Qwen3.5-9B/blob/main/LICENSE): 확인 시 Apache-2.0 표시, 배포 artifact revision 고정은 후속이다.

실행 코드/현재 패키지를 변경하지 않고 metadata·고지 파일·설정만 읽었다. 다음 작업은 [설치 계획](DESKTOP_INSTALLATION_PLAN.md)의 Task41 고지 수집/배포 판정이다.
