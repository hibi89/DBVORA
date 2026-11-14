> **2026-11-14 KST 실행자 변경 고지:** 사용자 최신 지시에 따라 아래 48개 원자 ID/수용 조건은 보존하되 실행은 **Codex GPT-6 Luna Max의 GitHub-only**로 위임. 최신 실행 정본: [P100_CODEX_LUNA_MAX_GITHUB_ONLY_20261114.md](P100_CODEX_LUNA_MAX_GITHUB_ONLY_20261114.md). 과거 Instant 실행 설명 및 SHA는 이력으로만 남기며, 현재 기능/CI/공식점수를 의미하지 않는다. High 최종검수/OWNER_GATE/RELEASE HOLD 그대로.

# DBVORA 최종설계 100% — GPT-6 Instant 실행·High 최종검수 마스터 플랜

> 기준 2026-11-14 KST / hibi89/DBVORA / feature/p0-db-map / 기능 기준 SHA 8bb07273f3829248bae8516ac467bfbf7eb4f751
> 사용자 확정: 백엔드·프론트엔드 최종설계 100%를 목표로 Instant가 개발하고 High가 완료 뒤 독립 검수. 크몽 상품 등록은 다른 담당자(Codex). DATA2WEB CodeQL 경고는 이번 작업 범위에서 제외.

## 1. 변경할 수 없는 정본과 현재 점수
- 최종설계 기준은 REQUIREMENTS.md의 7개 최상위 요구·완료 판정·금지사항, AGENTS.md의 OWNER-FINAL-BLUEPRINT-100 정책, 소유자의 최신 확정 지시. P100_REQUIREMENTS_TRACE의 R01~R07는 상세 분해와 과거 증거를 위한 추적표이며 요구 축소의 근거가 아님.
- 과거 제안 배점 R01 20 + R02 15 + R03 25 + R04 10 + R05 10 + R06 5 + R07 15 = 100은 사용자 미승인. 공식 최종완성률은 UNASSESSED이며, 과거 내부 기술범위 95%는 비공식 이력. 작업 수·테스트 합격 건수로 공식 퍼센트 계산 금지.
- 이 계획의 총 원자 작업은 48개(공통 3, 구조 7, 지표 6, 보관복구 10, 압축성능 3, 보안 5, 확장 3, Windows 6, 검수 5). 이 숫자는 공식 분모가 아닌 개발·감사 작업 단위이다.
- 상태 유지: DBVORA [작업중], RELEASE HOLD, 크몽 등록 실제 0, Vercel/Production 해당 없음. 원본 DB·백업·비밀·개인정보를 외부로 전송하거나 덮어쓰기/자동 삭제 금지. 유료/권한/보안 설정/배포/가격/상품 등록은 별도 사용자 승인.

## 2. 두 구현 방법 비교·최적안
| 설계 | 실행 성능/품질 | 현금비용 | 유지보수/위험 | 결론 |
| --- | --- | --- | --- | --- |
| A. 7개 요구 대형 일괄 개발 | 많은 변경이 뒤섞여 테스트 실패 원인 분리 어려움 | 0원 가능 | 중복작업·실패시 대량 롤백·거짓 완료 위험 | 미선택 |
| B. 소형 작업과 정확 SHA 게이트, 기존 구현·테스트 재사용 | 결함 격리, 원본 보호, 정확 재현 | 무료 합성 GitHub CI 위주 0원 | 매 회차 단일 행 갱신, 문서부담은 제한 | 채택 |

