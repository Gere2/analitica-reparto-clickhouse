# Delivery Atlas

> Historical record: dates, results, speaker allocations and pending statements below describe their original stage. For the current implemented project, 14-slide route and delivery status use [FINAL-DELIVERY.md](FINAL-DELIVERY.md), [DATABASE-STRUCTURE.md](DATABASE-STRUCTURE.md) and [DEMO-GUIDE.md](DEMO-GUIDE.md).
## Technical document for the team

**Audience:** Jere, Anuar and Echenique. **Code review:** 14 October 2026. **Reviewed base:** commit `5feb407`. The measurements and screenshots kept are from 7 October; this document does not claim that the services are running today.

### What we are building

An analytics infrastructure for a fictional food-delivery platform, inspired by Uber Eats and Glovo. We receive browsing actions, order statuses and courier positions; ClickHouse keeps the history and feeds a dashboard.

**There are two complementary parts:** the lab contains large public datasets; Delivery Atlas has our own event contract and a simulated operational scenario in Madrid. Their identifiers and populations stay separate.

### What is implemented

- One ClickHouse node, two logical databases and persistent storage in Docker.
- Python API, validation, SQLite queue, batch publishing and retry control.
- Browsing and GPS generators, a fictional catalog and order statuses.
- Dashboard with tracking, metrics, browsing and an inventory of sources.
- Shared website on Vercel, connected to Jere's computer through a read gateway and a temporary tunnel.

The complete commercial mini-app, its checkout connected to an order and a verified installation on another computer are still pending. The tracking data is fictional; we have no access to Uber Eats' or Glovo's internal telemetry.

### How to read this document

| If you want to understand... | Read first |
|---|---|
| The idea and the technologies | 1-2: architecture and components |
| How a record reaches the database | 3-7: ingestion, SQL and schemas |
| What data we are showing | 8-11: simulation, sources and dashboard |
| How to run or share it | 12-14: Vercel, start-up and queries |
| What is demonstrated and where to work | 15-16: results and code map |

Repository: https://github.com/Gere2/analitica-reparto-clickhouse. Demo published on 7 October: https://delivery-atlas-demo.vercel.app. Its updates depend on the local lab.

<!-- page -->
# 1. Architecture: who does each job

### Path of a new event

```text
Generator or manual action
        |
Python validation -> SQLite: pending event
        |
Batch publisher -> ClickHouse: history + aggregates
        |
Read API -> dashboard: metrics and positions
```

The built-in simulator calls the same validation and queue directly. An external client comes in over HTTP. The lab's public loads use their ETL scripts and write to another logical database.

### Services and addresses

| Component | Role and address |
|---|---|
| `clickhouse` | One ClickHouse server. Inside Docker: `clickhouse:8123`; from the computer: `127.0.0.1:8124`. |
| `atlas` | API, simulator and publisher in a single Python process. Web/API: `127.0.0.1:8001`. |
| `share-gateway` | Additional read service for sharing. Internal port 8080; no host port is published. |
| `share-tunnel` | Outgoing connection with Cloudflare towards the gateway. Only started for sharing. |
| Historical lab | `dashboard.py`, run separately on `127.0.0.1:8000`. Not part of the Atlas process. |

**A node is one instance of the database server.** The four sharing services are not four ClickHouse nodes: we still have one.

### Persistent storage

- `clickhouse_data` volume: ClickHouse tables, parts and state.
- `atlas_queue` volume: SQLite at `/state/outbox.sqlite`.
- Local `data/` directory: source files, manifests and private sharing configuration; ignored by Git.

The volumes keep data across restarts. On their own they provide no replica, backup or protection against disk loss. `delivery` and `delivery_atlas` share the same server and its resources.

**Reference files:** `compose.yaml`, `compose.share.yaml`, `Dockerfile.atlas`, `Dockerfile.share` and `dashboard.py`.

<!-- page -->
# 2. Technologies used and why

| Technology | Specific use in this project |
|---|---|
| ClickHouse 25.8 | Store massive events and query groupings, history and latest states. Image `clickhouse/clickhouse-server:25.8`; version observed in the measurement: 25.8.33.6. |
| SQL | Define tables, partitions, views and analytical queries. We use SQL even though the course groups this technology with NoSQL databases. |
| Python 3.12 in Docker | API, validation, publisher, simulation and gateway. The Atlas path uses the standard library, without installing a web framework. |
| SQLite | Local persistent queue and log of accepted IDs. Its role is to transport events to ClickHouse. |
| Docker and Compose | Reproduce the services, internal network, configuration and volumes. Atlas is enabled with the `atlas` profile. |
| HTML, CSS, JavaScript and SVG | Interface, HTTP queries, tables, bars and coordinate plane. No React or external map API is required. |
| Node.js and Vercel | Prepare the shared website and run `api/proxy.js` per request. The function forwards reads to the lab. |
| Cloudflare Tunnel | Temporarily connect Vercel with the local gateway over HTTPS, without publishing ClickHouse's SQL. Pinned image: `2026.3.0`. |
| Git and GitHub | Share code, documentation, SQL, screenshots and small results. The massive datasets are not in the repository. |
| ReportLab and Poppler | Generate and review this PDF. They are documentation tools, not dependencies of the demo. |

