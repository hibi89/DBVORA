# DBVORA Windows 3.11 / NTFS synthetic gate — 2026-10-26 KST

## Purpose
Provide an **offline**, fail-closed compatibility checkpoint before considering Windows backup and restore ready. The gate only uses generated OS temporary files and synthetic SQLite fixtures. It does not select, inspect, export, modify, or upload a customer's database. **A real Windows system was NOT available in this session and was NOT tested.**

## From an authorized complete private checkout
Using Windows and Python **3.11**, with Node installed and optional local ZSTD executable installed:

```powershell
py -3.11 -B -m scripts.windows_ntfs_gate
```

A single JSON result is printed, with `ready_for_customer_data=false` and `hardware_power_loss_verified=false` under every outcome. The process exits nonzero unless all gates pass:
1. Actual Windows OS, **Python 3.11**.
2. Windows API `GetVolumeInformationW` reports **NTFS** for the OS temporary drive only; no customer path is queried.
3. Existing `scripts.preflight_archiving.probe()` safely tests publish on an isolated temporary filesystem. Require `archive_publish_test=passed_on_temporary_filesystem` and no customer-ready/external-write flags.
4. Only after step 3 succeeds, run `scripts.verify_release_gate.verify()` and require all six PASS steps: >=**167** actual Python regression cases, actual synthetic ZIP/ZSTD+Receipt+restore+audit, Python compileall, Node DOM 1/1, source files and separate temp filesystem preflight.

Fixed failure codes include `WINDOWS_HOST_REQUIRED`, `PYTHON_3_11_REQUIRED`, `NTFS_TEMP_VOLUME_REQUIRED`, `DURABILITY_NOT_PROVEN_FAIL_CLOSED` and `REGRESSION_OR_SYNTHETIC_GATE_FAILED`. No path or raw exception is returned.

## Durability risk, not a certification
The current `dbvora.archive.safe_zip._sync_directory` is POSIX-oriented: opens a directory and fsyncs the descriptor. Python Windows fsync maps to CRT `_commit`; Windows directory handles use Win32 APIs and cannot be assumed interchangeable. We intentionally **do not bypass/skip** directory fsync on Windows. If preflight fails, the tool explicitly refuses to certify archive publishing; no customer data may be used.

References: https://docs.python.org/3/library/os.html#os.fsync ; https://learn.microsoft.com/en-us/windows/win32/fileio/obtaining-a-handle-to-a-directory ; https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-flushfilebuffers

## Executed evidence vs untested
- New tests `tests/test_windows_ntfs_gate.py` **11/11 PASS**, using platform-independent injected decision results on Linux Python3.13.5. Includes wrong OS/Python/FS, durability failure, false or incomplete report rejection, exception sanitization and success explicitly denying customer/hardware durability approval.
- Full Linux `python -m scripts.verify_release_gate`: **167/167 Python regressions PASS**, 0 failures/skips; real synthetic CLI 8/8, ZSTD passed, Python syntax, Node DOM 1/1 and temporary publish preflight PASS. All six gate steps PASS.
- Running `python -m scripts.windows_ntfs_gate` on this Linux runtime returned `BLOCKED_UNVERIFIED / WINDOWS_HOST_REQUIRED`, exit 1, **as intended**.
- Git blob SHA IDs for the four changed/added files were compared to the locally executed sources and match exactly. No GitHub Actions used, no paid CI, no Production.
- Actual Windows3.11/NTFS, physical power interruption, GUI browser/installer, secrets/customer data remain NOT_TESTED. Do not call the Windows product ready until tested on an authorized native host.

## Next
Execute the command above on authorized Windows3.11 NTFS. If durability is blocked, design and validate a genuine Windows-specific safe new-name publish/rollback mechanism with independent restore tests; never treat a skipped flush as PASS. After that, run a real browser test and packaging/installer validation. Explicit approval required before customer DB, destructive changes, Public source distribution or paid CI.