## 3. Instant 원자 작업표 — 한 행은 기능+검증+증거를 요구
| ID | 범위 | 해야 할 일 | 합격 기준/테스트 | 주체 | 초기 상태 |
| --- | --- | --- | --- | --- | --- |
| B00 | 공통 | 요구 정본·변경 이력 고정 | REQUIREMENTS 7개/금지사항/이전 설계 전체 누락·충돌 감사; 공식 승인 가중치 없으면 UNASSESSED | Instant | OPEN |
| B01 | 공통 | 현존 소스-테스트-설계 갭 전수 추적 | 소스·CI·CLI·UI 경로별 각 요구 수용조건과 미검증 매핑, 새 코드를 만들기 전 기존 구현 재사용 | Instant | OPEN |
| B02 | 공통 | 최신 기능 SHA 기준선·원본 보존 검증 | SHA 8bb07273의 기존 Windows/Linux/Chromium 증거 재확인 및 복구 기준선 기록 | Instant | EVIDENCE_RECHECK |
| R01-01 | 구조 | SQLite/PG·다중 SQLite 실제 구현 감사 | 단일·2~8 다중 DB 경계, PG TLS 메타데이터 읽기, DB별 ID·정직한 FK 스코프 확인 | Instant | EVIDENCE_RECHECK |
| R01-02 | 구조 | 여러 DB/서비스를 한눈에 보는 토폴로지 | DB 선택 탭만이 아닌 동일 화면의 전체 DB 노드·요약·클릭 탐색·관계 증거; 실 Chromium 2OS | Instant | OPEN |
| R01-03 | 구조 | PG 읽기 전용 진입 UI/통합 | 실 PG16 localhost TLS verify-full·read-only 및 악성 인증서/권한 실패, 브라우저·로그 DSN 미노출 | Instant | OPEN |
| R01-04 | 구조 | SQLite+PG 혼합 및 승인된 교차 관계 | 여러 서비스/DB의 출처 있는 링크만 보여주고 무증거 FK 추정 금지; 동일 테이블명 충돌 시험 | Instant | OPEN |
| R01-05 | 구조 | 대용량/비정상 카탈로그 한계·오염 테스트 | 1,000테이블·workspace2,000 제한, 악성 식별자·잘못된 관계·XSS/SQL/path 안전실패 | Instant | EVIDENCE_RECHECK |
| R01-06 | 구조 | 화면 클릭·키보드·모바일·오류 복구 | Tab/Enter/aria, 390px/desktop, 실 API/Chromium, 15초 timeout·재시도·하얀 화면 회귀 | Instant | EVIDENCE_RECHECK |
| R01-07 | 구조 | 비동기 DB 전환 경합·출처 혼동 방지 | A DB 조회 늦은 응답이 B DB 인스펙터/측정에 섞이지 않음, 새로고침 및 필터 보존 | Instant | OPEN |
| R02-01 | 지표 | SQLite main/WAL·dbstat 실제 측정 감사 | dbstat 64MiB/0.75초, opt-in, 동일 경로 파일교체 검사, 미지원/측정결과 출처 | Instant | EVIDENCE_RECHECK |
| R02-02 | 지표 | 두 시점 DB별 용량 비교 회귀 | 기존 Chromium26/26 증거 재사용, 변화 없음/동일 시각/DB 전환/연결 실패 무허위 수치 | Instant | EVIDENCE_RECHECK |
| R02-03 | 지표 | 실제 주기별 로컬 관측 이력 원장 | 기본 OFF·사용자 명시 실행, 시각·크기·해시·범위·중복/손상 차단; 3샘플 이상 추세 | Instant | OPEN |
| R02-04 | 지표 | CPU/RAM/디스크 측정 주체 정밀 구분 | DBVORA 프로세스 CPU/RSS와 파일시스템 사용량 분리, DB 서버 메모리 추정 금지·미지원 표시 | Instant | EVIDENCE_RECHECK |
| R02-05 | 지표 | PG 테이블/인덱스 통계 UI 및 한계 | pg_stat_user_tables 추정·heap/index 근거, 권한부족/통계지연/실측불가 UI 테스트 | Instant | OPEN |
| R02-06 | 지표 | 지표 장기 보존·데이터 정합·추세 화면 | 실제 3+ 관측만 차트, 기간·측정 범위·시각 롤백·손상·상한·개인정보 비저장 | Instant | OPEN |
| R03-01 | 보관복구 | SQLite WAL 포함 일관성 스냅샷 | 원본 불변, 승인된 로컬 대상만 새로 생성, WAL 동시 쓰기·복제 오류 실패안전 | Instant | EVIDENCE_RECHECK |
| R03-02 | 보관복구 | ZIP/ZSTD/CAS 모든 형식 독립 복원 | 동일 합성 DB의 SHA256·SQLite integrity 비교, manifest/ZIP 변조·대상 덮어쓰기 거부 | Instant | EVIDENCE_RECHECK |
| R03-03 | 보관복구 | 실제 CAS 증분 중복제거 세대 체인 | 원본/중복/변경 4세대·missing/corrupt parent·청크 실물 검증·이전 세대 독립 복원 | Instant | EVIDENCE_RECHECK |
| R03-04 | 보관복구 | 하루/주 실제 실행 러너 | 합성 임시 DB 대상으로 지정 슬롯 실행·중복 방지·재부팅 재개 검증; OS 자동등록·서비스 기본 OFF | Instant | OPEN |
| R03-05 | 보관복구 | 동일 요청 중복 실행·다중 프로세스 경쟁 | 동시 writer/read/restore, 성공 세대 불변, 요청당 최대 한 번 게시, 실패 명확한 HOLD | Instant | EVIDENCE_RECHECK |
| R03-06 | 보관복구 | ENOSPC/short-write/process kill 중단 복구 | 별도 프로세스 중단 및 재시도·고립 청크 HOLD, 원본/기존 정상 세대 SHA 보존 | Instant | EVIDENCE_RECHECK |
| R03-07 | 보관복구 | 복구 대상 선택·미리보기·실제 별도 복원 UX | 새 출력경로만 사용, 해시·내용 검증, 원본 overwrite 0, 복원 실패 안내와 사용자 선택 | Instant | OPEN |
| R03-08 | 보관복구 | 세대 보존·고립 파일·저장량 예측 | 보존 preview 및 승인 전 read-only 목록; 원본·백업 자동 삭제 0, 손상 보수적 처리 | Instant | OPEN |
| R03-09 | 보관복구 | NTFS/ACL·경로 경쟁·실 디스크 오류 경계 | Windows 합성 오류 검증·create-only·path alias/권한, 실물 내구성은 구분 | Instant | OPEN |
| R03-10 | 보관복구 | 소유자 실제 장치 전원중단/복원 수용 | 위험한 전원차단은 사전 승인·백업/장치 확보 뒤 수행; GitHub CI는 대체 불가 | Owner | OWNER_GATE |
| R04-01 | 압축성능 | ZIP/ZSTD/CAS 동일 원본 반복 벤치 | 동일 데이터·옵션·세대·하드웨어 기록, 해시 일치 및 표본수 포함 | Instant | EVIDENCE_RECHECK |
| R04-02 | 압축성능 | 용량/생성시간/복원시간/CPU/메모리 실측 | 반복·중앙값·편차·측정 불가·캐시 영향을 명시, 손실 없는 동일 조건 시험 | Instant | OPEN |
| R04-03 | 압축성능 | 성능 우월/70% 절감 등 허위 주장 차단 | PG/Supabase 직접 비교 미검증이면 비교불가, CI 샘플 수치를 고객 성능으로 홍보 금지 | Instant | OPEN |
| R05-01 | 보안 | localhost·Origin·Host·CSP·HTTP 메서드 위협 | 외부 origin·DNS rebinding·무단 경로/쿼리 차단, write method 405, 데이터 행 노출0 | Instant | EVIDENCE_RECHECK |
| R05-02 | 보안 | symlink/hardlink/동일 size·mtime 교체 TOCTOU | dev/inode/ctime identity와 원본·출력 safe path, ZIP 복원 경로 exclusive 테스트 | Instant | EVIDENCE_RECHECK |
| R05-03 | 보안 | PG DSN/비밀·로그/CI 아티팩트 누출 검수 | 실제 권한 실패·TLS 실패·상세 오류 path-free, 토큰/고객원본/비밀번호 원격 전송0 | Instant | OPEN |
| R05-04 | 보안 | LICENSE/NOTICE/SBOM·재배포 가능성 검토 | 제3자 의존성별 근거/불확실 항목 BLOCK, 법률/상용 승인 대리 금지 | Instant | OPEN |
| R05-05 | 보안 | ZIP manifest/해시/서명 신뢰경계 검증 | ZIP·SHA 둘 다 공격자 변조 가능 범위 정직 표시, 합성 변조·인증 없는 서명 주장 금지 | Instant | OPEN |
| R06-01 | 확장 | 다른 AX 소비용 버전형 read-only 메타데이터 계약 | 버전/스키마/근거/오류 명시, 고객 row·토큰 없음, 호환 불가 버전 거부 | Instant | OPEN |
| R06-02 | 확장 | 독립 CLI/UI + mock HAE/LA 통합 시험 | AX가 설치되지 않아도 완전 독립 동작, 모의 소비자가 스키마 검증·오류 격리 | Instant | OPEN |
| R06-03 | 확장 | 실제 HAE/LA/SOVIA 연동 필수범위 확인 | 초기 판매 오케스트레이션은 기존 정본상 비필수. 필수 확대는 사용자 명시 승인 후 별도 E2E | Owner | OWNER_SCOPE_GATE |
| R07-01 | Windows | 최신 기능 SHA 패키지/preview/빌드 증거 일치 | 무료 unsigned source ZIP/EXE SHA, 새 기능 포함 여부, 빌드+실행 구분 | Instant | OPEN |
| R07-02 | Windows | Windows 설치·실행·종료·재시작·제거 UX | 새 폴더만/기존 데이터 안전, 포트충돌·Python/브라우저 문제·기본 OFF 통제 | Instant | OPEN |
| R07-03 | Windows | 한국어 오류·승인·복구 UI/CLI 마감 | 위험 작업 미리보기·기본 거부, 잘린 화면/검색/선택·복원 오류 실브라우저 | Instant | OPEN |
| R07-04 | Windows | 사용자 Windows10/11 최신 SHA 실물 QA | 한 번에 합성 설치/실행/테이블/복원/제거, 개인정보 없는 증거; 최신 SHA와 과거 QA 구분 | Owner | OWNER_GATE |
| R07-05 | Windows | 재배포권·지원/환불·서명·구매자 수용 승인 | 소유자 확정 전 RELEASE HOLD, 유료/도메인/상품 등록 금지; 등록은 후속 Codex | Owner | OWNER_GATE |
| R07-06 | Windows | 실제 허가된 장기 고객환경 평가 | 동의한 데이터는 로컬에만 두고 익명화 결과로 수용; 실제 접근권/전원/복원 증거 | Owner | OWNER_GATE |
| G90-01 | 검수 | R01-R07 모든 수용조건 SHA 증거 일치 | 요구 ID→코드→실 실행/환경→미검증 추적표; 미승인 가중치 공식 점수화 금지 | Instant | OPEN |
| G90-02 | 검수 | 최신 SHA Win/Linux/Chromium/PG/압축 통합 게이트 | 실제 기능 기능SHA에서 0FAIL, OS별 PASS/SKIP 및 독립 복원 기록 | Instant | OPEN |
| G90-03 | 검수 | SAST·위협/라이선스 및 회귀 결함 정리 | 오류·비용·보안·권리·원본 보존 차단 상태 정직하게 표시 | Instant | OPEN |
| G90-04 | 검수 | High 독립 전수 감사/수정 반환 | Instant 최종 SHA 고정; 7요구 UI·backend·보안·복원·권리 대조 후 PASS/PARTIAL/FAIL | High | HIGH_GATE |
| G90-05 | 검수 | 소유자 수용/승인 공식 100점 판정 | 승인된 전체 요구 가중치 합100·필수 사용자/실기기/권리 증거 충족 시에만 공식 100 | Owner | OWNER_GATE |

