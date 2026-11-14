# DBVORA 100% 최종 High 독립 검수 기준

> 2026-11-14 KST / 검수자: GPT-6 High 역할 / 구현 주체: GPT-6 Instant / 기준 실행 플랜: P100_INSTANT_EXECUTION_PLAN_20261114.md

## 0. 검수 요청 조건
- Instant가 마스터 플랜 48개 작업의 구현 가능한 항목과 종단 테스트 증거를 원장에 기록한 후 사용자가 High 검수를 요청한다. High는 이 대화 밖에서 자동으로 실행되지 않는다.
- 검수 전 기능 SHA를 고정하고 HANDOFF→STATUS→AGENTS→REQUIREMENTS→P100 실행 플랜→실제 소스→CI·브라우저·PG·복원 로그 순서로 직접 대조한다. 이전 소스 PASS를 신기능 PASS로 가져오지 않는다.
- 공식 전체 요구 수용에 포함되는 owner-only 검수는 Instant/High가 대리 서명하지 않는다. 증거 불충분·배점 미승인 경우 최종완성률 UNASSESSED.

## 1. 필수 독립검수 12개
| 번호 | 검증 대항목 | High의 최소 실제 확인 기준 | 합격 제한 |
| --- | --- | --- | --- |
| H01 | 사용자 최종설계 전수 매핑 | 원래 REQUIREMENTS 7개/금지사항·사용자 최신 승인, 각 요구 ID와 기능/소스/검증/차단이 1:1 대응 | 누락·범위축소 금지 |
| H02 | R01 구조/서비스 지도 | SQLite 2~8·PG TLS 읽기 전용, 여러 DB 동시 노드·클릭형 테이블/PK/FK/인덱스·관계 출처 | 탭 전환만으로 전체 지도 PASS 불가 |
| H03 | R02 측정·추세 진실성 | main/WAL/SHM·dbstat·PG 통계·프로세스 CPU/RAM·FS disk, 2/3시점·stale/unavailable | DB별 CPU·추세 허위 가정 금지 |
| H04 | R03 원본 무손실 | 원본 SHA/mtime, SQLite WAL 일관 스냅샷, ZIP/ZSTD/CAS 독립 복원 SHA+SQLite integrity | 원본 덮어쓰기 발견 즉시 FAIL |
| H05 | R03 예약/증분·충돌 복구 | 실제 일/주 호출 경로와 기본OFF, 중복실행·멀티프로세스·ENOSPC·짧은 쓰기·강제종료·이전 세대 생존 | 계획·mock만으로 동작 PASS 금지 |
| H06 | R04 효율 증거 | 동일 원본·옵션·동일 hardware·반복 벤치, 저장 바이트/복원시간/생성시간/불확실성 | PG/Supabase 대비 과장 문구 금지 |
| H07 | R05 공격표면 | localhost Host/Origin/CSP, XSS·SQL·path alias/symlink·TOCTOU·PG verify-full·ZIP 변조 | 고객 비밀/DSN 노출 즉시 FAIL |
| H08 | R06 독립 확장 | typed/versioned metadata contract, AX 없이 완전 사용 가능, mock 소비자 호환 | 실제 HAE/LA/SOVIA 오케스트레이션은 사용자 승인 범위만 |
| H09 | 사용자 UI/오류 | Windows/Linux 실제 Chromium 390px/desktop, 키보드/aria·필터·다중DB 전환·복원 오류/재시도 | 반응 없는 Refresh·React/JS 흰 화면 금지 |
| H10 | R07 패키지·실물 운영 | source SHA와 산출물 매니페스트/해시 동일, Windows 실제 실행·종료·재시작·제거·원본 보존 | 미서명 Preview/CI는 구매자 검수 대체 불가 |
| H11 | 법무·정식 출시 경계 | LICENSE/NOTICE/SBOM·상업 권리/서명·지원/환불·구매자 승인 증거 | OWNER_GATE 미이행은 RELEASE HOLD |
| H12 | 숫자/인수인계 무결성 | GitHub HEAD/CI run head SHA, 원장/STATUS/HANDOFF/중앙 SHA, PASS/FAIL/SKIP/미검증 비교 | 승인 가중치 미확정이면 UNASSESSED |

## 2. 보고서 합격 원칙
1. 요구별 PASS_VERIFIED/PARTIAL/FAIL/OWNER_GATE를 별도 표로 작성하고 재현 명령, 실제 GitHub Actions URL, 정확 source SHA, 브라우저/PG/복원/Windows 현장 범위를 연결한다.
2. 오류 발생 시 원인 계층(API, DB, 파일 시스템, 브라우저, Git/CI, 배포), 실제 실패 로그, 개선 가능한 2개 설계안·비용·유지보수·중단 조건을 기록한다.
3. 기존 전체 소스/원본·고객 데이터·라이선스·비밀·등록 이력/RELEASE HOLD의 보존 여부를 검증한다. 사용자의 최종 라이선스/실물 QA/물리 정전/가중 승인 없이는 High가 공식100을 대신 선언하지 않는다.
4. 차이가 발견되면 작업ID로 Instant에게 반송하며, 단일 기능 SHA에서 다시 회귀한 다음 High가 독립 재검수한다.
5. 최종 보고에는 저장소/브랜치/기능 SHA·문서 SHA, CI Ubuntu/Windows PASS/FAIL/SKIP, 브라우저, 사용자 PC, 라이선스/보안, 남은 이슈, Vercel/Production N/A를 포함한다.

## 3. 산출물 확인 단계
- Instant 제출: 최신 원자 작업표 48개 상태/수용 증거·코드/테스트 링크·핵심 미검증·원본 불변성·사용자 전용 게이트 목록.
- High 제출: 전체 설계 요구 충족/미충족과 위험·권리·QA 재검수, 검증된 범위 한정 최종 판정.
- 사용자 제출: 정식 100점 가중치/실기기·법적 승인 여부. 미승인이라면 공식 UNASSESSED와 [작업중]/RELEASE HOLD 유지.

최종 High 감사 현재 상태: NOT_STARTED (본 문서는 계획/검수 프로토콜만 작성).