### Why ClickHouse fits

Our workload combines many event inserts with reads that count, group and compare periods. We organize the data with engines from the MergeTree family and prepare aggregate states for the dashboard. The goal is analytics, not resolving transactional payments or assignments.

ClickHouse does not measure clicks on its own: **we record events and the database makes it possible to analyse them**. A GPS position or a catalog row does not become a click just because it is stored there.

There is an initial implementation in `app/` with Flask 3.1.3 and `clickhouse-connect` 1.9.0. It is not the active Atlas API. The latter connects over HTTP with `urllib.request`; it returns JSON results and inserts in `JSONEachRow` format.

We also keep `docker-compose.yml`: the initial configuration of that app and Grafana 12.3.0, with the `grafana-clickhouse-datasource` plugin and a native connection to port 9000 of the `reparto` database. It was used to visualize queries through Grafana and to separate write/read users. The project's current path uses `compose.yaml` and our web dashboard; starting that file does not reproduce Atlas.

**Local configuration:** `clickhouse-config.xml` limits the merge pool to four; the Atlas client sets `max_threads=4`, synchronous inserts and waiting for the end of the query. These are settings for the demo machine, not a measurement of the engine's maximum capacity.

<!-- page -->
# 3. Ingestion, queue and retries

### Exact path

1. The client creates a UUID per event, its time and its content.
2. `atlas/server.py` receives the JSON and calls `contract.py` or `operations.py`.
3. `Store.accept()` opens an SQLite transaction with `BEGIN IMMEDIATE`, checks IDs and stores the batch.
4. The API responds once the queue has accepted the event. **202 does not mean the dashboard can already query it.**
5. `Publisher` reads up to 5000 pending events, groups them by table and inserts them with the ClickHouse client.
6. Only afterwards does it mark those rows as published. The materialized views process the inserts and the API queries the results.

### What SQLite keeps

| Structure | Content |
|---|---|
| `outbox` | Local sequence, unique `event_id`, SHA-256 of the canonical JSON, payload with `ingested_at` and a `published` flag. |
| `counters` | Accepted, duplicates, requests, conflicts and observed errors. |
| `metadata` | Last simulator configuration/run, to remember it on restart. |

It uses WAL, `synchronous=FULL` and a persistent connection protected by an `RLock`. The page cache is set to 32 MiB. These measures avoid reopening the connection on every tick; they do not replace a backup.

### Delivery contract

| Situation | Result |
|---|---|
| New ID and valid content | Stored; response 202. |
| Same ID and same content | The retry is recognized; 200 if the batch only contains duplicates. |
| Same ID with different content | 409 conflict; the SQLite batch is rejected. |
| Queue with 200000 pending | 503 with a retry indication. It is not confirmed as accepted. |
| Wrong contract / body too large | 400 / 413. Maximum 5000 events and 5 MiB per request. |

If a response is lost, resend **the same ID, time and content**. Creating a new UUID would turn the retry into another event.

A mixed batch may need three INSERTs into ClickHouse. They do not form a joint transaction. If the second one fails, the batch stays pending and is resent: it may produce physical copies, which the logical reads resolve. We do not promise physical exactly-once delivery.

<!-- page -->
# 4. How we designed ClickHouse

### Separation by function

| Database | What it contains |
|---|---|
| `delivery` | Public sources, their aggregates, historical replay and the CRUD scratch table. |
| `delivery_atlas` | Our own browsing, fictional catalog, positions, statuses and read views. |

### Engines and objects

| Element | What it means in our implementation |
|---|---|
| `MergeTree` | Typed history of the lab. Organizes data parts for the queries. |
| `ReplacingMergeTree(version)` | Keeps the most recent version of rows with the same sort key when they merge. Atlas uses `ingested_at` or `version`. |
| `AggregatingMergeTree` | Stores intermediate states of aggregate functions; they are combined at query time. |
| `SummingMergeTree` | Simple aggregates of the earlier lab. It is not the exact counter chosen for Atlas retries. |
| Incremental materialized view | Processes inserted blocks and writes states to another table. It is not a thread that continuously queries the whole database. |
| Read view | Saved query that finalizes/combines states when the API reads it. |

