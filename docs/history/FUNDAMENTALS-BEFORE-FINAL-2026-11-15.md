> Historical snapshot before the final documentation update of 15 November 2026. Source commit: `c7d4ca1`. For the submitted project use [the final delivery index](../FINAL-DELIVERY.md).

# ClickHouse: fundamentals, architecture and critical reflection

## Fit with the BD2 course

ClickHouse is a **columnar OLAP database with SQL**. In a NoSQL classification it is usually treated as a column-oriented analytical store, but it should not be presented as a "no SQL" engine: it uses an SQL dialect. It is worth explaining this nuance to the professor at the start. Its central problem here is answering aggregations over hundreds of millions of events while new batches keep arriving.

The product idea is inspired by the browsing analytics that a delivery platform would need: volume over time, exploration of products or categories, cart actions and purchases. **The real sources available are not Uber Eats or Glovo**. OTTO does contain explicit clicks; REES46 contains views, carts and purchases. They are not added up as if they were the same event or the same population.

## Where ClickHouse is used

The project started in 2009 for a web analytics platform and was released as open source in 2016 under the Apache 2 license ([official history](https://clickhouse.com/docs/about-us/history)). In the official list of adopters, Yandex Metrica appears as the main product built on ClickHouse.

The documentation groups its common uses into four families ([use cases](https://clickhouse.com/docs/use-cases)):

| Use | Why it fits |
|---|---|
| Real-time analytics and time series | Timestamped data that keeps arriving and is aggregated by interval |
| Observability: logs, metrics and traces | Large volumes that are appended and almost never modified; filtered by time and service |
| Analytical warehouse and queries over data lakes | Aggregations over very large tables with SQL |
| Machine learning and generative AI | Exploring and preparing large datasets for models |

Some examples from the [official list of adopters](https://clickhouse.com/docs/about-us/adopters):

| Company | Industry | Stated use |
|---|---|---|
| Cloudflare | CDN | Traffic analysis |
| Uber | Transport | Logging |
| eBay | E-commerce | Logs, metrics and events |
| GitLab | Code and DevOps | Application performance monitoring (APM) |
| Spotify | Music | Experimentation |
| Deutsche Bank | Finance | Business intelligence (BI) |
| Instacart | Delivery | Data engineering and infrastructure |
| DoorDash | E-commerce | Monitoring |
| Zomato | Online food ordering | Logging and food delivery |

The entries are submitted by the companies themselves, often with talks or articles from previous years. They do not prove that the companies still use it today or at what scale.

All these uses share a pattern: many events that are appended and rarely modified, and queries that aggregate millions of rows while reading few columns. It is the same workload that this project's fictional delivery platform needs. Several delivery companies on the list use it for logging, monitoring and data infrastructure.

## Data model

| Table | Source | Grain | Engine and order |
|---|---|---|---|
| `otto_archive` | Real OTTO | One click, cart or order within a session | `MergeTree`, month; `(event_time,session_id,event_position)` |
| `otto_replay` | Real OTTO, re-inserted | One replayed event with a new `ingested_at` | `MergeTree`, insertion day |
| `live_clicks` | This page | One click from a demo visitor | `MergeTree` |
| `rees46_events` | Real REES46 | One view, cart or purchase | `MergeTree`, month; `(event_date,event_type,category_id,product_id)` |
| `otto_scale_benchmark` | Derived | A labelled copy of an OTTO event | `MergeTree`, month; `scenario` makes the origin explicit |
| `otto_daily_rollup` | OTTO aggregate | Partial count by date and type | `SummingMergeTree` + materialized view |

The OTTO ETL turns each JSONL session into several rows, one per event. REES46 is read from seven CSV.gz files without extracting them to disk: `gzip` feeds `clickhouse-client`. Temporary compressed files and persistent tables serve different purposes.

In `MergeTree`, the `ORDER BY` determines the physical order and the sparse primary index of the data. Partitions help skip whole months when a filter matches them; the order helps locate ranges within parts. `LowCardinality(String)` suits repeated event types and brands. Reading only the columns needed reduces bytes compared with reading full rows. Not every `WHERE` will be equally efficient: the query and the indexes must be checked with `EXPLAIN indexes = 1`.

The materialized view receives the batches **inserted after it was created** and adds their counts to `otto_daily_rollup`. For an archive that is already loaded, `scripts/rollup.py` performs the backfill explicitly. In `SummingMergeTree` there may be several physical rows with the same key until parts are merged; that is why the query uses `sum(events) GROUP BY event_date,event_type` instead of assuming that each key takes exactly one physical row. The 87 OTTO day/type combinations are the logical unit of the aggregate.

## Consistency and availability

The demo uses **a single node** with a persistent Docker volume. After a confirmed insert, a query can read the new rows; part merges happen later in the background. There are no replicas and no high availability: if the container is down, the dashboard does not respond. The replayer resends historical events to another table, and its queries by `ingested_at` do not change the original date of the event.

At this volume, merges are also part of operations: they compete with queries for CPU, disk and memory. On this machine with about 4 GB, the default allowed up to 32 simultaneous merges; `clickhouse-config.xml` sets four and adjusts MergeTree's internal thresholds so that mutations remain valid. Compaction speed is traded for keeping resources available to the dashboard. [The official documentation](https://clickhouse.com/docs/reference/settings/server-settings/settings/background) states that reducing the pool requires a server restart, and [explains](https://clickhouse.com/docs/reference/settings/server-settings/settings/background-merges) how the ratio multiplies concurrency.

For a distributed deployment, shards can be spread with `Distributed` tables and copies kept with `ReplicatedMergeTree` and ClickHouse Keeper. That requires additional configuration and has consequences for consistency and latency; **it is neither demonstrated nor simulated with the local container**. It is explained with the diagram and with the observed limitation of a single node.

## Experiment that justifies ClickHouse

`scripts/benchmark.py` asks exactly the same question of the archive of 216,716,096 OTTO events and of the daily aggregate. It compares the results before accepting the measurement. It records time, `rows_read` and `bytes_read` from ClickHouse's JSON response, with the query cache disabled. It runs each OTTO query three times and takes the median. It also counts types in one REES46 month and groups the derived table of 1,083,580,480 rows by scenario. The report is saved to `data/query-benchmark.json`.

The measured result belongs to **this machine, these tables and this question**. It does not mean that ClickHouse always beats PostgreSQL, nor that an equivalent aggregate in PostgreSQL would be slow. The advantage illustrated is specific: computing a repeated answer once during ingestion avoids re-reading millions of events for every dashboard request.

## Insert, read, update and delete

- Insert: the ETL uses batches; the dashboard sends one new event per click; the replayer ingests small batches.
- Read: `SELECT` with time filters, `GROUP BY`, `countIf`, `uniqCombined64` and aggregates.
- Update and delete: `scripts/crud_demo.py` runs `ALTER TABLE ... UPDATE/DELETE` on a scratch table. These are mutations, more expensive than the pattern of appending events and querying aggregates; the historical archive is not modified in bulk just to show CRUD.

## Interfaces, clients and tools

The server accepts connections through several interfaces ([interfaces](https://clickhouse.com/docs/interfaces/overview), [ports](https://clickhouse.com/docs/guides/sre/network-ports)):

| Interface | Default port | In this project |
|---|---:|---|
| HTTP | 8123 (8443 with TLS) | Used by the Atlas API and the Python scripts. Compose publishes it on `127.0.0.1:8124` |
| Native TCP protocol | 9000 | Used by `clickhouse-client` inside the container. Not published outside |
| MySQL and PostgreSQL emulation | 9004 and 9005 | Not used |
| gRPC | 9100 | Not used |

Available tools:

- **Console:** `clickhouse-client`, for example `docker exec -it bd2-clickhouse clickhouse-client --user demo --password demo`.
- **The server's own web interfaces:** `/play` to run SQL and `/dashboard` with server charts. With our Compose they are at http://127.0.0.1:8124/play and http://127.0.0.1:8124/dashboard.
- **Official libraries** ([language clients](https://clickhouse.com/docs/integrations/language-clients)): Python (`clickhouse-connect`), JavaScript, Go, Java (also JDBC and R2DBC), C#, Rust, C++ and C. There are also JDBC, ODBC and ADBC drivers for BI tools.
- **Visualization:** Grafana with the `grafana-clickhouse-datasource` plugin, used by the previous version of this repository.

**Why Atlas uses HTTP with Python's standard library.** `atlas/clickhouse.py` sends SQL over HTTP with `urllib`:

- It adds no dependencies: the API image and the scripts only need Python.
- It is the same interface used by the official client, `clickhouse-connect` ([Python client](https://clickhouse.com/docs/integrations/python)).
- Dashboard queries pass values as typed server-side parameters (`{run:UUID}` with `param_run`) instead of concatenating them into the SQL.
- Inserts are sent in batches with `INSERT … FORMAT JSONEachRow`.

The cost is writing authentication, response parsing and error handling by hand, which `clickhouse-connect` already solves.

## Data quality and limits

- OTTO publishes anonymous item IDs, without name, price or category. Its training file has **216,716,096** events: **194,720,954** clicks, **16,896,191** carts and **5,098,951** orders. The classroom file is validated by SHA-256 and by these counts.
- REES46 publishes seven months of events from a marketplace without identifying its country. Its product views **are not OTTO clicks**. The local manifest keeps the file size and the counts per month.
- The billion-row table **is a derived stress test**, not a set of new observations; original and derived rows are always shown separately.
- `uniqCombined64` estimates distinct users/sessions; row counts are exact. The ratio between views and purchases is not a conversion rate of people unless window, session and attribution are defined.
- The OTTO replay shows real-time ingestion, but the events happened in the past. Clicks on the dashboard buttons are the only new actions originating in the demo.

## Comparison with a transactional database

| Need | Reasonable choice |
|---|---|
| Storing orders, payments and accounts that change individually | A transactional system such as PostgreSQL |
| Exploring years of events and grouping hundreds of millions of rows | ClickHouse |
| Showing frequent metrics on a dashboard | ClickHouse with a materialized view/rollup |
| Looking up or modifying an individual row as the main operation | PostgreSQL or another transaction-oriented engine |

Technical sources: [MergeTree](https://clickhouse.com/docs/engines/table-engines/mergetree-family/mergetree), [materialized views](https://clickhouse.com/docs/materialized-views), [horizontal scaling](https://clickhouse.com/docs/architecture/horizontal-scaling), [HTTP](https://clickhouse.com/docs/interfaces/http). Data: [OTTO](https://github.com/otto-de/recsys-dataset) and [REES46](https://data.rees46.com/).
