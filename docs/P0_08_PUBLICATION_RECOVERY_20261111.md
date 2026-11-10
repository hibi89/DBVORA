# DBVORA P0-08 — Offline workspace publication cleanup (2026-11-11 KST)

## Scope and design choice
Two designs were considered: (A) narrow generated-file cleanup around current HTML+observation writes, and (B) a new directory-wide transactional publisher. A was selected for no new runtime dependency, near-zero resource overhead, smaller regression surface and predictable maintenance. B would still need platform-specific crash and directory-metadata durability tests. This patch makes **no power-loss atomicity claim**.

## Observed code risk and implementation
Before the patch, `export_workspace(..., save_observation=True)` could leave a created HTML file when the later observation JSON write raised `ObservationError`. `write_observation` could also leave a partially written JSON file if its fsync/write failed.

- `dbvora/publication_cleanup.py`: best-effort cleanup by exact generated basename, regular-file check, device/inode identity captured from the owned file descriptor, and no symlink following. On uncertainty the file is retained instead of deleting a replacement.
- `dbvora/workspace_html.py`: closes the newly created HTML descriptor and attempts safe cleanup after HTML write failure or subsequent observation failure.
- `dbvora/workspace_observations.py`: closes the JSON descriptor and attempts safe cleanup after failed JSON write/fsync.
- Two new unittest modules: 7 standalone cleanup cases and 5 SQLite/export integration/failure cases; no customer data, network, scheduled work, overwrite or new dependencies.
- `scripts/verify_release_gate.py` now requires the three new source/test files and raises its Python discovery minimum from 324 to **336**; `tests/test_verify_release_gate.py` mocked fixtures updated to the same floor.

## Evidence and limitations
- Helper module exact Git blob SHA `060b48cde0b1cdd5ddd8bc3559ae48cfa6caa210` matched `git hash-object` of developer-tested Python file.
- Isolated Linux local helper behavior: **7/7 PASS**, 0 FAIL; Python compile checks passed. This does **not** verify full repository or integration tests.
- New full-source SQLite publication tests (5) and existing entire >=336 unittest regression, Node DOM, Windows Python3.11, native browser, power-cut durability and release gate are **NOT RUN** because the private full checkout is unavailable to the execution environment. No GitHub Actions billed or triggered.
- Current validation is bounded and not proof of atomic dual-file publication under abrupt power cut or adversarial races between lstat/unlink. The cleanup deliberately fails closed if file identity is uncertain.
- No original archives, customer DBs or existing files were modified by tests; previous code remains recoverable from Git parent commits. Product commercial completion **55% unchanged**, RELEASE HOLD.

## Next gate
1. On an authorized complete feature checkout, run `python -B -m unittest -v tests.test_publication_cleanup tests.test_workspace_publication tests.test_workspace_storage`, then `python -m scripts.verify_release_gate` and inspect any failures.
2. Verify Windows Python3.11 native fsync/failure-path behavior, and check that no generated file is left after injected failures. Do not claim power-loss atomicity.
3. Continue a measured, read-only PostgreSQL connector option and user-visible DB observability only after the above focused regression; do not connect to customer DB without separate approval.
4. Keep 55% until integrated evidence and substantive product-scope acceptance justify a new estimate.

Execution source: `hibi89/DBVORA@feature/p0-db-map`, source commits `0518269d8b1686f4dae686ebaec358eca41a4a7d` and `9d1d4b0898c5293f34f01feff4894c5ed97aabb1`. Documentation/gate follow-up SHA is the parent of the next development step, to verify after push.
