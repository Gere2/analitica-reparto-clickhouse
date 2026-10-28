# Delivery Atlas — analytics infrastructure for a delivery platform

BD2 project to design the analytics infrastructure of a fictional food-delivery platform. The goal is to receive massive browsing events, keep their provenance and feed a dashboard with ClickHouse. The current implementation, called Clickstream Lab in the OTTO dashboard, provides the data and performance lab on which we build that case.

**Project brief and checklist:** [docs/ASSIGNMENT.md](docs/ASSIGNMENT.md) summarizes what the assignment asks for and where each requirement is covered.

**ClickHouse dashboards:** the English analytics portal at `/analytics.html` brings together Customer Journey, ClickHouse Performance and five historical analyses. Every view exposes its source, fixed SQL and server statistics. The Madrid map remains on the live operations page. See [the dashboard guide](docs/CLICKHOUSE-DASHBOARDS.md) for scope, deployment requirements and query interpretation.

**Concurrent traffic:** mixed mode with **200 customers (3 AI + 197 simulated) and 80 couriers**, up to 500/150 from the controls. Customers in batches, varied pauses, linked purchases and an activity summary; [guide](docs/AI-CUSTOMERS.md), test with `python3 scripts/check_traffic.py` on the active scenario.

**Commercial mini-app (14 Oct):** http://127.0.0.1:8001/delivery.html. A person searches, filters, opens a restaurant, fills the cart and checks out. Every action goes to `POST /api/events` (`demo_live`) and checkout (`POST /api/checkout`) creates a real order in the simulation, which is delivered and tracked by GPS. It requires clicking "Start customers and delivery" on the dashboard. [Guide, events and verification](docs/MINIAPP.md).

**AI customers connected to delivery (14 Oct):** [start, schema and verification](docs/AI-CUSTOMERS.md). A local Qwen3 model decides actions; checkout creates the same order that gets assigned and tracked on the map. Fictional purchases and positions, no payment. Enable the `atlas` and `ai` profiles, download the model as the guide explains and open http://127.0.0.1:8001/.

**Technical guide for the team (14 Oct):** [full PDF](output/pdf/Delivery-Atlas-Documento-Tecnico-Equipo.pdf) and [editable version](docs/TEAM-TECHNICAL-GUIDE.md). It explains technologies, architecture, contracts and columns, ingestion, simulation, queries, sharing and the limits of the tests. It reviews the current code; the measurements included are from 7 Oct.

**To understand it quickly:** [4-page visual guide](output/pdf/Delivery-Atlas-Guia-Visual-Equipo.pdf), with a connection diagram, record types and first steps for Anuar and Echenique. [Editable summary](docs/TEAM-VISUAL-GUIDE.md).

**Update of 7 October:** the fictional platform already has a validated contract, a durable queue, batch publishing, SQL applied in `delivery_atlas`, a reproducible generator and an operations dashboard. The commercial mini-app is the next delivery. [Plan for Jere, Anuar and Echenique](docs/TEAM-PLAN.md) and [full infrastructure guide](docs/ATLAS-INFRASTRUCTURE.md).

**To split the work today:** [team guide in PDF](output/pdf/Delivery-Atlas-Guia-Equipo.pdf). [Tests of the new database](docs/ATLAS-RESULTS.md): one million verified synthetic events, retries and recovery after a restart. The exact aggregate preserves the result, but it does not yet improve on the speed of the detail table in this test.

**Live operations extension:** [kept data, columns, ingestion and tracking](docs/DATA-AND-TRACKING.md). Dashboard at **http://127.0.0.1:8001/**, with control of a simulated Madrid fleet, positions every two seconds, orders/statuses/fictional amounts, browsing and catalog. New tables in `sql/atlas_operations.sql`. Jere and Rayo continue the implementation; the split in the earlier PDF remains a proposal for when the team joins.

[Demo walkthrough and troubleshooting](docs/TRACKING-DEMO.md). Additional verified load: **100000 positions and 5965 synthetic statuses**, on top of the earlier browsing data. The two-second interval is a setting: the dashboard shows the observed delay and does not guarantee instant delivery.

### Getting started with the new platform, without downloading large datasets

```bash
docker compose -f compose.yaml --profile atlas up -d --build --wait
python3 -m unittest discover -s tests -v
python3 scripts/check_atlas.py
python3 scripts/atlas.py generate --events 10000 --batch 1000 --seed 42
python3 scripts/atlas.py status
```

On Windows, use `python` instead of `python3`; see [TEAM-INSTALL-TESTS.md](docs/TEAM-INSTALL-TESTS.md).

API at `http://127.0.0.1:8001`, SQL in [sql/atlas.sql](sql/atlas.sql), filters in `/api/summary`. 202 confirms receipt in the queue; publishing to ClickHouse happens afterwards. The historical lab and its figures are described below and keep their `delivery` database.

**Database structure:** [map of the lab and its evolution](docs/DATABASE-STRUCTURE.md). `sql/propuesta_delivery.sql` keeps the first design; the v1 implementation uses `sql/atlas.sql` with an aggregate of unique IDs to handle retries.

