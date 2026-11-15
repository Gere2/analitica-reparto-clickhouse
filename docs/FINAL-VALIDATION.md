# Final delivery validation

Checks recorded on 15 November 2026. The package release manifest identifies the exact documentation/source commit. The application, production configuration, approved presentation and script remain based on the reviewed `c7d4ca1` release.

## Automated and SQL checks

- **82 Python tests passed, zero skipped**, including real ClickHouse integration, out-of-order GPS equivalence, chunked gzip loading, matching query-log records, five-table archive verification and watchdog pause/reserve cases.
- **33 JavaScript tests passed, zero skipped**, including map/UI and public proxy behavior.
- The six export/report regressions passed again after correcting the generated report's archive-publication wording.
- The shared static build and benchmark Compose configuration passed. Whitespace and local document links are checked before packaging; package file hashes and extracted-resource checks are recorded in its release manifest.

Real SQL checks used ClickHouse **25.8.33.6** in a temporary native loopback instance on port 18124 with separate temporary data. Bootstrap was taken from the actual SQL mounts in `benchmarks/gps/compose.yaml`, including all four Atlas schema files and the GPS marker/reader setup. The lab configuration now mounts agents/mini-app SQL as well as browsing/operations, supplying all five tables required by the export integration check. Docker itself was not started for these tests; the native fixture validates SQL correctness, not Windows/container startup or capacity.

## Frozen files

The 98 recorded presentation/script/application/SQL/production-configuration files matched their pre-change hashes. In particular:

| File | SHA-256 |
|---|---|
| Approved 14-slide HTML | `06fe1de47c4e94e6205e9dffe64f12556e896f706ef31bbd08e4db9d235345a2` |
| Matching English script | `2ecf95f7e333c2e1c972fd8e4df04d3dfaf9db461a15d594f222abf7148d79e5` |
| Map JavaScript | `501a0a421128bb9c9ae6d03117b56d022156acbeb70317358edf5e4ab71975fe` |

Historical presentation files and speaker notes are also preserved. Documentation clarifications are separate files. The only setup change outside documentation is completing the isolated GPS lab's SQL mounts; the live application/map, applied SQL, gateway and production Compose/Vercel source files have no edits.

## Shared production connection

At 19:26 UTC the recreated tunnel returned 200 with the existing token and 401 without it for status, operations, Journey, Performance and datasets. Only production `ATLAS_SHARE_ORIGIN` was updated; the token was preserved server-side.

Production deployment `dpl_4uUyS8LYVqpYApBD38tjX6Ru14sk` reached READY from `c7d4ca1`. At 19:28 UTC all five public data routes returned 200; pending was zero and Performance reported 25.8.33.6. Public map, Leaflet and analytics assets matched the reviewed source. A later documentation-only release can have a different Git/deployment ID without changing those web assets.

The browser rendered real Madrid streets and 150 courier markers; selecting Courier 02 and using zoom worked. The interface explicitly reported a stopped run and old position ages. No new simulation was started for this check. The fresh 100-customer/50-courier run is an operating step for the agreed rehearsal, not a claim about these old positions. A scoped error/fatal runtime-log scan over the reconnection deployment found no entries in its 19:20–19:35 UTC window; successful HTTP reads were verified separately.

## Measurement evidence

The received GPS ZIP retains SHA-256 `3ed1f911283fd9afccaa222550754dda238a9df12ac8dbe701bd5861ab91d5d7`. Recomputing the twelve phase p95 values from its samples matches the presentation. There are 2,400 unique measured query IDs, 2,400 terminal server records and zero measured request errors. The runner source hash in that Windows report matches the current runner bytes after CRLF conversion; the difference from Git's LF file is line endings. This audits the supplied evidence; it is not an independent rerun of Anuar's large-corpus timings.

## Remaining operating and source updates

Keep Anuar's computer/tunnel active and recheck near the talk. The complete group rehearsal and Echenique's additional installation/CRUD record still need confirmation. PR #13 supplied all 21 manifests and the dated inventory. Their schemas, UUIDs, table/byte sums and per-run order totals were checked; the 37,310,637 archived rows and 2,895,578,932 compressed bytes agree. Public physical metadata for the five event tables matches the inventory, including the 32 unassigned browsing events outside the run archives. The CSV payloads were verified by Anuar, not downloaded and rechecked locally. These distinctions do not imply that code is missing or that an unrecorded check failed.
