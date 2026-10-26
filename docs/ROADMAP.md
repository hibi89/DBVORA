# 로드맵 — 목표와 실측 구분

## 계획된 순서
- **M0/작업일 1~3(목표)**: 합성 SQLite metadata reader, DB/테이블/컬럼/FK inventory JSON, 데이터 규모 표시, 클릭형 구조도, 로컬 실행. 성공: 실제 테스트 + 브라우저 기본 흐름 확인.
- **M1/작업일 4~6(목표)**: 안전한 SQLite backup snapshot, 압축 ZIP/ZSTD baseline, 독립 경로 무손실 복원·checksum 검사. 성공: 원본 불변·손상 복원 거부·실측 그래프.
- **M2/작업일 7~9(목표)**: 별도 아카이브 중복 제거/증분 스키마 초안, 일정 실행 idempotency, 백업 history. 성공: 중복 실행·불완전 parent·중단 복구 시험.
- **M3/작업일 10~14(목표)**: 최소 패키징·Windows 수동 점검·리소스 상한/오류 UX·벤치마크 비교. 상용 판매 가능 여부는 별도 결정.

**주의:** 3일 MVP 및 10~14일 판매 후보는 집중 개발 가정의 일정 목표이지 확정 납기나 개발 진도 아니다. PostgreSQL 및 타 엔진 연동·고급 그래프·엔터프라이즈, DB 호스팅 및 자동 인증/과금은 이후 별도 범위. 고객 신뢰성과 데이터 무손실은 마지막에 미룰 수 없다.

## 게이트
- G0: 저장소 초기화와 브랜치·인수인계 (설계 등록).
- G1: 합성 SQLite fixture/read-only inventory와 실제 pytest 통과.
- G2: 웹에서 클릭 탐색·localhost 브라우저/HTTP 검증.
- G3: snapshot+압축+복원·SHA/DB 일치·악조건 검증.
- G4: 실측 ZIP 비교 + 동일 데이터 조건 + 원본 불변.
- G5: 사용자 Windows 설치/전원단절·복원·라이선스/보안/상품 UX 확인.
- G6: 별도 사용자 승인 후 실제 고객 사례·상품화, 아니면 보류.

완료 보고 시 항상 repo/branch/SHA, CI·로컬 test PASS/FAIL, 실제 기능 검증, 남은 BLOCKED/NOT_TESTED, 배포 여부를 구분.
