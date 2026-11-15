# R02-02 — Growth timestamp and database scope evidence

**Result:** PASS_SCOPED for synthetic GitHub Actions coverage.  
**Application implementation SHA:** `1eb5284cf0ddc0ba6411324902efc4f4d8c917e9` (unchanged; existing behavior was validated).  
**Source/test SHA:** `ac087f39ed33cd990b0c8f6c042b005bdc6d6819`  
**Branch:** `feature/p0-db-map`

## Coverage added and reused

- Added `test_reverse_time_is_unavailable_without_negative_growth`: the same synthetic database IDs receive a baseline timestamp followed by a timestamp one second earlier. Each comparison is unavailable with `non_increasing_observation_time`; no `delta_main_file_bytes` value is produced.
- Existing comparison tests cover two actual snapshots, equal timestamps, and a missing database fingerprint without fabricated growth.
- The real Chromium localhost harness reuses two synthetic SQLite databases. It captures a valid accepted response, replays the same timestamp with a changed size, then an older timestamp with a changed size. Both must show `비교 불가` while the selected DB's sample count remains unchanged.
- A subsequent real inventory response must recover to exactly `직전 측정 대비 변화 없음 (0 B)`. This proves the rejected payloads did not replace the last accepted size baseline.
- Existing Chromium checks cover no-baseline/first measurement and DB switching: the selected DB keeps its own size, history, and comparison. The new stale response tests are run in the same two-DB synthetic flow.

## Exact-SHA GitHub Actions

At source/test SHA `ac087f39ed33cd990b0c8f6c042b005bdc6d6819`:

- Full fail-closed release gate [#43657990671](https://github.com/hibi89/DBVORA/actions/runs/43657990671) PASS, synthetic only. Ubuntu: 797/797 tests, 0 skips; Windows: 797 discovered, 796 pass plus the named POSIX-only skip `test_review_html.ReviewHtmlTests.test_created_report_is_mode_0600_on_posix`. All 12 required gate steps passed on both OSes.
- Chromium localhost acceptance [#43657990663](https://github.com/hibi89/DBVORA/actions/runs/43657990663) PASS, 37/37 checks on Ubuntu and 37/37 on Windows. This includes `multi_growth_equal_reverse_time_rejected`.
- PostgreSQL 16 TLS acceptance [#43657990651](https://github.com/hibi89/DBVORA/actions/runs/43657990651) PASS: 5 verified-TLS checks plus 10 browser checks.
- Final blueprint evidence [#43657990886](https://github.com/hibi89/DBVORA/actions/runs/43657990886) PASS.

All test DBs and replayed API payloads are synthetic. The application code stayed at implementation SHA `1eb5284cf0ddc0ba6411324902efc4f4d8c917e9`; the R02-02 commit added acceptance tests only. No customer DB, external data transfer, device/physical test, or production forecast is involved. Overall completion remains **UNASSESSED / RELEASE HOLD** and OWNER_GATE items remain open.
