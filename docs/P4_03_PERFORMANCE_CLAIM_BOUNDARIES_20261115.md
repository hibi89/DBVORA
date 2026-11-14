# R04-03 공개 성능 주장 경계 — 2026-11-15

## Scope and exact validation

R04-03 PASS_SCOPED at functional/test SHA [`4debf5aa580f49265d90de6f441cb1eda3382cbb`](https://github.com/hibi89/DBVORA/commit/4debf5aa580f49265d90de6f441cb1eda3382cbb).

- Full synthetic release gate [#43623040821](https://github.com/hibi89/DBVORA/actions/runs/43623040821): success at exact SHA. Ubuntu 765/765, 0 skips; Windows 765 pass + 1 named POSIX-only skip (`test_review_html.ReviewHtmlTests.test_created_report_is_mode_0600_on_posix`).
- Blueprint gate [#43623041398](https://github.com/hibi89/DBVORA/actions/runs/43623041398): success at exact SHA.

## Changes and audited surfaces

- Public `README.md` now states that CI synthetic samples do not establish customer performance or operating savings. It explicitly says a direct PostgreSQL/Supabase performance comparison has not been measured and is unavailable.
- Removed the historical README phrase claiming a specific 21.1% reduction. The detailed R04-01/R04-02 values stay in scoped engineering evidence, with runner and measurement limits; they are not customer performance claims.
- Added `tests/test_performance_claim_boundaries.py`; the full release gate requires this regression test and `README.md`. It rejects numeric percentage claims and direct provider superiority language in the public README while requiring the limitation text.
- Reviewed compression plan: it already prohibits pre-claiming superiority and mismatching PostgreSQL physical DB, snapshot archive, and exported-data comparisons.
- Reviewed the local web UI surfaces: CPU/RAM are labeled unavailable at database scope; PostgreSQL is an explicit metadata-only read path, not a performance benchmark or provider comparison.
- No direct PostgreSQL/Supabase throughput, cost, storage-price, or customer workload benchmark was run.

## Limits and disposition

The README regression guard covers the public README's percent and direct-superiority patterns; it is not a legal review or a universal semantic classifier. The claim review does not establish price savings, provider advantage, customer workload performance, commercial rights, or release approval. R04-03 is scoped complete; overall official completion remains `UNASSESSED` / `RELEASE HOLD`; owner, physical, and commercial OWNER_GATE items stay open.
