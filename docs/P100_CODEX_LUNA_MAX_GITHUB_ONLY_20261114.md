# DBVORA 최종설계 100% 경로 — Codex GPT-6 Luna Max / GitHub-only 실행 정본

> 작성 2026-11-14 KST · 실행자: Codex GPT-6 Luna Max · 독립 검수: ChatGPT GPT-6 High · 제품 소유자: 사용자  
> 저장소 `hibi89/DBVORA` · **기존 작업 브랜치 `feature/p0-db-map`만 수정** · 작성 직전 브랜치 HEAD: `2519290e69ca915fcd7997ee1ca12d42b6898676`. 실행 시작 시 HEAD 재조회 필수.  
> 본 파일은 **작업 공시/실행 명세**이며 제품 기능 완료, CI 성공 또는 공식 완성률 100% 선언이 아니다.

## 0. 정본·실행 권한·최종 목표
- 최종설계는 `REQUIREMENTS.md` 사용자 확정 7항(R01–R07), `AGENTS.md`의 OWNER-FINAL-BLUEPRINT-100, `docs/P100_INSTANT_EXECUTION_PLAN_20261114.md`의 기존 **48개 원자 ID**와 `docs/P100_HIGH_FINAL_REVIEW_20261114.md` H01–H12를 모두 보존한다. 이 문서는 **실행자 Instant → Codex Luna Max 변경, 순서·증거·GitHub-only 절차 구체화** 문서이다. 선행 계획의 ID/요구 삭제·축소 금지.
- 목표: 백엔드와 프론트엔드의 전체 R01–R07 기능을 GitHub에서 구현/검증하고 G90-01..03 기술 게이트를 통과한 뒤 고추론 GPT-6 High가 독립 감사(G90-04). **소유자 현장/권리 승인(G90-05)과 물리 정전·고객 환경 테스트는 GitHub만으로 대체 불가**, 증거 없으면 공식 최종완성률 `UNASSESSED` 및 `RELEASE HOLD` 유지. 95%는 과거 *비공식 기술 평가*일 뿐 현재 공식 95%가 아니다.
- 크몽 상품 등록·유료 결제·Vercel·Production·main/develop 병합·저장소 권한/공개·시크릿 추가·고객 DB 반입·백업 삭제·실사용 DB 변경은 **범위 제외 또는 별도 승인**. 사용자 PC/로컬 실행/파일 첨부/로그인/상용 테스트 요청 금지. 수용자가 나중에 독립 승인해야 하는 항목은 `OWNER_GATE`로 남긴다.
- Codex 작업 결과를 **오직 GitHub** 원격 브랜치 commit/PR, Actions run, artifacts(합성만), STATUS/HANDOFF/추적 문서로 남긴다. Codex의 별도 클라우드 작업공간이 존재해도 사용자의 로컬 PC를 쓰지 말며, 외부 서버/클라우드 DB/고객 파일을 테스트 수단으로 쓰지 않는다. 임시 GitHub-hosted Windows/Linux runner의 합성 테스트는 허용.
- 기존 작업을 소거하지 않는다. `main`은 안정 기준(조회 당시 `2c58799cde343ae0a176759e195202ecab97c345`), `develop`은 검증된 통합 기준(조회 당시 `890f842e3ba0e13c901e785633bdd06eadc76cce`)으로 **읽기만**. 작업 브랜치는 앞선 기능과 히스토리를 보존한다.

