# Delivery Atlas database structure

The current application uses `delivery_atlas` for fictional platform events and `delivery` for public datasets. The API applies `sql/atlas.sql`, `sql/atlas_operations.sql`, `sql/atlas_agents.sql` and `sql/atlas_miniapp.sql` at startup. The separate `delivery_proposal` DDL is an archived design, not the implemented schema.

## Event tables

| Table | Grain | Replacement key and version |
|---|---|---|
| `app_events` | One browsing action | `(source_kind,event_date,city_id,event_type,event_time,session_id,event_id)`; `ingested_at` |
| `customer_activity` | One customer decision/action | `(simulation_run_id,customer_id,event_time,event_id)`; `ingested_at` |
| `customer_orders` | One confirmed purchase record | `(simulation_run_id,order_id,event_id)`; `ingested_at` |
| `courier_positions` | One fictional GPS sample | `(simulation_run_id,city_id,courier_id,event_time,event_id)`; `ingested_at` |
| `order_events` | One complete order status snapshot | `(simulation_run_id,city_id,order_id,event_time,event_id)`; `ingested_at` |

These five tables use `ReplacingMergeTree(ingested_at)` and monthly event-time/date partitions. `ORDER BY` determines the physical sort order and sparse primary index; it does not reject duplicate keys. Retried immutable events can exist as physical copies. The API's ID/fingerprint contract prevents conflicting content, while `FINAL` or the appropriate exact aggregate produces logical answers at read time.

## Prepared state and read views

| Stored table | Insert materialized view | Read view | Grouping and answer |
|---|---|---|---|
| `app_daily_rollup` | `app_daily_rollup_mv` | `app_daily_counts` | Exact event-ID sets by source kind, date, city, section and event type |
| `courier_latest_state` | `courier_latest_mv` | `courier_latest` | Latest position per run, city and courier |
| `order_latest_state` | `order_latest_mv` | `order_latest` | Latest order snapshot per run, city and order |
| `customer_latest_state` | `customer_latest_mv` | `customer_latest` | Latest customer state per run and customer |

The stored tables use `AggregatingMergeTree`. Each materialized view processes inserted blocks, producing `uniqExactState` or `argMaxState`. Read views combine partial states with `uniqExactMerge` or `argMaxMerge` and the corresponding `GROUP BY`; one logical answer may be represented by several physical states before merging.

Latest-state weights use `(event_time,event_id)`, so an old sample arriving late does not replace a newer event-time state. The immutable-event contract makes replayed payloads stable. The map asks for the latest state rather than recomputing every courier from the whole history at every refresh. [The GPS experiment](GPS-BENCHMARK.md) compares those two ways of answering the same question.

The daily browsing aggregate has no run dimension. Its fixed live comparison covers all synthetic Madrid runs on the chosen date. It is distinct from the GPS benchmark, which explicitly filters one frozen run.

## Catalog and logical relationships

`demo_restaurants` and `demo_products` use `ReplacingMergeTree(version)` and are read with `FINAL`. Catalog rows retain fields such as `source_table`, `source_row`, `name_kind` and `price_kind`. A reused public product/name does not make its fictional price or a simulated purchase an observed commercial sale.

Relationships are logical identifiers checked by application code, not enforced foreign keys:

- A customer/session produces browsing actions and decisions; checkout links a confirmed `order_id` to that customer/session.
- An order snapshot references an order, restaurant and courier; GPS samples reference the courier and current order.
- Run identifiers keep simulation cohorts separate. Joins or filters over operations must retain the relevant run as well as the entity ID.
- Catalog product/restaurant references belong to the app's catalog. Unrelated OTTO, REES46, Criteo and Glovo populations are not joined as a single customer journey.

The diagram in [ATLAS-INFRASTRUCTURE.md](ATLAS-INFRASTRUCTURE.md) shows the ingestion and read path. [MINIAPP.md](MINIAPP.md) describes checkout identifiers and retry behavior.

## Provenance and types

UUIDs identify events, sessions, customers, orders, couriers and runs as applicable. `DateTime64(3,'UTC')` retains millisecond event and ingestion times. `LowCardinality` and enums represent repeated labels; nullable fields preserve missing references rather than inventing them. GPS constraints check coordinate ranges.

Manual browsing in `app_events` is `demo_live`. `atlas_miniapp.sql` also permits `demo_live` purchases in `customer_orders`; the related preparation/status and GPS remain synthetic. AI and rule-driven customer actions both remain fictional; `decision_mode` and recorded model decisions distinguish their origin. The Journey query reads `customer_activity`, not manual mini-app browsing.

## Public data and analytical queries

| Current host table | Meaning | Host-reported rows on 15 November |
|---|---|---:|
| `delivery.criteo_uplift` | Public advertising experiment record | 13,979,592 |
| `delivery.glovo_products` | Public catalog product record | 2,887,444 |

Counts come from [the dated host record](HOST-STATUS-2026-11-15.md). These tables are separate from the five fictional event tables and from their aggregate states.

Customer Journey computes unique sessions and ordered steps using `windowFunnel` over one run and a 30-minute interval. Performance reads physical metadata in `system.parts`/`system.tables` and completed SELECT families in `system.query_log`. Neither requires a new application table for each chart. Definitions and limits are in [CLICKHOUSE-DASHBOARDS.md](CLICKHOUSE-DASHBOARDS.md).

## Physical design and availability

Monthly partitioning groups event parts within one server; it is not sharding. Sorting helps filters whose access pattern matches the key, and its actual effect depends on the query/parts. Incremental prepared state moves repeated work to ingestion and uses additional storage. Its insertion/storage cost has not been separately measured in the GPS campaign.

One ClickHouse node, persistent volumes and a local SQLite queue are deployed. The queue and idempotent retries support recovery of pending publishes; the separate destination INSERTs do not form a multi-table transaction. No replicated high availability or sharded deployment has been demonstrated. See [APPLIED-THEORY.md](APPLIED-THEORY.md).

## Historical lab

`delivery.otto_archive`, `otto_replay`, `otto_daily_rollup`, `rees46_events`, `eleme_samples` and `otto_scale_benchmark` belong to earlier experiments, with their own grains and source conditions. They remain in the SQL/loaders but are not required by Atlas. The initial `delivery_proposal` and its pending implementation statements are preserved in [the earlier structure document](history/DATABASE-STRUCTURE-BEFORE-FINAL-2026-11-15.md).

Sources: applied project SQL; [MergeTree](https://clickhouse.com/docs/engines/table-engines/mergetree-family/mergetree); [ReplacingMergeTree](https://clickhouse.com/docs/engines/table-engines/mergetree-family/replacingmergetree); [AggregatingMergeTree](https://clickhouse.com/docs/engines/table-engines/mergetree-family/aggregatingmergetree).
