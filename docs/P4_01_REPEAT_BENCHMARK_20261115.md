# R04-01 반복 벤치마크 증거 — 2026-11-15

## 범위와 판정

R04-01은 ZIP, ZSTD level 3, raw CAS v1, zlib 압축 CAS v2의 동일 합성 SQLite 스냅샷 반복 비교를 위해 `scripts/benchmark_synthetic_archives.py`, 관련 테스트 및 release gate 검증을 추가했다. 기능/테스트 SHA: [`3919a1e3e0287f553f2b491834a67791309257ad`](https://github.com/hibi89/DBVORA/commit/3919a1e3e0287f553f2b491834a67791309257ad). 이 task는 이 CI 환경의 측정 범위로 `PASS_SCOPED`다.

같은 946,176 B 및 950,272 B 입력을 각 포맷별 3회 처리했고, 매 trial에서 두 세대를 독립 복원한 후 SHA-256을 확인했다. artifact 크기는 파일 길이의 합이다. 각 시험 실행 순서, 압축 옵션, OS/릴리스/아키텍처/CPU 식별자와 논리 CPU 수, Python·SQLite·ZSTD 버전 및 시간 표본/median/min/max가 기록됐다.

## GitHub Actions

- Full release [#43620565261](https://github.com/hibi89/DBVORA/actions/runs/43620565261): success. Ubuntu 761/761, 0 skip; Windows 761 pass + 1 named POSIX-only skip (`test_review_html.ReviewHtmlTests.test_created_report_is_mode_0600_on_posix`).
- Blueprint [#43620565587](https://github.com/hibi89/DBVORA/actions/runs/43620565587): success.

## 합성 runner 결과

| Runner | ZIP | ZSTD level 3 | raw CAS v1 | zlib CAS v2 |
|---|---:|---:|---:|---:|
| Ubuntu, 4 logical CPUs | 31,216 B; write median 21.347 ms; restore 8.417 ms | 27,651 B; 25.982 ms; 13.484 ms | 1,177,960 B; 23.006 ms; 9.135 ms | 24,637 B; 31.841 ms; 11.868 ms |
| Windows, 4 logical CPUs | 31,550 B; write median 59.421 ms; restore 39.903 ms | 27,824 B; 115.215 ms; 64.010 ms | 1,177,960 B; 202.550 ms; 52.995 ms | 25,046 B; 217.653 ms; 51.293 ms |

Ubuntu runner: Linux x86_64, Python 3.11.18, SQLite 3.45.1, ZSTD 1.5.7. Windows runner: Windows-2025 / AMD64, Python 3.11.9, SQLite 3.45.1, ZSTD 1.5.7. Each time is the median of three trials; the table shows write then independent restore time. The action log contains per-trial min/max and order.

## 한계 및 다음 작업

These synthetic GitHub runner samples are environment-specific and do not establish a universal performance ranking. OS cache was not cleared, concurrent host load is uncontrolled, and measured artifact bytes are file lengths rather than physical allocation. No user PC, real customer database, external data, or paid service was used. CPU time, sampled resident memory, and shared-volume free-space deltas are not yet included; implement and validate those scoped measurements under R04-02. Physical device and owner acceptance gates remain open. Overall official completion remains `UNASSESSED` / `RELEASE HOLD`.
