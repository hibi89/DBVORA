# DBVORA

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
- 아직 구현되지 않음: CLI·고객용 검증된 전원중단 복구·증분/예약 보관, Windows 설치기. 브라우저 실제 렌더링, 고객 DB 미검증. 합성 ZIP 결과를 상용 압축률로 해석 금지.
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

본 저장소는 Private. 라이선스·상표 사용권은 미확정이며 외부 공개/배포/실고객 연결은 별도 승인 사항이다.

### Local developer source preview (v0.2.0, unsigned)
From private source root, build a non-overwriting ZIP containing only DBVORA code and offline launcher templates:
```bash
python -m scripts.build_portable --output /absolute/existing/output
python -m scripts.build_portable --verify /absolute/existing/output/dbvora-dev-preview-0.2.0.zip
```
The ZIP is a source bundle, not a Windows installer or bundled Python. The extracted `README_PORTABLE.txt` documents prerequisite Python3.11 and optional UI dependency installation. The SHA-256 manifest is unsigned and does **not** authenticate origin. Only synthetic/approved test DBs until native Windows/NTFS validations pass. Browser Chromium-only DOM probe (not HTTP E2E): `python -m scripts.browser_visual_probe --chromium /usr/bin/chromium` with optional Playwright installed.