## 1. 설계 선택(성능·비용·유지보수)
| 선택 | 장점 | 단점/위험 | 결정 |
| --- | --- | --- | --- |
| A: 48개를 한 번에 대형 변경 | 작업 전환 감소 | 회귀 원인/원본 안전·정확 SHA 검증 어려움, 리뷰 비용 큼 | 제외 |
| B: 의존성 순서대로 소형 기능 커밋 + 합성 CI 묶음 게이트 | 실패 격리, 회귀·롤백 쉬움, 0원 기존 Actions 우선 | 증거/상태 기록 필요 | **채택** |
| C: 관측 데이터 저장을 HTTP POST/백그라운드 상시 자동화 | UI 연결 간편 | 기존 GET-only·동의 기본OFF·공격표면을 깨뜨림 | 제외 |
| D: 사용자 명시 동의 후 로컬 CLI/내부 서비스 실행으로 원장 기록, HTTP는 GET-only 조회 | 소버린/동의와 기존 API 호환, 재시작 후 조회 가능 | 사용자 동의/스케줄 구성 흐름을 명확히 설계해야 함 | **우선안** |
- 자동 관측·일/주 아카이브도 **기본 OFF**, 명시적 사용자 opt-in, 동일 실행/시간 슬롯 idempotency, 실패 시 기존 세대 유지. GitHub `schedule`로 사용자 DB를 수집하지 않는다. 실 시스템 작업 등록은 선택 가능한 구성 명세와 합성 runner 테스트까지만; 사용자 PC 실등록은 금지.
- CI가 비용 한도·권한·크레딧 문제로 막히면 `BLOCKED_CI` 기록하고 개선 가능한 방법 1회 재시도. 무의미한 재실행/빈 커밋/자동 반복 금지.

## 2. 시작 전 8가지 확인(첫 Codex 회차 필수)
1. GitHub repo/branch/HEAD, 로그인 계정·commit Author/Committer 및 쓰기 권한을 조회한다. `GIT_AUTHOR_EMAIL`/`GIT_COMMITTER_EMAIL` 덮어쓰기 금지. 브랜치가 뜻밖에 변경됐다면 새 변경 전에 diff 확인.
2. `HANDOFF.md` → `STATUS.md` → `AGENTS.md` → `REQUIREMENTS.md` → 이 파일 → 기존 48작업 마스터 → High H01–H12 → 실제 소스/테스트 순서로 읽는다. 길고 오래된 이력은 상단 최신 내용과 **실제 코드/정확 SHA Actions**가 우선.
3. 기능 HEAD `2519290...`의 최신 관측 원장·API 구현을 확인한다. 읽기전용 `GET /api/observations`와 opt-in `observation_ledger.py`는 이미 커밋됐지만 **최신 CI/로컬 실행 미검증**이다. 다시 만들지 말고 기존 테스트와 통합 문제부터 해결.
4. `R01-02` 다중 DB 동시 노드/키보드/390px는 이전 SHA에서 합성 Chromium 검증; `R01-07` 경합/Abort 일부 이전 SHA 검증. 재구현 금지, **새 HEAD에서 관련 회귀와 증거 정확성 확인**.
5. `R01-03` PG UI, `R02-03/R02-06` 영구 이력 UI 통합, `R03-04` 일·주 runner, `R03-07` 복원 UX가 우선 미완 갭. 실 PostgreSQL 16 localhost TLS 테스트 harness는 이미 존재.
6. `dbvora/api.py` / `dbvora/observation_ledger.py` / `dbvora/web` / `dbvora/connectors` / `dbvora/archive` / `scripts` / `tests`의 실제 경로 및 CI 구성부터 확인한다. 없는 모듈/명령을 존재한다고 가정하지 않는다.
7. `RELEASE HOLD`, `[작업중]`, 크몽 등록0, 공식 `UNASSESSED`를 보존한다. 외부 데이터·인증·시크릿·실고객 DB 없이 합성 fixture만 사용한다.
8. 이미 합격한 작업을 단지 문서 정리만으로 신규 완료 취급하지 않고, 이전 기능 PASS SHA와 신규 문서 SHA를 분리 기록한다.

