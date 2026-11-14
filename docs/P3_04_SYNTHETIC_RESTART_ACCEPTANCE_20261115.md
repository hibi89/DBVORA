# R03-04 — synthetic daily/weekly process-restart acceptance (2026-11-15 KST)

**Status:** PASS_SCOPED for GitHub-hosted synthetic process-restart behavior. This does not establish physical reboot, power-loss durability, or OS scheduler installation.

- Repository/branch: hibi89/DBVORA@feature/p0-db-map
- Functional source/test SHA: f844ce751ffd2d050f3fe1e8a62b699aa5959dc3
- New test: tests/test_daily_restart.py. Production runner code was already present and was not rewritten for this acceptance.
- Daily fault injection: the synthetic child process is terminated with exit code 86 immediately after reserving its UTC-day slot and before snapshot creation. A separate restarted CLI invocation for that same day returns HOLD and creates no artifact. The next UTC day can create a new snapshot/archive.
- Weekly behavior: separate CLI invocations in the same ISO week remain on the reserved slot; the following week gets a new slot and can create an archive.
- The synthetic SQLite source hash, size, and modification time remain unchanged. Ambiguous reserved slots remain held for manual review; there is no automatic retry or cleanup.
- Full release gate [#43612179872](https://github.com/hibi89/DBVORA/actions/runs/43612179872) completed successfully on this exact SHA: Ubuntu 744/744 PASS, 0 skips; Windows 743 PASS plus one named POSIX-only skip (test_review_html.ReviewHtmlTests.test_created_report_is_mode_0600_on_posix). Required gate steps passed.
- Blueprint gate [#43612180225](https://github.com/hibi89/DBVORA/actions/runs/43612180225) completed successfully on this exact SHA.
- No Chromium run was required for this CLI-only change. No real source DB, customer archive, scheduler, Windows user PC, physical reboot, or power-loss test was used.

This is scoped engineering evidence, not customer readiness. Physical restart/power-loss and owner acceptance remain OWNER_GATE. Overall official completion remains UNASSESSED and RELEASE HOLD.