**5-minute progress update, in English:** [simplified navigable presentation](http://127.0.0.1:8000/avance-bd.html), [editable PowerPoint](presentaciones/Delivery-Atlas-Simple-EN.pptx) and [bilingual cheat sheet in PDF](output/pdf/Delivery-Atlas-Cheat-Sheet-Simple-EN-ES.pdf). The walkthrough presents the project, ClickHouse, the data sources, the proposed ingestion and schema, a speed test and the next steps. There are also [editable notes](docs/PRESENTER-NOTES.md). The [review against the professor's notes](docs/THEORY-REVIEW.md) explains what fits and what is missing.

**For the team:** [project status and pending decisions](docs/TEAM-STATUS.md). The historical lab uses `compose.yaml`, the Python API `dashboard.py` and its dashboards in `web/`; the new Atlas infrastructure uses the `atlas` profile of the same Compose file and `atlas/server.py`. The repository also keeps files from the earlier Flask/Grafana implementation; follow [INSTALLATION.md](docs/INSTALLATION.md) to pick the right path.

| Source | What it represents | Volume |
|---|---|---:|
| [OTTO Recommender Systems Dataset](https://github.com/otto-de/recsys-dataset) | Real anonymized clicks, carts and orders | **216,716,096 events**, including **194,720,954 clicks** |
| [REES46 Marketplace](https://data.rees46.com/) | Real views, carts and purchases from a marketplace | **411,709,736 events** in seven monthly files, October 2019 to April 2020 |
| Stress scenarios | Five OTTO variants generated with SQL to measure queries; **not new users or clicks** | **1,083,580,480 derived rows** |
| [Ele.me · Tianchi](https://tianchi.aliyun.com/dataset/131047) | Food-delivery recommendation samples from China, with a binary click label | **2,170,299 samples loaded**, including **38,914 positive click labels**, from the first part D1_0; 146 M declared for the full dataset |

This is not data from Uber Eats, Glovo or necessarily from Spain. REES46 does not identify the marketplace's country. A REES46 view is not equivalent to an OTTO click either. The link with a delivery app lies in the **type of analytical work**: recording browsing events, showing them by time, category and brand, and querying the store without scanning its rows one by one.

The two sources add up to **628,425,832 rows of real events**, although they represent different populations and actions. The derived table of more than a billion rows is used only to test scale.

## What can be shown live

- [OTTO clicks dashboard](http://127.0.0.1:8000/): real archive, historical replay at a configurable pace and genuinely new clicks from the page, in three separate tables.
- [REES46 marketplace dashboard](http://127.0.0.1:8000/rees46.html): monthly volume, action type, categories, brands and a month filter over ClickHouse.
- [Scale dashboard](http://127.0.0.1:8000/scale.html): separates real events from derived rows, shows size on disk and the benchmark measurements.
- [Ele.me dashboard](http://127.0.0.1:8000/eleme.html): **2,170,299 real samples** from the food-delivery recommender, grouped by day, hour, anonymous city and meal period; [access, inspection and loading](docs/ELEME.md). Only the first official ZIP D1_0 is loaded; these are not 146 million clicks.
- **Archive vs aggregate:** a materialized view summarizes 216,716,096 OTTO events into 87 day-and-type keys, keeping the same result for that question. `scripts/benchmark.py` records time, rows and bytes read.
- **Billion-row test:** `delivery.otto_scale_benchmark` makes it possible to query 1,083,580,480 derived rows on a local machine, with `scenario` to mark their origin.
- **Reproducible measurement:** on this machine, grouping OTTO by day and type took 5.89 s from the archive vs 0.21 s from the aggregate (same answer, SQL cache disabled); grouping 1,083,580,480 rows by scenario took 1.44 s. Conditions and bytes read are in [RESULTS.md](docs/RESULTS.md).
- Python connected to ClickHouse for loading, replay, queries, and update and delete on a scratch table.

## Architecture

```text
OTTO ZIP JSONL ── Python ETL ──→ otto_archive (216.7 M real) ── MV ──→ otto_daily_rollup
                                       │
                                       ├─ SQL × 5 → otto_scale_benchmark (1,083,580,480 derived)
                                       └─ Python replay → otto_replay ───────┐
REES46 CSV.gz × 7 ── Python ETL → rees46_events ─────────────────────────────┤
Ele.me CSV ZIP → staging → full validation → eleme_samples ─────────────────┤
User → web buttons → Python API → live_clicks ───────────────────────────────┤
                                                     Python API → dashboards ┘
```

ClickHouse 25.8 runs in one Docker node. Data is stored in `MergeTree` tables; the daily materialized view uses `SummingMergeTree`. The browser queries a Python API, which in turn queries ClickHouse. The replay inserts historical events **now**, with an `ingested_at` different from the original `event_time`; it is not presented as a live public feed.

## Setup

```bash
docker compose -f compose.yaml up -d
python3 scripts/eleme.py init
python3 scripts/otto.py download
python3 scripts/otto.py load
python3 scripts/rollup.py
python3 scripts/rees46.py download
python3 scripts/rees46.py load
python3 scripts/scale.py
python3 scripts/benchmark.py
python3 scripts/check.py
python3 scripts/report.py
python3 dashboard.py
```

Prepare the loads before class. For the demo:

```bash
python3 scripts/otto.py replay --rate 5000 --limit 200000 --reset
python3 scripts/crud_demo.py
```

The short path runs only OTTO, the rollup and the dashboard. The full path needs extra space and time; see [INSTALLATION.md](docs/INSTALLATION.md). The OTTO ZIP comes from a [public mirror](https://huggingface.co/datasets/hazemessam/otto-recsys) and is verified by SHA-256 and by the three counts published by OTTO. The seven REES46 CSV.gz files are downloaded from the publisher and checked by size, decompression and rows loaded per month.

**Class material:** [installation guide](docs/INSTALLATION.md), [10-minute demo](docs/DEMO.md), [20-minute script](docs/PRESENTATION.md), [fundamentals and limits](docs/FUNDAMENTALS.md), [measured results](docs/RESULTS.md) and [navigable slides](http://127.0.0.1:8000/otto-presentacion.html).

## Sharing the dashboard

**Public read-only demo:** https://delivery-atlas-demo.vercel.app. The database and the simulator remain local: tracking updates while Jere's computer, Docker and the tunnel stay up. See [the sharing guide](docs/SHARING-VERCEL.md) for start-up, private variables, deployment and shutdown.
