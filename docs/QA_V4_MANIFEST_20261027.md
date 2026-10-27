# DBVORA offline QA kit v4 — pinned source manifest

- Verified on 2026-10-27 KST against private `hibi89/DBVORA`, branch `feature/p0-db-map`.
- **Source-baseline commit:** `318a49e3031b9d0aa052221e35ebdebbec70dedd` (file pins remain applicable after documentation-only commits; live branch HEAD will advance).
- **QA kit local ZIP SHA-256:** `1bd7ef0c0ab433f0f7593947595ae4fc39a0b8d19e623c8278f6e8b12c053929`; **11,169 bytes**. This ZIP exists as a ChatGPT-generated conversation artifact, **not** in the GitHub repository or a permanent download host.
- **50 source/test/config blobs** pinned below using canonical Git blob SHA-1 values from the actual authenticated GitHub tree.
- Harness selftests **16/16 PASS** on Python 3.13.5, verified again after fresh extraction. Nonexistent input and stale `dbvora-dev-preview-0.2.0.zip` both produced nonzero `FAIL_CLOSED`, with no source execution.
- The kit uses no paid CI, internet upload, pip installation, customer files or original source mutation. It rejects unexpected active files, unsafe ZIP members, modified blobs, missing required files and insufficient Python test counts before claiming synthetic acceptance.
- This kit is **not** a source checkout and cannot run all **214** feature Python tests without a complete owner-authorized private GitHub source ZIP. A source ZIP's Git blob SHA-1 match is not a signed commit-attestation. Never claim customer readiness, Windows/NTFS durability, genuine browser file navigation or physical power-loss proof.
- Prior QA kit v3's obsolete `--patch-resize` has been retired: feature JS already carries the fix. The v4 default command is `py -3.11 run_dbvora_qa.py --zip "<owner-private-source-zip>" --report "<new-report-path>"`. Optional Chromium in-memory probe: `--browser`.
- **Current blocker:** container lacks authenticated private GitHub archive access, so the complete suite remains **NOT RUN**. A safe future route is owner-local source ZIP or a separate explicitly approved CI runner; both must preserve security/cost limits.

## Reviewed Git blobs (50 files)