## 3. 48개 작업 실행 보드(원래 ID 그대로; 초기 표시는 **계획**, 상태는 매 커밋 근거로 갱신)
모든 행의 기본 DoD: **(a)** 기존 구현/요구 갭 확인 **(b)** 필요한 최소 코드와 자동화 테스트 **(c)** 안전·원본불변·비밀보호 확인 **(d)** 원격 GitHub commit SHA **(e)** 같은 SHA의 실제 Actions 링크+PASS/FAIL/SKIP 또는 명시적 NOT_RUN **(f)** STATUS/HANDOFF 반영. `RECHECK`는 과거 근거를 검토할 것이라는 뜻이지 현재 PASS가 아니다.

### A. 기준선·기능 갭 (B00–B02; 3)
| ID | 실행 단위/검증 산출물 | 초기 판정 |
| --- | --- | --- |
| B00 | REQUIREMENTS 7개·금지·OWNER 게이트 전체를 항목별 추적표에 고정; 누락시 즉시 반영 | RECHECK |
| B01 | API/CLI/UI/압축/리소스/테스트↔R01–R07 맵; 기능마다 구현/미검증 구분 | RECHECK |
| B02 | 정확 branch SHA·이전 2OS release/Chromium/PG·원본 불변 증거 확인; 최신 HEAD CI는 별도 | RECHECK |

### B. 구조/다중 DB/PG (R01-01..07; 7)
| ID | 실행 단위/검증 산출물 | 초기 판정 |
| --- | --- | --- |
| R01-01 | 단일/2–8 SQLite 및 PG read-only, 출처/안전ID·테이블/PK/FK/index·동일 이름 충돌 테스트 | RECHECK |
| R01-02 | **동시에 보이는 다중 DB 노드**·클릭·Enter·390px·2OS 실제 Chromium; 기존 구현/증거 재사용 | RECHECK |
| R01-03 | PG16 verified TLS 읽기전용 사용자 진입 UI/조회 흐름; 보안정보·DSN/경로 UI·로그 미노출, TLS/권한 오류 복구·Chromium | OPEN |
| R01-04 | SQLite+PG 함께 보는 서비스 지도 및 사용자 명시 cross-DB 관계의 unverified 표시; 추정 관계 금지 | OPEN |
| R01-05 | 1,000표/997FK/2,000 workspace 제한, XSS·식별자·무한 graph/메모리 상한 회귀 | RECHECK |
| R01-06 | 키보드 Tab/Enter, ARIA, 작은 화면, 로딩/오류/15초 timeout·재시도, 하얀 화면 방지 실제 브라우저 | RECHECK |
| R01-07 | 느린 A→B DB 전환/동일 DB 테이블 전환 뒤 stale/abort/failed 응답 혼입 방어와 adversarial browser regression | PARTIAL_RECHECK |

### C. 측정/관측/영구추세 (R02-01..06; 6)
| ID | 실행 단위/검증 산출물 | 초기 판정 |
| --- | --- | --- |
| R02-01 | SQLite main/WAL/SHM·dbstat 범위 명시, 64MiB/0.75초 opt-in, 파일 identity 교체·미지원 오류 | RECHECK |
| R02-02 | 한 DB의 2시점 용량 변화/무관측·동시간·역순·DB 전환 응답 정합 Chromium | RECHECK |
| R02-03 | **관측 기록 end-to-end**: 기존 원장+GET API 먼저 테스트 → 사용자 명시 동의된 *로컬* 기록 진입(CLI/내부 경계) → 재시작 후 조회 → 동일 시각·역순·변조·해시·10k 상한·다중 DB 격리 테스트, GET-only 보존 | PARTIAL |
| R02-04 | DBVORA 프로세스 CPU/RSS와 filesystem disk 및 지원 가능 PG/SQLite 출처 분리, 불능 DB 전용 CPU는 unavailable | RECHECK |
| R02-05 | `pg_stat_*` 표·인덱스 추정치/권한 없음·통계 지연·누락을 PG UI에 정직하게 표시; PG16 합성 TLS | OPEN |
| R02-06 | **기존 session 8샘플 → 검증된 영구 원장 UI 조회 통합**, 3개 이상 시계열·동일 범위·기간/오류/버전·렌더 XSS·재시작·2OS Chromium | PARTIAL |

