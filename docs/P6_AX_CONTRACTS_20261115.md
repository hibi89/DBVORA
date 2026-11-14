# R06 AX metadata contract acceptance — 2026-11-15

**Functional source/test SHA:** `3fd075226ef5c7e4aa1d66d3392c627315fd5cbc`  
**Result:** R06-01 and R06-02 PASS_SCOPED for the local synthetic contract boundary. No HAE/LA package or external service was installed or contacted.

## Published contracts

The `contracts/` directory now documents JSON Schema 2020-12 shapes for:

- `p0-01.v1`: one selected SQLite inventory.
- `p0-03.workspace.v1`: two to eight selected SQLite databases, explicit declared links, and unverified cross-database relationship scope.
- `dbvora.pg_catalog.v1` and `dbvora.pg_statistics.v1`: PostgreSQL catalog metadata and lag-prone estimates.
- `dbvora.local-table-storage.v1` and `dbvora.local-observation.v1`: optional bounded storage measurement and explicitly recorded local observations.
- `dbvora.multi_engine_offline.v1`: normalized offline SQLite/PostgreSQL metadata.
- `dbvora-error-v1`: stable path-free `{error: {code, message}}` response.

The contracts describe metadata and provenance; no database rows, DSNs, credentials, or tokens are part of the supported payloads. Unknown versions are rejected by the mock consumers. The error envelope maps to an unavailable state. PostgreSQL estimates are labeled as estimates and may lag.

## R06 task evidence

| ID | Result | Evidence | Limits |
| --- | --- | --- | --- |
| R06-01 | PASS_SCOPED | Versioned schemas cover all current versioned local API payloads and the offline mixed-engine report. `tests/test_ax_contract.py` validates synthetic single/multi SQLite API, PostgreSQL catalog/statistics route shapes, table-storage, observation ledger, mixed offline output, and path-free errors. | Schema coverage establishes payload shape and provenance only; it is not an external AX authorization or security certification. |
| R06-02 | PASS_SCOPED | `MockHAEConsumer` and `MockLAConsumer` run without external packages, validate `p0-01.v1` / `p0-03.workspace.v1`, reject `p0-03.workspace.v999`, isolate errors, and verify PostgreSQL stays disabled when no DSN is configured. Unsupported mixed-report version rejection is covered in `tests/test_multi_engine_report.py`. | These are mock consumers, not actual HAE/LA integrations. No external network is used by the tests. |
| R06-03 | OWNER_SCOPE_GATE | Kept as specified in the P100 plan. | Actual HAE/LA/SOVIA integration is outside the initial required scope absent an owner-approved expansion. |

## Exact-SHA verification

- Full Ubuntu/Windows release gate [#43636834475](https://github.com/hibi89/DBVORA/actions/runs/43636834475) PASS: 773 tests discovered on each OS (Ubuntu 773 PASS/0 skip; Windows 772 PASS + one named POSIX-only skip); all gate steps passed.
- Chromium HTTP/browser [#43636834445](https://github.com/hibi89/DBVORA/actions/runs/43636834445) PASS: 33 checks on each OS.
- Synthetic PostgreSQL 16 TLS/UI [#43636834428](https://github.com/hibi89/DBVORA/actions/runs/43636834428) PASS.
- Final blueprint evidence gate [#43636834707](https://github.com/hibi89/DBVORA/actions/runs/43636834707) PASS.

Next planned work is R07-01: verify that current Windows source ZIP/EXE artifacts include and identify the latest feature SHA, while preserving the existing OWNER_GATE for owner-device acceptance and commercial approval. Overall completion remains UNASSESSED / RELEASE HOLD.
