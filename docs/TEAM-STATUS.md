> **Extension of 14 Oct:** the local AI customer agent now exists, with the checkout → purchase → statuses → GPS link. [Guide to the extension](AI-CUSTOMERS.md). The manual mini-app and other pending points from this earlier review remain separate.

> Historical record: dates, results, speaker allocations and pending statements below describe their original stage. For the current implemented project, 14-slide route and delivery status use [FINAL-DELIVERY.md](FINAL-DELIVERY.md), [DATABASE-STRUCTURE.md](DATABASE-STRUCTURE.md) and [DEMO-GUIDE.md](DEMO-GUIDE.md).

# Project status for the team

## Update of 7 October 2026

**Later extension on the same day:** Jere asked to continue with Rayo until the team joins. Synthetic Madrid tracking, position/status tables, a demo catalog and an operations dashboard on port 8001 were added. See [DATA-AND-TRACKING.md](DATA-AND-TRACKING.md): it is the current status. The work split and PDF described below are the earlier proposal, not tasks we are waiting on.

The v1 infrastructure has been implemented in `delivery_atlas`: SQL, contract, Python API in Docker, persistent SQLite queue, publisher and generator. The delivery mini-app and the dedicated dashboard are still pending. The split is **Jere: database and ingestion; Anuar: mini-app; Echenique: dashboard and reproduction**. Read [TEAM-PLAN.md](TEAM-PLAN.md) and [ATLAS-INFRASTRUCTURE.md](ATLAS-INFRASTRUCTURE.md).

The applied SQL is `sql/atlas.sql`, with `ReplacingMergeTree` for the detail and ID sets in `AggregatingMergeTree` for the logical counts. The queue accepts retries with the same ID and content; a change of content returns a conflict. The API is on port 8001. The historical lab keeps its database and dashboards.

**Guide for the three of us:** [team PDF](../output/pdf/Delivery-Atlas-Guia-Equipo.pdf). One million synthetic events, retries and recovery after orderly shutdowns were verified. Detail and aggregate match, but the aggregate was not faster in the new test. [Results and conditions](ATLAS-RESULTS.md).

The following sections are the snapshot of 5 October, before this implementation. Their figures describe the historical sources and are not reused as benchmarks of the new database.

Update: 5 October 2026. This document describes what has been implemented and separates the proposals the group still has to decide on.

## What is done

- ClickHouse 25.8 in one Docker node, persistent volume and Python API.
- Loading, validation and dashboards for real sources; Python and SQL scripts.
- Materialized view and daily aggregate for OTTO.
- Replay of historical events while the dashboard is queried, and new clicks from the page itself, in separate tables.
- Insert, query, update and delete script on a scratch table.
- Installation, fundamentals, demo and results documentation; navigable slides.

| Source | Load verified on the development machine | Role |
|---|---:|---|
| OTTO | 216,716,096 events; 194,720,954 clicks | Volume, clicks and aggregation |
| REES46 | 411,709,736 events, seven months | Time, categories, brands, views, carts and purchases |
| Ele.me | 2,170,299 samples; 38,914 positive labels | Food-delivery recommendations in China; first ZIP D1_0 |
| Glovo FooDI-ML | 2,887,444 products; 415,137 from Spain | Catalog, no clicks or sales |
| Stress test derived from OTTO | 1,083,580,480 rows | Five derived scenarios; not new observations |

OTTO and REES46 add up to 628,425,832 real events from different populations. The Ele.me samples and the Glovo products are not mixed into that total. There are no common identifiers to attribute Ele.me clicks to Spanish Glovo products.

## Technical evidence

- Same daily OTTO aggregation: 5.8908 s from the history vs 0.2113 s from the aggregate; identical answers and SQL cache disabled. Median of three local runs.
- Grouping by scenario over 1,083,580,480 derived rows: 1.4357 s, one local run.
- Count of Ele.me positive labels: median of 0.0581 s for 2,170,299 rows, three local runs.
- Reading the full Ele.me JSON exhausted the local total memory limit of 3.50 GiB. No timing comparison between JSON and a typed column was completed.

These results do not compare ClickHouse with PostgreSQL nor establish performance on another machine. The original reports are in `data/*benchmark.json`; [RESULTS.md](RESULTS.md) and [ELEME.md](ELEME.md) explain conditions and limits.

## What GitHub contains

Code, SQL, Docker configuration, dashboards, documentation, result screenshots and small measurement reports. The ZIP/CSV files and the Docker volume are **not uploaded**: cloning the repository does not download the millions of rows. The instructions link to the sources and allow the data to be loaded. Ele.me requires a Tianchi account and reviewing its terms; the file is not redistributed.

For this version use `compose.yaml` and [INSTALLATION.md](INSTALLATION.md). Files from the earlier Flask/Grafana version of the repository are kept; their instructions, ports and metrics do not describe this implementation. The old presentations and dashboards from the first approaches are working material, not the final script.

## Fit with the assignment

There are real datasets, a dashboard, Python integration, CRUD, a columnar model and measurements. The guides cover installation, architecture, consistency, scaling and critical reflection. One node has been run: replication and sharding across nodes are explained, not demonstrated. The professor confirmed ClickHouse as the group's technology (19 October 2026). It uses SQL and should be presented as a columnar analytical engine. Requirements and the status of each one: [ASSIGNMENT.md](ASSIGNMENT.md).

## Project direction and pending decisions

**Delivery Atlas: analytics infrastructure for a fictional food-delivery platform.**

**New direction suggested by the professor and adopted by the group:** define a fictional food-delivery platform, with an analytics infrastructure for its events. The browsing path and a massive load can be simulated and must be labelled as such. An event contract and adapters would allow future real data to be added without changing every query and dashboard. See [FICTIONAL-PLATFORM.md](FICTIONAL-PLATFORM.md).

The [database map](DATABASE-STRUCTURE.md) explains the current lab and the proposed model. The [progress presentation and its notes](PROGRESS-UPDATE.md) are in English, last 5 minutes and prioritize structure and status. The [theory review](THEORY-REVIEW.md) identifies idempotency, ingestion metrics and full reproduction of the environment as the next adjustments.

The complete platform and the common contract are not implemented yet. The current infrastructure and datasets are the working base: OTTO demonstrates scale and ingestion; Ele.me provides real recommendations from the industry; REES46 extends the time dimensions; Glovo provides a Spanish catalog; the derived table serves as an optional stress test. Their results do not yet establish the performance of the future fictional platform.

Next decisions:

1. Settle which sources go into the 30 minutes and which remain supplementary material.
2. Align slides and documentation with that scope; Ele.me is integrated, but the main script is still centred on OTTO.
3. Rehearse a short demo of ingestion, dashboard and query comparison; CRUD on a scratch table.
4. Test the installation from scratch on another machine, with a reduced-volume path if needed.
5. Later, consider two nodes or a comparison of sort keys. There is already enough volume for the class; downloading more data is not a pending requirement of the project.
6. Define the fictional platform, its event contract, the simulated load and the adapters for future sources. Validate the infrastructure with semi-real data and with the available public datasets, keeping their provenance.

The data is historical. The replay demonstrates current ingestion of old events; the page buttons produce the only new actions in the demo. There is no live connection to Uber Eats, Glovo or Ele.me.