### D. 아카이브/복원/일·주 실행 (R03-01..10; 10)
| ID | 실행 단위/검증 산출물 | 초기 판정 |
| --- | --- | --- |
| R03-01 | SQLite backup API·WAL 동시쓰기·snapshot 일관성, 원본 SHA/mtime 유지 | RECHECK |
| R03-02 | ZIP/ZSTD/raw CAS/compressed CAS 각 독립 복원, 내용 SHA+integrity, 임의 경로/덮어쓰기/오염 거부 | RECHECK |
| R03-03 | 4세대 증분·중복·체인 개별 복원/부모 누락·손상·고립 청크 처리, 이전 세대 불변 | RECHECK |
| R03-04 | **일/주 opt-in 실행 runner**: CLI/서비스 호출만(기본OFF), 합성 날짜/UTC주 슬롯, 중복·재시작·실패 복구·시간대, 실제 GitHub Windows/Linux 실행 | OPEN |
| R03-05 | 멀티프로세스 동시 쓰기·예약 중복·복원 경쟁: 한 세대 한 번 publish/기존 보관본 불변 | RECHECK |
| R03-06 | ENOSPC·short-write·프로세스 abrupt-exit·재개·temp/orphan 관리; 기존 정상본 보존 | RECHECK |
| R03-07 | **별도 새 목적지로만 복원하는 미리보기/선택 UI 또는 안전한 워크플로 CLI**, 해시 검증·대상 존재 시 중단·오류 행동 안내, 브라우저/CLI 합성 | OPEN |
| R03-08 | 보존 정책 preview/용량·고립 파일 목록·누락/손상 보수적 처리; 자동 삭제0 | OPEN |
| R03-09 | Windows NTFS 경로 alias/ACL·rename/open handle/쓰기실패·독점생성 등 runner 합성 오류 주입 | OPEN |
| R03-10 | 실제 소유자 장치의 물리 정전·복구/원본 보존 **실물 수용**; GH만으로 수행 불가, Owner 승인까지 HOLD | OWNER_GATE |

### E. 벤치마크·보안·법적 경계 (R04-01..03, R05-01..05; 8)
| ID | 실행 단위/검증 산출물 | 초기 판정 |
| --- | --- | --- |
| R04-01 | ZIP/ZSTD/CAS 동일 합성 원본·옵션·기록 메타 반복 벤치, 복원 바이트/해시 일치 | RECHECK |
| R04-02 | 반복 N과 중앙값/분포·생성/복원시간/용량/CPU/RSS/IO 가용성·OS·캐시·제한조건 보고 | OPEN |
| R04-03 | PG/Supabase/70% 절감 등 직접 실측 없는 우월 주장 제거; 샘플값을 일반 성능 보장으로 바꾸지 않기 | OPEN |
| R05-01 | localhost Host/Origin/Fetch/CSP/GET-only, DNS rebinding/CSRF/XSS/임의 API 경로·row 노출0 시험 | RECHECK |
| R05-02 | symlink/hardlink/inode+ctime 교체·TOCTOU·path traversal/ZIP slip 및 create-only restore 검증 | RECHECK |
| R05-03 | PG credential/TLS/오류·로그·CI artifact/스크린샷에서 비밀·실파일 경로·사용자 row 노출0 확인 | OPEN |
| R05-04 | 실제 사용 의존성 LICENSE/NOTICE/SBOM 후보와 재배포 권리 검토표; 소유자/법적 확정은 별도 OWNER_GATE | OPEN |
| R05-05 | ZIP/manifest SHA 자기일치와 신원 인증·서명을 구별, 공격자 양쪽 변조 위협/한계·복원 거부 테스트 | OPEN |

