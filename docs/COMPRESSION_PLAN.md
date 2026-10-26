# 무손실 압축·복원 엔진 설계 및 검증 기준

## 목표와 비교의 공정성
목표는 ZIP/원본 대비 과거 데이터의 **보관 크기와 비용**을 실측으로 줄이는 것. ZIP보다 무조건 좋다거나 Supabase 실시간 데이터베이스 엔진을 이겼다고 사전 주장 금지. PostgreSQL 물리 DB, 스냅샷 아카이브, 장기 로그 Parquet을 서로 같은 제품 범위로 혼동하지 않는다.

## 단계
- C0: 일관된 스냅샷. SQLite online backup API 사용(동시 연결/WAL 시나리오 포함); 목적지 새 임시파일·체크섬. DB 원본은 읽기/조회만.
- C1: ZIP(deflate) 기준선 vs ZSTD(여러 레벨) vs 원본 파일. Parquet+ZSTD는 행형 DB 전체를 무조건 변환하지 않고 구조화된 **export 데이터**에 한해 별도 비교. 이미 압축된 영상/암호화 파일은 효과 제한.
- C2: content-addressed chunk 기반 중복 제거; 청크 해시로 서로 동일한 실제 바이트만 공유, hash collision 방어/확인, 참조계수/GC 검증. DB 일반 행 중복과 저장 파일 중복을 혼동하지 않는다.
- C3: 주기적 full snapshot + 변경분 delta/증분 저장. 스키마 변경·삭제/재정렬, 동일 데이터 재요청·부분 실패 재개, basis snap 보존·복원 체인 의존성 처리. 단계별 checkpoint.
- C4: 스케줄러, retention, 손상/전원단절 복구. 원본 또는 마지막 정본 백업 자동 삭제는 사용자 승인과 독립복원 검증 전까지 불허.

## manifest 제안
schema_version, archive_id, created_at_utc, source_type, source_snapshot_size_bytes, compression_codec/version/level, uncompressed_sha256, compressed_sha256, compressed_size_bytes, chunks[], parent_id(nullable), restore_validation(status, observed_at, restored_sha256), scope/consent. 원본 경로·비밀은 export manifest에 기본 저장하지 않는다.

## 무손실 판정 계약
1. 스냅샷 백업의 SQLite PRAGMA integrity_check = ok, 출처와 백업의 일관된 논리 상태 검증.
2. 압축→새 폴더로 복원→스냅샷과 SHA-256 정확히 일치. 필요시 실제 SQL fixture 쿼리 결과/레코드 건수 확인.
3. 손상된 압축바이트, manifest 위조, 누락 parent/chunk, 읽기 전용 경로, 디스크 부족·종료 신호, 중복 실행을 테스트해 안전 중단.
4. atomic publish 전 오류 발생 시 원본·최종 아카이브 불변, orphan 임시파일만 격리/정리 가능.
5. 복구 완료 로그는 검증 후에만 기록. 백업 성공은 복원 성공을 뜻하지 않는다.

## 성능 벤치마크 동일 조건
- 합성 세트: 반복 문자형 로그 / JSON 이벤트 / 컬럼 반복 높은 CSV / SQLite 관계형 / random incompressible / 이미 압축된 파일 / 하루 변경분 / 스키마 변화·삭제.
- 지표: 원본 logical size, 스냅샷 물리 bytes, 저장소 총 사용량(부모+자식+manifest+중복 해시 포함), ratio, 압축·복원 wall time, peak RAM, process CPU, 디스크 I/O, 성공 복원율.
- 같은 기기/같은 데이터/같은 snapshot, 3회 이상 반복하고 편차 기록. 운영 원가 = 디스크 절감액 - CPU/관리/복원 비용. 더 낮은 용량 수치만 선택적으로 보고하지 않음.
- 표준 벤치마크 데이터/대용량 아카이브는 GitHub에 올리지 않는다. 코드·생성기·경량 보고서만 기록.

## 구현 의사결정
ZSTD·ZIP 등 코덱은 검증된 라이브러리 활용. 데이터 분류·압축 정책·메타데이터·복원 체인·비용 분석은 DBVORA 고유 구현. 외부 기술 라이선스/패키징·Windows wheel 등 조사 후 확정.
