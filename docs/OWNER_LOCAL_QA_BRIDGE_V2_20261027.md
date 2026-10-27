# DBVORA owner-local QA v2 — ZIP byte mismatch recovery (2026-10-27 KST)

## Confirmed owner Windows observation
- Owner ran v1 on Windows Python 3.11 with authenticated private GitHub clone.
- Git HEAD `d87c8d5f072df73bcfb60f09ec41395b59a30d20`, **50/50 Git tree source blobs verified**.
- Original v1 ZIP SHA-256 `2b0be7c29da854afbbf476639651403b55232facc40efe97f143c4d0e214dddc`, produced from `git archive --format=zip --prefix=dbvora-source/`.
- Bundled QA v6 failed **before code execution**: `SOURCE_BLOB_MISMATCH`, `source_blobs_pinned_sha1_verified=false`, empty QA steps. This is a ZIP transport/bytes mismatch, not evidence of failing product tests.
- Exact per-file mismatch cause is **not yet proven**. Git archive attribute substitution is one plausible class; no claim it happened here. Do not weaken pins or retry the same v1 path.

## Alternatives and decision
- A: diagnose and continue using `git archive`: negligible compute/cost, but owner archive already failed and cause not isolated.
- B **selected**: use authenticated Git object blobs directly via `git cat-file blob <sha>` and Python `zipfile`. This bypasses export substitutions, validates all blob SHA-1 before packaging, and independently validates each packed blob afterward. Retains QA v6 unmodified, 50 pinned blobs and fail-closed rules; no extra services or paid CI.
- Existing v1 ZIP/report and source stay unchanged. Generated v2 names never overwrite v1 files.

## v2 evidence and artifact
- Standalone temporary conversation ZIP **`DBVORA_owner_private_verify_v2_20261027.zip`**: **17,768 bytes**, SHA-256 `54c17ffdb65c3d48488770419f6131c2ad5ae548fb5f7f19d991dda3d0c9a03e`.
- Contains bridge v2 source, README, six synthetic tests and original QA v6. **No private DBVORA source, credentials, customer files or original backups** included.
- Linux Python v2 synthetic isolated tests **6/6 PASS** (raw object roundtrip, overwrite refusal, bad pin rejection, symlink refusal, local export-subst example, and 50-fake-blob end-to-end QA transport that reaches `archive_structure=PASS` then correctly fails missing real tests). QA v6 isolated tests **19/19 PASS**, freshly extracted package repeated **25/25 PASS**.
- This does **NOT** establish owner Windows v2 behavior or all 214 Python product tests. v1 owner result is actual Windows evidence, not full release acceptance.

## Next action on authorized owner PC
Extract v2 to new directory (do not merge with v1), run:
```powershell
py -3.11 verify_private_source_v2.py --clone --qa-kit qa_v6 --output .
```
Then inspect sanitized `DBVORA_QA_v2_<sha12>.json`. If it passes initial source verification, inspect unit/release gate outcomes and repair actual failures; if it fails, record exact stable error_code and stop rather than repeating identical command.
- Entire **214 Python tests, ZIP/ZSTD roundtrip, Node DOM, six-stage release gate and actual Windows NTFS/fsync/browser navigation** are not yet proven by this v2 package. The QA full gate may validate a subset on Windows once executed; no customer readiness even on host synthetic pass.
- `main` and `develop` stay untouched; feature product code not changed; Vercel/Production N/A.
