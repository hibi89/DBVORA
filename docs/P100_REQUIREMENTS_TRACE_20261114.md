## 2026-11-14 exact-SHA 보강 검증 및 최신 미완료 추적
- 기능 소스 `9d24a58a045fd89a11d46c685ee59adec3ed63e8`, [전체 양OS #43549905413](https://github.com/hibi89/DBVORA/actions/runs/43549905413): Python651 발견, Linux651PASS/Win650PASS+1플랫폼SKIP/0FAIL, 필수12/12×2 OS. [실 PG #43545900975](https://github.com/hibi89/DBVORA/actions/runs/43545900975) PostgreSQL16 localhost verify-full TLS·읽기전용 계정·실카탈로그·HTML 5/5. 이 2건은 고객/사업자 PG QA와 구분.
- R01(20점 제안): 실제 PG read-only TLS + Chromium localhost Windows/Linux synthetic 클릭 8×2 PASS. 실제 Win10/고객 스키마와 통합 서비스 관계는 사용자/사업자 수용 전 **PENDING**.
- R02(15점 제안): SQLite 파일/dbstat·2시점 변경 및 PostgreSQL pg_stat_user_tables 추정/heap/index 실측을 명확히 구분, CPU/RAM 미지원 수치는 표시하지 않음. 장기 리소스 관찰·실사용 환경 **PENDING**.
- R03(25점 제안): 기존 ZIP/ZSTD 원본 무손실 독립 복원과 raw CAS v1, 별도 compressed zlib CAS v2 **실제 임시 디스크 두 세대+독립 복원/오류 거부 12체크**, 일자별 원장 예약(실 OS 스케줄러 미설치); 물리 정전·디스크 고장·보존정책/자동 삭제/고객 복구 **PENDING**.
- R04(10점 제안): 동일 *합성* SQLite 2세대 ZIP2 총31,216B Linux(Windows31,550B), raw CAS1,177,960B, zlib CAS v2 24,637B Linux(Windows25,046B) 실측; zlib 절감 Linux6579B·Windows6504B, 데이터·압축률의 일반화 금지. 실제 고객 데이터 동의 없는 벤치·비교와 운영비 대조 **PENDING**.
- R05(10점 제안): TLS verify-full 실제 CA 거부, PG role no write, no customer row extraction, localhost guard·new-only/한정 복원 PASS. 공개소스 사용권/NOTICE·서명/물리 보안·장기 배포 권한 **PENDING**.
- R06(5점 제안): DBVORA standalone offline HTML/CLI 동작, 실제 HAE/LA/SOVIA 연계 종단검증은 원요구상 초기 판매 비필수 가능하나 전체 최종설계 수용에는 **PENDING**으로 보존.
- R07(15점 제안): Windows2025 unsigned synthetic EXE 실제 실행 [#43546585469](https://github.com/hibi89/DBVORA/actions/runs/43546585469), 61소스 파일/해시 검증 [latest preview](https://github.com/hibi89/DBVORA/actions/runs/43549905406), **Win10 실제 QA·타사 권리/지원/환불·서명 여부·가격/크몽 게시0** PENDING.
- **제안 가중치 합100은 사용자 승인 전임**; 검증 항목만을 임의 분수/성공률로 바꿔 공식 점수 산정하지 않음. 공통 정본에 따라 **UNASSESSED**, 이전 내부95 이력·[작업중]·RELEASE HOLD 유지.

# DBVORA 사용자 최종설계 요구 전체 추적 및 P100 승인 전 제안 — 2026-11-14

**공식 점수: UNASSESSED.** 아래 100점 배분은 사용자가 새로 승인한 최종 가중치가 아닌 **기술 책임자 제안**이다. 전체 요구는 `REQUIREMENTS.md`(2026-10-26 원본, 7개 상위 요구) 및 `AGENTS.md`의 2026-11-13 OWNER-FINAL-BLUEPRINT-100 기준 그대로다. 100점 점수는 확정·검증된 수용조건으로만 합산 가능; 소규모 단위/합성 CI/과거 내부95를 공식 점수로 오인하지 않는다.

| 요구 | 확정 최종 기능 / 제안 가중치 | 실제 구현·최신 검증 범위 | 공식 남은 미수용·차단 |
| --- | --- | --- | --- |
| R01 Visibility / 제안20 | 승인된 SQLite/PG 엔진·서비스 구성도, DB→테이블→컬럼/PK/FK/인덱스 클릭형 탐색 | SQLite localhost+실 Chromium Windows/Linux 8/8 ×2 [run43544065399](https://github.com/hibi89/DBVORA/actions/runs/43544065399); PG16 실제 TLS/FK 5/5 [run43545900975](https://github.com/hibi89/DBVORA/actions/runs/43545900975); 2–8개 SQLite 구조맵/수동 cross-DB 링크 | 사용자 Windows10 실제 뷰/고객 DB 형식 다양성, PG 인증 환경, 멀티서비스 실제 구조 관계 수용 |
| R02 Metrics / 제안15 | 파일·테이블 용량/증감·실측 가능 CPU/RAM/디스크·리소스 근거·추세 | SQLite main-file + `dbstat` 예산 제한, 2 시점 관측, PG pg_stat stats/heap/index; 미지원 CPU/RAM `unavailable` | 주기적 안전 관측·Windows 실제 측정/권한·측정 범위/장기 추세 검증 |
| R03 Recovery/Archiving / 제안25 | 주기적·증분 보관, ZIP/ZSTD 압축·무손실 복원, 원본 불변·중복실행/전원중단 대응 | `safe_zip`, `zstd_archive`, `request_service`, `receipts`, `recovery_catalog`; Windows NTFS 창 생성만 + 정확 SHA; 새로운 `archive.daily_synthetic` 일자별 예약·중단 HOLD, [P3 사용법](P3_DAILY_SYNTHETIC_SLOT_20261114.md); Linux/Windows full release [run43546332776](https://github.com/hibi89/DBVORA/actions/runs/43546332776) | **진짜 증분 복원 체인/실행 스케줄러·보존 세대 관리/정전·디스크 가득참/고객 환경 QA 미완**. 중복 계획은 아직 실제 dedup 저장소 아님 |
| R04 Compression efficiency / 제안10 | 실제 측정 기반 ZIP 대 ZSTD·Supabase/PG 저장비용 효율 향상 목표 | 합성 압축 비교·반복 실행 기능 및 데이터 출처 표시; 벤치마크 무조건 우월 주장 금지 | 유형별 동일 조건의 장기/실 데이터 권한 확보 실측, 하드웨어·운영비·분포·복원 성능 비교 |
| R05 Sovereign/security / 제안10 | 필수 서버 구독 없이 로컬·승인 네트워크만, 무단 쓰기/삭제/키 노출 방지 | localhost API host/origin/POST 차단, PG opt-in verify-full read-only, 고객 데이터/비밀 CI 0, ZIP 신뢰경로·비밀번호 미출력 | 사용권/패키지 해시/공개 repo 검토, Windows end-user 정책, 타사 라이선스/NOTICE 감사 |
| R06 Independent AX extension / 제안5 | 독립 기능 및 향후 HAE/LA/SOVIA 연결 가능 | 독립 CLI·HTML·PG metadata 계약, DB 수정/자동 에이전트 결합 금지 | 실제 HAE/LA/SOVIA 이종 제품 E2E 미검증. 원설계에 따르면 초기 출시에서 통합 오케스트레이터는 **비필수** |
| R07 Windows delivery/commercial acceptance / 제안15 | 실제 Windows 고객 사용, 설치/운영 UX, 라이선스/권리·지원·가격·크몽 등록 | GitHub Windows2025 full 617/628 범위 검증, owner source ZIP(56+ files), unsigned Windows synthetic EXE **빌드+실행 PASS** [run43546585469](https://github.com/hibi89/DBVORA/actions/runs/43546585469), 2026-11-14 판매 원고 초안 | 소유자 Windows10/11 실기기, 실 고객/서명·SmartScreen/법적 권리·지원/환불/가격/판매 승인 및 크몽 실제 등록0 |

**가중치 제안 합 100:** 20+15+25+10+10+5+15. **기록만으로 승인 아님.** 원본 요구를 추가/축소/재정의하지 않는다. 사용자 승인 후 상세 세부 항목 100점 수용표, 항목별 정확 기능 SHA/PASS·FAIL·SKIP·미검증에 따라 실제 공식률 산정. 과거 내부 기술범위 `95/100`은 별도 이력으로 유지.

## 검증/보류 분리
- 자동 합성-only full 릴리스: Ubuntu24.04 Python3.11 628 PASS, Windows2025 627 PASS/1 POSIX-only SKIP (2026-11-14 신규 P3, [Actions](https://github.com/hibi89/DBVORA/actions/runs/43546332776)), 필수 게이트 각각 10/10 PASS.
- 실제 PostgreSQL16 임시 localhost TLS verify-full+read-only 계정 및 실제 카탈로그 연결: 5/5 PASS [run43545900975](https://github.com/hibi89/DBVORA/actions/runs/43545900975).
- 실제 Chromium localhost HTTP 화면 합성 8/8 Windows+Linux [run43544065399](https://github.com/hibi89/DBVORA/actions/runs/43544065399).
- Windows2025 PyInstaller core-only unsigned demo 실제 실행 PASS SHA [run43546585469](https://github.com/hibi89/DBVORA/actions/runs/43546585469). **고객 실행/Windows10/11 직접 GUI/물리 정전/실 PG 사업자 서버/서명·법적 판매권 미검증**.
- 현재 [작업중], RELEASE HOLD, 실 크몽 등록0, Vercel/Production 미적용. 유료 서비스·고객DB·비공개 키 전송 금지. 사용자 최소 PC/폰 행동은 오후 1시에 통합 전달.
