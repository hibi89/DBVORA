# R04-02 CPU/RSS/volume scoped benchmark — 2026-11-15

## Scope and exact validation

R04-02 extends the R04-01 synthetic repeated benchmark. Functional/test SHA: [`eb191c9783102f108057073f42334503f4ab9e85`](https://github.com/hibi89/DBVORA/commit/eb191c9783102f108057073f42334503f4ab9e85). The same synthetic two-generation snapshots (946,176 B and 950,272 B) were processed in 3 trials per available method; both generations were independently restored and SHA-256 checked on each trial.

- Full release gate [#43622284063](https://github.com/hibi89/DBVORA/actions/runs/43622284063): success at this SHA. Ubuntu 764/764, 0 skips; Windows 764 pass + 1 named POSIX-only skip: `test_review_html.ReviewHtmlTests.test_created_report_is_mode_0600_on_posix`.
- Blueprint gate [#43622284359](https://github.com/hibi89/DBVORA/actions/runs/43622284359): success at this SHA.

## Environment

| Runner | Reported environment |
|---|---|
| Ubuntu 24.04 | Linux 7.0.0-1017-azure, x86_64, 4 logical CPUs, Python 3.11.18, SQLite 3.45.1, ZSTD 1.5.7 |
| Windows-2025 | Windows release 10, AMD64 Family 26 Model 2 Stepping 1 (reported runner value), 4 logical CPUs, Python 3.11.9, SQLite 3.45.1, ZSTD 1.5.7 |

## Per-operation medians and trial ranges

Each cell is median `[min–max]` across 3 trials. Wall create includes the archive creation API (which may self-verify); wall restore includes independent restore and restored-file SHA-256. Process CPU is `time.process_time_ns` delta for the current Python process around each operation.

| Runner | Method | Artifact file lengths (B) | Wall create ms | Wall restore ms | Python CPU create ms | Python CPU restore ms |
|---|---|---:|---:|---:|---:|---:|
| Ubuntu 24.04 | ZIP | 31216 | 22.879 [21.951–23.263] | 8.359 [8.254–8.589] | 19.862 [19.715–21.886] | 6.862 [6.790–6.989] |
| Ubuntu 24.04 | ZSTD level 3 | 27651 | 25.603 [25.006–25.678] | 15.368 [13.657–16.445] | 9.392 [9.289–9.622] | 6.865 [6.712–6.920] |
| Ubuntu 24.04 | raw CAS v1 | 1177960 | 23.191 [23.156–23.609] | 9.205 [9.033–9.223] | 14.528 [14.511–14.675] | 7.821 [7.759–7.851] |
| Ubuntu 24.04 | zlib CAS v2 | 24637 | 32.535 [31.903–32.589] | 11.277 [11.140–11.346] | 24.108 [23.998–24.322] | 9.805 [9.788–9.986] |
| Windows-2025 | ZIP | 31550 | 80.430 [72.366–95.113] | 51.119 [48.634–51.335] | 31.250 [15.625–46.875] | 15.625 [0.000–31.250] |
| Windows-2025 | ZSTD level 3 | 27824 | 126.527 [117.138–128.173] | 73.859 [73.456–74.134] | 15.625 [0.000–31.250] | 0.000 [0.000–31.250] |
| Windows-2025 | raw CAS v1 | 1177960 | 281.330 [253.023–283.548] | 63.781 [61.162–65.419] | 62.500 [31.250–93.750] | 15.625 [0.000–15.625] |
| Windows-2025 | zlib CAS v2 | 25046 | 261.345 [257.379–269.169] | 63.818 [62.299–64.075] | 46.875 [15.625–62.500] | 31.250 [31.250–31.250] |

## Boundary RSS and shared-volume free-space deltas

RSS is the maximum of the two before/after boundary samples per operation, summarized across 3 trials; it is not peak RSS. Volume numbers are change in free bytes on the temp directory's containing shared host volume; negative means free space decreased. These are file-system observations, not per-process disk I/O counters.

| Runner | Method | Sampled max RSS create B | Sampled max RSS restore B | Shared volume free delta create B | Shared volume free delta restore B |
|---|---|---:|---:|---:|---:|
| Ubuntu 24.04 | ZIP | 24240128 [24178688–24252416] | 24240128 [24182784–24252416] | -40960 [-40960–-40960] | -1896448 [-1896448–-1896448] |
| Ubuntu 24.04 | ZSTD level 3 | 24231936 [24199168–24252416] | 24231936 [24199168–24252416] | -40960 [-40960–-40960] | -1896448 [-1896448–-1896448] |
| Ubuntu 24.04 | raw CAS v1 | 24231936 [24203264–24244224] | 24236032 [24219648–24244224] | -1200128 [-1200128–-1200128] | -1896448 [-1896448–-1896448] |
| Ubuntu 24.04 | zlib CAS v2 | 24236032 [24223744–24244224] | 24236032 [24223744–24244224] | -102400 [-102400–-102400] | -1896448 [-1896448–-1896448] |
| Windows-2025 | ZIP | 23519232 [22859776–23552000] | 23371776 [22880256–23543808] | -36864 [-36864–-36864] | -1896448 [-1896448–-1896448] |
| Windows-2025 | ZSTD level 3 | 23486464 [23085056–23748608] | 23486464 [23089152–23764992] | -36864 [-36864–-36864] | -1900544 [-1900544–-1900544] |
| Windows-2025 | raw CAS v1 | 23433216 [23261184–23564288] | 23425024 [23261184–23625728] | -1196032 [-1196032–-1196032] | -1896448 [-1896448–-1896448] |
| Windows-2025 | zlib CAS v2 | 23437312 [23207936–23638016] | 23486464 [23367680–23506944] | -98304 [-98304–-98304] | -1896448 [-1896448–-1896448] |

## Interpretation limits

- Process CPU and RSS describe the current Python process only; they do not include external child-process CPU or memory, including the ZSTD CLI subprocess. CPU values are not CPU percent.
- Per-process disk I/O bytes are unavailable and explicitly not measured. The free-space delta is a shared volume signal; other runner activity can affect it and it is not attributable to DBVORA alone.
- The two-boundary RSS maximum can miss short peaks. OS caches were not cleared; trial method order rotates. Runner load is uncontrolled.
- Artifact size is emitted file length, not physical block allocation. These exact synthetic runner samples do not establish customer hardware performance, universal codec ranking, provider pricing, or savings.
- No user PC, customer data, external transmission, paid infrastructure, or owner approval gate was used. Overall completion remains `UNASSESSED` / `RELEASE HOLD`; owner and physical gates remain open.
