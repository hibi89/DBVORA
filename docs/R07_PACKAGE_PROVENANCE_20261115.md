# R07-01 Package Provenance — 2026-11-15 KST

**Acceptance:** R07-01 PASS_SCOPED at source/test commit `4914c59a7009e223e02924fd4f1f92c4a1431bf0`. This scope covers unsigned source ZIP/Windows demo EXE build, embedded or sidecar source/hash evidence, artifact upload, and synthetic execution on GitHub-hosted runners.

## Exact-SHA verification

- Full release gate [#43639974974](https://github.com/hibi89/DBVORA/actions/runs/43639974974): PASS on `4914c59a7009e223e02924fd4f1f92c4a1431bf0`. Ubuntu: 777/777, 0 skips. Windows: 776 PASS + one named POSIX-only skip (`test_review_html.ReviewHtmlTests.test_created_report_is_mode_0600_on_posix`); all 12 synthetic gate steps PASS.
- Unsigned source ZIP [#43639974931](https://github.com/hibi89/DBVORA/actions/runs/43639974931): PASS. Manifest and build report both record `source_commit` `4914c59a7009e223e02924fd4f1f92c4a1431bf0`; verifier accepted 75 source files, including all nine `contracts/` files. ZIP SHA-256: `9f20ba18824214ccb2fb20a1d9a9bb6ace5619f1aed93cd913677d98d4624815`. The packaged offline self-check passed 9/9.
- Windows demo EXE [#43639974945](https://github.com/hibi89/DBVORA/actions/runs/43639974945): PASS on `windows-2025`. The synthetic-only EXE generated one HTML report, confirmed the content security policy and absence of the synthetic sentinel row, and wrote/read back a JSON sidecar whose source commit and EXE SHA matched. EXE SHA-256: `b27397e61241ec059688bffe324b2eeaaa705dc8dfde48940df2224e92fbe30b`.
- Blueprint gate [#43639975373](https://github.com/hibi89/DBVORA/actions/runs/43639975373): PASS.

## GitHub artifacts

- ZIP artifact `dbvora-UNSIGNED-OWNER-PREVIEW-4914c59a7009e223e02924fd4f1f92c4a1431bf0` (artifact `14131449475`), whole artifact digest `sha256:a62be33597828815d0d096b460970cd2404ab52247da03c73e8dc7aa88d10269`. Contains the source ZIP and unsigned build report.
- Windows artifact `dbvora-UNSIGNED-SYNTHETIC-WINDOWS-DEMO-4914c59a7009e223e02924fd4f1f92c4a1431bf0` (artifact `14131459465`), whole artifact digest `sha256:01ad866a36836f691dc9ccc2903b71ea483ded0a32b4d69463397bf6a41d190f`. Contains the EXE and `DBVORA-SYNTHETIC-OWNER-PREVIEW.build-info.json` sidecar.
- Both artifacts use the existing seven-day retention policy. The ZIP hash and EXE hash above identify their payload files; the artifact digests identify the outer GitHub artifact archives.

## Failure corrected before acceptance

The first packaging implementation commit `7429a5298ecd59096269395fffb8cc0c20aa143e` passed both packaging workflows but the full release gate found five trusted-extraction fixture failures because that older synthetic fixture omitted the new `source_commit` manifest field. Commit `e12dc5542d22ed659b0355ff6896397956d57357` updated the fixture. The final exact-SHA full gate then passed on `4914c59a7009e223e02924fd4f1f92c4a1431bf0`.

## Scope limits

The manifest field and hashes are unsigned traceability/integrity evidence. They do not authenticate a publisher or certify a deterministic reproducible binary build. The Windows execution used synthetic-only data on a hosted runner; it does not replace actual owner-device Windows 10/11 QA, physical durability checks, or customer readiness. R07-04 and owner/legal/physical gates remain open. Overall completion remains UNASSESSED / RELEASE HOLD.