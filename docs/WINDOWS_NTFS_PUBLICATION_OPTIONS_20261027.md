# DBVORA — Windows NTFS durable publication alternatives (2026-10-27 KST)

## Actual owner evidence
Private source SHA `a4044829ba1e109a58bae45a16cf884553b7cd34` was checked out on owner's Windows Python3.11 machine. `python -m scripts.verify_release_gate` returned FAIL_CLOSED (not a customer-ready pass):
- 223 discovered Python cases, nine skipped, unittest exit 1, up to 20 failing test IDs.
- synthetic real CLI: `CLI_PUBLISH_FAILED`, 0 checks.
- temp filesystem preflight: `PUBLISH_FAILED`.
- Node DOM: process exit 0, no recognized TAP counts.
- source checkout and compileall: PASS.

Read code: `safe_zip._sync_directory` expects POSIX-like directory `os.open` + `os.fsync`. On Windows, this may be unsupported. A Linux synthetic injected directory-open failure in the **exact Git blob** of `safe_zip.py` reproduced `PUBLISH_FAILED` while the original synthetic staging file remained and no archive was published. This supports the failure category, but is **not host-level proof** that Windows returned that exact OS error. Do not disable `_sync_directory` or mark archival durability proven.

## Architecture options before changing backup semantics
| Option | Product behavior | Runtime / money | Quality and constraints |
| --- | --- | --- | --- |
| **A. Retain fail-closed POSIX-only durability path** | On unsupported Windows filesystems refuse snapshot/archive writes; read-only metadata UI can remain available after separate checks | $0; smallest code/maintenance | Guarantees no false durable backup; Windows archive feature blocked, unsuitable final Windows backup product |
| **B. Explicit Windows-native create-only publication backend, strict safety gates** | Prototype Windows NTFS native handles/flush/atomic no-replace publish (Win32 operations under OS temp path), independently verify new data; select only if actual disk durability and crash-recovery tests pass | $0 external cost; high engineering/test overhead; Windows native validation necessary | Potentially permits genuine Windows functionality without weakening safeguards, but native metadata write-through semantics and power loss durability must be independently proven; do not claim them from API flags alone |
| C. WSL2/POSIX-only backup process, Windows read-only UI | Separate archive operation under WSL2 after user installation | $0 license, installation/operational burden | More moving parts and confused path/NTFS vs Linux filesystem semantics; requires additional validation |

**Recommendation B as a separately gated research/implementation branch or opt-in synthetic experiment, keeping current release path FAIL_CLOSED.** This changes a safety-critical filesystem publication implementation, so requires explicit owner approval prior to product activation or fallback policy changes. Until independently verified, don't enable archive writes in customer mode.

## Safe next work already done in feature branch
- Node runner now requests `--test-reporter=tap` explicitly; strict TAP requirement remains exactly one test, one pass, zero fail. Node v22.16 Linux real TAP smoke emitted the expected summary; actual owner's Node rerun pending.
- Python report includes fixed-format skipped test IDs, plus failing test IDs, without paths/reasons; **expected Python tests 225** (original 214 + 11 release gate regression additions; 25 gate test methods).
- Reporter/skip regex focused synthetic smoke passed locally, but exact full checked-in 25 module / Windows 225 suite NOT RUN after modification; customer readiness FALSE, six-stage PASS not claimed.

## Following checkpoint
1. Owner approval (only for safety-critical Windows publication design), then evaluate availability/behavior of Win32 directory flush and create-only atomic publication on a **synthetic OS temporary NTFS** folder.
2. Independently test create-once, no-overwrite, successful byte-exact restored content, forced API failure cleanup, concurrent creation, reboot/power interruption (no unsafe destructive shutdown on customer's machine), and errors fail-closed. If robust metadata durability cannot be proved, keep Windows archive unavailable.
3. Later run `git pull --ff-only` and a single owner Windows 225-case unified gate. Node should have TAP diagnostics; skipped test IDs will isolate OS permissions/optional dependencies.
4. Separate native `file://` UI, installer, authentication, customer DB and Production checks; do not promote main/develop without verified acceptance. No paid CI/public source/real DB/auto-delete.
