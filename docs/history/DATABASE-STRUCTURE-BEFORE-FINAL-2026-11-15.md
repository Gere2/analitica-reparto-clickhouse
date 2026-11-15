> Historical snapshot before the final documentation update of 15 November 2026. Source commit: `c7d4ca1`. For the submitted project use [the final delivery index](../FINAL-DELIVERY.md).

# Delivery Atlas: database structure

## Evolution of 7 October

The operations extension adds `demo_restaurants` and `demo_products` (fictional catalog), `courier_positions` (GPS history) and `order_events` (status history). The `courier_latest_state` and `order_latest_state` tables, their materialized views and the read views `courier_latest` / `order_latest` compute the latest state according to event time. The applied SQL is in `sql/atlas_operations.sql`; [the audit and the tracking model](../DATA-AND-TRACKING.md) explain columns, provenance and limits. Public data remains in `delivery`; the simulated operations live in `delivery_atlas`.

The v1 infrastructure already applies `sql/atlas.sql` in the separate `delivery_atlas` database. It uses `app_events` with `ReplacingMergeTree`, `app_daily_rollup` with `uniqExact` states and a read view `app_daily_counts`. The API's persistent queue makes it possible to recover pending publishes and recognize retries with immutable content. See [the applied infrastructure](../ATLAS-INFRASTRUCTURE.md).

The `delivery_proposal` design described below is kept as the initial proposal of 5 October. It is not the schema used by the new API. In v1, the simple counter aggregate has been replaced by sets of IDs to avoid double counting on resends.

Project progress, 5 October 2026. Goal: analytics infrastructure for a fictional delivery platform, with simulated events and a procedure to add compatible real sources.

## 1. What exists today

One ClickHouse 25.8 node in Docker, `delivery` database, persistent volume, loading and queries with Python. The API queries the tables and the browser displays the results. The datasets stay separate according to their meaning and provenance.

| Table | Grain of one row | Role | Engine |
|---|---|---|---|
| `otto_archive` | Event within an OTTO session | Real history | MergeTree |
| `otto_replay` | Insertion of a replayed OTTO event | Ingestion during the demo | MergeTree |
| `live_clicks` | New click on a dashboard button | Demo interaction | MergeTree |
| `otto_daily_rollup` | Partial count per day and type | Incremental aggregate | SummingMergeTree |
| `rees46_events` | View, cart or purchase | Marketplace history | MergeTree |
| `eleme_samples` | Recommender sample with a click label | Industry case | MergeTree |
| `eleme_staging` | Sample from a file being validated | Publishing by complete file | MergeTree |
| `glovo_products` | Catalog product sample | Industry and Spanish offer | MergeTree |
| `otto_scale_benchmark` | OTTO event in a derived scenario | Volume stress test | MergeTree |

`demo_events` is used for scratch CRUD. The `restaurants`, `foods`, `orders`, `order_items`, `clicks`, `click_summary` and `daily_clicks` tables belong to the first Meituan approach and are kept as earlier material. They do not represent the new contract of the fictional platform.

## 2. OTTO: simple structure with large volume

`sql/schema.sql` defines `session_id UInt32`, `article_id UInt32`, `event_time DateTime64(3, 'UTC')`, `event_type LowCardinality(String)` and `event_position UInt16`.

- Grain: one event within a session.
- Partition: `toYYYYMM(event_time)`.
- Physical order: `(event_time, session_id, event_position)`.
- Typical query: counts by date and event type.
- A row does not contain the product name or its category: the source does not publish them.

`otto_replay` adds `ingested_at`. It keeps the historical moment and records separately when the event entered during the demo. A new replay can insert the same event again: this table records the replay, it does not count new observed users.

## 3. Ele.me: broad context and controlled publishing

`sql/eleme.sql` keeps user, restaurant, product, anonymous city, hour, meal period, the `clicked` label and all the original features in `raw_features String` as JSON.

The loader validates 39 fields and the known ranges, publishes only complete files and records their SHA-256. `source_id`, `source_file` and `source_row` make it possible to trace the file and the row. `source_id` combines the ZIP fingerprint and the member to distinguish its physical content.