### F. 확장·Windows 상품 사용성 (R06-01..03, R07-01..06; 9)
| ID | 실행 단위/검증 산출물 | 초기 판정 |
| --- | --- | --- |
| R06-01 | 외부 AX 소비용 **read-only, versioned** 메타데이터 스키마·오류·출처, raw row/token 없는 계약 | OPEN |
| R06-02 | HAE/LA 없이 독립 실행, mock 소비자 스키마 v1 호환·미지원 버전 거부·네트워크 기본OFF | OPEN |
| R06-03 | 실제 HAE/LA/SOVIA 통합은 초기 필수 아님; 별도 요구 확대가 없는지 문서 확인, 확대는 사전 승인 | OWNER_SCOPE_GATE |
| R07-01 | 최신 기능 SHA 기반 unsigned ZIP/EXE 산출·내부 SHA manifest, 소스와 바이너리 산출 재현 검증 | OPEN |
| R07-02 | GitHub-hosted Windows 실제 portable launch/종료/재시작/제거·기존 폴더/port 충돌·기본OFF | OPEN |
| R07-03 | 한국어 오류·동의·복원·안전/실패 안내, 실제 Chromium 390px/desktop·키보드/ARIA 스크린샷 | OPEN |
| R07-04 | 구매자/소유자의 **실제 Win10/11 실물 QA**는 GH runner 대체 불가, 별도 OWNER_GATE | OWNER_GATE |
| R07-05 | 상업권·서명·지원/환불·가격/소유자 최종 사용 수용은 GH만으로 확정 불가, RELEASE HOLD | OWNER_GATE |
| R07-06 | 동의된 실제 고객환경 장기 평가·물리 오류/복원은 데이터 접근·소유자 승인 필요; GH는 합성만 | OWNER_GATE |

### G. 게이트·감사 (G90-01..05; 5)
| ID | 실행 단위/검증 산출물 | 초기 판정 |
| --- | --- | --- |
| G90-01 | 모든 48 ID의 `소스SHA → 실제 테스트 run head SHA → 결과 → 미검증 → 요구 R01–R07` 표, 누락0 | OPEN |
| G90-02 | **기능 freeze SHA에서** Ubuntu/Windows 전체 Python+Node, 실제 localhost Chromium, PG16 TLS, ZIP/CAS 복원/runner/Windows preview 합성 게이트 0FAIL | OPEN |
| G90-03 | path/HTTP/DSN/CVE·의존성·기본OFF/개인정보·LICENSE/NOTICE 검사, 미해결 블로커·변경 범위 기록 | OPEN |
| G90-04 | ChatGPT GPT-6 High **독립 검수**: H01–H12 전수 실증 재조회·문제 코드 반송, 사용자 새 검수 요청 전 NOT_STARTED | HIGH_GATE |
| G90-05 | 소유자 요구·공식 가중치 100점 승인, 실물/상업권/물리정전 등 필수 수용 후 최종 100 판정; GH-only에서 불가 | OWNER_GATE |

**48/48 ID 존재 여부를 주기적으로 대조할 것.** 위 `OPEN/RECHECK/PARTIAL`은 시작 초깃값이며 현재 정식 완료율/진척 증명이 아니다.

