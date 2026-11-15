# R01-01 SQLite/PostgreSQL inventory boundaries — 2026-11-15

## Result

**PASS_SCOPED** at feature/source/test SHA `1eb5284cf0ddc0ba6411324902efc4f4d8c917e9` on `feature/p0-db-map`.

The live multi-SQLite endpoint now has explicit CI coverage for the upper bound of eight configured databases. The new synthetic API acceptance creates eight distinct files, verifies all eight are inventoried under distinct database IDs, confirms each foreign-key edge remains attached to its own SQLite database, checks the eighth database's table-storage lookup, and compares source SHA-256 and mtime before and after both reads. It also asserts no source path or row sentinel is serialized and that a routine inventory refresh does not trigger the optional table-storage scan.

Existing checks cover the two-database lower bound, duplicate/path identity rejection, over-eight fail-closed behavior, path-free metadata, same-name collision handling, and read-only PostgreSQL catalog access. The PostgreSQL connector header was corrected to describe the actual validation boundary: ephemeral synthetic PostgreSQL 16 in GitHub Actions; owner/customer servers remain unverified. No runtime behavior or database access was broadened.

## Exact-SHA GitHub Actions

All listed workflows ran with head SHA `1eb5284cf0ddc0ba6411324902efc4f4d8c917e9`.

| Workflow | Result |
| --- | --- |
| [Full offline release gate #43655575943](https://github.com/hibi89/DBVORA/actions/runs/43655575943) | PASS. Ubuntu 794/794, 0 skips; Windows 794 discovered, 793 passed and one named POSIX-only skip (`test_review_html.ReviewHtmlTests.test_created_report_is_mode_0600_on_posix`). All 12 required steps passed on both OSes. |
| [Chromium localhost acceptance #43655575969](https://github.com/hibi89/DBVORA/actions/runs/43655575969) | PASS, 36 checks on Ubuntu and 36 on Windows. Includes two live database nodes, selection/navigation, mobile layout, database-scoped inspector/storage and no source mutation. |
| [PostgreSQL 16 verified-TLS acceptance #43655576024](https://github.com/hibi89/DBVORA/actions/runs/43655576024) | PASS: 5 live-TLS checks and 10 PG UI checks. The synthetic SQLite/PostgreSQL same-name collision and explicit unverified link remain covered; permission-error retry and secret-free recovery also pass. |
| [Unsigned source ZIP preview #43655575933](https://github.com/hibi89/DBVORA/actions/runs/43655575933) | PASS: 75 files, synthetic packaged self-check 9/9, embedded source SHA `1eb5284cf0ddc0ba6411324902efc4f4d8c917e9`; ZIP SHA-256 `ce1c3c5f682a0e678e24c16490883132b9d0cf07f057010d0d165e649a2bed95`. GitHub artifact ZIP ID 14137159002, digest `sha256:536656daed77c860adc747dfbb86e5459ff2f6dd1f82b80ed9db34f9a809e1e1`. |
| [Unsigned synthetic Windows demo EXE #43655576003](https://github.com/hibi89/DBVORA/actions/runs/43655576003) | PASS: frozen executable ran against synthetic SQLite. EXE SHA-256 `dcae6f36f10b7166fa888d800c3a5c916ae4898ba187a4526d149cb74d5786d4`; GitHub artifact ZIP ID 14137604090, digest `sha256:52c5b5ed973a00da234e6ce2c1bd4befa2e2afaf2e277b8b200f96022c9f1480`. |
| [Blueprint evidence gate #43655576143](https://github.com/hibi89/DBVORA/actions/runs/43655576143) | PASS. |

### Supporting artifact digests

- PG UI screenshots: artifact 14137079352, digest `sha256:8d45af1e1a8764fcafa91e42954893c543f1d4db176729960490114d98d9761b`.
- Metadata-only Python SBOM candidate: artifact 14136959617, digest `sha256:6287634a5db142922d6e6d57fa38914dacd5c339e42f6d9305dfee9734f88415`.
- Ubuntu Chromium screenshots: artifact 14137378236, digest `sha256:8f4b212cc465a96abdf1a0059170821d8f329e64a72dfcfb466c4bc9a577bdce`.
- Windows Chromium screenshots: artifact 14137634280, digest `sha256:7206cee9fbea52f246c77a427d553457f2d6cc539721288e9a6023d453d88878`.

## Scope and limits

The eight database sources and all fixtures were synthetic. The PG16 instance was ephemeral, local to the GitHub runner, and accessed through verified TLS with a read-only role. This is not owner-device, customer-data, commercial, or physical durability acceptance. No customer data, role/grant, repository privilege, security setting, or production environment was changed.

Overall completion remains **UNASSESSED / RELEASE HOLD**. Next matrix item: **R02-01 EVIDENCE_RECHECK** (SQLite main/WAL/SHM and dbstat scope, opt-in limits, file identity changes and unsupported cases).