> **[2026-11-14 P100 진행·최신 정확 검증]** 기능 source `2011d5fda1bd3d91b0010b5901fdf6149e0a31cc`, Ubuntu24.04 Python677PASS/0FAIL, Windows2025 676PASS+1 POSIX-only SKIP/0FAIL, 필수 12/12×2 [CI](https://github.com/hibi89/DBVORA/actions/runs/43553401567). CPU·RAM은 **DBVORA Python process**, 디스크 total/free는 승인된 **로컬 볼륨**만 실제 측정/출처 구분, remote PostgreSQL CPU·RAM은 미지원(null). [최신 미서명 synthetic developer ZIP](https://github.com/hibi89/DBVORA/actions/runs/43553401541) 62파일 안쪽 SHA `1c1b4a395a7ee21fbd2cd8127aea479c55be0755284988f36d70fd998e5b8e38`, 고객 출하용 아님. **공식 P100 UNASSESSED(내부 기술95는 과거 이력), [작업중]/RELEASE HOLD/실 크몽 등록0**, 실제 Win10·물리전원손실·상업권리/지원/가격/사용자 acceptance 미완료. 사용자 개입은 기존 13시 통합 알림.

> **2026-11-14 최신 자동 수용 범위:** [source SHA `c9823a3d48c4`](https://github.com/hibi89/DBVORA/actions/runs/43551764326)에서 Ubuntu669PASS·Windows668PASS+POSIX전용SKIP1 /0FAIL, 각 필수12/12 PASS·최소668 커버리지. 합성-only v2 CAS ENOSPC/게시오류, 실제 자식 프로세스 강제 종료, ISO-week 슬롯·경로오류 비노출 검증. [최신 unsigned source ZIP 61파일/검증 SHA](https://github.com/hibi89/DBVORA/actions/runs/43551568838), 오너 QA `docs/OWNER_WINDOWS_QUICK_QA_20261114.md`. **실 Win10/전원손실·고객DB/서명·사용권·가격·판매 승인 전: 공식 P100 UNASSESSED, [작업중], RELEASE HOLD, 등록0**. 13:00 KST에 소유자 개입만 모음.

> **최신 P100 작업 검증(2026-11-14 KST):** `9d24a58a045fd89a11d46c685ee59adec3ed63e8`에서 [Windows2025+Ubuntu24.04 합성 전체 #43549905413](https://github.com/hibi89/DBVORA/actions/runs/43549905413) **651 발견/OS·Windows650PASS+1SKIP/Linux651PASS·12/12 필수 게이트/OS**. 실제 로컬 PostgreSQL16 `verify-full` read-only 5/5 [#43545900975](https://github.com/hibi89/DBVORA/actions/runs/43545900975), Chromium localhost 8/8×2 [#43544065399](https://github.com/hibi89/DBVORA/actions/runs/43544065399), 사용자용 **61파일 unsigned 개발자 ZIP** [#43549905406](https://github.com/hibi89/DBVORA/actions/runs/43549905406), unsigned Windows *합성 데모 전용* EXE 실제 실행 [#43546585469](https://github.com/hibi89/DBVORA/actions/runs/43546585469). Raw CAS v1와 별도 압축 zlib CAS v2 CLI는 synthetic-only, 독립복원/손상거부 검증 완료. 합성 동일 2세대에서 Linux ZIP31,216B vs v2 24,637B(21.1% 적음)이며 일반 성능 보장 아님. 아직 고객·실 Windows10/전원단절·상업라이선스·실상품은 미검증: **공식 UNASSESSED, [작업중], RELEASE HOLD, 크몽 등록0, Production 미적용**. 기존 README의 오래된 인벤토리·미검증 서술보다 최신 `STATUS.md`의 정확 SHA를 우선한다.

> **현행 저장소 공개범위 안내(2026-11-14 KST)**: GitHub에서 `hibi89/DBVORA`는 현재 **Public**으로 관측된다. 아래 본문의 `Private`는 이전 상태의 역사적 문구다. 공개 여부·권리 변경은 소유자 승인사항이며 라이선스·NOTICE 및 고객 배포 승인 전까지 **판매 RELEASE HOLD**, 코드가 공개라는 사실이 무제한 재사용 허락을 의미하지 않는다. 최신 릴리스 게이트 증거는 `STATUS.md`, `HANDOFF.md`를 참조.

# DBVORA

> **2026-10-28 USER CANONICAL HAE INTEGRATION:** [HAE 4-필수-제품 생태계 정본 (PRIVATE)](https://github.com/hibi89/HAE/blob/main/docs/ECOSYSTEM_CANONICAL.md) — HAE 자연어·단계별 고객 안내 → LA 플로우/실제 업무 데이터 DB 쓰기 → SOVIA 위험·실행 감사 → DBVORA 승인된 DB의 구조·크기·상태·검증 백업/복구 → HAE 통합 결과. **DBVORA는 전체 HAE 완성의 필수 통합 요소이면서 독립 제품**이다. 업무 데이터 실제 저장은 LA/승인된 데이터 어댑터 책임이고 DBVORA는 관리·가시화·보존을 맡는다. 현재 전체 연결은 목표일 뿐 실현 완료 아님. 다른 REA_APP/SMAX/코드체커 등은 외곽 확장 모듈.

**Database Visibility · Optimization · Recovery · Archiving**

로컬 우선, 사용자 소유 데이터 기반의 **통합 DB 관제·무손실 아카이빙·저장 최적화** 제품 (P0 인벤토리·로컬 UI 및 P1-C0/C1 합성 SQLite 백업·ZIP/ZSTD 복원·비교 및 P1-C2 장애 처리 및 P1-C3 재시작 읽기 전용 검증 구현; 상용 안정성 검증 전).

> **새 ChatGPT 채팅방 재개 문장:** `[디비보라 깃헙보고 작업해]`
>
> 이 문장이 들어오면 저장소의 **최신 원격 상태**를 확인하고 `CHAT_BOOTSTRAP.md` → `HANDOFF.md` → `STATUS.md` → `AGENTS.md` → `REQUIREMENTS.md` → `docs/NEXT_TASK.md` → 실제 소스 순서로 읽은 후, 이전 완료 작업을 반복하지 말고 첫 미완료 작업을 직접 진행한다. 사용자 메시지 `ㄱ`는 다음 개발 단위 진행 신호다.

## 제품 경계

- **DB 구조 맵**: 연결된 DB·테이블·컬럼·키·검증된 관계를 클릭해서 탐색한다.
- **관제**: 데이터 크기, 저장량 변화, *실제로 측정 가능한 범위* 내의 연결/자원 정보를 확인한다.
- **저장 최적화**: 안전한 스냅샷 생성 → 유형별 압축·선택적 중복 제거 → 검증된 무손실 복원 → 선택적 보존 정책.
- **소버린**: 기본적으로 localhost에서 실행하며 고객 데이터/비밀을 당사 서버로 전송하지 않는다.
- **다른 제품과 독립**: REA_APP은 앱 기술 역설계 도구이지 DBVORA의 중앙 오케스트레이터가 아니다. DBVORA도 AX 생태계 전체를 통제하는 플랫폼이 아니다.

## 현재 실제 상태 (브랜치별로 구분)

- main / develop: 원래 초기 설계·문서 기준, 아직 제품 기능 코드 미반영.
- feature/p0-db-map: P0-01 read-only 인벤토리 + P0-02 FastAPI localhost 구조맵 UI, 합성 Python unittest 28/28, Node DOM 시뮬레이션 1/1, 실제 localhost HTTP 200/403 확인. 브라우저 E2E는 정책 차단으로 미검증. 최신 SHA는 원격 직접 조회.
- feature/p0-db-map의 신규 P1-C0: SQLite online backup 기반 합성 snapshot, ZIP/manifest, 독립 새 경로 복원, SHA256+integrity_check 확인. 전체 Python 46/46 PASS 및 Node DOM 1 PASS. 실제 고객 DB/Windows/Power-cut 미검증.
- feature/p0-db-map P1-C1: ZSTD 레벨 1/3/9, 안전한 신규 경로 복원, 손상·변조 거부, 합성 동일 조건 3회 벤치마크. 전체 Python 62 PASS, Node DOM 1 PASS (P1-C2 이전 기준). 공식 zstd CLI가 로컬에 별도 필요하며 Windows 실행 파일은 패키징되지 않았다.
- feature/p0-db-map P1-C2: 파일/디렉터리 fsync, 새 파일 독점 게시 및 게시 오류 롤백, 임시파일 판독/명시적 정리, 강제 프로세스 종료·다중 프로세스 실험. Python 76/76 PASS (Linux synthetic only). 실제 전원 차단 검증은 미완료.
- feature/p0-db-map P1-C3: 재시작 후 SQLite/ZIP/ZSTD 파일을 별도 임시 폴더로 복사·검증하고 원본/이전 정본은 변경하지 않는 감사 기능, 임시파일/불완전 파일 분류, 합성 파일시스템 호환성 진단. Python 96/96 PASS. 콘텐츠 무결성과 실제 게시 내구성은 구별.
- feature/p0-db-map P1-C4: 백업별 독립 completion receipt와 이전 기록 SHA 계보, 완전 복원 검증, 기록 누락/변조/손상 거부, 중복 작성 안전 실패. Linux 합성 테스트 누적 Python 125/125 PASS. 영수증은 미서명·미암호화이며 전원 차단 보증 아님.
- 개발용 archive CLI는 구현됨(P1-C5, 합성 검증만). 아직 구현되지 않음: 고객용 검증된 전원중단 복구·증분/예약 보관, Windows 설치기. 브라우저 실제 렌더링, 고객 DB 미검증. 합성 ZIP 결과를 상용 압축률로 해석 금지.
- 실행 방법: [docs/P0_02_USAGE.md](docs/P0_02_USAGE.md); P0-01 계약: [docs/P0_01_USAGE.md](docs/P0_01_USAGE.md); 다음 작업: [docs/NEXT_TASK.md](docs/NEXT_TASK.md).
- 외부 유료 API·서버·데이터 전송·Vercel 배포 없음.

## 문서 및 작업 구조

- [CHAT_BOOTSTRAP.md](CHAT_BOOTSTRAP.md) — 단문 재개 절차
- [HANDOFF.md](HANDOFF.md) — 필수 10개 항목 인수인계
- [STATUS.md](STATUS.md) — 진행·차단·검증 현황
- [AGENTS.md](AGENTS.md) — 개발·보안·Git 운영 원칙
- [REQUIREMENTS.md](REQUIREMENTS.md) — 사용자 요구와 범위
- [docs/P0_02_USAGE.md](docs/P0_02_USAGE.md) — 로컬 웹 실행·검증·제약
- [docs/P1_C0_VERIFICATION.md](docs/P1_C0_VERIFICATION.md) — 합성 SQLite 백업·ZIP 무손실 복원 계약 및 검증
- [docs/P1_C1_BENCHMARK.md](docs/P1_C1_BENCHMARK.md) — ZIP/ZSTD 합성 데이터 3회 실측·한계
- [docs/P1_C2_DURABILITY.md](docs/P1_C2_DURABILITY.md) — 중단·동시성·fsync 검증과 비보장 범위
- [docs/P1_C3_RECOVERY.md](docs/P1_C3_RECOVERY.md) — 재시작 검증·파일 복구 상태/한계
- [docs/P1_C4_RECEIPTS.md](docs/P1_C4_RECEIPTS.md) — 독립 완료 기록·미서명 계보·중단 검증
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) — 설계 대안·선정안·데이터 흐름
- [docs/COMPRESSION_PLAN.md](docs/COMPRESSION_PLAN.md) — 압축·복원·벤치마크 계약
- [docs/ROADMAP.md](docs/ROADMAP.md) — MVP 이후 단계
- [docs/NEXT_TASK.md](docs/NEXT_TASK.md) — 다음 실제 구현 작업
- [docs/INTEGRATION_BOUNDARIES.md](docs/INTEGRATION_BOUNDARIES.md) — 다른 AX 제품과 경계

**2026-11-14 확인:** 실제 GitHub 저장소 상태는 Public (기존 Private 표기는 오기). 상업 이용/배포 권리, 타사 NOTICE·LICENSE 및 고객 지원·판매 승인은 아직 미확정이다. 사용자 사전 승인 없이 저장소 접근 정책이나 보안 설정을 변경하지 않으며 실고객 연결·대외 판매는 RELEASE HOLD.

### Local developer source preview (v0.2.0, unsigned)
From private source root, build a non-overwriting ZIP containing only DBVORA code and offline launcher templates:
```bash
python -m scripts.build_portable --output /absolute/existing/output
python -m scripts.build_portable --verify /absolute/existing/output/dbvora-dev-preview-0.2.0.zip
```
The ZIP is a source bundle, not a Windows installer or bundled Python. The extracted `README_PORTABLE.txt` documents prerequisite Python3.11 and optional UI dependency installation. The SHA-256 manifest is unsigned and does **not** authenticate origin. Only synthetic/approved test DBs until native Windows/NTFS validations pass. Browser Chromium-only DOM probe (not HTTP E2E): `python -m scripts.browser_visual_probe --chromium /usr/bin/chromium` with optional Playwright installed.

### No-dependency local schema HTML (2026-10-26)
From the developer ZIP or source checkout, Python 3.11+ can generate an **offline one-file HTML topology report** without installing FastAPI/Uvicorn:
```sh
python -m dbvora.export_html --db /absolute/synthetic.sqlite --out /absolute/existing/folder
```
On Windows, use `py -3 -m dbvora.export_html --db "C:\absolute\synthetic.sqlite" --out "C:\existing\folder"` or `export_dbvora_map_windows.cmd` with those two arguments. Open generated HTML offline. It includes schema metadata names, so **never share a confidential schema without authorization**; no rows or customer DB paths are inserted. [Detailed usage and evidence](docs/OFFLINE_HTML_PREVIEW_20261026.md). This is unsigned, not a standalone installer or customer-ready Windows backup solution.

## Fastest synthetic-only MVP preview (2026-10-27)

Use Python 3.11+ from a checkout and an **existing absolute output directory**. No FastAPI/Node/SQLite source file is required from the operator, and no real customer database is read:

```powershell
py -3.11 -B -m dbvora.demo_preview --synthetic-only --out "E:\\DBVORA_GIT"
```

Open the newly generated `dbvora-map-<uuid>.html` with a local browser. The created SQLite database is synthetic (departments/employees, FK, indexes); it is deleted with its OS temporary directory after export. The new HTML filename is generated exclusively, never overwriting an existing one. **It is a schema map, not a backup**. The HTML contains only synthetic metadata and is safe for demo use; no network or paid service is used by the generator.

Developer checks: `python -m unittest -q tests.test_demo_preview` (six tests). First isolated Linux3.13 control-flow smoke with a mocked HTML exporter: **6/6 PASS**; full Git checkout integration and real `file://` browser are not yet verified. Existing offline self-test (`python -m dbvora.offline_selftest`) tests the actual exporter but doesn't persist a demo HTML. Read `docs/MVP_GAP_MATRIX_20261027.md` for scope, original-design differences and release gates. Do not load real/customer databases until specifically authorized and Windows archive safety has passed.

## P0-03 multi-DB workspace metadata (2026-10-27)

`dbvora.workspace.inspect_workspace([db_a, db_b, ...])` aggregates **2–8 explicitly selected absolute SQLite files** into one read-only metadata contract. It includes separate DB nodes, table/column/index descriptions, scoped declared FK edges and measured sum of main DB file bytes. It deliberately does **not** infer cross-DB relations, query table rows or report fabricated CPU/RAM usage. Synthetic test: `python -m unittest -q tests.test_workspace_registry`.

A two-DB interactive offline HTML prototype exists as a **separate temporary conversation source ZIP**, not yet committed to GitHub; do not mistake it for a shipped UI. Release gate minimum 261 Python cases. Details: [docs/P0_03_WORKSPACE_EVIDENCE_20261027.md](docs/P0_03_WORKSPACE_EVIDENCE_20261027.md).

## P0-03 interactive multi-DB HTML MVP (2026-10-27)

One-command **synthetic-only** demonstration from private source checkout, using an already existing absolute output folder:

```powershell
py -3.11 -B -m dbvora.workspace_html --synthetic-only --out "E:\\DBVORA_GIT"
```

Opens a newly created `dbvora-workspace-<uuid>.html`: 2 temporary SQLite databases, DB selector, tables/columns/PK/indexes, declared FK SVG lines, size sourced only from main DB file bytes. The generated SQLite fixture files are removed; no real source DB, network, package install or backup write is required. **Do not mistake this for a customer-ready backup or native Windows certified package.**

For synthetic/authorized fixture databases only: `python -m dbvora.workspace_html --db /absolute/one.sqlite --db /absolute/two.sqlite --out /existing/absolute/output`. No implicit database search or row export; between 2 and 8 distinct SQLite paths. Tested locally on Linux3.13.5: 22/22 Python target cases and Chromium 12 DOM checks PASS; actual Windows file navigation and full 276 test suite are unverified. Evidence: `docs/P0_03_WORKSPACE_EVIDENCE_20261027.md`.

## P0-04 manual, unverified cross-DB metadata links
Offline multi-DB HTML now shows a separate cross-DB relationship panel. Only explicitly declared, catalog-valid column pairs appear, labeled **user-declared / unverified**; clicking one selects the destination database/table. No real cross-DB FK constraint or row-level join is inferred.
The synthetic `--synthetic-only` demo includes a generated example `products.id -> invoices.product_id`. Operators with separately authorized DBs may supply a **local** absolute JSON array using `--links-file ABS_LINKS_JSON` alongside repeated `--db ABS_DB` flags, with fields `from_db,from_table,from_column,to_db,to_table,to_column` and 1-based database indices. JSON is bounded to 16 KiB; unknown columns, duplicates, self-links and malformed inputs fail closed.
See `docs/P0_04_CROSS_DB_LINK_EVIDENCE_20261027.md`. Current local scope: 36/36 synthetic Python tests + 9/9 Chromium set_content checks passed; full >=290 suite, file:// and customer/Windows release unverified.

## P0-05 measured SQLite storage and two-observation changes

The multi-DB workspace now includes optional `sqlite_dbstat` **allocated btree page bytes** per named table (including its index btrees), capped to 64MiB SQLite main DB size and 0.75s scan budget. These are not exact disk usage or row bytes; virtual table storage can be incomplete, and WAL-backed pages are distinct from the main database file size. Missing dbstat shows **unavailable**, never a guessed value. CPU/RAM remain unavailable.

For two *synthetic or separately authorized* SQLite DBs, first create a baseline via `python -m dbvora.workspace_html --db ABS_A --db ABS_B --out ABS_EXISTING_DIR --save-observation`. Later pass the returned local `dbvora-observation-*.json` in `--baseline-file ABS_JSON` with the same DB paths; the offline HTML displays **Δ** main-file bytes and table btree allocation. This is a difference between two measurement times, not a forecast or scheduled monitoring. JSON is metadata-only (table names may be sensitive), max 512KiB, uniquely created with no overwrite. Full source/path, rows, passwords and file contents are not exported. Evidence: `docs/P0_05_STORAGE_EVIDENCE_20261027.md`. Targeted synthetic Linux **50/50 PASS**, Chromium `set_content` interaction PASS, but complete **>=304** gate and actual Windows/browser file navigation remain NOT_RUN.

## P0-06 complete synthetic multi-DB MVP smoke

From the full private checkout: `python -m scripts.mvp_offline_gate`. It generates two **temporary synthetic** SQLite files, runs 13 product-module checks (FK, explicitly unverified cross-DB link, independent HTML SHA/no row leak, manual baseline + actual size delta, dbstat provenance and no-overwrite), emits JSON and deletes the entire test fixture. Expected code 0 on `PASS_SYNTHETIC_P0_ONLY`; this is **not** a production or Windows archive pass.

Eight new `tests.test_mvp_offline_gate` checks have been added; targeted reconstructed P0 subset **58/58 PASS** on Linux Python3.13.5. Full private checkout Python >=**312** plus Node, real CLI, actual file:// and Windows native gates remain **NOT RUN**, due environment/source limits. More: [P0-06 evidence](docs/P0_06_MVP_INTEGRATED_GATE_20261027.md).

## P0-07 input security (2026-10-27)
User-supplied observation and cross-database metadata JSON files are read with a bounded, checked file descriptor. Duplicate JSON properties and non-finite numeric constants are invalid. Synthetic demo rejects observation-save mode rather than silently accepting an ignored argument. Targeted P0 Linux Python3.13.5 **70/70 PASS**; full checkout >=**324** and Windows safety **NOT RUN**. See `docs/P0_07_METADATA_INPUT_SECURITY_20261027.md`.