## 4. Instant 실행 순서
1. 첫 ㄱ/ㄱㄱ: HANDOFF→STATUS→AGENTS→REQUIREMENTS→이 파일→실제 GitHub 최신 HEAD/코드를 읽고 B00/B01/B02에서 요구·소스·테스트 간 불일치 매핑. 단순 계획만 보고하지 말고 다음 미완료 R01-02 실제 구현에 착수.
2. R01-02(한 화면 다중 DB/서비스 노드) → R01-03(PG UI/진입) → R01-07(경합) → R02-03(장기 로컬 관측) → R03-04(기본 OFF 실제 예약러너) → R03-07(복원 UX)를 우선 개발. 나머지는 선행 조건/위험 순서대로 시행. 외부 사용자 게이트는 마지막에 모으고 독립 작업을 계속한다.
3. 매 작업: 시작 HEAD·읽기/쓰기 경계·안전/비용/재실행 경로 확인 → A/B안 비교 → 최소 수정 → 합성 테스트+필요한 실 Chromium/PG/압축 독립 복원 → 원본불변 확인 → 기존 브랜치에 비강제 커밋 → GitHub Actions 정확 SHA 결과 확인 → STATUS/HANDOFF/중앙 원장 동기화.
4. 기존 PASS 기능은 무의미하게 다시 만들지 않는다. EVIDENCE_RECHECK는 이미 검증된 요구 범위와 실제 미완 gap를 먼저 확인하고, 범위 충족이면 정확한 SHA·명령·PASS/FAIL/SKIP를 기록한다. 기구현 테스트만 반복했다고 새 완성률을 올리지 않는다.
5. 진전 없는 실패: 원인 분석 후 실제 개선 방법으로 최대 한 번 재시도, 두 번 실패하면 STOP/PIVOT. 비용/원본 변경/외부 전송/권한·보안 정책 변경/출시 등 승인 사항은 사용자에게 일괄 요청한다.
6. 각 ㄱ 회차 종료: 이번 작업 ID, 실제 수정 파일과 기능 SHA, 테스트 실행 SHA/URL, PASS/FAIL/SKIP, 완료 조건·미검증, 공식 UNASSESSED(미승인일 때), 역사95 별도, 다음 작업을 한 번에 보고. STATUS.md/HANDOFF.md 10항과 중앙 kmong-productization 동기화. 중앙 반영 실패 시 KMONG_HUB_SYNC_PENDING.

