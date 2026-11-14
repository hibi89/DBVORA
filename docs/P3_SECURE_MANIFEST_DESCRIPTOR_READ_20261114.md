# DBVORA P3 — immutable descriptor-based manifest validation

2026-11-14 KST · Verified exact source `0caf6080eceb8fd725926621ed478b2a2e8f348a`

## Risk and design choice
The former `restore_compressed` manifest path check used `lstat` then a *separate* `Path.read_bytes()` opening. A same-size/same-mtime file substitution between those calls could bypass the post-read stat check. This is a narrow, actual local filesystem race, not evidence of an exploited customer environment.

- **A: maintain path-based reads:** few lines but no inode/object continuity guarantee; fragile under concurrent local publishers or attackers.
- **B: open a bounded descriptor and compare identity before/after:** standard-library only, minimal scope, no new network permissions or charges; **chosen**.

## Code and contract
`dbvora/archive/compressed_cas.py`: new `_read_manifest_unchanged` opens a max-512KiB regular single-link manifest via `os.open` and `O_NOFOLLOW` when the OS exposes it. Compares device, inode, size, nanosecond modified/changed timestamps from the initial path, open file, after read FD, and final path. Reads at most `MAX_MANIFEST + 1` bytes. Identity or length changes cause `MANIFEST_CHANGED` and no restore publication. File paths/credentials do not enter errors.

`tests/test_compressed_cas_failures.py`: isolated throwaway synthetic manifests; swaps an identical-size identical-mtime clone precisely before the restore descriptor open. Confirms fail-closed, no restored artifact, and unchanged synthetic DB checksum/mtime. No real owner/customer file was modified.

## Exact GitHub verification
[commit `0caf6080eceb8fd725926621ed478b2a2e8f348a`](https://github.com/hibi89/DBVORA/commit/0caf6080eceb8fd725926621ed478b2a2e8f348a) · [release CI #43562802300](https://github.com/hibi89/DBVORA/actions/runs/43562802300) **2/2 SUCCESS**:
- Ubuntu24.04 Python3.11: 699 discovered/699 PASS, 0FAIL/0SKIP.
- Windows2025 Python3.11: 699 discovered/698 PASS/0FAIL/1 named POSIX-only SKIP.
- Mandatory release gate 12/12 on both, including Node frontend DOM, safe ZIP/ZSTD/CAS restoration, PG synthetic offline HTML, and archive durability.

This checks a *synthetic* local swap, not malicious actor resistance across all OS/kernel race schedules, physical power loss, continuous backups, real PostgreSQL/customer permissions, Windows10 owner acceptance, signed customer packages, licensing, or legal/commerce readiness.

Official whole-design completion: **UNASSESSED**; historic internal engineering 95 is not the official score. Preserve `[작업중]`, RELEASE HOLD, 0 actual Kmong registrations, Production/Vercel not deployed. No new owner PC actions while traveling.
