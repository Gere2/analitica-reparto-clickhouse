# Repository map

What every folder and file in this repository is, and whether it is part of the current demo. Updated on 19 October 2026 for the team branch with the mini-app, English translation and shared-demo recovery: 185 tracked files.

## The repository in one minute

The repository contains **three generations** of the same project. Knowing which one a file belongs to explains almost everything:

| Generation | What it is | ClickHouse database | Start / port | Status |
|---|---|---|---|---|
| **1. First app** | Flask web app + Grafana, events from a small "reparto" app, Criteo/MT-LIFT datasets | `reparto` | `docker-compose.yml`, ports 8080 (app) and 3000 (Grafana) | **Old.** Kept but not used; it does not reproduce Atlas |
| **2. Data lab** ("Clickstream Lab") | Large public datasets (OTTO, REES46, Ele.me, Glovo, Meituan TRD) and a billion-row scale test, with dashboards | `delivery` | `compose.yaml` + `python3 dashboard.py`, port 8000 | **Lab.** Shows volume and query speed. Needs tens of GB of downloads; fully loaded only on Jere's computer |
| **3. Delivery Atlas** | Fictional delivery platform: event API, durable queue, simulated customers and couriers, GPS tracking, mini-app | `delivery_atlas` | `compose.yaml --profile atlas`, port 8001 | **Current.** The main path for the presentation; starts with one command and no large downloads |

Generations 2 and 3 share the same ClickHouse container (`bd2-clickhouse`, host port 8124) but use different databases. Generation 1 uses its own containers and must not run at the same time (it shares the Compose project name).

**Labels used below:** **Atlas** = current platform · **Lab** = large-dataset lab · **Old** = first app · **Docs** = documentation · **Tooling** = build, sharing or test helpers.

## Root of the repository

| File | Label | What it is |
|---|---|---|
| `README.md` | Docs | Entry point: what the project is, quick start for Atlas, the datasets and the lab |
| `PRODUCT.md` | Docs | Product brief: users, purpose, constraints and principles (used by design tooling) |
| `DESIGN.md` | Docs | Visual design notes for the Atlas dashboard (colours, layout, structure) |
| `compose.yaml` | Atlas + Lab | Docker Compose: `clickhouse` (always), `atlas` API (profile `atlas`) and `ollama` local AI (profile `ai`) |
| `Dockerfile.atlas` | Atlas | Image for the Atlas API: Python 3.12 slim, copies `atlas/`, the Atlas SQL and `web/` |
| `clickhouse-config.xml` | Atlas + Lab | ClickHouse server settings: limits background merges to four so the demo machine keeps memory free |
| `dashboard.py` | Lab | Python backend of the lab dashboards on port 8000 (`/api/otto`, `/api/rees46`, `/api/scale`, `/api/eleme`, `/api/glovo`, `/api/live-click`) |
| `compose.share.yaml` | Tooling | Extra Compose file to share the dashboard: read-only gateway + Cloudflare tunnel |
| `Dockerfile.share` | Tooling | Image of the read-only sharing gateway (`atlas/share.py`) |
| `vercel.json` | Tooling | Vercel configuration of the public read-only website |
| `.vercelignore` | Tooling | Only the dashboard files, the proxy and the build script are uploaded to Vercel |
| `.dockerignore` | Tooling | Keeps data, PDFs and presentations out of Docker images |
| `.gitignore` | Tooling | Keeps datasets, `.env`, secrets and build output out of Git |
| `.gitattributes` | Tooling | Binary files (PDF, PPTX, PNG) and LF line endings for `.sh` scripts |
| `docker-compose.yml` | Old | Compose file of generation 1 (Flask app + ClickHouse + Grafana) |
| `.env.example` | Old | Passwords template for `docker-compose.yml` |

## `atlas/` — the Atlas API (current platform)

A single Python process, standard library only, served on port 8001. It receives events, stores them durably, publishes them to ClickHouse and serves the dashboard and the mini-app.

| File | What it does |
|---|---|
| `server.py` | HTTP server and routes (`/api/events`, `/api/checkout`, `/api/order`, `/api/operations`, `/api/simulation/*`, `/api/status`, `/api/summary`…) plus the batch **publisher** thread |
| `store.py` | Durable SQLite queue (*outbox*): accepts events, detects retries and conflicts by `event_id` and a SHA-256 fingerprint, applies backpressure |
| `clickhouse.py` | Minimal ClickHouse client over HTTP: applies the SQL at start-up, inserts batches and runs the dashboard queries |
| `contract.py` | Validation of browsing events (contract v1): required fields, allowed actions, dates and provenance |
| `operations.py` | Validation of GPS positions and order snapshots |
| `simulation.py` | Simulated Madrid fleet and the start/stop of every simulation mode |
| `commerce.py` | Rules of the fictional shop: carts, budgets, checkout, courier assignment, delivery and GPS |
| `customer_agent.py` | Who decides for each customer: local AI (Ollama), local test policy or traffic simulator |
| `customer_runtime.py` | Threads that run customers and GPS, committing to the queue before changing state |
| `catalog.py` | Seeds the demo catalog: 12 fictional restaurants and 36 dishes |
| `share.py` | Read-only gateway used when the dashboard is shared publicly |
| `__init__.py` | Marks the folder as a Python package |

