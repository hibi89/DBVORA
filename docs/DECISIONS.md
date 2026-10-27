# 결정 기록 (ADR 간략)

## ADR-001: MVP 실행 아키텍처 (2026-10-26)
- 후보 A: 로컬 Python FastAPI + stdlib SQLite + 경량 JS/SVG UI, 임베디드 메타데이터 SQLite. 소프트웨어/호스팅 초기 현금비 0원 지향, Windows 패키징은 후속.
- 후보 B: Electron/React + PostgreSQL 서버 + 다중 플러그인 관리형 백엔드. 기능/데스크톱 UX 확장 장점이 있으나 초기 설치 부담·메모리/배포/운영비 높음.
- **선택 A**: 3일 MVP 속도, 사용자가 원하는 PC 로컬·소버린, 낮은 운영비. 반응형 시각화와 멀티DB는 점진적 확장.
- 확정하지 않은 것: 판매가, 상표, 외부 배포, 라이선스, Supabase 엔진 수준 실시간 성능 경쟁.

## ADR-002: 압축 전략
- A: ZSTD/Parquet/ZIP 비교 + 안전한 스냅샷, 중복·증분 인덱스는 자체 개발.
- B: 신규 무손실 코덱을 처음부터 개발.
- **선택 A**, B는 충분한 데이터/벤치마크로 개선 가능성 입증할 때 연구. 기존 ZSTD를 자체 발명했다고 주장하지 않는다. 초기 벤치마크에 ZIP 포함.
- 라이브 원본은 별도, 원본 보존→복원 검증→성능과 비용 측정.

## ADR-003: 고객 DB 수집
- A: 사용자가 지정한 SQLite에 읽기 전용 접근, 명시적 메타데이터만, 비밀 저장 최소화.
- B: 전체 파일/테이블 원문을 한곳에 미러링.
- **선택 A**; 개인정보·디스크 비용·원본 영향 감소. B는 현재 불필요.

## ADR-004: 작업 방식 및 Git
- main 안정 / develop 통합 / feature/p0-db-map 첫 코드. 수동 PR 승인 전 데이터/권한 변경 없음.
- 품질: 실제 검증 전 성공 주장 금지. 주요 단위 완료 시 SHA/STATUS/HANDOFF 갱신.

## ADR-005: strict audit CLI without breaking enumeration (2026-10-27)
- Alternative A: change existing audit exit code on any failed receipt/artifact, breaking older consumers.
- Alternative B: additive `--require-all-verified` mode, fail-closed for empty/unverified catalogs while default audit remains read-only inventory. **Choose B** for compatibility and explicit automation policy with zero additional dependencies.
- Evidence: docs/P1_C6_STRICT_AUDIT_20261027.md, genuine synthetic subprocess tests 3/3 PASS. Unsigned receipt + content proof is **not** cryptographic authenticity or crash durability.

## ADR-006: Orphan receipt rejection in opt-in strict mode (2026-10-27)
- Option A: add orphan receipt entries to all audit catalogs; more contract churn and downstream risk.
- Option B: scan only generated-style receipt basenames for missing corresponding verified artifacts after normal strict verification, preserving legacy audit output and unrelated user files. **Chose B**: bounded local filename-only pass, zero dependencies.
- Evidence and limits: `docs/P1_C7_ORPHAN_RECEIPT_20261027.md`. This is not proof of signed receipts, crash durability or customer readiness.

## ADR-007: Offline QA source transport for incomplete private checkout (2026-10-27)
- **A: Repeat GitHub clone or use a remote CI runner.** The current container has no GitHub DNS/auth. Repeating failed clone wastes time; remote CI may require billing or rights changes and therefore needs explicit approval before execution.
- **B: Owner-authorized private source ZIP + SHA-pinned offline QA kit.** No remote data upload, no paid runner, low maintenance and fail-closed on source mismatch. Requires owner to obtain the private ZIP once. **Selected B as a zero-cost handoff/verification path**, without falsely claiming full test execution.
- QA v4 source baseline `318a49e3031b9d0aa052221e35ebdebbec70dedd`, **50** Git blobs; kit 16/16 selftests PASS. See `docs/QA_V4_MANIFEST_20261027.md`. Complete 214 test suite remains unexecuted. Future CI option remains approval-gated.
