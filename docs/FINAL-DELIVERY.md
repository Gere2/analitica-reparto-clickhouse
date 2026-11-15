# Delivery Atlas final delivery

This is the entry point for the code, presentation, Markdown documentation and small evidence files. The package's release manifest identifies its exact source commit and file hashes. The approved presentation and script are preserved byte for byte.

**Submission:** Upload the final ZIP to [Proyect I on Canvas](https://ufv-es.instructure.com/courses/71424/assignments/604206). The exported assignment lists **15 November 2026 at 23:55 (Madrid time)** as the file deadline. Check the submission receipt in Canvas; the oral presentation slot is separate.

## Presentation and rehearsal

Open [Delivery-Atlas.html](../presentaciones/final-2026-11-11/Delivery-Atlas.html) after extracting the package, and use [SCRIPT-EN.md](../presentaciones/final-2026-11-11/SCRIPT-EN.md). The HTML contains 14 English slides, embedded images/fonts and notes. It needs no server for its static slides. Live dashboard data and map tiles have separate host/network dependencies.

| Speaker | Prepared slides | Prepared time | Additional live part |
|---|---|---|---|
| Echenique | 1, 2, 3, 10, 14 | 3:15 | Scratch CRUD after slide 14, about 1 minute |
| Juanro | 4, 9, 12 | 4:10 | Explain storage and the GPS plot |
| Anuar | 5, 6, 11, 13 | 4:40 | Journey/Performance after slide 8, about 2 minutes |
| Geremi | 7, 8 | 2:30 | Map, AI decisions and public data within the prepared parts |

The core totals **14:35**. With the dashboard and CRUD additions, 2:25 remains for transitions/buffer inside 20 minutes. Questions follow in the approximately ten-minute discussion slot. [PRESENTATION.md](PRESENTATION.md) and [DEMO-GUIDE.md](DEMO-GUIDE.md) describe the route. The retained closing at slide 10 leads into the experiment appendix, 11–14.

[DEFENCE-NOTES-EN.md](DEFENCE-NOTES-EN.md) gives terminology and evidence clarifications alongside the retained checkpoint wording. It does not replace or edit the approved script.

## Reproduce and understand Atlas

1. Follow [ATLAS-INSTALL.md](ATLAS-INSTALL.md) for the small local installation. Large public sources and AI are optional extensions. If using the extracted source instead of Git, skip the clone step and run commands from its root.
2. Read [DATABASE-STRUCTURE.md](DATABASE-STRUCTURE.md), the four applied `sql/atlas*.sql` files and [ATLAS-INFRASTRUCTURE.md](ATLAS-INFRASTRUCTURE.md) for the implemented data model and pipeline.
3. Use [FUNDAMENTALS.md](FUNDAMENTALS.md) and [APPLIED-THEORY.md](APPLIED-THEORY.md) for analytical storage, consistency, idempotency, availability and tradeoffs.
4. Follow [DEMO-GUIDE.md](DEMO-GUIDE.md) and [CLICKHOUSE-DASHBOARDS.md](CLICKHOUSE-DASHBOARDS.md) for the map, session funnel, physical/query metadata, public datasets and local CRUD.
5. Read [GPS-BENCHMARK.md](GPS-BENCHMARK.md), [SIMULATION-RUNS.md](SIMULATION-RUNS.md) and [HOST-STATUS-2026-11-15.md](HOST-STATUS-2026-11-15.md) for measured results, archived data and the dated host record.
6. See [TEAM-INSTALL-TESTS.md](TEAM-INSTALL-TESTS.md), [FINAL-VALIDATION.md](FINAL-VALIDATION.md), [ASSIGNMENT.md](ASSIGNMENT.md) and [AI-USE-AND-SOURCES.md](AI-USE-AND-SOURCES.md) for reproduction, validation, assignment mapping and attribution.

The complete archive contains application/API code, web resources and Leaflet/license, SQL, Compose/Dockerfiles, scripts, tests, the isolated GPS lab, documentation and the approved deck. It omits private credentials, local environment files, Docker volumes, caches and massive datasets. The small received GPS evidence archive is included with its source hash; the large synthetic exports and public datasets remain linked inputs.

## Results and interpretation

The frozen GPS campaign compares latest positions from history with prepared state inside ClickHouse, using 4,371,300 positions, 150 couriers and a 2-CPU/2-GiB lab. At two readers, history client p95 is 1,625–1,969 ms and prepared state 266–281 ms. All 2,400 measured requests succeeded and match server log records. Preparing the repeated answer reduces read work under those conditions.

This is a latency-target boundary for a particular workload, not a universal engine limit. It does not compare database products, find the prepared design's maximum concurrency or separately measure its insertion/storage cost. Public catalog/advertising records, fictional event rows, physical states and query result rows have different meanings.

The dated host record reports 21 verified exports with 37,310,637 rows and 23,978,916 GPS positions in ClickHouse. All 21 per-run manifests and their detailed table are included. The [live inventory](INVENTORY-2026-11-15.md) has 37,310,669 logical rows: 32 browsing events without a run ID account for the difference from the archive total. The 50-million generation milestone was not reached.

## Runtime checks before the talk

The public connection was restored and checked on 15 November at 19:28 UTC: status, operations, Journey, Performance and datasets returned 200. The browser showed the Madrid map with 150 historical courier positions, selection and zoom. [The host record](HOST-STATUS-2026-11-15.md) separates the earlier failed tunnel from the successful reconnection. Shared access remains GET-only with the token server-side, and depends on keeping Anuar's host and tunnel running.

Keep the watchdog and long-run producers paused during the presentation. Coordinate the fresh 100-customer/50-courier hybrid run with the host; recorded AI reasons remain usable after the bounded model-call budget is spent. Use the local host if public sharing fails, and labelled recorded captures if local/live data is unavailable.

The full timed four-person rehearsal and Echenique's additional installation/CRUD record still need confirmation. These are operating/rehearsal checks; the archive includes the code and instructions needed to perform them. This package is not automatically uploaded or submitted to the campus.

## Historical material

The original Flask/Grafana app, Clickstream Lab, earlier measurements and old slide files remain as project history. Their dates, datasets, speaker allocations and pending sections do not override the current guides. Start with [history/README.md](history/README.md) if that background is relevant. The current presentation is the 14-slide HTML linked above.
