# DBVORA STATUS — P1-C4 receipt & unsigned lineage verified (2026-10-26 KST)

Private repo hibi89/DBVORA, work branch feature/p0-db-map. Previous remote HEAD 9649de10115e1204692ed7a870dc15153d309e2d. Confirm new HEAD from GitHub AFTER committing. main/develop stable at 890f842e3ba0e13c901e785633bdd06eadc76cce.

| Capability | State | Evidence |
| --- | --- | --- |
| P0 SQLite inventory + localhost map | SYNTHETIC_HTTP/DOM_PASS | Real browser E2E still BLOCKED_ENV |
| P1-C0 online SQLite backup and ZIP byte-exact restore | PASS_LOCAL | Existing tests retained |
| P1-C1 ZSTD CLI levels 1/3/9 + ZIP comparisons | PASS_LOCAL | ZSTD binary local Linux, not in wheel |
| P1-C2 fsync/exclusive new publication/failure cleanup | PASS_LOCAL | No power-cut proof, Windows not tested |
| P1-C3 independent read-only restart catalog | PASS_LOCAL | Verify original artifacts without modifying them |
| **P1-C4 receipts: exact file + parent SHA chain** | **PASS_LOCAL_SYNTHETIC** | New-only sidecar, independent restore and lineage verification, no auto-heal |
| P1-C4 receipt audit | **PASS_LOCAL_SYNTHETIC** | Missing receipt != success; corrupted parent/manifest/archive != success |
| Full Python automated tests | **125 PASS / 0 FAIL / 0 SKIP** | Previous 96 + 29 new, Linux Python 3.13.5, SQLite 3.46.1 |
| Node DOM, Python wheel, compileall | PASS_LOCAL | DOM 1/1, new receipt module packaged |
| 3-trial synthetic codec smoke | PASS_LOCAL | 2 datasets; all raw/ZIP/ZSTD restore hashes identical |
| Python 3.11/Windows/NTFS | NOT_TESTED | Local zstd not bundled |
| Sudden hardware power loss / authenticated provenance | NOT_PROVEN | Sidecars self-reported and unsigned |
| Customer DB/Production/GitHub Actions | NOT_TESTED | No customer files, no hosted deployment |

Invocation: python -W error::ResourceWarning -m unittest discover -s tests -q; python -m compileall -q dbvora tests scripts; node --test tests/test_ui_dom.cjs; python -m scripts.preflight_archiving; python -m scripts.bench_codecs --trials 3 --rows 16.

New files dbvora/archive/receipts.py, tests/test_receipts.py and docs/P1_C4_RECEIPTS.md. Receipt is a separate SHA-connected record, NOT encryption, signature, durable external evidence or ownership attestation. Missing receipt leaves artifact CONTENT_VERIFIED_PUBLISH_UNPROVEN until opt-in re-verification. No original archives overwritten/deleted, no customer data committed.

Next: docs/NEXT_TASK.md P1-C5 local CLI and Windows synthetic smoke / integration planning. Review and customer permission before any actual DB use, hosted deployment, deletion, payment or public distribution.
