# DBVORA — MVP-first implementation versus original design (2026-10-27 KST)

## Development execution order
1. **MVP first:** reproducible single-SQLite read-only structural inspection and clickable/offline HTML with a zero-input synthetic demo; local CLI where available. Do not present packaging or customer-ready backups as completed.
2. **Compare with original requirements:** extend the working MVP progressively toward multi-DB topology, DB-specific measured storage/resource display and lossless archiving. Ship code/tests in independent reversible increments; preserve working paths.
3. **Hardening and release:** after functionality, complete Python3.11/Windows, actual browser, recovery failure injection, power-loss/durability and security. The minimum integrity/non-destructiveness guarantees still apply **from day one**, not deferred.

## Two MVP delivery approaches
| Criterion | A: Python3.11 read-only SQLite and single HTML export (selected) | B: FastAPI service and Windows archive backend as mandatory MVP |
| --- | --- | --- |
| Setup/time | One command, Python stdlib; fastest demonstrable UI | Requires local dependencies and risky Windows FS publication |
| Extra cash | $0 | $0 possible but build/test complexity much higher |
| Stability | Private, offline, no server and no backup writes; rollback trivial | Broader surface, Windows fsync gate currently blocks archive |
| Scope trade-off | Single DB preview, no real customer use or backup | Closer to final product but hard to safely certify |
| Follow-up | Add locally served UI, measured per-table costs, multi-DB, archiving after evidence | Would push demonstrable MVP behind Windows durability research |

**Decision:** Finish and verify A as the P0 visual MVP, then gap-close requirements. Keep P1 ZIP/ZSTD recovery research isolated; no safety flag bypass.

## Original user requirements versus current source
| Requirement | Verified implementation evidence | Gap / next actionable work | MVP classification |
| --- | --- | --- | --- |
| DB -> table -> column/PK/index/FK navigation | `dbvora/inventory.py`, `dbvora/web`, `dbvora/export_html.py`; prior synthetic HTML/DOM tests | Current full SHA checkout & native browser with screenshot/interaction | CODED, FULL GATE PENDING |
| Zero-external-dependency demo | New `dbvora/demo_preview.py` creates only synthetic temp SQLite and export to user-selected existing folder; six tests | Real exporter end-to-end on complete checkout; actual Windows file:// | CODED, ISOLATED SMOKE ONLY |
| Whole database/service architecture map, multiple connections | Current P0 is one SQLite file and verified FK graph only | Multi-database top-level registry and user-declared evidence-based links | NOT IMPLEMENTED |
| Storage/resource usage with correct measurement scope | `dbvora/metrics.py` measures main SQLite file; unknown CPU/RAM not fabricated | Measured table-level size only where SQLite dbstat is available; measured process/storage trends where supported; label WAL excluded | PARTIAL |
| Lossless snapshot, archive, restore | `safe_zip.py`, `zstd_archive.py`, CLI and receipts; prior Linux synthetic evidence | Independent complete checkout, native NTFS safety and physical durability policy | CODED, WINDOWS ARCHIVE BLOCKED |
| Compression efficiency against ZIP | Synthetic benchmarks with limited fixtures and measurement | Repeat on independent larger workloads/space/CPU/RAM, no universal claim | PARTIAL |
| Chunk dedup and incrementals | Dedup estimator only, no protected chunk store or restore chain | Implement after safe full backups and orphan/parent handling | NOT IMPLEMENTED |
| Scheduling and resource-aware retention | No verified production scheduler | Idempotency ledger, resume/crash recovery, no auto-delete without approval | NOT IMPLEMENTED |
| Windows installer / product readiness | Portable developer source ZIP and HTML exporter exist | Native installer, customer consent, accessibility, browser/runtime, backup and real power-cut review | NOT READY |
| Private/no paid network | Local-only design, GitHub Private | Audit packaging/licenses/logs/telemetry before sale | DESIGN APPLIES |

## New P0 demo scope and acceptance
- Command: `py -3.11 -B -m dbvora.demo_preview --synthetic-only --out <existing absolute folder>` from checkout.
- Generated database: departments/employees, FK, index, a row canary. SQLite temporary file is deleted; only the exported HTML remains. No customer path, HTTP connection, external API or automatic backup writes.
- Generated HTML must include schema metadata, not the row canary, and preserve SHA256/size reported by existing exporter; target filename must be new UUID pattern. Relative output, invalid filename or unexpected export results fail closed; public error codes never echo private paths.
- Tests: `tests.test_demo_preview` six cases, real integrated exporter used in committed test; on current developer container, **only isolated 6/6 smoke with a stand-in exporter** was run. No real full Git checkout run. Release gate minimum from 248 to **254**; count increase is not proof of passing all cases.
- No package installation, customer DB use, CI runner billing, repository visibility changes or production route changes authorized.

## Next unblocked sequence
1. Reconstruct/pin a complete current feature checkout in an authorized execution environment and run `python -m unittest -q tests.test_demo_preview tests.test_export_html tests.test_offline_selftest`, then `python -m dbvora.offline_selftest` and synthetic demo in an existing temp directory. Inspect generated HTML/browser when permitted.
2. Implement the first missing high-impact original feature **multi-DB topology metadata** using synthetic opt-in configurations, retaining explicit source/evidence for every edge and no implicit cross-DB relationship guessing.
3. Once P0 visuals are reliable, return to complete Windows NTFS ZIP/ZSTD backup safety and end-to-end durability; original archiver remains fail-closed until validated.
4. Full `>=254` Python tests, Node/browser, Windows data safety, recovery and packaging before customer or commercial use.

## Environment/provenance
- Private `hibi89/DBVORA`, branch `feature/p0-db-map`; inspected parent `93945ffc72e1dd6c22ac3bc80c005752b6d9de93`.
- Isolated test workspace Python3.13.5 6/6 PASS with a mock HTML renderer; real source exporter integration was **not executed** in that workspace. Both new source blobs locally Git SHA1 checked before commit.
- Current Windows owner proof remains prior NTFS **15/15 twice**, not this demo's native browser. Vercel/Production N/A. Native consumer/customer readiness **UNVERIFIED**.
