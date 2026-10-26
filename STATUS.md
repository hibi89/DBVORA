# DBVORA STATUS — 초기 설정

- 기록 시점: 2026-10-26 KST. 원격 문서 12개(README 제외) fetch 및 main 기능/문서 기준 커밋 1b2d4275f47774befa17f1c0fbeb292930042db7 확인. 새로운 문서 갱신 커밋과 새 채팅 HEAD는 반드시 재조회. 코드 개발 착수 없음.
- 저장소: hibi89/DBVORA, Private. main / develop / feature/p0-db-map **세 브랜치 모두 GitHub 원격 검색으로 실존 확인**. 문서 업데이트 뒤 최종 SHA 동기화 재검증 예정.
- 진도 표현: **기획·개발환경 구성 진행 / 제품 기능 구현 0% / 상용제품 미완료**. 일정은 3일 MVP, 이후 10~14일 후보 *목표*, 보장 아님.

| 항목 | 상태 | 검증 |
| --- | --- | --- |
| 저장소 생성 및 읽기/쓰기 접근 | VERIFIED | GitHub repo metadata 및 첫 README commit |
| 채팅 재개·설계·요구사항 문서 | VERIFIED_DOCS_ONLY | 원격 fetch로 12개 경로 확인, 제품 기능 아님 |
| 코드 브랜치 | VERIFIED_EMPTY_OF_PRODUCT_CODE | main·develop·feature/p0-db-map 확인, P0 코드 미작성 |
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
