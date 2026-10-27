# DBVORA Windows first complete-gate output and diagnostic hardening — 2026-10-27 KST

## Real owner evidence
Owner on an existing authenticated Windows/Python3.11 Git checkout ran `py -3.11 -B -m scripts.verify_release_gate` at feature commit `a867f744a41ce2f561cebba31b38691e37d90bab`. The previous Python CP949 `UnicodeDecodeError` did not recur. Gate returned:
- checkout: **PASS**
- python_unittest: **FAIL**, **218 discovered**, **0 reported skipped** but skip identity false. **NOT 218 passed**.
- real_cli_roundtrip: **FAIL**, 0 checks, ZSTD failed/unknown
- compileall: **PASS**
- node_dom: **FAIL**
- filesystem_preflight: **FAIL**
- Overall **FAIL_CLOSED**, `ready_for_customer_data=false`. This is not proof that all four subcomponents have independent product defects. The original gate omitted subprocess return codes, test failure names and published archive failure codes, so the exact failure set cannot be established from the original JSON.

## Suspected shared Windows blocker (code-grounded, not host-proven)
In `dbvora/archive/safe_zip.py`, `_sync_directory` calls `os.open(directory, ...)` then `os.fsync(fd)`, otherwise raises `DURABILITY_UNAVAILABLE`. `_publish_new` wraps failed publish in `PUBLISH_FAILED`. This POSIX-style directory fsync may be unsupported on Windows/NTFS; it could cause archive snapshot, ZIP restore and filesystem preflight to **fail closed correctly**. No fsync bypass or success simulation is allowed. The Node failure is independent and remains UNKNOWN pending TAP numbers; Python failure names remain UNKNOWN pending diagnostic report.

## Options compared
- A. Ask owner to run five commands and share raw stderr: no code effort but repeated user handling and risk disclosing absolute local paths. Rejected.
- B. **Selected:** preserve existing six-stage fail-closed gate; append bounded diagnostic fields directly to JSON (only stable test IDs, fixed-form error codes, process exit codes and numeric Node TAP totals). No raw traceback or path. Owner still runs **one command** using existing Git checkout. Cheapest, privacy-preserving and actionable.

## Changes
- `scripts/verify_release_gate.py`: minimum Python cases **223** (= original 214 plus 4 strict UTF-8 and 5 new diagnostic regressions); bounded unittest failing test IDs (max 20), failed suite skip-summary parsing, per-step subprocess exit code; CLI fixed error code; Node TAP counts and fixed reason; file publish fixed reason. All error codes validated against `[A-Z][A-Z0-9_]{0,63}`. Original pass requirements are unchanged.
- `tests/test_verify_release_gate.py`: 23 gate tests total; new 5 tests cover unsuccessful Python failure IDs and skip summary, fixed CLI failure code, unsafe string redaction, Node TAP counters, and filesystem publish error code.
- Targeted isolated Python3 sanity checks of the **diagnostic parsing expressions** passed: unittest failed name, skipped summary, TAP counts, accepted fixed code and rejected path-shaped code. These do not substitute for running all 23 checked-in regression tests or all 223 product tests.

## Next owner action
In existing `E:\DBVORA_GIT`, assuming clean repository and Git authentication already verified:
```powershell
cd E:\DBVORA_GIT
git status --short
git pull --ff-only
if ($LASTEXITCODE -eq 0) { py -3.11 -B -m scripts.verify_release_gate }
```
Share the single generated **sanitized JSON** output. Do not share raw test logs or customer data.
- The Python suite and synthetic archive may still FAIL on Windows by intentional durability safeguards. Diagnose exact fixed codes before any Windows-specific durable publish design or storage-engine modifications. Windows3.11/NTFS native filesystem behavior and real `file://` GUI require distinct verification. No customer DB, public release, paid CI, `main/develop` promotion, original backup deletion or weakened fsync.