## `web/` — what the browser shows

| Files | Label | What it is |
|---|---|---|
| `atlas-dashboard.html` / `.js` / `.css` | Atlas | Live operations dashboard at http://127.0.0.1:8001/: customers, fleet map, orders, browsing, data inventory |
| `delivery.html` / `.js` / `.css` | Atlas | Commercial mini-app at http://127.0.0.1:8001/delivery.html: search, cart, checkout and tracking |
| `favicon.svg` | Atlas | Browser tab icon |
| `index.html`, `otto.js`, `otto.css` | Lab | OTTO clicks dashboard (port 8000) |
| `rees46.html` / `.js` / `.css` | Lab | REES46 marketplace dashboard |
| `scale.html` / `.js` / `.css` | Lab | Scale dashboard: real vs derived rows, disk size, benchmark |
| `eleme.html` / `.js` / `.css` | Lab | Ele.me recommendation samples dashboard |
| `glovo.html`, `glovo.js` | Lab | Glovo catalog dashboard |
| `meituan.html` | Lab | Earliest dashboard, for the Meituan TRD dataset ("Radar Delivery") |
| `app.js`, `style.css` | Lab | Shared script and styles of the lab dashboards |
| `avance-bd.html`, `assets/avance-*.png` | Docs | Browser version of the 5-minute progress presentation (served on port 8000) |
| `otto-presentacion.html`, `presentacion.html`, `presentacion-delivery.html` | Docs | Earlier slide decks in HTML, from previous stages of the project |

The lab pages are still in Spanish.

## `sql/` — database schemas and demo queries

| File | Label | What it is |
|---|---|---|
| `atlas.sql` | Atlas | Browsing events (`app_events`) and the daily aggregate with unique IDs |
| `atlas_operations.sql` | Atlas | Demo catalog, GPS positions, order statuses and their "latest state" views |
| `atlas_agents.sql` | Atlas | Customer activity, purchases (`customer_orders`) and latest customer state |
| `atlas_miniapp.sql` | Atlas | Adds `demo_live` to the purchases' `source_kind`, for mini-app orders |
| `atlas_consultas.sql` | Atlas | Queries to explain the browsing model in class |
| `atlas_tracking_consultas.sql` | Atlas | Queries to explain tracking in class |
| `schema.sql` | Lab | Tables of the lab: OTTO (archive, replay, daily rollup, billion-row test), REES46, Glovo, Meituan TRD, live clicks from the lab page and the CRUD scratch table `demo_events` |
| `eleme.sql` | Lab | Ele.me sample and staging tables |
| `criteo.sql` | Atlas + Lab | `delivery.criteo_uplift`: the Criteo Uplift v2.1 advertising experiment, shown in the dashboard's "Downloaded datasets" view |
| `propuesta_delivery.sql` | Docs | First design of the platform's tables (5 October). Never applied; replaced by `atlas.sql` |

The four Atlas schema files are applied automatically when the API starts.

## `scripts/` — command-line tools

Run them from the repository root with `python3` (or `python` on Windows).

**Atlas**

| Script | What it does |
|---|---|
| `atlas.py` | `generate` a reproducible load of browsing events; `status` of the queue and counts |
| `operations.py` | Load a reproducible historical GPS/order scenario through the API |
| `check_atlas.py` | Integration check: retries, conflicts, lost responses, detail = aggregate |
| `check_operations.py` | Tracking check: out-of-order GPS, invalid coordinates, failure between INSERTs. **Overwrites `docs/evidencia-tracking.json`** |
| `check_customer_agent.py` | End-to-end check with the real AI model: decision → purchase → delivery → GPS |
| `check_traffic.py` | Checks a running 200-customer / 80-courier scenario |
| `recover_atlas.py` | Recovery exercise: stops and restarts the local services (never deletes volumes) |
| `benchmark_atlas.py` | Compares the same logical count on the detail table and on the aggregate |
| `crud_demo.py` | The INSERT / SELECT / UPDATE / DELETE demo required by the assignment, on a scratch table |

**Lab: loading the public datasets**

