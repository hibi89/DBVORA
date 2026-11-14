# DBVORA P3 — short-write fail-closed CAS staging

**2026-11-14 KST · source `0abe50bbd2197f316c4626e00b02d1264abe068e`** — backend synthetic-only, cost zero.

## Decision
Option A: retain `Path.write_bytes(payload)` with no return or readback check (slightly less I/O but partial writes can leave incompletely published manifests). Option B: validate staged byte count and independently read the bounded staged bytes before publication, reject mismatch with a fixed path-free error. **B chosen**; max 64KiB raw chunks / 512KiB manifest cap, no new service, subscription or customer access.

Changes: `dbvora/archive/compressed_cas.py` adds `_write_staged_exact(staged, payload)`, used for zlib chunks and JSON manifests. It confirms exact returned byte count and staged content. If either disagrees, `STAGED_WRITE_UNVERIFIED` and normal staged-temp finally cleanup, *no new final chunk or manifest publication*. This does not claim actual power-cut durability.

## Synthetic negative tests
`tests/test_cas_partial_write.py` tests 3 independent scenarios with fresh temp SQLite: (1) real short bytes for chunk (no chunk or manifest published), (2) real short bytes for manifest after a valid prior generation (prior manifest byte-identical, independent restore succeeds), (3) false full-length write return with only half payload stored (readback catches it). Source DB and snapshot SHA unchanged.

## Failure diagnosis and correction
- [first exact SHA `92c7a9c8` OS run #43566541865](https://github.com/hibi89/DBVORA/actions/runs/43566541865): Ubuntu passed 706/706, Windows **FAIL** one new `test_partial_manifest_write_keeps_previous_generation_restorable`.
- [diagnostic workflow SHA `dd9eb892` #43566989375](https://github.com/hibi89/DBVORA/actions/runs/43566989375): explicit detailed Windows unittest traceback shows `AssertionError: CompressedCasError not raised`. The test's Path.parent/.part predicate did not fire the synthetic partial write on Windows. This is an *injection/test design error*, not evidence the production guard silently accepted a detected short write.
- Final [source SHA `0abe50bbd219`](https://github.com/hibi89/DBVORA/commit/0abe50bbd2197f316c4626e00b02d1264abe068e): injection selects manifest JSON payload by `cas.CONTRACT` marker, verifies exactly one injection occurred. No production guard was relaxed. [Windows2025 + Ubuntu24.04 full #43567268531](https://github.com/hibi89/DBVORA/actions/runs/43567268531): **2/2 SUCCESS**, 706 discovered, Ubuntu706 PASS/0 FAIL/0 SKIP; Windows705 PASS/0 FAIL/1 named POSIX-only SKIP; mandatory 12/12 PASS per OS including Node frontend DOM test.

## What this does not verify
Physical power failure, customer environment, actual buyer Win10/11, hostile multi-process writer race across every scheduling interleaving, long-term backup policies, code signing, commercial licensing/NOTICE and user final weighted 100-point acceptance. Source-only synthetic gates are not launch certifications. Official **UNASSESSED** (historic internal95 only), `[작업중]`, RELEASE HOLD, actual Kmong registration0, Vercel/Production not applicable. No customer data/keys or existing backups changed.
