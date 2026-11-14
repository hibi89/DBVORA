# R01-04 — mixed SQLite/PostgreSQL links and name collisions

Date: 2026-11-15 KST  
Repository/branch: hibi89/DBVORA / feature/p0-db-map  
Functional and test SHA: cd2588e126c5014d2311b15a1041350b457380e1  
Scoped status: PASS_SCOPED

## Acceptance implemented

- The mixed-engine metadata map displays SQLite and PostgreSQL databases together.
- Cross-database links are added only from an explicit JSON declaration. The output marks each link as user-declared/unverified, sets verified=false, and keeps cross_database_edges_verified=0. No foreign key or join is inferred across databases.
- Each link endpoint identifies a 1-based database position, schema, table and column. SQLite requires a null schema; PostgreSQL requires an exact schema. The referenced table and column must exist in that database. Self-links, duplicate links, unknown columns, malformed keys and more than 64 links fail closed.
- The report assigns collision-resistant table identities and scopes navigation by database id plus table identity. A SQLite users table and PostgreSQL public.users table remain distinct, and the link selects the intended PostgreSQL target.
- The optional mixed CLI --links-file input is read only from an explicitly selected absolute local JSON file, bounded to 16 KiB. The existing synthetic-only and plaintext metadata acknowledgements still apply. SQLite inputs are numbered in repeated --sqlite order; an explicitly enabled PostgreSQL input follows them.
- The offline HTML uses text nodes for metadata, revalidates link endpoints before rendering, embeds no source paths or records, and sends no network requests.

Example manifest:

```json
[
  {
    "from_db": 1,
    "from_schema": null,
    "from_table": "local_users",
    "from_column": "id",
    "to_db": 2,
    "to_schema": "public",
    "to_table": "users",
    "to_column": "id"
  }
]
```

This declaration expresses operator intent only. It does not verify that row values match and does not create a database constraint.

## Exact-SHA verification

- Full synthetic release gate [#43650797153](https://github.com/hibi89/DBVORA/actions/runs/43650797153): Ubuntu 791/791 PASS with 0 skips; Windows 790 PASS plus the named POSIX-only skip test_review_html.ReviewHtmlTests.test_created_report_is_mode_0600_on_posix. All 12 mandatory release-gate steps passed on both operating systems.
- Real PostgreSQL 16 verified-TLS/read-only and Chromium UI [#43650797203](https://github.com/hibi89/DBVORA/actions/runs/43650797203): TLS acceptance 5 checks; browser acceptance 9 checks. The browser run included synthetic SQLite users and PostgreSQL public.users, no-declaration/no-inference, explicit unverified link, target selection, no external request, and row/DSN/path leak checks.
- General localhost Chromium [#43650797152](https://github.com/hibi89/DBVORA/actions/runs/43650797152): 35/35 checks on Ubuntu and 35/35 on Windows.
- Source ZIP [#43650797187](https://github.com/hibi89/DBVORA/actions/runs/43650797187): 75 files, offline HTML self-check 9/9, inner ZIP SHA-256 1c0dd5c25267746d790397ce61a51c111bf6bd8e340317191f0ceac7e3cc333d. Artifact 14135143788; outer artifact digest sha256:52b181545b66c40cf5cb252c25e321678259d330b757b3fb095159dbd235e70c.
- Windows demo EXE [#43650797191](https://github.com/hibi89/DBVORA/actions/runs/43650797191): synthetic run passed, EXE SHA-256 6c0feb66d748af68c8b407da8bf5368260b79843322a8432e6019a8bf6ab56cb. Artifact 14135018935; outer artifact digest sha256:91ebcafd9977cf0b85b62d621ed42537d55d4d1cb2dd35e51aeb60ff1105ccde.
- Final blueprint gate [#43650797372](https://github.com/hibi89/DBVORA/actions/runs/43650797372): PASS. This records structural evidence only.

Screenshots are synthetic-only, retained seven days: general Chromium Ubuntu artifact 14135812830 (sha256:70f63cc16df1c506ebc966ae7e005d46775f6936bb2f32f4b52d05c2e83ea4c9), Windows artifact 14135822913 (sha256:31d09a7e485d60b61832c93f096882363397d0c30752d227ab2efe270ccd8570), and PostgreSQL/mixed-map artifact 14135503271 (sha256:fb1ee945e1ad156cc9c583ecc8407af87863f4892df37b982097391346c973f2).

## Failed attempts and corrections

- Full gate [#43649508843](https://github.com/hibi89/DBVORA/actions/runs/43649508843) at 8ce4675 found one test fixture typo: the invalid SQLite schema case changed to_schema instead of from_schema. The test now mutates the SQLite source endpoint.
- Chromium mixed-report attempts [#43649760119](https://github.com/hibi89/DBVORA/actions/runs/43649760119) and [#43650037148](https://github.com/hibi89/DBVORA/actions/runs/43650037148) did not render the link button after replacing an already-used page's document. The test now loads the mixed report in an isolated browser page; the exact final PG16/browser run passes.
- Full gate [#43650307346](https://github.com/hibi89/DBVORA/actions/runs/43650307346) found Windows fixture-cleanup errors because two newly added tests left SQLite connections open. The tests explicitly close those connections; final Windows full gate passes.

## Limits and release status

All new cross-link and runner fixtures use synthetic data. The PostgreSQL service is an ephemeral loopback-only GitHub Actions container using a read-only role and verified TLS. No customer database, user PC, or external service was used. Unsigned ZIP/EXE evidence does not provide publisher authentication or owner-device acceptance. Overall final completion remains UNASSESSED / RELEASE HOLD; physical power-loss, owner-device, legal and commercial acceptance gates remain open.