```text
dbvora/__init__.py fe155fd8a31bef8f318b674b7b5d0f15e45a19c7
dbvora/__main__.py 555e1b6b3f112677295ba4ea2ba0c9eb37a974c5
dbvora/api.py 81338d4c4a64d2afa36e6619f39c469e0863289f
dbvora/archive_cli.py ccc965d7d62d268143f0c43e40e96bb10345d77e
dbvora/archive/__init__.py f68c3e061275f5802621deff0a7dc365e5ad2876
dbvora/archive/dedup_plan.py 51f3bcca0826f530712e7c9ac57040caae1e026b
dbvora/archive/receipts.py 82e5782001a407a111bb385c1782bbbcd4ef9f00
dbvora/archive/recovery_catalog.py 056abad676b13781778993a46c3ae7dd7da77660
dbvora/archive/safe_zip.py a58d2c3bfd3b95a98ada74f59e208b58e35d2e13
dbvora/archive/zstd_archive.py 94f638ce8a252f282229312d79dda95464b2a061
dbvora/connectors/__init__.py 92dcfba781a8770fe1080f5b1d5dae8984ae7850
dbvora/connectors/sqlite_reader.py 1d663d9d8243b75dbca0e697428870328bd87509
dbvora/errors.py 03649675b51aed9e7438072b26dd3411160c6695
dbvora/export_html.py ce0accd9939e7174c1cdee27a8ea9a2b4a953901
dbvora/inventory.py f40135add5cd8106b1ae722a0b799ec88a842cbd
dbvora/metrics.py 49c501398d1f63d98bfddd2109fc18f02045dd3d
dbvora/offline_selftest.py 290e1f61a8d87f130c662ac15d6582c150575835
dbvora/serve.py 75109db4c95c3ee155ef9f751998580d8324ce2f
dbvora/web/app.js c448d89782ef2ab5bd6440549365b7c9fda1739b
dbvora/web/index.html 16ddbbf4ef7144dec2c7428af71cec877a5e27b0
dbvora/web/style.css 4601a7cbdc0320e554cbf59966e3b99046b06483
pyproject.toml bc9dcba10199ab8a0cdd9e00afd0c3da4c13cfd3
scripts/bench_codecs.py 7198b88a65c302c6550b89cd9ac4f3e73e844158
scripts/browser_visual_probe.py 8ba1c985170e056991805c3a660483625fa9dbd3
scripts/build_portable.py 6eef2b5a9ba41d3b7f21d6c2a6c2f545a78cace2
scripts/offline_html_browser_probe.py 1bc43ccad0b371c2412af5d90e749be3c2d617dd
scripts/preflight_archiving.py cc66798c7fc91b10050fffe24e1601019190671e
scripts/synthetic_cli_gate.py e4d41c73b599300746136b5ed574e080781f4f1e
scripts/verify_release_gate.py fd8d39c29b73bdc96a7bd3fff45ad0646d651c21
scripts/windows_ntfs_gate.py 3efb32ab3a76fbdbb3e735de8929198620c0513b
tests/__init__.py e69de29bb2d1d6434b8b29ae775ad8c2e48c5391
tests/fixtures/__init__.py e69de29bb2d1d6434b8b29ae775ad8c2e48c5391
tests/fixtures/make_sqlite.py 7f407189ba98b70be22f52b7ca45b53c935f63e3
tests/test_api.py fb5719882d1cabe266b145afb69e130852b80f57
tests/test_archive_cli.py 7aefaab7c405c702ba2d476c7e9c1a9b35fd4afd
tests/test_audit_strict.py 31e62c0de1fc6598aa3bd77b4d0860bfab4b1a12
tests/test_dedup_plan.py 73e63048dd4a144d56cc62dca32638d7fd28e3e6
tests/test_durability.py 683e08918685f716905ee049805a93fabc1e1058
tests/test_export_html.py cb524f88f8a11f7cc25fe0e539f05c756c4d0563
tests/test_inventory.py 49b35d915432f8abce7903ceee9649f94c7f95e2
tests/test_offline_selftest.py f52b3bc90d58027cf7d0e3a8b5267c81f4d0ce2d
tests/test_portable_build.py 9b6568eea3574c06be0f743f4ab9f8f9e7d81a5d
tests/test_receipts.py c2c1757d5bf99d5665c7bad1e9f745914bf82eca
tests/test_recovery_catalog.py a30e1158d0d87e848800a3491ef57e4d28178e9b
tests/test_safe_zip.py d81c4756c0bddd0a3843ad27738a1423ff762b92
tests/test_synthetic_cli_gate.py a2bef5a06ae9f640dddaa4534374cabd901c4539
tests/test_ui_dom.cjs 88d0f6602116057c57db046b800c03a9ed706f83
tests/test_verify_release_gate.py c5aa98d938afe5058ab989197a772fbb34dd62f1
tests/test_windows_ntfs_gate.py e223acd69636a2acbf42ee287c539bea38a800f1
tests/test_zstd_archive.py 7404581469edfd23ca371846a514137d79bc3c63
```

## Acceptance rules

1. Confirm source ZIP came from the private repository and matches the 50 pinned blobs. Refuse to run any unreviewed executable ZIP member; never bypass pin failures.
2. Run Python `>=214` checked-in test cases, `python -m scripts.verify_release_gate` six-stage synthetic acceptance (real ZIP/ZSTD roundtrip, Node DOM and temporary FS preflight), and optional Chromium where supported.
3. Preserve original source ZIP unchanged and discard only the temporary test checkout. Final report remains `ready_for_customer_data=false` regardless of synthetic result.
4. Separately validate native Windows Python 3.11 NTFS durability and actual local `file://` opening before customer release.