## 5. 최종 합격은 3단계
- Instant: 각 개발 작업의 수용 조건을 정확한 GitHub SHA의 실제 테스트로 확인, G90-01..03 추적표·통합회귀·보안/권리 문제 정리. 이 단계는 개발 기술 증거이지 전체 사용자 공식 100점 보증이 아님.
- High: 동일한 최종 기능 SHA를 독립 재조회한 뒤 R01~R07 전체 설계·백엔드/프론트엔드·안전 복원·성능/소버린·화면/UX·라이선스/릴리스 근거를 재검수. 구현자의 PASS 요약만 복사하지 않는다. High는 스스로 자동 예약 실행되지 않으며 사용자가 최종검수를 요청해야 한다.
- 소유자: 실제 Windows10/11 설치·사용 수용, 승인된 100점 세부 가중치, 고객/물리 정전/법무/사용권/판매 승인 같은 대체 불가 게이트. 미이행 조건은 PASS 또는 공식 100%로 처리하지 않는다. 크몽 실제 등록은 별도 Codex 업무.

## 6. 이번 설계에 사용된 최신 실제 근거
- 실제 기능/테스트 SHA 8bb07273f3829248bae8516ac467bfbf7eb4f751. Windows/Linux 전체 release Actions https://github.com/hibi89/DBVORA/actions/runs/43595216968 는 2/2 SUCCESS, Python723 발견 Ubuntu723PASS/0FAIL/0SKIP, Windows722PASS/0FAIL/1 지정 POSIX 전용 SKIP, 필수12/12×2 PASS.
- 실제 localhost Chromium https://github.com/hibi89/DBVORA/actions/runs/43595217004 는 Win/Linux 각 26/26 PASS, 합성 SQLite 1,000테이블/997FK/24회 refresh·4회 합성 연결 오류; 2~8다중 DB 선택, DB별 현재 세션 2시점 main-file 증감은 구현·합성 확인. 전체 DB 노드를 동시에 보여주는 지도, PG 실 UI 통합, 장기 추세, 실제 OS 스케줄, 사용자 최신 Windows10 통합 수용은 별도 미완.
- 계획서 공개는 소스 개발·테스트 추가·High 최종감사 완료가 아니다. 과거 이력·모든 위험/미확인 상태를 보존한다.

## 7. 원장 갱신 규칙
- Instant는 위 표의 초기 상태를 임의 DONE으로 바꾸지 말고 항목별 PASS_SCOPED / IN_PROGRESS / BLOCKED / OWNER_GATE / HIGH_GATE와 정확 SHA/테스트 링크를 갱신한다. 전체 기능이 검증된 작업에만 PASS_SCOPED를 부여하고, 실제 고객/실기기 수용은 별도 열에 계속 미검증.
- 작업 기록 문서만 커밋한 HEAD와 기능·테스트 SHA는 분리 표시. 'CI Ready'나 생성된 파일 경로만으로 실제 기능 성공을 주장하지 않는다. 시점별 이전 실패기록 보존.
