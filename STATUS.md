# DBVORA STATUS — P1-C1 ZIP/ZSTD comparison, 2026-10-26 KST

Repository: hibi89/DBVORA (PRIVATE). Work branch: feature/p0-db-map. Previous verified HEAD 078109b6f81128bd0484089bf134895745c1ab5e. **Actual new feature SHA must be re-read after committing; this document cannot contain its own commit SHA.** main/develop previous stable 890f842e3ba0e13c901e785633bdd06eadc76cce untouched.

| Capability | State | Evidence |
| --- | --- | --- |
| P0-01 SQLite metadata reader | TESTED_SYNTHETIC | prior unit tests retained |
| P0-02 localhost JSON + SVG map | HTTP_AND_DOM_TESTED | prior HTTP and Node DOM passed; actual browser E2E BLOCKED by managed policy |
| P1-C0 SQLite online backup + ZIP restore | TESTED_SYNTHETIC | SHA and integrity, failure-path coverage |
| P1-C1 optional official ZSTD CLI levels 1/3/9 | TESTED_SYNTHETIC_LINUX | bounded .dbvz envelope, checksum and independent SQLite restore |
| ZSTD corruption/manifest/disk output defense | TESTED_SYNTHETIC | 16 new tests; truncation, tamper, cap, symlink, missing codec, publish failure |
| Full Python tests | **62 PASS / 0 FAIL / 0 SKIP** | Linux Python 3.13.5 SQLite 3.46.1 |
| Node DOM/JS syntax | PASS_LOCAL | 1 DOM pass; node --check passed |
| Python wheel | PASS_LOCAL | ZIP and ZSTD code + web assets included, but ZSTD executable is external |
| 3-trial ZIP vs ZSTD synthetic benchmarks | MEASURED_LOCAL | two 565248-byte fixture snapshots, all restore SHA match; docs/P1_C1_BENCHMARK.md |
| Real browser/Windows/Python 3.11 | NOT_TESTED/BLOCKED | Chromium managed policy, no Windows device |
| Customer DB, high-load live WAL, power-fail restart | NOT_TESTED | no customer data/consent |
| GitHub Actions | NOT_RUN | local test only |
| Vercel/Production | NOT_APPLICABLE | offline local product |

Compression examples (single host, three-run median, archive metadata included): repetitive sample ZIP 3799 bytes vs ZSTD-3 1373 bytes; incompressible SQLite payload ZIP 528037 vs ZSTD-3 526749 bytes. **These are small synthetic data, not user savings/performance promises.** Command: python -m scripts.bench_codecs --trials 3.

Compatibility note: local official zstd CLI 1.5.7 available; pip Python zstandard installation attempted but public index inaccessible due DNS. The implementation uses the CLI with explicit no-shell subprocess, not a bundled Python wheel codec. On a machine lacking zstd CLI it fails safely as CODEC_UNAVAILABLE; ZIP baseline remains functional. ZSTD custom .dbvz is unencrypted and unsigned; checksums are not attack authentication.

Run: python -W error::ResourceWarning -m unittest discover -s tests -q; node --test tests/test_ui_dom.cjs; python -m scripts.bench_codecs --trials 3
Next: docs/NEXT_TASK.md P1-C2 durability/crash-recovery proof and Windows packaging feasibility. No actual customer DB modified or raw DB committed.
