# P5 Security acceptance — 2026-11-15

**Functional source/test SHA:** `3fd075226ef5c7e4aa1d66d3392c627315fd5cbc`  
**Overall:** scoped GitHub synthetic evidence only. No customer data, production credentials, user PC, privileged parent-directory attack, physical power-loss, legal approval, or cryptographic signing was used.

## R05 task evidence

| ID | Result at exact SHA | Evidence | Limits |
| --- | --- | --- | --- |
| R05-01 | PASS_SCOPED | Chromium run [#43636834445](https://github.com/hibi89/DBVORA/actions/runs/43636834445) passed 33 HTTP/browser checks on Ubuntu and Windows, including Host/Origin/method guards and `simulated_dns_rebinding_host_origin_rejected`. | The rebinding case sends attacker Host/Origin and fetch-site headers to the loopback listener; it does not alter DNS or prove behavior against a real resolver, proxy, or network. |
| R05-02 | PASS_SCOPED | Full release [#43636834475](https://github.com/hibi89/DBVORA/actions/runs/43636834475) passed 773 tests discovered on each OS (Ubuntu 773 PASS/0 skip; Windows 772 PASS + 1 named POSIX-only skip), including the safe ZIP/create-only, symlink/hardlink, path traversal, and file identity regression coverage. | Privileged parent-directory swaps, real storage exhaustion, and physical power loss remain unproven. |
| R05-03 | PASS_SCOPED | PostgreSQL TLS/UI run [#43636834428](https://github.com/hibi89/DBVORA/actions/runs/43636834428) passed synthetic PostgreSQL 16 verify-full, read-only catalog/statistics, wrong-CA fail-closed, no-rows/no-DSN, and desktop/mobile screenshot assertions. | This is an ephemeral synthetic server and generated certificate; customer credentials, production TLS, and customer logs were not used. |
| R05-04 | OWNER_GATE | The same PG run produced the metadata-only Python SBOM candidate `dbvora-python-sbom-3fd075226ef5c7e4aa1d66d3392c627315fd5cbc` (artifact 14129504441, 1,479 bytes, digest `sha256:8a084776d83bc44ef7414cb2fe40cefefa68ecd94875fe4b28b5bad14d23db1c`). | This is an inventory candidate, not a legal determination. The repository still lacks owner-approved LICENSE/NOTICE and customer terms; transitive/build-specific licensing and redistribution rights need owner/legal review. |
| R05-05 | PASS_SCOPED | The full gate passed synthetic archive integrity/tamper tests. Receipts explicitly remain `unsigned_untrusted`; SHA consistency is not signer identity. | No signature/key-management system is implemented. An actor able to replace both payload and manifest can recompute hashes; authenticity is not claimed. |

## Artifacts and exact-SHA gates

- Full Ubuntu/Windows gate: [#43636834475](https://github.com/hibi89/DBVORA/actions/runs/43636834475) — 773 tests discovered on each OS: Ubuntu 773 PASS/0 skip; Windows 772 PASS + 1 named POSIX-only file-mode skip (`test_review_html.ReviewHtmlTests.test_created_report_is_mode_0600_on_posix`). All 12 gate steps passed.
- Real Chromium: [#43636834445](https://github.com/hibi89/DBVORA/actions/runs/43636834445) — 33/33 checks on Ubuntu and Windows, including the simulated rebinding request.
- Synthetic PostgreSQL 16 TLS and UI: [#43636834428](https://github.com/hibi89/DBVORA/actions/runs/43636834428) — verified TLS/read-only role, FK/catalog, estimated-statistics provenance, wrong CA rejection, and browser leak checks passed. Screenshot artifact 14130550353 is 1,065,398 bytes, digest `sha256:84f39ffa06cd2e4374b821e3cfd1b6db6e579cee9c54fc597b6d723f4442bcbe`.
- Blueprint gate: [#43636834707](https://github.com/hibi89/DBVORA/actions/runs/43636834707) PASS.

The Windows release attempt at parent SHA `3824054493381c986b8dc4e8421bb6997b026368` reached the former 240-second unittest timeout; it was not a named test failure. The release gate now allows 480 seconds and passed on this exact SHA. An earlier PostgreSQL workflow at `b798c0fe4c0beee1e5f74669ccb406fec3e71b7d` failed because its screenshot artifact directory was not exported; workflow environment/path triggers were repaired before this passing run.

**Official P100 completion remains UNASSESSED / RELEASE HOLD.** R05-04 owner/legal clearance and the physical/security boundaries above remain open.
