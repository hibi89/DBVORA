# Synthetic-only daily/weekly UTC slot semantics, 2026-11-14

User blueprint requires periodic daily and weekly archiving. This is a no-cost **explicit invocation primitive**, not an installed OS scheduler, customer backup service, cron task, job runner or automated removal system.

Choice A: implement a separate weekly state machine, extra storage and crash/replay semantics. Higher maintenance and duplicate safety logic.
Choice B (selected): reuse proven existing daily one-shot reservation and fail-closed request ledger, with a canonical Monday UTC period key and a namespaced w- job ID. Different selected dates in the same ISO week share the same slot; cross-year weeks are based on the Monday date rather than the year number. Daily and weekly keys cannot collide. No new permissions, packages, background process, customer data or service are introduced.

Use python -m dbvora.archive.daily_synthetic --period weekly --source (ABSOLUTE SYNTHETIC SQLITE PATH) --snapshot-dir (EXISTING PATH) --archive-dir (EXISTING PATH) --ledger-dir (EXISTING PATH) --job-id demo01 --utc-day 2026-11-14 --synthetic-only --accept-plaintext . Do not run with customer data. The result includes period_start_utc, selected_utc_day, a new-only snapshot/archive and manual-review receipt. Re-running within that week is HELD, not silently retried.

The standard --period daily is unchanged. The CLI now fails closed with a fixed code for malformed arguments rather than echoing invalid flag values (which may be local paths). No real OS scheduler is installed; no automatic retention, deletion, customer data or power-loss guarantee is claimed. P100 UNASSESSED/RELEASE HOLD pending owner acceptance.

Test: python -m unittest -v tests.test_weekly_synthetic and full synthetic release gate on both Windows2025/Linux Ubuntu24.04.
