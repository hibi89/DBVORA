# R07-02 — Portable lifecycle acceptance (2026-11-15 KST)

**Functional/source/test SHA:** [`3f138530321a35dc96c1682f1ebb2fac3fac85ce`](https://github.com/hibi89/DBVORA/commit/3f138530321a35dc96c1682f1ebb2fac3fac85ce)  
**Scope status:** `PASS_SCOPED` for GitHub-hosted synthetic lifecycle checks only.

## Implemented

- The source ZIP README now gives manual launch, Ctrl+C stop, same-command restart, and safe folder removal instructions. It requires extraction to a new empty app folder; database files stay outside it. No service, auto-start, background process, or browser auto-launch is installed.
- The generated Windows `.cmd` and POSIX `.sh` launchers accept an optional port (default 8765). The local server binds only to loopback and returns fixed startup errors. PostgreSQL remains disabled when `DBVORA_POSTGRES_DSN` is absent.
- Port preflight now checks whether a local listener accepts a connection. This avoids treating recently closed connections in TIME_WAIT as an occupied port; the actual server bind remains the final race check.
- The lifecycle regression starts the extracted source ZIP using the platform launcher, loads a synthetic SQLite inventory, verifies PostgreSQL is disabled without its environment setting, starts a second process on the occupied port and checks `PORT_IN_USE`, stops the first process, verifies the port is no longer listening, restarts on that port, and removes only the extracted app directory.
- The test hashes the synthetic SQLite file before and after and verifies that both the database and a marker file in the separate owner-data directory remain present and unchanged.
- The full-gate failure diagnostic now includes the lifecycle module. The PostgreSQL UI acceptance helper captures child stderr only to recognize an allowlisted fixed startup error code; it does not print a DSN or raw paths.

## Exact-SHA GitHub evidence

| Check | Run | Result |
| --- | --- | --- |
| Full Ubuntu/Windows release gate | [#43642757174](https://github.com/hibi89/DBVORA/actions/runs/43642757174) | PASS; 779 discovered on each OS, Ubuntu 779 PASS/0 skips; Windows 778 PASS + one named POSIX-only skip; all 12 gate steps PASS on both |
| Chromium localhost E2E | [#43642757197](https://github.com/hibi89/DBVORA/actions/runs/43642757197) | PASS; 33/33 checks on Ubuntu 24.04 and 33/33 on Windows 2025 |
| PostgreSQL 16 TLS and UI E2E | [#43642757164](https://github.com/hibi89/DBVORA/actions/runs/43642757164) | PASS; verified TLS/read-only synthetic catalog 5 checks and browser UI 8 checks |
| Unsigned source preview ZIP | [#43642757175](https://github.com/hibi89/DBVORA/actions/runs/43642757175) | PASS; manifest source commit matches SHA; 75 files; offline self-check 9/9; ZIP SHA-256 `3cc92b6d625206cb2a5604e4a4171488f45ee4403a6ab4d2b8406083fd2c97c6` |
| Unsigned Windows demo EXE | [#43642757229](https://github.com/hibi89/DBVORA/actions/runs/43642757229) | PASS; sidecar source commit matches SHA; EXE SHA-256 `5f3d0e9cf936ae83ffe13570e1c8d1425d704c846a8c1531bbf401e2a0632771` |
| Final blueprint evidence | [#43642757612](https://github.com/hibi89/DBVORA/actions/runs/43642757612) | PASS |

The ZIP artifact is [ID 14133270147](https://github.com/hibi89/DBVORA/actions/runs/43642757175/artifacts/14133270147), outer artifact digest `sha256:bde6a512760cce3c4d35327715454cc564279a360dd0d56801d6b556d6b5365e`. The EXE artifact is [ID 14132822092](https://github.com/hibi89/DBVORA/actions/runs/43642757229/artifacts/14132822092), outer artifact digest `sha256:bc79e96e3bfd63e3535b86beaf4972c6da456ea9996cf0f286085cbee3ba502e`. Both expire after seven days. SHA values prove integrity only; neither artifact is signed or customer-ready.

## Failure and repair history

The first implementation SHA `0e78a2c519b9cea1e1fdd5e64add80ce48cb15a7` failed the Ubuntu lifecycle case in [full gate #43641811853](https://github.com/hibi89/DBVORA/actions/runs/43641811853); its Windows job passed. The PostgreSQL TLS/UI run [#43641811902](https://github.com/hibi89/DBVORA/actions/runs/43641811902) also reported `LOCAL_SERVER_START_FAILED`. The original PostgreSQL helper discarded child stderr, so those runs did not establish the exact startup error. The final source switched the port check to a listener connection probe, added safe startup-code diagnostics, and passed the full rerun and PostgreSQL UI check at the SHA above. This is the verified repair; the original underlying error was not directly logged.

## Limits and next work

These are synthetic tests on GitHub-hosted Ubuntu 24.04 and Windows 2025. They do not prove owner-device Windows 10/11 behavior, physical power-loss durability, customer database suitability, installer signing, or commercial readiness. Those owner/legal/physical gates remain open; the overall P100 completion stays **UNASSESSED / RELEASE HOLD**.

**Next task:** R07-03 — finish Korean error, consent, safe restore and failure guidance, with real Chromium checks for desktop/390px, keyboard use, ARIA, and screenshots.