| Script | What it does |
|---|---|
| `otto.py` | Download, verify, load and replay the OTTO clickstream (216.7 M events) |
| `rollup.py` | Backfill and check the OTTO daily materialized view |
| `rees46.py` | Download and load the seven REES46 monthly files (411.7 M events) |
| `scale.py` | Build the labelled billion-row stress table from OTTO |
| `eleme.py` | Inspect, validate and load Ele.me ZIP files through a staging table |
| `glovo.py` | Download and load the Glovo FooDI-ML catalog |
| `criteo.py` | Download, verify and load the Criteo Uplift v2.1 dataset (14.0 M rows) into the Atlas ClickHouse |
| `download.py`, `prepare.py`, `load.py` | Download, transform and load the Meituan TRD dataset |

**Lab: measuring and reporting**

| Script | What it does |
|---|---|
| `benchmark.py` | Raw vs aggregated OTTO query benchmark → `data/query-benchmark.json` |
| `eleme_report.py` | Ele.me column vs raw JSON measurement → `data/eleme-benchmark.json` |
| `check.py` | Audits counts and provenance of the lab before a demo |
| `report.py` | Writes `docs/RESULTS.md` from the manifests and benchmarks |

**Tooling**

| Script | What it does |
|---|---|
| `build_technical_guide.py` | Builds the technical PDF from `docs/TEAM-TECHNICAL-GUIDE.md` (needs ReportLab) |
| `build_team_guide.py` | Builds the team guide PDF (content written inside the script) |
| `build_visual_guide.py` | Builds the 4-page visual guide PDF |
| `build_shared.mjs` | Prepares the read-only dashboard for Vercel (removes the controls) |
| `start_shared_demo.py` | Starts the current shared lab, checks its authenticated tunnel and optionally updates and deploys the linked Vercel project |

**Old (generation 1)**

| File | What it is |
|---|---|
| `simular_sesiones.py` | Simulated sessions for the first app's `eventos_app` table |
| `cargar_criteo.sh` | Loads the Criteo Uplift CSV into the first app's database |
| `consultas_demo.sql` | Demo queries of the first app |

## `tests/` — automated tests (42 in Python, 7 in JavaScript)

Run with `python3 -m unittest discover -s tests -v` and `node --test tests/test_delivery_ui.cjs`. They need no downloads. Two Python tests need a disposable ClickHouse and are skipped unless `ATLAS_TEST_CLICKHOUSE_URL` is set (see `docs/MINIAPP.md`).

| File | Tests | What it checks |
|---|---:|---|
| `test_atlas.py` | 4 | Queue: retries, conflicts, atomic batches, full queue, invalid contract |
| `test_commerce.py` | 9 | Checkout linked to the order, budgets, rollback, courier continuity, clock race |
| `test_miniapp.py` | 13 | Mini-app checkout: prices computed by the server, idempotent retries, delivery of the same order, `/api/order` tracking outside the dashboard's 200-order window |
| `test_delivery_ui.cjs` | 7 | Mini-app JavaScript: cart locked during checkout, concurrent confirmations, retries, stale tracking responses |
| `test_operations.py` | 5 | GPS and order validation, routing, chronology, deterministic simulation |
| `test_share.py` | 2 | Allowed routes and parameters of the sharing gateway |
| `test_operations_reader.py` | 3 | Concurrent HTTP viewers share one snapshot, expired results refresh, failed reads retry |
| `test_shared_start.py` | 2 | Uses the newest complete Quick Tunnel origin and rejects unrelated hosts |
| `test_data_views.py` | 4 | Downloaded-datasets summary (missing, empty and loaded tables), its gateway route, and AI agents versus simulated customers counted apart in a real ClickHouse |

## `docs/` — documentation

**Start here**

| File | What it is |
|---|---|
| `REPOSITORY-MAP.md` | This document |
| `ASSIGNMENT.md` | The assignment brief in our words and the checklist of every requirement |
| `ATLAS-INFRASTRUCTURE.md` | Atlas architecture, start-up, SQL model, API contract and limits |
| `TEAM-INSTALL-TESTS.md` | Installation test on Windows and common problems |
| `MINIAPP.md` | The commercial mini-app: events, checkout, verification |
| `TRACKING-DEMO.md` | Step-by-step tracking demo and troubleshooting |

**Theory and design**

| File | What it is |
|---|---|
| `FUNDAMENTALS.md` | ClickHouse fundamentals: type, uses, data model, consistency, interfaces, limits, comparison |
| `APPLIED-THEORY.md` | Each course concept and the Atlas decision it justifies |
| `THEORY-REVIEW.md` | Review of the project against the professor's notes |
| `DATABASE-STRUCTURE.md` | Database structure: lab tables and the Atlas model |
| `DATA-AND-TRACKING.md` | Inventory of kept data, tracking tables and how the latest position is computed |
| `FICTIONAL-PLATFORM.md` | Original scope and design of the fictional platform |
| `AI-CUSTOMERS.md` | AI and simulated customers, purchases and concurrent traffic |
| `TEAM-TECHNICAL-GUIDE.md` | Long technical guide for the team (source of the technical PDF) |
| `TEAM-VISUAL-GUIDE.md` | Short visual summary (source of the visual guide PDF) |

