# DBVORA STATUS — 초기 설정

- 기록 시점: 2026-10-26 KST. 현재 GitHub HEAD는 새 채팅 시작 시 반드시 재조회. 이 문서 작성 시 코드 개발 착수 없음.
- 저장소: hibi89/DBVORA, Private. 기본 main, 개발용 develop, 초기 코드 feature/p0-db-map을 목표로 신규 생성하며 실존 여부는 종료 검증 보고를 따른다.
- 진도 표현: **기획·개발환경 구성 진행 / 제품 기능 구현 0% / 상용제품 미완료**. 일정은 3일 MVP, 이후 10~14일 후보 *목표*, 보장 아님.

| 항목 | 상태 | 검증 |
| --- | --- | --- |
| 저장소 생성 및 읽기/쓰기 접근 | VERIFIED | GitHub repo metadata 및 첫 README commit |
| 채팅 재개·설계·요구사항 문서 | SETUP_IN_PROGRESS | 최종 파일 재조회 필요 |
| 코드 브랜치 | PENDING | 브랜치 원격 검증 예정 |
| SQLite 스키마 메타데이터 읽기 | NOT_STARTED | 코드/테스트 0 |
| 구조맵 UI 및 클릭 탐색 | NOT_STARTED | 브라우저 검증 0 |
| PostgreSQL read-only 연결 | NOT_STARTED | 외부 호출 0 |
| 압축 / 복원 / 중복 / 증분 | NOT_STARTED | 벤치마크 0 |
| 예약 작업·원본 보존·장애 복구 | NOT_STARTED | 장애주입/복원 시험 0 |
| 고객 Windows 설치·라이선스 | NOT_STARTED | 수동 검수 0 |
| Vercel / Production / 외부 API | NOT_APPLICABLE | 서버 배포 초기 대상 아님 |

## 우선순위
1. 문서/브랜치 실제 원격 확인. 이미 완료되었다면 반복하지 않는다.
2. feature/p0-db-map에서 첫 합성 SQLite fixture + read-only 메타데이터 수집 구현.
3. 자동 테스트를 실행하고 PASS/FAIL 수·SHA 보고, STATUS/HANDOFF/NEXT_TASK 갱신.
4. 로컬만으로 가능한 시각화 UI를 개발·브라우저 테스트.
5. 이후 일관 스냅샷·ZSTD/ZIP 압축·검증된 복원으로 확장.

## 현재 차단·승인
실고객 DB와 시스템 권한·실파일 접근, 외부 유료 API/서비스, 가격/상표·Public 공개·실 배포·고객 개인정보 활용은 사용자 사전 승인 필요. 현재 테스트는 허구/합성 자료만.
