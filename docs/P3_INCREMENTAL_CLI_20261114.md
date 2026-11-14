# DBVORA incremental standalone CLI acceptance — 2026-11-14 KST

Scope: **synthetic-only**, no customer database or server access, no automatic schedule, no deletion, no signed manifest, no at-rest encryption. New CLI \`python -m dbvora.incremental_cli\` exposes the previously isolated content-addressed engine for independently inspectable execution, with explicit acknowledgments.

## Safe one-time operator workflow
1. Use DBVORA's existing verified **synthetic** \`dbvora-<32hex>.sqlite\` snapshot inside a distinct snapshot directory. Prepare *three further different* existing absolute directories for \`chunks\`, \`manifests\`, and \`restored\`.
2. Execute \`python -m dbvora.incremental_cli create --snapshot <absolute-synthetic-snapshot> --chunk-dir <absolute-chunks> --manifest-dir <absolute-manifests> --synthetic-only --accept-plaintext\`.
3. Independently execute \`python -m dbvora.incremental_cli restore --manifest <absolute-manifest-json> --chunk-dir <absolute-chunks> --output-dir <absolute-restored> --synthetic-only --accept-plaintext\`.
4. Outputs only nonsecret status, digest, filenames, new/reused block counts. The restore validates **each chunk's bytes**, full SHA-256 and SQLite integrity, then only creates a new destination file.
5. Test with \`python -m scripts.incremental_cli_gate\`. It repeats the first snapshot, independently restores it, rejects missing acknowledgment, tampers a chunk, and checks all old bytes/source hash remain untouched; **test tampering happens only inside a disposable temporary test directory**.

## A/B alternative
A. ZIP/ZSTD generation per snapshot, verified full restore, simplest recovery and existing release default. B. New manifest+64KiB immutable SHA-256 content store. Reuses identical blocks across snapshots but adds manifest/reference retention complexity. Choose **B for synthetic preview and verified storage efficiency measurement only**, keep A as safety fallback. No deletion of chunks/manifest generations is allowed; garbage collection requires owner risk approval plus physical power-loss and customer restore drills.

## Release gates
- Cross-platform Windows2025 and Ubuntu24.04 full suite at the exact source SHA.
- Full gate must include \`synthetic_incremental_cli_roundtrip\` as an additional **mandatory** stage, not only module tests.
- Owner Windows10/11 and real interruptions, encryption, licensed packaging, customer acceptance still pending. 0원, \`[작업중]\`, official UNASSESSED, RELEASE HOLD.

## 2026-11-14 compressed v2 CLI extension
The original CLI create/restore defaults to raw v1 and is backward compatible. Explicit --format zlib selects independent versioned compressed CAS v2 and requires separate .cz chunk and manifest directories. No implicit auto-detection or conversion of v1 data. Real subprocess gate now checks both raw and compressed create/repeat/reuse/independent restore, explicit wrong-format rejection, tamper denial and source preservation, all in temporary synthetic-only directories. No customer DB or installer/retention operation is authorized. Full Windows/Linux exact-SHA gate remains mandatory.
