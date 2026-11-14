# DBVORA synthetic daily archive scheduling primitive (P3 step) — 2026-11-14

**Implemented vs NOT implemented**: This is one **opt-in daily-slot execution primitive** using the existing SQLite snapshot → ZIP/ZSTD → independent restore → reservation ledger. It does **not install or enable a scheduler**, delete old backups, perform incremental chunk storage, prove exactly-once crash durability, or accept customer data. User approval is required for an actual OS Task Scheduler/cron job.

## Two zero-cost designs
| Design | Performance & cost | Reliability and maintenance |
|---|---|---|
| A: embedded always-on Python daemon / timer | Free, but a background process consumes RAM/CPU and needs its own timezone/DST/process service UI | More restart/race/upgrade paths, harder to recover, risk of silent retry |
| **B: native Windows Task Scheduler / cron (not installed) calls one self-contained date-slot command** | Free, zero idle process, no server or new dependency | OS decides when to call; DBVORA uses deterministic UTC job/day key, ledger reservation **before** creating the first file. Ambiguous attempts remain held until owner review. |

**Chosen B**, code-only primitive at `dbvora/archive/daily_synthetic.py`. Running or installing scheduled jobs on a user PC is **not authorized automatically**.

## Synthetic-only invocation (never customer data)
Prepare four *different, existing, absolute, non-symlink directories*: an approved **synthetic SQLite** source, new snapshots, new archives and a ledger. Then run one explicit UTC slot:

```sh
python -m dbvora.archive.daily_synthetic \
  --source /abs/synthetic.sqlite \
  --snapshot-dir /abs/new-snapshots \
  --archive-dir /abs/new-archives \
  --ledger-dir /abs/new-ledger \
  --job-id synthetic01 \
  --utc-day 2026-11-14 \
  --codec zip \
  --synthetic-only --accept-plaintext
```

Returned status `RECORDED_UNVERIFIED_REQUIRES_OWNER_REVIEW` is **not customer-ready**, even after independent restored bytes match. Same UTC slot+job ID cannot run twice; a changed codec/destination with the same key yields `REQUEST_PLAN_CONFLICT`; a crash after reservation yields `DAILY_SLOT_HELD_FOR_MANUAL_REVIEW`. Never auto-delete or automatically retry. Manual audit by the owner is required for ambiguous remnants. The ledger, ZIP, and snapshots are **unencrypted** and must stay in trusted local directories.

### Test and stop conditions
- `python -m unittest -v tests.test_daily_synthetic`
- Both Windows2025 and Ubuntu24.04 full release gate exact SHA before changing status.
- Requires owner Windows10 QA, power-loss and storage exhaustion/locking stress, actual archive retention policy authorization and optional approved PG TLS before customer sales.
- Original source files, backups, ledger and any user data are never removed or overwritten by this primitive.