## 4. 실제 코딩 순서(선행 조건·문제 분리)
- **S0 — 보존·갭 (B00–B02)**: 기존 source/CI/owner gates 및 정합성 읽기. 최신 observation API 단위테스트 CI 미검증을 먼저 기록.
- **S1 — 관측 작동 루프 (R02-03 → R02-06 → R02-02·01·04)**: 기존 `tests/test_observation_ledger.py`, `tests/test_observation_api.py`와 API를 재사용. ① 영구원장 read-only GET exact tests ② 동의된 로컬 기록 CLI/내부 호출 ③ UI `/api/observations` 조회와 세션 history 격리 ④ 3+시계열/결측·손상·재시작, 두 OS·Chromium. 기존 GET-only에 POST 추가 금지.
- **S2 — 전체 DB 지도+PG (R01-01/02 재검토 → R01-03 → R02-05 → R01-04 → R01-07/05/06 회귀)**: 이미 검증된 다중 SQLite topology를 다시 쓰지 말고 PG 진입·mixed metadata·권한/TLS/DSN masking을 보강. `scripts/pg_tls_local_acceptance.py`, `scripts/browser_http_e2e.py` 활용.
- **S3 — 복원과 실 실행 (R03-01/02/03 근거 확인 → R03-04 → R03-05/06 → R03-07 → R03-08/09)**: 데이터 기밀·원본 불변, 게시 atomicity/임시실패, 합성 일/주 runner, 조회·복구 preview. 원본/마지막 정상 아카이브 삭제 절대 금지.
- **S4 — 성능·보안 (R04-01..03, R05-01..05)**: 같은 합성 샘플에서 반복 벤치 + security regression. CI artifact·로그·스크린샷에서 비밀/고객데이터 금지.
- **S5 — 계약·사용성 (R06-01/02, R07-01..03)**: 독립 AX 메타데이터 계약, Windows-hosted portable 실행, 한국어 UX/오류/복원. R06-03/R07-04..06은 Owner gate로 보존.
- **S6 — 정확 SHA 동결/최종 검수 (G90-01..03 → G90-04 → G90-05)**: 기능 SHA 동결→필수 GH Actions 통과→High가 재조회 검수. 소유자 현장/법적 결정을 자율 수행·대리 승인하지 않는다.

각 S 구간의 작업은 여러 작은 commit으로 쪼개고, 테스트는 **적절한 기능 체크포인트에 묶어** 돌린다. CI를 무조건 건너뛰어 100이라고 주장하지도, 문서/사소한 변경마다 불필요하게 전체 CI를 반복하지도 않는다.

## 5. GitHub-only 실행·검증 계약
- 수정: `feature/p0-db-map`에만 최소 수정 commit, 혹은 같은 저장소의 **기존 브랜치를 대상으로 하는 PR**. 다른 브랜치/저장소로 변경하려면 승인 받는다. 소스·테스트 단위와 임시 방어 설계를 커밋/PR에 설명. force push/빈 커밋/원본 rewrite 금지.
- 실행: 이미 있는 `.github/workflows/dbvora-release-gate.yml` (Ubuntu+Windows Python3.11/Node22), `dbvora-browser-http-e2e.yml` (2OS Chromium), `dbvora-pg-tls-live.yml` (합성 PG16 TLS), `dbvora-windows-demo-exe.yml`, `dbvora-owner-preview.yml` 활용. 기존 워크플로의 push `paths` 필터는 일부 파일만 감시하므로 **비트리거를 PASS라고 오인하지 말 것**. 새 기능의 정확 SHA에서 필요 시 안전한 `workflow_dispatch`를 사용해 run head_sha를 검증한다.
- 명령(기존 workflow에서 실제 실행하는 기준): `python -m scripts.verify_release_gate`, `python -m scripts.browser_http_e2e`, `python -m scripts.pg_tls_local_acceptance`. 각 프로젝트의 실제 옵션/환경은 YAML·소스에서 다시 확인.
- **중요**: GitHub Actions의 `concurrency cancel-in-progress: true`로 이전 SHA run이 `CANCELED`될 수 있다. 이를 PASS로 취급하거나 CI 점수로 산입하지 않는다. 마지막 기능 변경 SHA 고정 후 필수 gate의 성공 run head SHA 정확 비교.
- CI가 실패하면 정확한 실패 단계/로그 확보→원인별 2안 비교→최소 수정→1회 개선 재시도. 검증 가능한 개선이 없는 2회 실패는 STOP/PIVOT + 문제/원인/대안/사용자 선택사항. GitHub 일시 장애는 제품 코드 오류로 단정하지 않기.
- 테스트 자료는 CI runner가 생성한 **합성 SQLite/PG** 전용. 실 고객 DB·비밀번호·개인경로·사용자 메일/토큰은 로그, artifact, issue, README, commit에 절대 기록하지 않는다. Artifact 보존기간·해시 명시.
- 진척 점수는 **공식 `UNASSESSED` 고정**, 승인 가중치가 없는 상태에서 48개 작업 완료수·과거 기술95·G50/G70 같은 단계명을 퍼센트로 환산하지 않는다. 기술 게이트는 각 task `PASS_SCOPED`로만 표시.
- 중앙 `hibi89/hackathon-command-center-2026@kmong-productization` 상태 원장은 **공식 점수/원장 변경 권한·최신 HEAD 확인 후** 동기화. 이 계획 공시만으로 중앙 공식 완성률을 올리지 않으며, 중앙 업데이트 권한/정합성 불가면 `KMONG_HUB_SYNC_PENDING` 문서화.

