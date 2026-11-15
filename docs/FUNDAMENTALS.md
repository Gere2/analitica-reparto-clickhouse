# ClickHouse fundamentals and project limitations

## Fit with the BD2 course

ClickHouse is a column-oriented SQL database management system for online analytical processing (OLAP). The professor assigned ClickHouse to this group. Column orientation describes physical storage; it should not be used alone to classify a logical data model as non-relational. The project uses typed tables, SQL, joins and analytical aggregates. [Official introduction](https://clickhouse.com/docs/get-started/about/intro).

The workload is a fictional delivery platform: customer actions, purchases, order status snapshots and courier GPS arrive continuously, while the dashboards need aggregate and latest-state answers. The app, its data contract and its prepared states make the use of ClickHouse explicit.

## Where ClickHouse is used

Append-heavy analytical events support product analytics, observability, time-series analysis and reporting over large histories. These questions often read a few columns from many records. ClickHouse's column storage, compression, sorted parts and parallel execution suit that pattern.

A transactional system is a reasonable system of record for payments, accounts and individual order changes. Delivery Atlas demonstrates the analytical pipeline around fictional operations; it is not a production payment or dispatch service.

## Data model

The [implemented schema](DATABASE-STRUCTURE.md) is defined in the four `sql/atlas*.sql` startup files. Five event tables retain browsing, decisions, purchases, status history and GPS. Four `AggregatingMergeTree` tables store exact daily event-ID sets or latest entity states, maintained by insert materialized views. Read views merge the states for the dashboards. The catalog stores versioned restaurant/product rows.

`ORDER BY` defines physical order and the sparse primary index, not a uniqueness constraint. Monthly partitions organise event parts and maintenance within one node. `LowCardinality`, enums and typed timestamps represent repeated labels and event time. Query filters must match the access pattern; a sort key does not make every filter equally efficient.

## Consistency and availability

Accepted events are committed to the local SQLite queue before a 202 response. The publisher then sends separate destination INSERTs. Until publication finishes, analytics can lag behind receipt. A partially successful publish is retried with the same immutable IDs; physical duplicate copies can appear before replacement merging.

`ReplacingMergeTree` background merges provide eventual deduplication. Exact logical reads use `FINAL` or suitable event-ID/state aggregation; waiting for a merge is not an immediate uniqueness guarantee. Incremental materialized views process inserted blocks, so the daily aggregate stores ID sets rather than adding physical retry copies with a plain counter. [ReplacingMergeTree guide](https://clickhouse.com/docs/guides/developer/replacing-merge-tree).

ClickHouse documents transactional guarantees for specific INSERT conditions, including a single block into a partition of a MergeTree-family table. The Atlas publisher does not wrap all destination tables in one transaction. Recovery relies on the queue and idempotent event semantics. [INSERT guarantees](https://clickhouse.com/docs/concepts/features/operations/insert/transactions).

The deployed node has no replica or high availability. Persistent volumes preserve ordinary restarts; backups and replicated storage address different failure modes. The queue can fill or its disk can fail. Replication with `ReplicatedMergeTree`/Keeper and distribution across shards are architecture topics, not completed multi-node tests here.

## Experiment that justifies ClickHouse

The [completed GPS comparison](GPS-BENCHMARK.md) freezes 4,371,300 fictional positions and 150 couriers in a separate lab with 2 CPUs and 2 GiB of container memory. It verifies equal full answers before and during measurements, then compares recomputing latest positions from history with reading prepared state.

At two concurrent readers, history client p95 is 1,625–1,969 ms and prepared state is 266–281 ms over three repetitions of 200 requests per design. All 2,400 measured requests succeeded and have matching server query-log records. History read a median 4,371,336 rows per request; the prepared query read 150 in this corpus/state layout.

This supports a specific conclusion: preparing the repeated latest-position answer reduces read work under the same tested concurrency and resource budget. The one-second target is an experimental latency criterion, not ClickHouse's universal capacity. The campaign did not measure PostgreSQL/DuckDB, the prepared design's maximum concurrency, or the insertion/storage cost of maintaining its view.

The [older one-million-event experiment](ATLAS-RESULTS.md) found the exact daily aggregate slower than detail for its own workload. That result remains valid within its conditions; prepared state is useful when the measured access pattern warrants its cost.

## Insert, read, update and delete

The publisher groups events into batches. Reads use typed parameters, `FINAL`, `GROUP BY`, exact ID aggregates, `argMaxMerge` and `windowFunnel` according to the question. Updating and deleting are possible: the classroom CRUD uses synchronous mutations on `delivery.demo_events` and shows their result explicitly. The event histories instead append new snapshots.

`scripts/crud_demo.py` also temporarily pauses merges on existing legacy large tables and restarts them in `finally`. Its row changes are confined to the scratch table; those merge-control commands are an additional operational effect. Rehearse it on the agreed host outside the isolated benchmark.

## Interfaces, clients and tools

Atlas uses ClickHouse's HTTP interface through Python's standard library. The API validates input; SQL values use typed parameters, and inserts use `JSONEachRow`. This keeps dependencies small while requiring our own transport/authentication/error handling.

| Interface or page | Project access |
|---|---|
| ClickHouse HTTP and SQL playground | `http://127.0.0.1:8124/play` on the host |
| Atlas API, operations and mini-app | `http://127.0.0.1:8001/` |
| Analytics portal | `/analytics.html` on the host or shared website |
| Isolated GPS lab | Loopback port 18124, separate project/volume and read-only benchmark user |
| Public demo | Authenticated host gateway behind a server-side GET proxy; token absent from browser code |

Official language clients and `clickhouse-client` are alternatives to the minimal HTTP client. Simulation controls, checkout, arbitrary SQL and CRUD remain local. Query logs flush asynchronously; missing records are not zero-duration queries.

## Data quality and limits

Criteo provides public advertising records and Glovo provides a public catalog. These are not private production order/click histories from Glovo or Uber Eats. The [dated host inventory](HOST-STATUS-2026-11-15.md) records loaded tables. Fictional actions, manual actions and historical sources retain their own provenance and row meanings.

The map uses real streets with fictional GPS. Its recorded lines connect samples without street routing. Polling every two seconds does not guarantee a two-second end-to-end delay; the displayed age describes freshness.

Customer Journey uses one run, unique sessions and ordered steps within 30 minutes. Unfinished sessions differ from an explicit abandonment. Physical rows in `system.parts`, exact logical event counts, stored aggregate states and result rows are different metrics. Client latency, server duration, query CPU time and query memory likewise have distinct meanings.

## Comparison with a transactional database

| Need | Appropriate approach |
|---|---|
| Repeated analytical counts and latest positions over event histories | ClickHouse with measured physical design and prepared state |
| Transactional payments/accounts and frequent individual record changes | A transaction-oriented system such as PostgreSQL |
| A cross-database performance claim | Equivalent answers, comparable schema/indexes, frozen data and an actual controlled experiment |

The column/row illustration in the retained slides represents a heap scan. PostgreSQL can use covering indexes and index-only scans when the required values and visibility conditions permit it; our results do not establish its performance. [PostgreSQL index-only scans](https://www.postgresql.org/docs/current/indexes-index-only-scans.html).

Further reading: [current architecture](ATLAS-INFRASTRUCTURE.md), [applied theory](APPLIED-THEORY.md), [presentation clarifications](DEFENCE-NOTES-EN.md) and [sources/AI assistance](AI-USE-AND-SOURCES.md). Historical OTTO/REES46 examples remain in [the earlier fundamentals](history/FUNDAMENTALS-BEFORE-FINAL-2026-11-15.md) and [legacy results](RESULTS.md).
