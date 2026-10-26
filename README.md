# DBVORA

**Database Visibility · Optimization · Recovery · Archiving**

로컬 우선, 사용자 소유 데이터 기반의 **통합 DB 관제·무손실 아카이빙·저장 최적화** 제품 (P0-01 읽기 전용 인벤토리 구현, UI MVP 미완료).

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
- feature/p0-db-map: P0-01 합성 SQLite 읽기 전용 스키마 인벤토리 코드 및 unittest 16/16 로컬 통과. 실제 원격 HEAD는 GitHub에서 재조회.
- 아직 구현되지 않음: 클릭형 UI, localhost API, 압축·무손실 복원, 예약 작업, Windows 설치기. 브라우저·Windows·고객 DB 미검증.
- P0-01 사용/제약은 [docs/P0_01_USAGE.md](docs/P0_01_USAGE.md), 다음 작업은 [docs/NEXT_TASK.md](docs/NEXT_TASK.md).
- 외부 유료 API·서버·데이터 전송·Vercel 배포 없음.

## 문서 및 작업 구조

- [CHAT_BOOTSTRAP.md](CHAT_BOOTSTRAP.md) — 단문 재개 절차
- [HANDOFF.md](HANDOFF.md) — 필수 10개 항목 인수인계
- [STATUS.md](STATUS.md) — 진행·차단·검증 현황
- [AGENTS.md](AGENTS.md) — 개발·보안·Git 운영 원칙
- [REQUIREMENTS.md](REQUIREMENTS.md) — 사용자 요구와 범위
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) — 설계 대안·선정안·데이터 흐름
- [docs/COMPRESSION_PLAN.md](docs/COMPRESSION_PLAN.md) — 압축·복원·벤치마크 계약
- [docs/ROADMAP.md](docs/ROADMAP.md) — MVP 이후 단계
- [docs/NEXT_TASK.md](docs/NEXT_TASK.md) — 다음 실제 구현 작업
- [docs/INTEGRATION_BOUNDARIES.md](docs/INTEGRATION_BOUNDARIES.md) — 다른 AX 제품과 경계

본 저장소는 Private. 라이선스·상표 사용권은 미확정이며 외부 공개/배포/실고객 연결은 별도 승인 사항이다.