- Partition: `source_id`, for this finite corpus and publishing by file.
- Order: `(sample_day, city_id, request_hour, category_id, shop_id, source_row)`.
- Flow: read the ZIP, batches into staging, full verification and `MOVE PARTITION` into `eleme_samples`.
- No insert materialized view on this table: moving parts does not trigger that kind of view.
- A negative label does not prove an impression, and the positive ratio is not the production CTR.

## 4. Physical design and aggregates

ClickHouse stores data by column. `MergeTree` organizes parts that it merges in the background. `ORDER BY` determines the physical order and, if no separate `PRIMARY KEY` is declared, its sparse primary index. The key does not enforce uniqueness. Partitions split storage and make operations on whole groups easier.

The `otto_daily_rollup_mv` view aggregates each inserted block by date and type. `scripts/rollup.py` performs the backfill of the rows that existed before it was created. The table keeps 87 logical keys. It is queried with `sum(events) GROUP BY event_date,event_type` because one key may take several physical rows until they are merged.

Verified comparison of the same answer: 5.8908 s from 216,716,096 events vs 0.2113 s from the aggregate, median of three runs. These are local results and do not compare different engines.

## 5. Model of the fictional platform, still a proposal

`sql/propuesta_delivery.sql` contains a reviewable DDL in `delivery_proposal`. **It has not been applied to the server or connected to the API.**

| Object | Role | Status |
|---|---|---|
| `app_events` | One browsing action with context and provenance | Proposed DDL |
| `app_daily_rollup` | Counts per day, city, section, action and provenance | Proposed DDL |
| `app_daily_rollup_mv` | Feed the aggregate with new inserts | Proposal conditional on deduplicating retries |
| Mini-app and generator | Emit that event contract | Pending implementation |
| Real adapters | Validate a source's correspondence with the contract | Pending implementation |

The central table contains:

- Identity: `event_id UUID`, `schema_version UInt16` and `session_id UUID`.
- Time: `event_time`, `ingested_at` and `event_date MATERIALIZED`.
- Action: `event_type` and `section`.
- Context: optional user, city and optional restaurant/product references.
- Provenance: `source`, `source_kind`, `source_record_id` and `simulation_run_id`.

Monthly partitions and the proposed order `(source_kind, event_date, city_id, event_type, event_time, session_id)`. That order prioritizes filters by provenance and date, then city and action. Its performance still has to be measured against alternatives on the same load.

The aggregate stores event counts, not unique sessions or a user funnel. Those metrics will need definitions of window and session and queries that respect time order.

## 6. Integrity and future integration

The API must validate types, actions, version and mandatory fields. A stable ID makes it possible to recognize retries, but `MergeTree` does not remove them just because that field is declared. The publisher's protocol must avoid counting the same logical event twice before updating the aggregate. That part is still pending design, implementation and testing.

For a new source, check semantics, time zone, ID stability, coverage and terms of use. Assign a namespace and keep unknown fields as missing. Keep the original to cross-check counts. Ele.me will remain as separate samples while there is no valid correspondence with events from the new app.

No joins between the current datasets are required: they share no keys. The new mini-app will reference its own catalog. A Glovo-based catalog will have internal identifiers and will document how it handles repeated store names.

## 7. Operating status and next steps

There is real loading, dashboards, replay, demo clicks, CRUD and benchmarks. The integrated delivery path and the generator for the new contract are missing. The demo runs on one node, with about 4 GiB of Docker memory and a total server limit of about 3.50 GiB. Reading the full Ele.me JSON exhausted that limit and did not produce a finished comparison.

Next delivery: manual path, validated contract, retry test, batch publishing and the platform dashboard. Then, measure a large load and compare history/aggregate with the same answer. Two nodes and a new physical order are later experiments.

## References

- Project code: `sql/schema.sql`, `sql/eleme.sql`, `dashboard.py` and scripts.
- Measurements: [RESULTS.md](../RESULTS.md), [ELEME.md](../ELEME.md) and reports in `data/`.
- [MergeTree](https://clickhouse.com/docs/reference/engines/table-engines/mergetree-family/mergetree).
- [SummingMergeTree](https://clickhouse.com/docs/reference/engines/table-engines/mergetree-family/summingmergetree).
- [Incremental materialized views](https://clickhouse.com/docs/concepts/features/materialized-views/incremental-materialized-view).
