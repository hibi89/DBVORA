# Windows core-only signed-status disclaimer / synthetic EXE plan (2026-11-14)

**No customer readiness claim.** The GitHub Actions standard Windows runner builds `DBVORA-SYNTHETIC-OWNER-PREVIEW.exe` with PyInstaller and executes it with a temporary in-memory/synthetic SQLite fixture. It generates only a new read-only offline HTML structure map. No source/database path can be supplied through this entrypoint. No real customer DB, backup, schedule, PostgreSQL connection or destructive mutation is exposed.

## Two designs
- Source ZIP + local Python 3.11: already verified, free, most transparent; user needs local Python and package setup.
- Unsigned PyInstaller core EXE: free standard Windows runner and no Python on the owner machine. More build/runtime/license/antivirus surface. **Selected for user preview only**, never as the customer product without rights and own-PC acceptance.

## Build/safety
- PyInstaller upstream license grants an explicit commercial bundle exception: https://www.pyinstaller.org/en/stable/license.html . This does **not** resolve third-party transitive dependency rights or the author's own product license.
- Build uses only SQLite/Python core, packages local HTML/CSS/JS assets, uses no optional FastAPI/Uvicorn/PostgreSQL dependencies.
- GitHub Actions must show **real frozen executable execution** with `CREATED_SYNTHETIC_DEMO` and original synthetic database file not retained. A successful PyInstaller build alone is insufficient.
- EXE is **unsigned** and may trigger SmartScreen/antivirus. User should never be told to bypass protective dialogs or whitelist an untrusted program merely to make a test pass.
- Artifact expires after seven days; exact source SHA and exe SHA must be recorded from the job output. No permanent distribution/installer/release created.
- Customer/production release remains HOLD until own Windows 10/11 execution, code signing or explicit unsigned acceptance policy, actual local data protections, NOTICE/license, support and final customer instructions are approved.
