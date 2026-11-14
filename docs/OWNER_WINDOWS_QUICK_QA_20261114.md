> **2026-11-14 소유자 유효 ZIP 우선:** [run #43553401541](https://github.com/hibi89/DBVORA/actions/runs/43553401541) `dbvora-UNSIGNED-OWNER-PREVIEW-2011d5...` 바깥 artifact를 다운로드하고, 안쪽 `dbvora-dev-preview-0.2.0.zip` 해시가 **`1c1b4a395a7ee21fbd2cd8127aea479c55be0755284988f36d70fd998e5b8e38`**(62파일)인 경우에만 압축해제/합성 검수. 테스트 코드/기능 SHA `2011d5fda1bd3d91b0010b5901fdf6149e0a31cc`, 양 OS [검증 #43553401567](https://github.com/hibi89/DBVORA/actions/runs/43553401567) 성공. 이전 작업 폴더의 구 버전과 섞지 말 것. 윈도우 EXE 데모는 별도 구버전·미서명 합성-only여서 지금 62파일 source 최신기능의 실행본이라 주장 금지. 어떤 보안 경고도 우회하지 말고 해당 경고와 오류 상태만 확인. **현재 PC 사용자 검수는 미실행**, 13:00 KST 통합 지시 때만 사용자 요청. 고객DB/PG 비밀번호/개인정보/실서비스 사용 금지.

> **2026-11-14 최신 사용자 ZIP 연결 정정:** [Ubuntu source preview #43553401541](https://github.com/hibi89/DBVORA/actions/runs/43553401541), artifact `dbvora-UNSIGNED-OWNER-PREVIEW-2011d5...`, 검증된 **안쪽 62파일 ZIP SHA-256 `1c1b4a395a7ee21fbd2cd8127aea479c55be0755284988f36d70fd998e5b8e38`**. 이 SHA가 다르면 실행 중단. 이전 SHA의 ZIP을 Downloads에서 자동 최신으로 선택하지 말고 이 해당 실행의 바깥 artifact만 해제할 것. 새로운 CI/test source `2011d5fda1bd3d91b0010b5901fdf6149e0a31cc`는 기존 사용자용 ZIP의 앱 기능과 별도이며 [Windows/Linux 677 discovery 12/12 PASS](https://github.com/hibi89/DBVORA/actions/runs/43551764326) 확인. 이 미서명 ZIP·명령에 고객 DB/키 입력 금지. 아직 사용자가 Win10 실제 QA를 수행한 증거는 없으며 13시 통합 요청 전 즉시 PC 작업 불필요.

# DBVORA 사용자 Windows10 실기기 한 번 검수 — 2026-11-14
**오늘 13:00 KST 통합 알림 전 사용자 PC 작업 요청 없음.** GitHub Windows2025/Linux 합성 테스트 통과로 소유자 Windows10에서 나중에 실제 사용성·설치·NTFS·오프라인 화면을 한 번만 확인하면 됨. 고객 DB·암호·PG 연결 문자열·개인정보는 **입력 금지**. 0원 공개 테스트 도구만 사용.

## 최신 정확 SHA 검증 및 선택형 단독 데모
- 현재 원본 기능검증 SHA `2011d5fda1bd3d91b0010b5901fdf6149e0a31cc`, 最新 ZIP 내부SHA `1c1b4a395a7ee21fbd2cd8127aea479c55be0755284988f36d70fd998e5b8e38`; 반드시 [해당 ZIP run #43553401541](https://github.com/hibi89/DBVORA/actions/runs/43553401541)만 사용하고 다운로드 폴더에 기존 예전 ZIP이 있으면 **자동으로 최신 하나를 추정하지 말고** 위 SHA 일치한 파일만 선택. 해시 불일치 시 중단. 바깥쪽 artifact의 SHA와 안쪽 preview ZIP SHA는 서로 다름.
- Python 미설치 시 [Windows2025 미서명 합성 전용 EXE 성공 #43546585469](https://github.com/hibi89/DBVORA/actions/runs/43546585469)를 별도 검토할 수 있으나, **오래된 코드 SHA의 합성 HTML 단일 시연만 가능**(raw/zlib CAS/실고객 DB 포함 안 됨). EXE SHA256 `510cb5733cbffd8bc134b5a9ed9781d9fe64782db6661c8f047504d0141c128d`; SmartScreen/백신 경고가 있으면 우회/예외 등록하지 말고 결과만 보고. PC 사용자 최종 QA는 소유자 현장 점검 후에만 수용.

## 우선 경로 — GitHub 생성 검증 ZIP으로 PC 작업 최소화 (무료·합성 데이터 전용)
- <https://github.com/hibi89/DBVORA/actions/runs/43553401541> 하단 **Artifacts**에서 `dbvora-UNSIGNED-OWNER-PREVIEW-2011d5...` 다운로드. 그 **바깥쪽 ZIP**을 별도 폴더로 압축 해제하면 **안쪽 `dbvora-dev-preview-0.2.0.zip`** 및 `unsigned-build-report.json`을 찾을 수 있음. artifact는 **2026-11-21 KST 만료 예정**.
- 안쪽 ZIP의 검증된 SHA-256은 **`1c1b4a395a7ee21fbd2cd8127aea479c55be0755284988f36d70fd998e5b8e38`** (GitHub source `2011d5fda1bd3d91b0010b5901fdf6149e0a31cc`, 62 소스 파일, 미서명). 내려받은 파일의 hash가 다르면 **즉시 중단**. 절대 고객 DB/키를 입력하지 않음.
- 설치 전제: **기존 Python 3.11**만 필요. 아래 검증은 FastAPI/Node/zstd 설치나 유료 결제 불필요. 기존 같은 이름 폴더 덮어쓰기 금지.

```powershell
# 바깥쪽 Actions 아티팩트 ZIP은 수동 압축해제하여 안쪽 ZIP 위치만 선택
$inner = Get-ChildItem -Path "$env:USERPROFILE\Downloads" -Filter 'dbvora-dev-preview-0.2.0.zip' -File -Recurse -ErrorAction Stop |
  Sort-Object LastWriteTime -Descending | Select-Object -First 1
if (-not $inner) { throw '개발자 미리보기 ZIP 없음' }
$expected = '1c1b4a395a7ee21fbd2cd8127aea479c55be0755284988f36d70fd998e5b8e38'
if ((Get-FileHash -LiteralPath $inner.FullName -Algorithm SHA256).Hash.ToLowerInvariant() -ne $expected) { throw 'ZIP SHA 불일치: 실행 금지' }
$dest = Join-Path $env:USERPROFILE 'Downloads\DBVORA-OWNER-SYNTHETIC-QA'
if (Test-Path -LiteralPath $dest) { throw '기존 대상 폴더 존재: 새 이름 선택 후 재시도' }
Expand-Archive -LiteralPath $inner.FullName -DestinationPath $dest
Push-Location -LiteralPath $dest
try {
  & .\verify_dbvora_portable_windows.cmd
  if ($LASTEXITCODE -ne 0) { throw 'ZIP 출처 미서명 정합성 검사 실패' }
  & .\check_dbvora_windows.cmd
  if ($LASTEXITCODE -ne 0) { throw '합성 스키마 검사 실패' }
  & .\check_dbvora_archive_windows.cmd
  if ($LASTEXITCODE -ne 0) { throw '합성 ZIP/ZSTD 복원 검사 실패' }
  $output = Join-Path $dest 'synthetic-map-preview'
  New-Item -ItemType Directory -Path $output | Out-Null
  py -3.11 -B -m dbvora.demo_preview --synthetic-only --out $output
  if ($LASTEXITCODE -ne 0) { throw '오프라인 HTML 생성 실패' }
  Get-ChildItem -LiteralPath $output -Filter 'dbvora-map-*.html' |
    Sort-Object LastWriteTime -Descending | Select-Object -First 1 |
    ForEach-Object { Invoke-Item $_.FullName }
} finally { Pop-Location }
```

브라우저에서 **테이블 클릭·FK/컬럼·화면 잘림만 눈으로 확인**한다. 실제 Windows10/NTFS QA는 사람이 확인한 후에만 완료 판정한다. GitHub 자동화 Windows2025와 별도이며, ZIP의 manifest SHA는 **서명·원저작자 인증이 아님**. 오프라인 PowerShell/로컬 검증이므로 로그인·외부 업로드 불필요. 오류가 있으면 경로·개인정보를 지우고 **상태 코드/테스트 결과만** 전달.

아래 기존 전체 원본 clone + 현재 651개 발견 release gate 방식은 **선택적 추가 심층 QA**이며 이번 1회 실기기 UX 검수 목적에서는 우선 경로를 권장한다.

## PowerShell — 귀가 후 복사해 실행
1. 이미 Git for Windows, Python 3.11, Node 22+가 설치되어 있으면 재설치 불필요. Downloads에 **새 폴더로만** 복제; 기존 프로젝트 복사본/데이터를 덮어쓰지 않는다.
```powershell
Set-Location "$env:USERPROFILE\Downloads"
$target = "DBVORA-OWNER-QA-20261114"
if (Test-Path -LiteralPath $target) { throw "동일 이름 폴더 존재: 중단(덮어쓰기 금지)" }
git clone --single-branch --branch feature/p0-db-map https://github.com/hibi89/DBVORA.git $target
if ($LASTEXITCODE -ne 0) { throw "git clone 실패" }
Set-Location -LiteralPath $target
py -3.11 -m pip install -e ".[ui,test]"
if ($LASTEXITCODE -ne 0) { throw "개발 테스트 패키지 설치 실패" }
py -3.11 -m scripts.verify_release_gate
if ($LASTEXITCODE -ne 0) { throw "synthetic full release gate FAIL - 출시 중단" }
```
2. 별도의 합성 데이터 기반 오프라인 HTML 파일만 생성·열어보기:
```powershell
$out = Join-Path $env:USERPROFILE "Downloads\DBVORA-OWNER-PREVIEW"
if (-not (Test-Path -LiteralPath $out)) { New-Item -ItemType Directory -Path $out | Out-Null }
py -3.11 -B -m dbvora.demo_preview --synthetic-only --out $out
if ($LASTEXITCODE -ne 0) { throw "합성 HTML 생성 실패" }
Get-ChildItem -LiteralPath $out -Filter "dbvora-map-*.html" |
  Sort-Object LastWriteTime -Descending | Select-Object -First 1 |
  ForEach-Object { Invoke-Item $_.FullName }
```
3. 브라우저에서 테이블 클릭→컬럼·PK/FK·인덱스, 창 폭을 좁혔을 때 가로 넘침 여부만 확인. 실제 고객 DB 없이 합성 데이터로만 시험한다.

**기대값:** PASS_SYNTHETIC_ENVIRONMENT_ONLY와 release gate 12단계 PASS. zstd 별도 실행파일이 없다면 정확한 skipped_no_local_codec 표기 및 게이트 판정에 따르며, 임의 PASS 처리 불가. 현재 호스팅 Windows 2025의 POSIX chmod 0600 전용 테스트 1개 SKIP은 허용된 별도 플랫폼 항목. 사용자 Windows10에서는 오류 발생 시 error_code/failed_test_ids/상태만 공유하고 로컬 폴더/실데이터/토큰은 올리지 않는다.

정확 최신 CI 합격 기능·검증 소스 SHA: 2011d5fda1bd3d91b0010b5901fdf6149e0a31cc (사용자 포터블 소스 ZIP code 2011d5fda1bd3d91b0010b5901fdf6149e0a31cc; 이후 CI/테스트 강화만). 복제 시 최신 코드가 달라졌으면 해당 SHA의 새 Actions 결과를 확인해야 한다. 이 테스트 통과로 고객용 서명/배포권/실 PG TLS/물리 power-loss 검증 또는 최종100점이 자동 승인되는 건 아니다.
