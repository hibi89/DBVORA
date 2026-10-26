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

## P1-C0 첫 구현 결과 — 2026-10-26 KST
합성 SQLite online backup API -> 완전한 새 경로 스냅샷 + SQLite integrity_check/SHA256 -> ZIP(deflate) 저장 + 고정 manifest -> 임시 독립 복원 검증 후 비덮어쓰기 게시 -> 새 경로 복원, 바이트 SHA 동일. Linux Python 3.13.5 자동화 전체 46 PASS. WAL 커밋 데이터 fixture·위조 manifest checksum·깨진 ZIP·중복·경로 순회·실패시 원본 보호 검증. 아주 작은 fixture 24,576 bytes -> ZIP 1,006 bytes 사례는 일반 압축률 주장 금지. ZIP은 암호화/서명 없음. 512MiB 크기 제한, os.link Windows 호환·전원 장애·live concurrency 미검증. C1 측정 결과는 docs/P1_C1_BENCHMARK.md 참조. 상세 docs/P1_C0_VERIFICATION.md.

## P1-C1 구현·측정 — 2026-10-26 KST
공식 zstd CLI 1.5.7을 로컬에서 호출하는 합성 SQLite ZSTD-1/3/9 엔진 구현. 단일 .dbvz 용기에 유효성 검증된 JSON 메타데이터와 ZSTD 프레임을 넣고, 원본/압축본 SHA 및 독립 SQLite 복원을 확인. 전체 Python 62/62 PASS, Node DOM 1 PASS, wheel 정적 자산과 Python 코드 포함(그러나 zstd 실행 파일은 미포함). 565248바이트 동일 스냅샷의 세 번씩 반복 측정에서 반복 데이터 ZIP 3799B / ZSTD-3 1373B, 랜덤 BLOB 데이터 ZIP 528037B / ZSTD-3 526749B. 용량만 유리했을 뿐 CLI 호출/복원 시간이 더 길 수 있음; 메모리·CPU 전체 사용량 미측정. 파괴/손실 없는 합성 실험만으로 사용 고객 압축 이익/우월성을 주장하지 않는다. 서명·암호화·fsync 디렉터리·Windows 바이너리 번들·전원 중단 복구는 미완료. 상세 docs/P1_C1_BENCHMARK.md.

## P1-C2 장애 및 저장 내구성 실험 — 2026-10-26 KST
Linux 합성 SQLite에서 스테이징 단일 링크 regular-file 검증→파일 fsync→배타적 새 하드링크 게시→상위 디렉터리 fsync 적용. 게시 직후 디렉터리 sync 실패 시 *새 링크만* 되돌리려고 시도하며, 기존 정본은 건드리지 않는다. 여러 임시파일 생성 중 오류 시 이미 생성한 임시파일 정리. 최소 1시간 경과 임시파일을 읽기 전용 검사하고, POSIX에서 실행자 명시 확인(`confirm=True`) 없이는 절대 정리하지 않음. 강제 종료(os._exit(17))·4개 프로세스 8개 동시 스냅샷 포함 Python 76개 테스트 통과. 실제 전원 차단·Windows NTFS·악성 파일 시스템 경합·한계 자원 상황의 내구성은 미검증. 실고객 자동 정리는 여전히 금지. docs/P1_C2_DURABILITY.md 참조.

## P1-C3 재시작 이후 검증 (2026-10-26 KST)
새 recovery_catalog.py는 임의 고객 DB 스캔 없이 사용자가 명시한 아카이브 디렉터리의 DBVORA 패턴만 선별한다. 파일·시간/링크 정보 비교 후 별도 임시 위치로 동결 복사해 독립 SQLite integrity_check / ZIP manifest+복원 SHA / ZSTD frame+복원 SHA를 검사하고 보고한다. 최종 또는 오류 파일 어느 것도 자동 수정/삭제하지 않는다. 출력 상태 CONTENT_VERIFIED_PUBLISH_UNPROVEN은 콘텐츠가 현재 복원됨을 뜻하며 원본 게시의 물리적 내구성·출처 인증을 뜻하지 않는다. 96개 Linux 합성 Python 테스트 PASS, 실제 새 Python 프로세스 재시작 점검 PASS. `python -m scripts.preflight_archiving`은 운영체제 TEMP 파일시스템의 합성 파일만 사용하고 Windows 검증을 주장하지 않는다. 보완 사항: 독립적 commit receipt, crash recovery ledger, Windows/NTFS·물리 전원 차단 및 보안/암호화. 자세한 근거 docs/P1_C3_RECOVERY.md.

## P1-C4 별도 완료 영수증/lineage — 2026-10-26 KST
합성 데이터의 새로 게시된 스냅샷·ZIP·ZSTD에 대해 opt-in 방식으로 별도 dbvora-receipt-UUID.json을 배타적 신규 생성, 각각 독립 복원·SHA 검증 후 부모 기록명/부모 기록 SHA를 연결한다. 재시작시 독립 파일 복사·완전 복원·부모 체인 무결성 확인으로 기록 누락/손상/계보 불일치 분류. 동시 작성자는 단일 정본만 성공, 기존 아카이브/영수증 덮어쓰기 금지. Python 전체 125/125 PASS(신규 29), Node DOM 1 PASS. 영수증은 SHA 연결된 *미서명 자체 기록*일 뿐 신뢰할 수 있는 작성자·전원 장애 내구성·진본성 증명은 아니다. JSON에 원본 절대경로/레코드 내용/키 기록 없음. docs/P1_C4_RECEIPTS.md 참조.
