# PostgreSQL local read-only catalog UI

The local viewer can display a PostgreSQL catalog when the operator configures the server process with the environment variable DBVORA_POSTGRES_DSN. The value is read only from the server environment; it is not accepted in URLs, browser fields, command arguments, or API request bodies.

The PostgreSQL section starts in an idle state. The local viewer connects only after the operator clicks the PostgreSQL metadata lookup button. The API is GET-only, rejects query parameters, and calls the existing connector with verified TLS and statistics disabled. The connector opens a read-only transaction, applies short connection and statement timeouts, and reads bounded PostgreSQL catalog metadata. The UI renders schema/table names, relation kinds, columns, primary keys, indexes, and foreign keys as text nodes. It never selects table rows and does not show DSNs or connection exceptions.

If DBVORA_POSTGRES_DSN is absent, the endpoint is disabled. A TLS or connection failure is reported with a fixed safe message; the operator can retry after correcting the server-side setting and restarting the local viewer. Do not configure customer credentials in GitHub Actions.

The GitHub-only acceptance uses an ephemeral loopback PostgreSQL 16 instance, synthetic rows and a synthetic row canary, a temporary wrong CA, and real Chromium. It checks no eager request, verified TLS catalog display, safe failure and retry, no row/DSN leak, and 390 px layout. This evidence is CI acceptance for synthetic data; it is not customer-environment approval.
