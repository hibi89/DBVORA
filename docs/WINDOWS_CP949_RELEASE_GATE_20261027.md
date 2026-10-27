# DBVORA — Windows CP949 Node TAP release-gate incident (2026-10-27 KST)

## Owner-observed failure (real Windows Python 3.11)
- In authorized local Git checkout `E:\DBVORA_GIT` on `feature/p0-db-map`, user executed `py -3.11 -B -m scripts.verify_release_gate`.
- `subprocess` background `_readerthread` raised `UnicodeDecodeError: 'cp949' codec can't decode byte 0xe2 in position 80`. The harness then crashed at `tap = node_out + "\n" + node_err` because `node_out is None`.
- This occurred during Node TAP output capture. It is a **harness/locale handling bug**; it does not establish that the real Python/ZIP/ZSTD/Node application tests passed or failed. No complete gate JSON was returned. Earlier v1 archive ZIP pin mismatch is an independent transport issue; since Git clone works, don't ask owner to run v1 or v2 ZIP tooling again.

## Design choices and selected fix
1. Replace undecodable bytes with Unicode replacement characters (easy) — would hide corrupted test evidence, rejected.
2. **Selected:** capture process streams as bytes; set `PYTHONIOENCODING=utf-8` in inherited child environment; decode stdout and stderr explicitly as **strict UTF-8**, return `(-1, "", "")` on decoding error, timeout, missing output, OS failure. This preserves fail-closed validation and prevents `None` concatenation without altering Windows system encoding or other environment settings.

## Code and evidence
- `scripts/verify_release_gate.py`: updated `_run`, imports os; `EXPECTED_PYTHON_TESTS=218` (original 214 + 4 new regression cases).
- `tests/test_verify_release_gate.py`: 18 focused test methods, adding real child UTF-8 output, malformed UTF-8 fail-closed, missing stream fail-closed, forced UTF-8 child environment preservation. Existing decision fixtures changed to 218; one-short regression now tests 217.
- Executed **local standalone mirrors of the new subprocess routine** on Linux Python 3.13.5: **6/6 PASS**. Separately executed **real Node 22.16.0 TAP with a Unicode test name: 1/1 PASS**, strict UTF-8 decoding. Remote branch source/test content fetched and static checks passed; **full 18 checked-in tests not run in this container**, current **218 Python full suite and six-stage release gate not run**. Native Windows3.11 revalidation awaits owner.
- Any previous QA v6/v1/v2 source SHA pin archive is **stale for the modified source/test blobs**. Never waive pinning; direct authorized Git checkout is the approved zero-cost path now.

## Next exact instructions
On owner Windows PowerShell, existing verified local repo, **do not clone or download ZIP again**:
```powershell
cd E:\DBVORA_GIT
git status --short
git pull --ff-only
py -3.11 -B -m scripts.verify_release_gate
```
Only run release gate if `git pull --ff-only` succeeds. Send only the sanitized JSON result; no source ZIP, credentials or customer DB.

Then analyze any FAIL steps using narrow synthetic tests; do not label Windows synthetic gate PASS as customer-ready. Native NTFS durability/power-loss, real file:// and customer database use remain separately unverified. Feature only; no main/develop promotion, paid Actions, public repo, destructive archive changes or Production/Vercel deployment.
