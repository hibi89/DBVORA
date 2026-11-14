# R07-03 한국어 안전·복구 UX 증거

- 기준: `2026-11-15 KST` · 저장소 `hibi89/DBVORA` · 브랜치 `feature/p0-db-map`
- 작업: `R07-03` PASS_SCOPED · 정확 기능/테스트 SHA: `8dc0a4dd9096ec9b92a683db53912c00a017f03c`
- 범위: 로컬 읽기 동의 안내, 한국어 오류 복구, 기본 거부 복원 CLI 안내, 실제 Chromium desktop/390px·keyboard·ARIA 검증

## 구현 요약

- DBVORA 화면과 주요 UI 설명을 한국어로 정리했다. 접을 수 있는 안전 안내는 실행 범위를 설명하고, SQLite 실제 행/접속 정보 비표시·원본 불변·관측 원장 명시 opt-in·PostgreSQL 조회 버튼별 요청을 밝힌다.
- 복원은 별도 CLI이며 합성 데이터 전용임을 안내한다. 읽기 전용 미리보기, 아카이브와 스냅샷의 두 SHA-256 값, `--synthetic-only`, `--accept-plaintext`, 원본과 분리된 출력 경로를 요구한다. 생성물은 암호화되지 않는다는 점을 UI와 CLI 도움말에 표시한다.
- API의 알려진 오류는 한국어 복구 안내로 매핑하고, 서버 내부 오류 문구를 화면에 그대로 출력하지 않는다. 새로고침 실패 시 마지막 정상 데이터베이스·검색·선택 정보를 보존한다.
- CLI의 도움말·동의 실패·복원 오류를 한국어로 제공하며 경로를 노출하지 않는다. Windows 테스트 helper가 UTF-8을 명시해 CLI JSON을 읽도록 했다.
- browser/PG workflow 경로에 공통 DOM/CLI 회귀 입력을 추가해 변경된 사용자 문구와 각 검증 게이트를 같은 SHA에서 실행한다.

## 정확 SHA Actions

| 검증 | Actions | 결과 |
|---|---|---|
| Ubuntu/Windows 전체 synthetic release gate | [#43647307300](https://github.com/hibi89/DBVORA/actions/runs/43647307300) | PASS · Ubuntu 783/783, 0 skip; Windows 783 발견, 782 PASS + 지정 POSIX-only 1 SKIP; 필수 단계 12/12 각 OS |
| Chromium localhost E2E | [#43647307293](https://github.com/hibi89/DBVORA/actions/runs/43647307293) | PASS · 35/35 Ubuntu, 35/35 Windows; 오류 복구 포함 스크린샷 각 OS 6장 |
| PostgreSQL 16 TLS + UI | [#43647307279](https://github.com/hibi89/DBVORA/actions/runs/43647307279) | PASS · TLS/read-only 5 checks, UI 8 checks |
| Source ZIP | [#43647307331](https://github.com/hibi89/DBVORA/actions/runs/43647307331) | PASS · source SHA 일치, 75 files, offline self-check 9/9; inner ZIP SHA-256 `1ff2f8c7b89a394074ebe6ec2568e58ca74c99135396ba6ca0b32ddef081f382` |
| Windows EXE | [#43647307329](https://github.com/hibi89/DBVORA/actions/runs/43647307329) | PASS · 합성 DB로 실행 검증; EXE SHA-256 `d80fc2d90f7c6e0bc5fb416683e31e21038744f44fe889c4750110449a7290ff` |
| Blueprint | [#43647307578](https://github.com/hibi89/DBVORA/actions/runs/43647307578) | PASS structural evidence; official completion은 계속 UNASSESSED |

## 산출물 증거

- Source ZIP artifact ID `14134722497`, 업로드 ZIP digest `sha256:245b32da83ce3787749faff6b719ff34b8b89faee226abc2a7ff266f9e8fd791`.
- Windows EXE artifact ID `14134278857`, 업로드 ZIP digest `sha256:2ac390db1ae2f06d3ed9a28fff4624e499307fd22291c1e2e06c90cdff0a87fb`.
- Ubuntu Chromium screenshot artifact ID `14133599520`, digest `sha256:10e8332a113e988b81dea70cc494dd458794e653f20fff0755cf08393cdbb060`.
- Windows Chromium screenshot artifact ID `14133953529`, digest `sha256:8e6f4c8b1134799f4d4cb2bdc3a7ecc0eabd39b34d2de627b5e6c98f19a9e341`.
- PostgreSQL UI screenshot artifact ID `14134089643`, digest `sha256:a7495371ad6158bd3f11a5122e098330b0755929e28d7c340d7ecb2db0f9ff46`.
- Blueprint report artifact ID `14134508448`, digest `sha256:c7a47e191c3834f891f39b261ec94ccc3b496255bd2d40cf579da7a0fc76020f`.

## 회귀 보정 이력과 한계

- 한국어 UI 적용 뒤 남은 영문 문구를 기대하던 test/API/Chromium assertions를 정정했다. Windows strict-audit tests는 UTF-8 CLI pipe를 CP1252로 decode하던 helper를 고쳐 해결했고, 마지막 SHA 전체 회귀에서 통과했다.
- R01-05(대용량·비정상 카탈로그) 및 R01-06(키보드·ARIA·모바일·오류 복구)도 이 정확 SHA의 전체/Chromium 증거로 PASS_SCOPED 처리한다.
- 테스트는 합성 SQLite/PostgreSQL만 사용하며 GitHub-hosted runners 한정이다. 사용자 실기기, 물리 전원중단, 장기 고객 데이터, 재배포권/법적 승인은 검증하지 않았다. ZIP/EXE는 unsigned preview이며 상용 릴리스가 아니다.
- 다음 작업: R01-04 SQLite+PostgreSQL 승인 교차 관계·동일 테이블명 충돌 검증. 공식 전체 완성률은 UNASSESSED / RELEASE HOLD를 유지한다.