## 6. 한 작업 완료 보고 템플릿(STATUS/HANDOFF에 실제 근거로 채우기)
```text
ID: Rxx-yy | 상태: OPEN/IN_PROGRESS/PASS_SCOPED/BLOCKED_CI/OWNER_GATE/HIGH_GATE
최종 요구/수용: REQUIREMENTS Rxx + 세부 테스트 기준
시작 branch HEAD: <sha>
실제 변경: <파일, 변경 기능, 읽기/쓰기 경계, A/B 결정>
코드 SHA: <sha> / 테스트 추가 SHA: <sha> / 문서 SHA: <sha>
실행: <workflow URL + run head_sha + OS + 명령>
결과: <PASS n / FAIL n / SKIP n / CANCELED 여부>
원본 보존·비밀·GitHub artifact 검사: <검증 결과 or NOT_VERIFIED>
남은 문제: <실기기/법적/물리 장애 등, 가정과 구별>
다음 실행 ID: <정확히 하나>
공식 최종완성률: UNASSESSED | 과거 기술95(비공식) | RELEASE HOLD | 크몽0
```

## 7. Codex 종료·High 인수인계 기준
- 각 세션 종료 시 `STATUS.md` + `HANDOFF.md` 10항 + `docs/NEXT_TASK.md`에서 **완료 ID / 대기 ID / 정확 기능 SHA / Actions URL / 미검증** 일치. 상태 불변이면 불필요한 커밋 금지.
- 48개 항목 상태 표, 최종 HEAD, PR/commit 목록, run head SHA, Windows/Ubuntu 각 PASS/FAIL/SKIP, Chromium·PG·독립 복원·성능·정적 보안·사용권, 변경 파일, 원본 및 비밀 불변, owner gates를 요약해 사용자에게 반환. 신규 코드를 위해 새 저장소/유료 서비스/배포 자산을 만들지 않는다.
- High 검수는 `docs/P100_HIGH_FINAL_REVIEW_20261114.md` H01–H12를 기능 SHA로 독립 수행. `G90-04`는 Codex 자기 검수로 대체 불가. High 수정 필요시 Codex 작업 ID로 반송.
- **GitHub-only 목표의 상한을 명시**: 모든 GitHub 재현 가능한 개발/합성 테스트를 PASS 시켜도 소유자 실제 PC·전원단절·상업 권리/가격/지원/100점 공식 수용을 충족했다고 주장할 수 없다. 범위 축소 없이 별도 `OWNER_GATE`로 유지. 사용자가 지금 로컬 작업을 하지 않는다는 결정은 그대로 존중한다.

## 8. 지금 바로 시작할 단위
**첫 실제 변경:** `R02-03`과 `R02-06`의 기존 opt-in 영구 원장/GET API를 최신 HEAD에서 확인, `tests/test_observation_ledger.py`·`tests/test_observation_api.py` 검증 경로와 UI 통합 갭을 분리. 최초 코드 변경은 읽기 전용 UI 연결과 결정론적 synthetic test처럼 최소 단위로 시행. 이후 필요시 명시 동의 CLI 기록 경로(POST 없이), 재시작·차단 테스트. **코드 수정 전 최신 HEAD 재조회; 이 문서 커밋의 HEAD로 시작**.