**Results**

| File | What it is |
|---|---|
| `RESULTS.md` | Lab measurements: OTTO, REES46, billion-row test (generated by `report.py`) |
| `ATLAS-RESULTS.md` | Atlas measurements: one million events, retries, recovery, detail vs aggregate |

**Datasets and lab**

| File | What it is |
|---|---|
| `INSTALLATION.md` | Installation of the large-dataset lab |
| `DEMO.md` | 10-minute demo script of the lab |
| `ELEME.md` | Ele.me dataset: source, loading, measurements |
| `GLOVO.md` | Glovo catalog: source, counts, limits |
| `LEGACY-DATASETS.md` | Datasets of the first app (MT-LIFT, Criteo, Madrid census) — **Old** |

**Team and presentation**

| File | What it is |
|---|---|
| `TEAM-STATUS.md` | Project status and pending decisions |
| `TEAM-PLAN.md` | Initial split of work between Jere, Anuar and Echenique |
| `PRESENTATION.md` | Earlier 20-minute script (Clickstream Lab); still to be rewritten for Atlas |
| `PROGRESS-UPDATE.md` | Speaker guide of the 5-minute progress update |
| `PRESENTER-NOTES.md` | Bilingual cheat sheet: English to say, Spanish to rehearse |
| `SHARING-VERCEL.md` | How to share the dashboard publicly through Vercel and Cloudflare |

**Data files and images**

| Files | What they are |
|---|---|
| `evidencia-*.json` (8 files) | Saved evidence of checks already run (Atlas load, GPS load, tracking, freshness, customers, traffic links, sharing, Vercel). Records, not to be edited by hand |
| `auditoria-esquemas.json` | Audit of the tables and columns of the running instance on 7 October |
| `chuleta-bilingue.json` | Content source of the bilingual cheat sheet PDF |
| `capturas/` (9 images) | Screenshots of the dashboard, the mini-app, mobile views and the public website |
| `*-preview.png` (4 images) | Previews of the lab dashboards |
| `atlas-data-flow.svg` | Slide-ready diagram (16:9) of how the three kinds of data reach ClickHouse and the dashboard |

## Other folders

| Folder / file | Label | What it is |
|---|---|---|
| `api/proxy.js` | Tooling | Vercel function: forwards read-only requests to the sharing gateway |
| `data/*-benchmark.json` | Lab | Benchmark reports (`query-`, `scale-`, `eleme-`). Everything else in `data/` is downloaded data and is not in Git |
| `output/pdf/` | Docs | Generated PDFs: technical guide, team guide, visual guide, two bilingual cheat sheets, English presenter notes. The guides are still in Spanish |
| `output/images/` | Docs | Diagram of how the services connect |
| `presentaciones/*.pptx` | Docs | PowerPoint decks: the 5-minute progress update (Spanish and English) and simplified/visual English versions |
| `presentaciones/*.json` | Docs | Content sources of those decks |
| `app/` | Old | Flask app of generation 1: `app.py`, its HTML template, `Dockerfile` and `requirements.txt` |
| `clickhouse/init/` | Old | SQL and user script run by generation 1's ClickHouse container on first start |
| `grafana/provisioning/` | Old | Grafana data source configuration of generation 1 |
| `datos/.gitkeep` | Old | Empty folder for generation 1's CSV files |

## What is not in Git

| Item | Where it lives | Why |
|---|---|---|
| Downloaded datasets (OTTO, REES46, Ele.me, Glovo, TRD) | `data/`, `datos/` | Tens of GB; each source has its own terms |
| ClickHouse data and the Atlas queue | Docker volumes `clickhouse_data` and `atlas_queue` | Local state of each computer |
| Sharing secrets | `data/sharing/` | Tokens must never be committed |
| Professor's course materials | `recursos/` (local only) | The repository is public |
| Vercel build output | `shared-public/` | Generated by `build_shared.mjs` |
| Run manifests and check results | `data/atlas/` | Generated by the Atlas scripts |

## Suggested reading order

1. `README.md` and this map.
2. `docs/ASSIGNMENT.md`: what the assignment asks for and where it is covered.
3. `docs/ATLAS-INFRASTRUCTURE.md`, section 2: start Atlas.
4. `docs/MINIAPP.md` and `docs/TRACKING-DEMO.md`: what to show.
5. `docs/FUNDAMENTALS.md` and `docs/APPLIED-THEORY.md`: what to explain.
