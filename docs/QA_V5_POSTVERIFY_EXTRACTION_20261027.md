# DBVORA QA v5 — post-verification ZIP replacement guard

Updated: 2026-10-27 KST. Source repository: private `hibi89/DBVORA`, branch `feature/p0-db-map`.

## Purpose and finding

QA v4 validates pinned GitHub source blobs inside a proposed owner's private source ZIP, closes the archive and later reopens the original ZIP for extraction. An attacker/process with the ability to replace the ZIP at that boundary might substitute an unverified file between validation and execution. Existing ZIP member/CRC checks are not a substitute for checking content against the reviewed Git blob identities **again** at extraction.

The fix is confined to the **offline QA harness**, not the DBVORA product code or release gate:
- During copying each ZIP member to a disposable checkout, stream-compute a Git blob SHA-1 using the member's expected uncompressed byte length.
- For every source/config/test file in the 50-path trusted pinned manifest, verify that the just-extracted bytes match the reviewed Git blob ID. Reject unexpectedly short/long content and changed ZIP metadata/read failures with fixed, path-free `ZIP_CHANGED_AFTER_VERIFICATION`.
- No executable process is started until all extraction and the post-extraction checks have finished. Original source ZIP stays unchanged by the harness. Ignore no mismatches and never auto-repin.
- The ZIP contents must still satisfy the existing preflight filename, size, traversal, symlink, duplicate and SHA pin checks.

## Tested evidence

- Python 3.13.5, local offline `python -W error::ResourceWarning -m unittest -q test_runner test_source_pinning`: **19/19 PASS**, 0 FAIL/SKIP; Python compileall PASS.
- Additional security regressions: a same-length ZIP swapped immediately after a successful preflight fails closed and the mocked process executor is never called; standalone extraction of a changed same-length ZIP fails; an unmodified pinned ZIP extracts byte-exact output.
- The QA v5 archive was extracted to a new OS temporary directory and all **19/19 tests** passed again.
- Inputs missing or from the outdated developer source preview were rejected nonzero.
- Current GitHub baseline used for 50 pinned executable/config blobs remains source commit `318a49e3031b9d0aa052221e35ebdebbec70dedd`. Later **documentation-only** HEAD advances do not change those blobs.
- Independently re-ran current GitHub-blob-matching four-file offline synthetic QA focus: `tests.test_audit_strict` + `tests.test_verify_release_gate` **18/18 Python PASS** on local complete dependencies for those modules. This is **NOT** the entire DBVORA 214-test release gate.

## Output and limitations

- Local ChatGPT conversation artifact `DBVORA_full_source_QA_kit_v5_20261027.zip`, **10,770 bytes**, SHA-256 `701a6c8f5bc146fc6a6517cea9f1c4dbe3610efe1cf54ba667031b0ab94cca4b`.
- It contains exactly 5 files: `README.txt`, `pinned_git_blobs.txt`, `run_dbvora_qa.py`, `test_runner.py`, `test_source_pinning.py`. It contains no private DBVORA product source, customer DB, credentials or paid CI trigger. The ZIP is an ephemeral conversation attachment, not hosted in this GitHub repo.
- No GitHub source/archive ZIP can be cloned from this execution container: unauthenticated API/raw hostname resolution failed and the private complete branch ZIP is unavailable. Accordingly **the full 214 checked-in Python tests and six-stage unified ZIP/ZSTD/Node release gate remain NOT RUN at the current feature SHA**. Windows3.11/NTFS durability, real file:// browser navigation, hardware power cut and customer safety are also NOT VERIFIED.
- Review and failure criteria for the full source ZIP remain in `docs/QA_V4_MANIFEST_20261027.md`. Native GitHub CLI/CI execution needs authorized access and any paid CI/public source, customer or destructive action needs separate approval.

## Next

Provide an owner-authorized complete private source archive to the same offline runner, check all 50 Git blobs against trusted pins, run all >=214 current Python tests and `python -m scripts.verify_release_gate`. Address genuine failures and run native Windows3.11/NTFS + browser validation before release. Do not treat 19 harness selftests as product acceptance.
