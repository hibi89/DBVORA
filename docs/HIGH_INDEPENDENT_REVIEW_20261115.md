# DBVORA — GPT-6 High 독립 검수 1차 (2026-11-15 KST)

> **PARTIAL / 공식 최종완성률 UNASSESSED / RELEASE HOLD.** 사용자의 Codex 작업 중단 후 현 브랜치 실측 조회 결과. 본 보고서는 코드 변경 없이 감사 증거를 기록하며, 승인 없는 원본/배포/권한 변경을 수행하지 않는다.

## 기준 SHA 및 직접 확인한 CI

- Repository: `hibi89/DBVORA`; branch: `feature/p0-db-map`; 감사 착수 HEAD: `5e170375321703ad715a6411eedea2480c48f956` (문서 HEAD).
- 최신 기능·테스트 검증 SHA: `49ab1080dc8a7a28f0e1435233f51d1caff0f87a`. 비교 `49ab1080..5e170375`: 뒤이은 **12 커밋은 문서 7개만** 변경. 이전 인계 `be539297..`부터 신규 커밋 총 107개.
- [정확 기능 SHA 전체 release gate](https://github.com/hibi89/DBVORA/actions/runs/43679171661): Ubuntu **798 PASS / 0 FAIL / 0 SKIP**; Windows **797 PASS / 0 FAIL / 1 POSIX 전용 SKIP**. 두 OS 필수 12/12 단계 PASS. GitHub job IDs 132705840086 및 132705840362에서 성공과 테스트 집계를 독립 재조회.
- [Windows unsigned EXE](https://github.com/hibi89/DBVORA/actions/runs/43679171613): 실제 Windows runner 빌드·합성 실행 PASS, EXE SHA256 `da9a111a2e6aadf7329f77b2f5369bf3f2b4ed4d6df752b00f827d12cdf8cdc7`; 고객 준비 false, 미서명.
- [Unsigned ZIP](https://github.com/hibi89/DBVORA/actions/runs/43679171633): 75개 소스 파일, self-check 9/9, ZIP SHA256 `3b9856c8eb89ff169eb83c2f7f05a539bc022a201e84bc8221457bacf25f407e`. [최종설계 증거 게이트](https://github.com/hibi89/DBVORA/actions/runs/43679171766) SUCCESS. 이는 사용자 승인/상업 출시/물리 정전 검증을 대체하지 않는다.
- [실 HTTP+Chromium 2 OS](https://github.com/hibi89/DBVORA/actions/runs/43657990663) SUCCESS, 검증 문서상 37/37 checks/OS. [실 synthetic PG16 TLS + Chromium](https://github.com/hibi89/DBVORA/actions/runs/43657990651) SUCCESS, PG TLS/metadata 5 checks, UI 10 checks. **두 workflow job log를 직접 재조회**. 이후 최신 기능 SHA까지 비교에서 앱 실행 소스 변경이 없고 프로세스 측정/WAL snapshot 회귀 테스트만 추가됨.
- 실제 Chromium 스크린샷을 감사자가 눈으로 별도 판독한 것은 아님. 사용자 Windows 실물·고객 데이터·물리 정전은 미검증. 연결 도구의 code-scanning alerts 조회는 미지원이어서 열린 SAST 경고 수는 미확인.

## 48 작업 현황 (원장 직접 파싱)

- 총 48개 ID 존재; **PASS_SCOPED 33 / OPEN 5 / EVIDENCE_RECHECK 2 / HIGH_GATE 1 / OWNER_GATE 6 / OWNER_SCOPE_GATE 1**.
- OPEN: `B00`, `B01`, `G90-01`, `G90-02`, `G90-03`.
- EVIDENCE_RECHECK: `B02`, `R03-03`; High G90-04는 본 감사로 착수했으나 **최종 전수 승인 아님**.
- OWNER_GATE: `R03-10`, `R05-04`, `R07-04`, `R07-05`, `R07-06`, `G90-05`. OWNER_SCOPE_GATE `R06-03`.
- **33/48=68.75%는 ID 개수 기준일 뿐 공식 완성률 점수가 아님.** 이전 비공식 기술 95%와 비교 불가.

## H01~H12 개별 판정 (검증 범위 제한)

| 항목 | 감사 판정 | 근거/제한 |
| --- | --- | --- |
| H01 설계 전수 | PARTIAL | REQUIREMENTS R01~R07과 48 ID 존재, G90-01 최종 추적표 미완 |
| H02 DB 지도 | PASS_SCOPED | api.py, web/app.js, 양 OS HTTP/Chromium·PG 실 synthetic TLS 근거 |
| H03 측정·추세 | PASS_SCOPED | process CPU/RSS와 host volume 출처 구분, 실제 DB 서버 CPU unavailable |
| H04 무손실 | PASS_SCOPED | WAL 동시 writer snapshot 회귀·ZIP/ZSTD/CAS SHA 및 integrity 검증; 물리정전 제외 |
| H05 예약·복원 | PARTIAL | synthetic 일/주 CLI·중복/오류 주입 PASS; R03-03 부모 체인·실 OS 스케줄러 미완 |
| H06 효율 | PASS_SCOPED | 동일 합성 입력 2세대 3회 반복, 실고객/PG/Supabase 경쟁 입증 아님 |
| H07 보안 | PARTIAL | loopback/Host/Origin/CSP/GET-only/PG verify-full 직접 확인; G90-03·실 열린 경고 미확인 |
| H08 AX 계약 | PASS_SCOPED | versioned read-only metadata/mock 소비자 테스트, 실제 HAE/LA 별도 |
| H09 UX | PARTIAL | 390px/키보드/오류복구 Chromium 로그, 시각검수 일부 미실시 |
| H10 Windows 패키징 | PARTIAL | GitHub Windows unsigned EXE/ZIP 합성 PASS, 사용자 Windows 실물 미검증 |
| H11 법무·출시 | OWNER_GATE | root LICENSE/NOTICE 부재, 재배포권/지원/환불/서명 미승인 |
| H12 수치·인계 | PARTIAL | 기능/문서 SHA 및 상태 집계 확인, 공식 가중치·허브 동기화 미확인 |

## 발견사항 및 수정 우선순위

1. **R03-03 부모 세대 연결 갭 (P1 / RECHECK)**: `dbvora/archive/compressed_cas.py`의 manifest는 `contract,codec,chunk_bytes,snapshot_sha256,snapshot_size_bytes,chunks`의 독립 스냅샷 계약이다. `incremental_cas.py`도 독립 manifest다. `tests/test_cas_generation_lifecycle.py`는 4개 세대 재생·독립 복원과 손상 신규 chunk 시 이전 세대 생존을 **실제로 테스트**하지만, parent manifest hash/reference 검증은 구현 계약에 없다. 48개 요구의 '부모 누락/손상 체인'은 **별도 충족 근거 부족**. 대안 A: 독립 복원을 최종 요구로 인정해 요구 수정(사용자 명시 승인 필요); 대안 B 권고: v1/v2 호환을 보존한 versioned parent-link 계약/파손 부모 거부/4세대 회귀 추가 후 정확 SHA 검수. 기존 정상 데이터/manifest 파괴 금지.
2. **R03-04 예약 운영 경계 (P1 / PARTIAL)**: `daily_synthetic.py`는 `synthetic_only`·plaintext ack 강제, `scheduler_installed:false`, `ready_for_customer_data:false` 보고. 명시 호출 가능한 합성 슬롯 러너는 인정, 구매자 OS 자동 일정 서비스·장기 백업을 완료로 부를 수 없음. Owner consent 후 실제 설치/시작/중복/중단 복구 설계 필요.
3. **R05-04 라이선스·공개 상태 (P1 / OWNER_GATE)**: 원격 metadata 조회상 repo `Public`. Git tree에서 root LICENSE/NOTICE 없음. `docs/COMMERCIAL_LICENSE_AUDIT_20261114.md`도 종속성 전이 권리·서명·판매 조건 미확정. 일반 '비공개 정본' 지침과 실제 public 상태가 다름. 무단 visibility/권한 변경 금지. 공개라는 사실만으로 유출이라고 단정하지 않음.
4. **G90-01~03·H09 (P1 / OPEN)**: 전체 48 ID의 정확 기능SHA→run SHA→실행환경→잔여 제한 추적표, freeze-SHA 통합 증명, 종속성/보안 경고·시각 UI 감사 미완. 사용자 실기기/상업·정전 수용 불가 영역은 OWNER_GATE로 남긴다.
5. **P2 문서 동기화**: 마스터 48작업표에서 R03-01/02는 PASS_SCOPED이나 Codex 실행 초깃값 표에는 RECHECK가 남아 있다. 선두 문서에 최신 판정 표시를 보강하되 과거 흔적 보존. `HANDOFF.md`/ `STATUS.md`/ 중앙 원장에 본 감사 결과 반영 필요.

## 후속 Codex 반송 최소 조건

- `R03-03`: 기존 raw CAS v1/compressed CAS v2 파일을 유지하고, 원본 보존한 backward-compatible 세대 링크 또는 사용자 범위 승인. 변경 소스와 4세대 parent missing/corrupt, 재생, 동시 read/write, 이전 세대 독립 복원 테스트. 정확 SHA GitHub Ubuntu/Windows 전체 gate + 브라우저/PG 회귀.
- `G90-01/02/03`: 단일 freeze SHA의 정확한 증거 매핑·실행 실패/skip·권리 및 종속성 판정. 과거 FAIL/CANCELED는 PASS로 계산하지 않는다.
- OWNER 전용: 실제 Windows10/11, 물리 전원중단, 최종 사용권/재배포/지원, 공식 100점 가중 승인. **원본 및 정상 백업 보존**, 출시 보류.
