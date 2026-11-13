# PRs 10–12: integration review, 13 November 2026

Reviewed heads: PR #10 `dcdd48528e40da14fe58fd6526d33d35d66e3c50`, PR #11 `da99591cc2f35bca6a5362c3ccb0b4e65fcf29b7`, PR #12 `a291dd2899e9f890a946a174645cbc176002e8a3`. All three were merged into an isolated candidate based on main `0f9fb838dd7e5200ed892503fe23e95a8ca022bc`, then corrected and validated together before publication.

## Corrections included

- Export large runs in bounded HTTP chunks, verify gzip/CSV records and run identity, compare source counts before/after each table, and record SHA-256. Existing archives are verified rather than accepted because a directory exists. Concurrent exporters cannot share a final target; failed staging attempts stay separate and do not enter run reports.
- Require an explicit integer pending zero, a successful verified export, unchanged stopped-run identity, free disk and no maintenance pause immediately before watchdog restart. An incomplete reserve-triggered stop/export remains paused and retries. Docker recovery starts existing containers instead of recreating them.
- Apply the known 262,144-row import block settings to the isolated GPS loader while keeping its 512 MiB query budget; this does not change the measured SELECT queries.
- Route installation, rehearsal and presentation documentation to the exact 11 November 14-slide HTML and English notes. Preserve the old 16-slide outline as an archive. Preserve the current script, slide content and four-speaker allocation. Document host/gateway updates and the independently started second API without resetting volumes or exposing credentials.
- Describe the archived runs' event spans accurately; a long timestamp span containing a pause is not continuous uptime.

## Validation

- **82 Python tests passed, zero skipped**, including real SQL integration, out-of-order GPS equivalence, chunked gzip import, complete query-log joins, real five-table gzip exports, archive corruption and watchdog maintenance/reserve scenarios.
- **33 JavaScript tests passed**, including map behavior. Shared-site build, Bash syntax, benchmark Compose configuration, Markdown local links and `git diff --check` passed.
- Real ClickHouse **25.8.33.6** ran only in a disposable loopback native instance on port 18124, with separate temporary data. Docker was not started. These tiny integration fixtures validate correctness; they are not a rerun of Anuar's hardware capacity experiment or his Windows Docker installation.
- The original application/map files, API, gateway, production Compose and Vercel/build configuration have no changes relative to the reviewed main baseline.
- The repository HTML exactly matches the approved presentation: SHA-256 `06fe1de47c4e94e6205e9dffe64f12556e896f706ef31bbd08e4db9d235345a2`.

## Received GPS evidence

The [6 November release](https://github.com/AnuarH16/analitica-reparto-clickhouse/releases/tag/gps-benchmark-2026-11-06) ZIP has SHA-256 `3ed1f911283fd9afccaa222550754dda238a9df12ac8dbe701bd5861ab91d5d7`. ZIP CRC verification passed. Its full report contains 2,400 distinct measured query IDs, all successful and joined to server query records, across 12 phases. Its p95 and server-work values match the presentation. This verifies the supplied evidence; no independent large-corpus timing is claimed. PostgreSQL and DuckDB timings remain future work.

## Host handoff

Before this release, the public website and map assets returned HTTP 200, but `/api/status`, `/api/journey` and `/api/performance` returned HTTP 503. A successful frontend deployment alone cannot repair an offline host/tunnel. Anuar must update the existing host and gateway, preserve its volumes and token, check the current tunnel address, and validate local and shared reads using [DEMO-GUIDE.md](DEMO-GUIDE.md). Recheck public data access after that host-side work.