References: [ReplacingMergeTree](https://clickhouse.com/docs/reference/engines/table-engines/mergetree-family/replacingmergetree), [AggregatingMergeTree](https://clickhouse.com/docs/reference/engines/table-engines/mergetree-family/aggregatingmergetree) and [materialized views](https://clickhouse.com/docs/reference/statements/create/view).

### Partitioning, order and uniqueness

The Atlas event tables are partitioned by month. Their `ORDER BY` organizes data for reads and defines the keys the replacing engine acts on; **it does not enforce a UNIQUE constraint**. Immutable identity and content are controlled first in SQLite.

Merges happen after insertion: `count()` over physical rows may differ from a logical read. We use `FINAL` to resolve copies when reading detail, `uniqExact` to count IDs and `argMaxMerge` to get the latest state.

`CREATE ... IF NOT EXISTS` allows starting without recreating existing objects. It is not a migration system: editing the SQL does not automatically transform an already created table or backfill aggregates with its history. Evolving the schema needs an explicit procedure.

<!-- page -->
# 5. Browsing: contract and daily aggregate

**A row of `delivery_atlas.app_events` represents one logical action.** It does not represent a position, a unique user or a paid sale.

| Column or group | SQL type and meaning |
|---|---|
| `schema_version` | `UInt16`; supported version: 1. |
| `event_id`, `session_id` | `UUID`; event identity and session grouping. |
| `event_time`, `ingested_at` | `DateTime64(3, 'UTC')`; event time and acceptance into the queue. |
| `event_date` | `Date MATERIALIZED toDate(event_time)`; computed by ClickHouse. |
| `event_type`, `section`, `city_id` | `LowCardinality(String)`; action, screen/section and city. |
| `user_id`, `restaurant_id`, `product_id` | `Nullable(String)`; known references; `null` when unknown. |
| `source` | `LowCardinality(String)`; generator or client that produced the record. |
| `source_kind` | `Enum8`: `synthetic`, `demo_live`, `public_historical` or `historical_replay`. |
| `source_record_id` | `Nullable(String)`; reference to the original historical observation. |
| `simulation_run_id` | `Nullable(UUID)`; identifies a synthetic run. |

The API requires the common fields, validates UUIDs and dates with a time zone, converts to UTC and rejects unknown fields. A synthetic event needs a run; a historical one needs an original reference. Product and cart events also need `restaurant_id` and `product_id`.

Supported actions: `search`, `filter_applied`, `restaurant_opened`, `product_opened`, `product_impression`, `cart_added`, `order_submitted`. The contract allows more actions than the basic generator shows.

### The four browsing objects

```text
app_events -> app_daily_rollup_mv -> app_daily_rollup
                                      |
                               app_daily_counts
```

`app_daily_rollup` groups by provenance, date, city, section and action. It stores `AggregateFunction(uniqExact, UUID)`; the materialized view produces `uniqExactState(event_id)` and the view combines them with `uniqExactMerge(event_ids)`.

That way a resend with the same ID and dimensions is not added twice within the group. We do not simply add up the `count()` of each INSERT. The exact set has a memory and merge cost, which shows up in the measurements.

**Sort key of the detail table:** `(source_kind, event_date, city_id, event_type, event_time, session_id, event_id)`. **Source of truth:** `sql/atlas.sql` and `atlas/contract.py`.

<!-- page -->
# 6. Positions and orders: columns used

**There are two separate fact tables.** `courier_positions` records a position; `order_events` records a complete snapshot of an order when its status changes.

### Columns common to both tables

| Fields | Type and use |
|---|---|
| `schema_version` | `UInt16`; v1 contract validated by Python. |
| `event_id`, `simulation_run_id` | `UUID`; event and run. |
| `courier_id`, `order_id` | `UUID`; courier and order in the simulation. |
| `event_time`, `ingested_at` | `DateTime64(3, 'UTC')`; event time and acceptance. |
| `city_id`, `source` | `LowCardinality(String)`; city and producer. |
| `source_kind` | `Enum8('synthetic'=1)`; these routes only accept fictional telemetry. |

### GPS-only fields

| Fields | Type and use |
|---|---|
| `latitude`, `longitude` | `Float64`; coordinates. Validated ranges: ±90 and ±180. |
| `speed_kmh`, `accuracy_m` | `Float32`; simulated speed and accuracy. The API accepts 0-150 km/h and 0-10000 m. |

### Order-status-only fields

| Fields | Type and use |
|---|---|
| `restaurant_id` | `String`; fictional pickup business. |
| `status` | `LowCardinality(String)`; status allowed by the contract. |
| `amount_minor`, `currency` | `UInt32` and `FixedString(3)`; integer cents and `EUR`. |
| `pickup_lat`, `pickup_lon`, `dropoff_lat`, `dropoff_lon` | `Float64`; fictional pickup and dropoff coordinates. |
| `order_created_at`, `promised_delivery_at` | `DateTime64(3, 'UTC')`; creation and fictional deadline. |

Statuses: `created`, `preparing`, `picked_up`, `en_route`, `delivered`, `cancelled`. The API checks that creation is not later than the event and that the deadline is not earlier than creation; it does not implement a transactional state machine that forbids every business transition.

Both tables use `ReplacingMergeTree(ingested_at)` and monthly partitioning. GPS is ordered by `(simulation_run_id, city_id, courier_id, event_time, event_id)`; orders, by `(simulation_run_id, city_id, order_id, event_time, event_id)`.

`ingested_at` is added by the queue. `_stream` is an internal routing marker removed before the INSERT; the client must not send it. Code and DDL: `atlas/operations.py` and `sql/atlas_operations.sql`.

<!-- page -->
# 7. Getting the latest state without losing the history

### GPS

```text
courier_positions -> courier_latest_mv
                            |
                    courier_latest_state
                            |
                     courier_latest
```

The materialized view stores `argMaxState` in an `AggregatingMergeTree` table. The `courier_latest` view combines those states with `argMaxMerge`. The grouping key is run, city and courier.

The comparison criterion is `tuple(event_time, event_id)`. The most recent event time wins; on a tie, the UUID resolves it deterministically. Latitude, longitude, speed, order and times are stored together in a tuple, so the result comes from the same row.

### Example: an old position arrives late

| Event | Event time | Arrival time | Result |
|---|---|---|---|
| A | 12:00:02 | 12:00:03 | Position initially selected. |
| B | 12:00:00 | 12:00:04 | Kept in the history; it does not replace A. |

Ordering only by arrival would move the courier backwards. Our criterion takes the event time. Reference: [argMax](https://clickhouse.com/docs/reference/functions/aggregate-functions/argMax).

### Orders

`order_events -> order_latest_mv -> order_latest_state -> order_latest` applies the same pattern, grouping by run, city and order. It keeps the complete snapshot: status, courier, business, amount, coordinates and times.

The `*_state` objects store aggregate states, not a user document or a direct GPS row. The `*_latest` views are what the API consumes. The history is still available in the fact tables.

### Relationships and consistency

The simulator creates consistent references between courier, order and fictional business. There are no foreign keys that ClickHouse checks in this model. The IDs do not identify people from other datasets.

The API queries positions, orders, metrics, pace and time through separate SELECTs. They are not a single transactional snapshot: brief differences may exist during publishing. Nor is there any replica or sharding configured. Separating by run prevents mixing runs when reading states.

<!-- page -->
# 8. Simulation and catalog: what we invented

### Fleet in clock time

`atlas/simulation.py` contains `Scenario` (scenario data) and `Simulator` (thread that generates ticks). By default: Madrid, 12 couriers, seed 42 and a requested interval of two seconds. It accepts 1-50 couriers and intervals of 1-10 seconds.

Each tick produces GPS; only status changes produce order snapshots. Cycles last 160 s and start staggered; some orders start already advanced, so their first history may be partial. About 12% of cycles are configured to cancel. These parameters describe the generator, not real demand in Madrid.

Coordinates are interpolated between origin, pickup, an intermediate point and dropoff. The next route starts from the previous destination, or from the pickup after a cancellation. Approximate speed and 5 m accuracy are also simulated; they have not been observed or validated against real streets.

Generation uses a seed and UUID5 to reproduce the scenario when the run and times are kept. Starting another fleet creates a new run. Stopping keeps the history; restarting the API remembers the last run but **does not automatically reactivate the simulator**.

### Two different browsing generators

- `scripts/atlas.py`: large reproducible load, three cities and sequences of five complete actions. Not suitable for estimating real abandonment.
- Built-in simulator: synthetic sessions with possible abandonment between steps. They are generated separately from the orders; there is no commercial link between that checkout and the delivery.
- `scripts/operations.py`: historical GPS/status load over HTTP with fixed times. It does not generate a fleet that moves now, nor does it send its auxiliary clicks.

### Catalog: 12 businesses and 36 products

`atlas/catalog.py` seeds it on start-up if the expected quantities do not exist. `demo_restaurants` stores ID, name, city, coordinates, fictional origin and `version`. `demo_products` stores ID, business, name, `price_minor`, EUR, `price_kind`, `name_kind`, `source_table`, `source_row` and `version`.

If Glovo Madrid is loaded, it takes 36 names and their source rows; on another computer it uses fallback names. **Price, location and assignment to the business are still fictional.** `name_kind` keeps the provenance of the name. The order amount is generated independently: it is not the sum of a real basket from the catalog.

Catalog DDL: keys `restaurant_id` and `product_id`, engine `ReplacingMergeTree(version)`. The future mini-app can reuse `GET /api/demo-catalog`.

<!-- page -->
# 9. Public sources: volume and meaning

Counts documented on **7 October 2026**, before new inserts. They have not been recounted to write this PDF. The column audit is in `docs/auditoria-esquemas.json`.

| Source / table in `delivery` | Verified rows | What one row represents |
|---|---|---|
| OTTO / `otto_archive` | 216,716,096 | Browsing event: click, cart or order. |
| REES46 / `rees46_events` | 411,709,736 | E-commerce view, cart or purchase. |
| Ele.me / `eleme_samples` | 2,170,299 | Recommendation sample with a `clicked` label. |
| Glovo / `glovo_products` | 2,887,444 | Published catalog product; not a click. |
| TRD / `orders` | 1,068,495 | Historical order from the same TRD/Meituan corpus. |
| TRD / `clicks` | 4,021,488 | Step of a recorded sequence of restaurants. |
| TRD / `click_summary` | 517,353 | Summary of a sequence; not an individual event. |
| TRD / `restaurants`, `foods` | 29,072 / 179,778 | Business and product dimensions. |
| TRD / `order_items` | 3,445,180 | Relationship between order and product in that corpus. |
| `otto_replay` | 1,200,000 | Insertion of a replayed old event. |
| `otto_scale_benchmark` | 1,083,580,480 | Row derived from OTTO for stress testing; not a new observation. |

### Useful fields we keep

OTTO: session, article, time, action and position. REES46: time, action, product, category, brand, price, user and session. Ele.me: file/row, user, store, item, anonymous city, time context, label and original features in JSON. Glovo: row, country, city, business, product, section and description.

TRD makes it possible to relate orders, clicks and products using its own IDs and dates. `price_band` is a price range, not an exact amount. Its click sequences do not provide the couriers' GPS.

Glovo has 415,137 products from Spain and 68,575 from Madrid in the documented load. The dashboard sample does not prove that those products or businesses are still active today.

**We do not join the IDs of OTTO, REES46, Ele.me, Glovo and Atlas.** A sum of all their rows does not mean users, clicks or orders of a single platform. Criteo, MT-LIFT and the Madrid census appear in old proposals, but not in the audited active tables.

<!-- page -->
# 10. How the historical data was loaded

These paths belong to the lab. The small Atlas demo can start without downloading its massive files.

| Code path | Transformation and use |
|---|---|
| `scripts/download.py`, `prepare.py`, `load.py` | Download/prepare TRD, convert TSV to typed fields and load the corpus tables. `sql/schema.sql` defines the schema. |
| `scripts/otto.py` | Manage the OTTO archive, load events, verify counts and replay them into `otto_replay`. |
| `scripts/rees46.py` | Read compressed CSV per month, validate header/size and publish batches with partial-load control. |
| `scripts/eleme.py`, `sql/eleme.sql` | Validate the 39-field format, load staging and publish complete files with `MOVE PARTITION`. |
| `scripts/glovo.py` | Transform the FooDI-ML catalog into `glovo_products`, keeping the source row and attributes. |
| `scripts/rollup.py`, `benchmark.py` | Prepare OTTO aggregates and compare lab queries. |
| `scripts/scale.py` | Create the derived stress scenario. It adds no extra observed clicks. |
| `dashboard.py` and pages in `web/` | Read the lab and show OTTO, REES46, Ele.me, Glovo, TRD and volume. |

### Rigour checks

Reports, manifests, fingerprints and counts are kept in each importer's paths. OTTO was checked against the archive's fingerprint and counts; REES46 checks each month; Ele.me keeps `source_id`, file and row, as well as the original features.

For Ele.me, having 39 columns is not enough: their correspondence must be verified before confirming the layout. The reviewed load is one part of the announced dataset, not all of the platform's data.

Moving parts with `MOVE PARTITION` does not trigger an insert materialized view as if new rows were inserted. Nor is a retrospective aggregate created automatically when a materialized view is added to an existing history.

The replay keeps the historical time and adds the ingestion time. **Entering the database during the demo does not turn it into a click from a current user.**

The large source files stay outside Git and the Vercel upload. The team shares the code and instructions; obtaining a source again requires following its access and terms. The guides for each dataset are in `docs/LEGACY-DATASETS.md`, `GLOVO.md` and `ELEME.md`.

<!-- page -->
# 11. Dashboard and API: where each piece of data comes from

The dashboard uses `web/atlas-dashboard.html`, `.css` and `.js`. The API serves web and JSON from the same origin; the browser does not need direct ClickHouse credentials.

| Local endpoint | What it returns or does |
|---|---|
| `GET /api/operations` | Positions, order list, metrics and GPS in 5 s intervals. Uses the last run if no other is given. |
| `GET /api/track` | Up to 240 logical positions of the courier/run, ordered to draw the path. |
| `GET /api/simulation` | Simulator status, configuration and last run. |
| `GET /api/status` | Pending/published and phases of the local publisher. |
| `GET /api/summary` | Aggregated browsing; filters for date, city, provenance and action. |
| `GET /api/recent` | Last 30 global browsing events. |
| `GET /api/inventory` | Table metadata, estimated physical rows and disk. |
| `GET /api/catalog` | Glovo Madrid sample if loaded. |
| `GET /api/demo-catalog` | The demo's businesses/products, with provenance per field. |
| `POST /api/events`, `/api/operations` | Acceptance into the browsing or telemetry queue. |
| `POST /api/simulation/start`, `/stop` | Local fleet control. Start accepts `fleet`, `interval`, `seed`; stop receives `{}`. |
| `GET /health` | Runs `SELECT 1` and checks the publisher status for the healthcheck. |

### Dashboard reads

- Active, delivered, cancelled and amount: latest state of each order. Late: orders still active whose fictional deadline has passed.
- List limited to 200 orders; the metrics query the whole run. `truncated` warns about the conservative limit.
- The SVG plane projects latitude/longitude. The line uses only the positions received for the current order; it does not compute street routes.
- GPS per 5 s: `uniqExact(event_id)` over the last two minutes. Browsing: counts by action, not conversion of those orders.

Tracking is queried again after completing the previous cycle and waiting 2 s; browsing, about every 10 s. Polling cycles do not overlap. The inventory is loaded when the page opens.

The local dashboard can record a manual search. `event_time` is the action time; `ingested_at` measures acceptance by the API. Their difference does not measure complete publishing. Position age shows the visible delay; if a query fails, the previous data is kept and a warning is shown.

<!-- page -->
# 12. Sharing: Vercel and Cloudflare

### Path of a remote query

```text
Teammate -> Vercel: HTML + JavaScript + GET function
         -> Cloudflare: temporary HTTPS URL
         -> share-gateway: token and allowed routes
         -> local Atlas API -> local ClickHouse
```

Vercel hosts the interface and the per-request proxy. The ClickHouse server, the SQLite file and the permanent threads remain in Docker on Jere's computer. If the computer sleeps or the tunnel stops, the website stays published and stops receiving updates.

### Files and access protection

`scripts/build_shared.mjs` copies the three assets, sets read mode and removes the start/stop and insert controls. `api/proxy.js` only accepts GET and allowed routes; it uses `ATLAS_SHARE_ORIGIN` and `ATLAS_SHARE_TOKEN` from server variables. The token is not added to the browser JavaScript.

`atlas/share.py` requires the token, validates UUIDs/parameters, limits the response to 2 MiB and rejects POST, PUT, PATCH and DELETE. It reduces the status/simulation fields and does not return detailed internal errors.

Allowed public routes: `simulation`, `operations`, `status`, `track`, `summary`, `inventory`, `catalog`. Sharing limits summary to Madrid and to `synthetic`/`demo_live`; it does not expose all the filters of the local API. Nor does it publish `recent` or `demo-catalog`.

| Gateway cache | Duration |
|---|---|
| Tracking, status and path | 1.5 s |
| Browsing | 10 s |
| Inventory and catalog | 60 s |

Maximum 128 keys, with separate locks per endpoint so that the inventory does not block GPS. The function cuts the wait at 12 s; its maximum duration configured on Vercel is 30 s. These caches can add delay.

### Conditions of the shared demo

The link is visible to anyone who has it. It carries fictional data, aggregates and the public catalog through Vercel/Cloudflare. ClickHouse keeps its local port; the write API is not opened through the tunnel either.

The `trycloudflare.com` URL changes when another tunnel is created: `ATLAS_SHARE_ORIGIN` must be updated and redeployed. Secrets live in `data/sharing/` and in sensitive Vercel variables; allowed code in `.vercelignore`. Full procedure: `docs/SHARING-VERCEL.md`. There is no availability independent of the laptop.

The current Compose uses local demo credentials; it does not implement the role separation of a production application. References: [Vercel functions](https://vercel.com/docs/functions/limitations) and [Cloudflare Quick Tunnels](https://developers.cloudflare.com/tunnel/get-started/quick-tunnels/).

<!-- page -->
# 13. Reproducible start for teammates

### Requirements and small path

Docker with Compose v2 and Python 3.10 or later on the computer; the containers use Python 3.12. Get the code from the repository, including the changes in PR 1/branch `codex/actualizacion-clickstream-eleme` while it is not merged.

From the project folder:

```bash
docker compose -f compose.yaml --profile atlas up -d --build --wait
docker compose -f compose.yaml --profile atlas ps
python3 -m unittest discover -s tests -v
python3 scripts/check_atlas.py
python3 scripts/check_operations.py
```

Open `http://127.0.0.1:8001/`. Start the simulation; select a courier and check time, coordinates and path. Record a manual search and choose the manual-actions source to find it.

The HTTP tests need the API and ClickHouse; they add labelled check rows. The unit tests check contracts/queue/routes without downloading historical data. On a new machine the catalog will be fictional and the public sources will not appear until they are loaded.

### Optional small loads

```bash
python3 scripts/atlas.py generate --events 10000 --batch 1000 --seed 42
python3 scripts/atlas.py status
python3 scripts/operations.py --positions 10000 --fleet 12 --seed 42
```

Wait for `pending=0` before checking loads or measuring. To reproduce browsing exactly, save and reuse `--run-id`, `--start`, `--seed` and `--events`: without a fixed date the generator chooses another one. The GPS load computes a deterministic run from date, seed, fleet and number of positions.

### Logs, changes and stopping

```bash
docker compose -f compose.yaml --profile atlas logs --tail 60 atlas
docker compose -f compose.yaml --profile atlas stop
```

Repeat `up ... --build --wait` after changes to Python, SQL or web files. The simulator will need to be started again. Keep the volumes; `down -v` deletes the database and queue storage.

Sharing requires preparing the private files and starting the additional Compose file, as the Vercel guide explains. **Do not launch the sharing file on a new installation before creating `data/sharing/gateway.env`.**

<!-- page -->
# 14. Queries and diagnostics you should know

### Three queries to demonstrate the model

```sql
-- Logical count by type: reading ID sets.
SELECT event_type, sum(events) AS events
FROM delivery_atlas.app_daily_counts
WHERE city_id = 'madrid' AND source_kind = 'synthetic'
GROUP BY event_type;

-- Positions of the last run, using its real UUID.
SELECT courier_id, latitude, longitude, event_time
FROM delivery_atlas.courier_latest
WHERE simulation_run_id = {run:UUID};

-- Engine and size: metadata, not a count of users.
SELECT database, name, engine, total_rows
FROM system.tables
WHERE database IN ('delivery', 'delivery_atlas');
```

The `{run:UUID}` parameter needs the run from `GET /api/simulation`; the Python client passes `param_run`. Atlas read filters are parameterized instead of concatenating user values.

### Reading a failure layer by layer

| Symptom | Check and meaning |
|---|---|
| No couriers appear | See `GET /api/simulation`; start from the local demo. A restart remembers data but does not reactivate generation. |
| Accepted, but not visible yet | See pending and phase in `/api/status`; 202 confirms SQLite, not publishing. |
| Pending grows / publisher error | Check ClickHouse health and the Atlas logs. The publisher retries; the queue has a limit. |
| Public source empty on another machine | The massive files and volumes do not travel with Git. The simulation works anyway. |
| Vercel stops updating | Check the computer, Docker, tunnel and origin URL. The controls belong to the local dashboard. |
| Different physical counts | Retries/merges can change physical rows. Query with `FINAL`, unique IDs or logical views. |

### CRUD required by the course

`python3 scripts/crud_demo.py` demonstrates INSERT, SELECT, ALTER UPDATE and ALTER DELETE on `delivery.demo_events`, waiting for the mutations to finish. The table is a scratch table, separate from the Atlas flow.

The script temporarily pauses merges on three large historical tables if they exist and re-enables them in `finally`. Keep this in mind when using it during loads. The application's order statuses are represented by inserting another snapshot; each GPS row is not updated with a mutation.

<!-- page -->
# 15. Evidence, limits and relation to BD2

**These are saved checks from 7 October 2026.** They do not replace a new test under load or an installation on another computer.

| Check | Result and scope |
|---|---|
| Atlas browsing | 1,000,000 synthetic events verified by run. Sending to API/queue: 323.5853 s; not isolated ClickHouse throughput. |
| Historical GPS | 100000 positions and 5965 statuses verified in ClickHouse. Sending 105965 records: 435.887 s with concurrent activity. |
| Retry and content | Duplicates recognized; 409 conflict if the content of the same ID changes. |
| Recovery | Pending event recovered after orderly shutdowns and a restart with volumes kept. It does not test disk loss. |
| Failure between INSERTs | Resend of a mixed batch: 4 physical / 2 logical positions; 2 logical orders. There is no transaction across tables. |
| Old GPS event | Does not replace the position with the more recent time. Invalid coordinate: 400. |
| Local fleet read | Three samples without concurrent historical load: maximum data age 1.761-2.279 s; queries 0.177-0.855 s. |
| Vercel | Seven routes read; times/positions advanced and a write returned 405. An initial 503 was observed and recovered. Last check: 12 couriers, maximum data age 3.796 s in the query. |

### A result we must explain honestly

The exact Atlas aggregate returned the same result as the detail table, but its median was **0.703 s**, vs **0.498 s** for the detail, over three queries per alternative. Reading fewer rows did not guarantee less time: combining exact sets has a cost. The faster result of the OTTO aggregate belongs to another schema/query and does not demonstrate an improvement for Atlas.

### What we can present to the professor

Context and columnar model; engines/partitions/views; Docker installation; Python connected over HTTP; public and labelled synthetic datasets; ingestion, dashboard and CRUD; measurements with their conditions; an explanation of replication and sharding as extensions, without claiming that we ran them.

### What is still to be solved

Commercial mini-app and checkout-order link; reproduction on another machine; retention/backup; sustained delay tests under load; schema evolution and, later, an experiment with more nodes. The queue keeps published payloads and grows; no telemetry TTL or high availability is configured.

Evidence: `docs/evidencia-atlas.json`, `evidencia-carga-gps.json`, `evidencia-tracking.json`, `evidencia-frescura.json`, `evidencia-sharing.json`, `evidencia-vercel.json`. The `tests/` folder contained 11 test methods when the code was reviewed; this document does not rerun the integration tests or the benchmarks.

<!-- page -->
# 16. Code map and how to pick it up as a team

### Which file to touch for each change

| Need | Main files |
|---|---|
| Add/validate a browsing action | `atlas/contract.py`, `sql/atlas.sql`; review generators and tests. |
| Change GPS or order fields | `atlas/operations.py`, `sql/atlas_operations.sql`, simulator and queries. Plan a migration. |
| Change acceptance, deduplication or persistence | `atlas/store.py`; check conflicts, restarts and retries. |
| Change batches, routes or publisher phases | `atlas/server.py`, `atlas/clickhouse.py`. |
| Change fleet, statuses or coordinates | `atlas/simulation.py`; `scripts/operations.py` reuses `Scenario`. |
| Change the catalog and provenance | `atlas/catalog.py`, `demo_*` tables; do not attribute fictional prices to Glovo. |
| Add a metric or visualization | SELECT in `atlas/clickhouse.py`, endpoint in `server.py`, components in `web/atlas-dashboard.*`. |
| Build the commercial mini-app | New web files and `POST /api/events`; catalog from `/api/demo-catalog`. Coordinate the link with orders. |
| Change sharing | `atlas/share.py`, `api/proxy.js`, `scripts/build_shared.mjs`, `vercel.json`, `compose.share.yaml`. |
| Review historical loading/querying | The corresponding importer, `sql/schema.sql`, `sql/eleme.sql`, `dashboard.py`. |

### Onboarding path

Jere can explain ingestion, SQL and tests. Anuar can start with the contract, the catalog and the client that records actions. Echenique can start with the queries that feed the dashboard, the delay warnings and the local reproduction. This is a reading guide; the final split will be agreed when you join.

Before modifying a part, identify **what its row represents**, how its ID is generated, what provenance it has and how it is read in the presence of retries. Test a small change on the local path before deploying it. There is no need to load all the historical data to work on Atlas.

### Sources to go deeper

- Executable code and DDL: `atlas/`, `sql/`, `api/`, Compose and the scripts described here.
- Reproduction: `docs/TRACKING-DEMO.md` and `SHARING-VERCEL.md`.
- Model and audit: `docs/DATA-AND-TRACKING.md`, `DATABASE-STRUCTURE.md` and `auditoria-esquemas.json`.
- The team's initial PDF guide predates tracking; this document describes the code reviewed on 14 October.

**Idea the whole team must be able to explain:** we generate/receive events, confirm them in a queue, publish their history and aggregate states to ClickHouse, and the dashboard queries what actually reached the database. The public data demonstrates volume; the simulation demonstrates our operational infrastructure.
