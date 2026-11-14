# R03-05/R03-06 — concurrency and interruption recovery acceptance (2026-11-15 KST)

**Status: PASS_SCOPED** for synthetic GitHub-hosted process and file fault injection. This does not prove physical power-loss durability or actual full-disk behavior.

- Final source/test SHA: 653722bee4ac595220cc9c8d44459ce9b1e1ee33
- Full release gate [#43616426097](https://github.com/hibi89/DBVORA/actions/runs/43616426097) PASS: Ubuntu 750/750, 0 skips; Windows 750 PASS, 1 named POSIX-only skip (test_review_html.ReviewHtmlTests.test_created_report_is_mode_0600_on_posix). Required gates pass.
- Blueprint gate [#43616426451](https://github.com/hibi89/DBVORA/actions/runs/43616426451) PASS at the same SHA.

## R03-05 concurrency
- tests/test_request_ledger.py: four spawned processes reserve one synthetic request; exactly one gets RESERVED_NOT_EXECUTED and three get REPLAY_REQUIRES_MANUAL_REVIEW. The shared ledger contains one request row for that request.
- tests/test_request_service.py: three spawned processes call archive_once for the same synthetic request; exactly one ZIP is published and recorded, while two receive REQUEST_REPLAY_HELD. The source DB and snapshot bytes remain unchanged.
- tests/test_cas_concurrency.py: three spawned processes restore the same compressed-CAS manifest concurrently; each produces a distinct new file with matching SHA-256 and SQLite integrity. The manifest and source DB remain unchanged, with no staged files left behind.
- Existing thread-level CAS writer collision, simultaneous restore, and request replay tests remain in the same regression suite.

## R03-06 interruption and write failure
- tests/test_cas_partial_write.py injects short chunk/manifest writes and a false full-length write claim. No partial manifest is promoted; a previous generation remains independently restorable.
- tests/test_compressed_cas_failures.py injects ENOSPC at chunk publication, new-generation publication, and restore publication. Existing good manifests/restores remain unchanged.
- tests/test_cas_abrupt_exit.py and tests/test_cas_abrupt_process.py exercise spawned child process termination while staging or before publication. The last good generation remains restorable and source hashes remain stable.
- tests/test_durability.py exercises orphan inventory and process exit during a staged publication. Cleanup is either manual and explicit or not performed.

One R03-05 test attempt at SHA 5b15b9a failed because test code hard-coded a wrong ledger filename; [#43615599456](https://github.com/hibi89/DBVORA/actions/runs/43615599456) records the failure. The test now imports the canonical LEDGER_NAME, and the full final SHA suite passes. No production failure was indicated by that test-only defect.

No user DB, customer archive, local PC, OS scheduler, actual full disk, physical power cut, or real-world restore was used. R03-10 and real-device/owner acceptance remain OWNER_GATE. Overall completion stays UNASSESSED / RELEASE HOLD.
