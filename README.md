# Delivery Atlas

Delivery Atlas is a fictional food-delivery platform whose analytical events are stored and queried in ClickHouse. A Python API accepts customer actions, order snapshots and GPS positions into a persistent queue, publishes batches, and serves English dashboards with a real Madrid basemap and simulated couriers.

**[Final delivery index](docs/FINAL-DELIVERY.md)** · **[Installation](docs/ATLAS-INSTALL.md)** · **[Demo and rehearsal](docs/DEMO-GUIDE.md)** · **[Current database model](docs/DATABASE-STRUCTURE.md)**

## Presentation

Use [the approved 14-slide HTML](presentaciones/final-2026-11-11/Delivery-Atlas.html), its [matching English script](presentaciones/final-2026-11-11/SCRIPT-EN.md) and the [four-speaker route](docs/PRESENTATION.md). Download/extract and open the HTML in a browser; GitHub displays its source. The presentation has embedded static resources and works offline. Live data and map tiles require their own running services/network.

The first ten slides retain the prepared checkpoint; four appended slides describe the GPS experiment and future work. The HTML, figures, script and speaking allocation remain unchanged. [Technical clarifications](docs/DEFENCE-NOTES-EN.md) explain current terminology and evidence alongside that retained wording.

## Start a small local installation

Install Docker with Compose, Git and Python 3.10 or newer. From the repository root:

```bash
docker compose -f compose.yaml --profile atlas up -d --build --wait
python3 -m unittest discover -s tests
python3 scripts/check_atlas.py
```

On Windows use `python` instead of `python3`. Open the dashboard at <http://127.0.0.1:8001/>, analytics at <http://127.0.0.1:8001/analytics.html>, and the mini-app at <http://127.0.0.1:8001/delivery.html>. Start a traffic simulation from the host dashboard. The [installation guide](docs/ATLAS-INSTALL.md) explains expected integration-test skips, optional AI, public datasets and common problems. Large source downloads are optional.

Updating an existing host requires the pause, queue-drain, export and volume-preservation steps in [DEMO-GUIDE.md](docs/DEMO-GUIDE.md). A second checkout can select a different Compose project and volumes; do not use it as a shortcut to replace the demo host.

## ClickHouse in the project

| View or path | Analytical work |
|---|---|
| Operations and Madrid map | Latest courier/order state from `argMaxState` and `argMaxMerge`; recorded GPS history and position age |
| Customer Journey | Unique session cohort and ordered 30-minute `windowFunnel` over one run, with replacement copies removed |
| ClickHouse Performance | Engines, sort keys, active parts, compression and completed query families from `system.query_log` |
| Criteo and Glovo explorers | Fixed analytical SQL over separate public advertising and catalog tables |
| Isolated GPS experiment | Equal-position verification, frozen input, repeated bounded reader concurrency and query-log evidence |

Dashboard definitions and cache/measurement boundaries are in [CLICKHOUSE-DASHBOARDS.md](docs/CLICKHOUSE-DASHBOARDS.md). Public access is read-only: simulation controls, checkout, SQL and CRUD stay on the local host.

## Data and evidence

Atlas simulation and manual actions retain explicit provenance. Local AI contributes bounded decisions; rule-based traffic generates most of the volume. Public datasets remain separate by population and meaning: a catalog product is not an observed order.

[The host record dated 15 November](docs/HOST-STATUS-2026-11-15.md) reports Anuar's 21 verified exports with **37,310,637 rows**, and **23,978,916 GPS positions** in ClickHouse. All 21 [committed manifests and their run log](docs/SIMULATION-RUNS.md) are included. The [inventory](docs/INVENTORY-2026-11-15.md) has 37,310,669 logical event rows in ClickHouse, including 32 browsing events without a run ID that are outside the run archives. Neither inventory total is the timed benchmark's corpus.

The [GPS comparison](docs/GPS-BENCHMARK.md) uses **4,371,300 positions and 150 couriers** in a separate 2-CPU/2-GiB lab. With two concurrent readers, history client p95 is **1,625–1,969 ms**, compared with **266–281 ms** for prepared state. The received campaign has 2,400 successful measured requests and complete server-log joins. This is a comparison of two designs inside ClickHouse under a one-second target; cross-database measurements and view-maintenance costs remain future work.

## Documentation and delivery

- [Fundamentals and limitations](docs/FUNDAMENTALS.md), [applied theory](docs/APPLIED-THEORY.md) and [current schema](docs/DATABASE-STRUCTURE.md).
- [Architecture and ingestion](docs/ATLAS-INFRASTRUCTURE.md), [AI customers](docs/AI-CUSTOMERS.md), [mini-app](docs/MINIAPP.md) and [sharing](docs/SHARING-VERCEL.md).
- [Requirements and completion record](docs/ASSIGNMENT.md), [installation records](docs/TEAM-INSTALL-TESTS.md), [sources and AI assistance](docs/AI-USE-AND-SOURCES.md).
- [Repository map](docs/REPOSITORY-MAP.md) and [project decisions](docs/PROJECT-DECISIONS.md).

The public site is <https://delivery-atlas-demo.vercel.app>. Availability depends on Anuar's host, authenticated gateway and current tunnel origin. The dated host record distinguishes his local checks from the public connection; a READY frontend deployment alone does not prove data access.

## Earlier work

The repository retains the first Flask/Grafana app and the larger Clickstream Lab. They explain the project's evolution and historical measurements; they are not required for the small Atlas installation or the prepared talk. OTTO, REES46 and Ele.me are optional legacy sources and are not loaded on Anuar's current host.

See [historical material](docs/history/README.md), [legacy installation](docs/INSTALLATION.md), [legacy demo](docs/DEMO.md), [legacy measurements](docs/RESULTS.md) and the separate [one-million-event Atlas benchmark](docs/ATLAS-RESULTS.md). Historical row meanings and machine-specific timings must retain their dates and conditions.
