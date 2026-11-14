# P3-A/B Two-generation, synthetic-only archive size measurement (2026-11-14)

This benchmark measures actual output file sizes on the SAME two SQLite snapshot generations. It is a **reproducible synthetic fixture only**, not an assertion of general compression superiority or cloud provider cost, CPU, storage IOPS, crash durability, or customer readiness.

Compare:
- **A (default)**: two independently restorable ZIP files using DBVORA's existing signed=false manifest+snapshot archive engine.
- **B (optional development)**: two independently restorable CAS manifests and immutable shared SHA-256 chunk files (64KiB fixed blocks); no automatic deletion, encryption, signature, or customer onboarding.

Run from a complete source checkout: \`python -m scripts.benchmark_synthetic_archives\`. The script creates its entire workload inside an OS-managed disposable temporary directory: 200 rows with invented 4KiB data and a changed row in generation 2, two SQLite online backups, ZIP archives, CAS manifests, independent ZIP and CAS restores (both generations), SHA256 checks, source metadata preservation. No external DB or network access.

The JSON fields \`two_zip_archives_bytes\` and \`cas_total_stored_bytes\` are **actual emitted files' byte sizes** for two generations; \`cas_minus_zip_bytes\` may be positive or negative. Compression performance is workload-dependent and may favor ZIP for compressible data. \`cas_second_new_content_bytes\` is the newly emitted chunk payload excluding manifest and filesystem metadata. Nothing about this test proves storage-cost superiority over Supabase/PostgreSQL.

The full release gate includes an additional mandatory \`synthetic_archive_size_comparison\` stage that requires both restore verifications, source unchanged, measured bytes and **no universal compression claim**. User Windows10/11 approval and actual multi-generation physical storage failure tests remain required for real backup products. Release HOLD.
