# R01-03 PostgreSQL permission recovery — 2026-11-15

## Result

**PASS_SCOPED** at feature/source/test SHA `41aa567f0504ace5109afaa3dbe6dcc63aa7f34e` on `feature/p0-db-map`.

This change makes PostgreSQL permission failures understandable and retryable in the read-only UI. The connector recognizes PostgreSQL SQLSTATE `42501` from both psycopg driver error attributes (`sqlstate` and `pgcode`), maps it to the fixed `PG_PERMISSION_DENIED` code, and does not forward driver text, DSNs, CA paths, database paths, or row data. The Korean UI message explains that the selected read-only role lacks permission and offers a retry after access is corrected.

The API applies the safe permission message to catalog and statistics failures. Synthetic unit/API tests cover code classification and sanitization. The real-PG browser workflow injects a one-shot permission error at the API boundary, verifies the safe UI and absence of secrets, then retries against the same real PostgreSQL 16 instance with verified TLS. No role, grant, credential, repository permission, or security setting was changed.

## Exact-SHA GitHub Actions

All listed runs used head SHA `41aa567f0504ace5109afaa3dbe6dcc63aa7f34e`.

| Workflow | Result |
| --- | --- |
| [Full offline release gate #43654447078](https://github.com/hibi89/DBVORA/actions/runs/43654447078) | PASS. Ubuntu 793/793 with 0 skips; Windows 793 discovered, 792 passed and one named POSIX-only skip (`test_review_html.ReviewHtmlTests.test_created_report_is_mode_0600_on_posix`). All 12 required gate steps passed on both OSes. |
| [Chromium localhost acceptance #43654447035](https://github.com/hibi89/DBVORA/actions/runs/43654447035) | PASS, 36 checks on Ubuntu and 36 on Windows. Includes database topology, keyboard navigation, DB-scoped filters/storage, reload, source immutability, and HTTP guards. |
| [PostgreSQL 16 verified-TLS acceptance #43654447096](https://github.com/hibi89/DBVORA/actions/runs/43654447096) | PASS: 5 live-TLS checks and 10 PG UI checks. |
| [Unsigned source ZIP preview #43654447028](https://github.com/hibi89/DBVORA/actions/runs/43654447028) | PASS: 75 files; packaged synthetic self-check 9/9. Embedded source commit `41aa567f0504ace5109afaa3dbe6dcc63aa7f34e`; ZIP SHA-256 `b065f8bef8c81af6174ce8fd21e5acddba3a05df1625ce616e98f83678f22080`. GitHub artifact ZIP ID 14137376647, digest `sha256:6888f5073d808de2424c3fed58c4317c755942486d7662e7aad743eb2fa0fdbe`. |
| [Unsigned synthetic Windows demo EXE #43654447043](https://github.com/hibi89/DBVORA/actions/runs/43654447043) | PASS: frozen executable ran against synthetic SQLite. EXE SHA-256 `2cb874493a84c59a7e2608ab64e2f0d31b12c10a891cfaa7041a5e292fee7470`; GitHub artifact ZIP ID 14137047964, digest `sha256:e7d8e847f0fa6473cb71008146a37c5f55233ad01871bd05caa4c9413cb58fc2`. |
| [Blueprint evidence gate #43654447279](https://github.com/hibi89/DBVORA/actions/runs/43654447279) | PASS. |

The PG UI acceptance reported `permission_error_safe_retry_recovery`, `no_rows_or_dsn_in_browser`, `explicit_stats_may_lag_and_view_unavailable`, and `real_pg16_sqlite_same_name_collision_and_explicit_unverified_link`. The live TLS checks reported verified TLS/read-only access, catalog/FK/view metadata without rows, statistics provenance, offline HTML without rows, and fail-closed wrong-certificate handling.

## Scope and limits

All test records and fixtures were synthetic. The permission error is injected once by the acceptance harness at the API boundary; production database privileges are not modified. These GitHub-hosted checks do not establish customer-data readiness, owner-device acceptance, Windows NTFS power-loss durability, commercial rights, or final release approval. Overall completion remains **UNASSESSED / RELEASE HOLD**.

Next matrix item: **R01-01 EVIDENCE_RECHECK** (single/multi-database boundaries and metadata provenance).

## Revalidation at the later R01-01 source/test SHA

The permission recovery code was unchanged at SHA `1eb5284cf0ddc0ba6411324902efc4f4d8c917e9` and remained covered by the exact-SHA [PG16 TLS/UI run #43655576024](https://github.com/hibi89/DBVORA/actions/runs/43655576024): 5 TLS checks plus 10 browser checks, including `permission_error_safe_retry_recovery` and `no_rows_or_dsn_in_browser`. The same SHA passed the [full Ubuntu/Windows gate #43655575943](https://github.com/hibi89/DBVORA/actions/runs/43655575943) and [Chromium #43655575969](https://github.com/hibi89/DBVORA/actions/runs/43655575969). The R01-01 eight-database evidence is recorded separately in [R01_01_MULTI_DB_BOUNDARY_20261115.md](R01_01_MULTI_DB_BOUNDARY_20261115.md).
