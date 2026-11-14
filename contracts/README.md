# DBVORA metadata contracts

These JSON Schema files describe the versioned metadata payloads emitted by DBVORA's local read-only APIs and offline mixed-engine report.

| Contract | Payload |
| --- | --- |
| `p0-01.v1` | One explicitly selected SQLite database inventory |
| `p0-03.workspace.v1` | Two to eight explicitly selected SQLite databases |
| `dbvora.pg_catalog.v1` | PostgreSQL catalog metadata |
| `dbvora.pg_statistics.v1` | PostgreSQL estimated statistics, which may lag |
| `dbvora.local-table-storage.v1` | Optional bounded SQLite btree allocation measurement |
| `dbvora.local-observation.v1` | Local, explicitly recorded SQLite file-size observations |
| `dbvora.multi_engine_offline.v1` | Offline normalized SQLite/PostgreSQL metadata report |
| `dbvora-error-v1` | Path-free API error envelope |

Consumers should accept only contract versions they recognize, validate the corresponding schema, and map a stable error envelope to an unavailable state. An incompatible payload change requires a new contract version. The contracts describe metadata only; they do not authorize database access, customer-data use, or external orchestration. PostgreSQL statistics are estimates and are not exact row counts.
