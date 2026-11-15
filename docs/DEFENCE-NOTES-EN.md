# Technical clarifications for the retained presentation

The approved 14-slide HTML and `SCRIPT-EN.md` are frozen. These clarifications describe the current project and evidence alongside their checkpoint wording; they do not alter the slides, notes, timing or speaking allocation.

| Slides | Clarification |
|---|---|
| 3 | ClickHouse is a column-oriented SQL database for OLAP. Column orientation describes physical storage. Specific INSERTs have documented atomic/transactional guarantees; Atlas publishes its destination tables separately. |
| 4 | The row/column illustration describes a heap-scan access pattern. PostgreSQL can also use covering indexes and index-only scans; no cross-database timing was performed here. |
| 5 | A 202 confirms a durable queue entry. ClickHouse visibility follows publication. The tested recovery model covers pending publishes/retries, not disk loss or replicated availability. |
| 7–8 | Streets are real, courier GPS/orders are fictional, and recorded lines connect samples rather than follow street routing. Model decisions are bounded and retain their origin; public catalog/advertising data remain separate. |
| 9 | The Journey and Performance code is implemented. The host update and successful public reads are recorded on 15 November; the fresh demonstration run and full group rehearsal still require confirmation. Background merging is not an immediate uniqueness guarantee. |
| 10 | The original checkpoint closing leads into the four-slide experiment appendix. Keep the full route within the 20-minute slot. |
| 11–13 | Since the appendix was prepared, the full supplied report has been checked: all 2,400 measured query IDs have server records and recomputed phase p95 values agree. CPU records support resource competition as an explanation; the campaign did not isolate every possible cause. |
| 14 | PostgreSQL/DuckDB comparisons remain planned. More rows only matter to a measurement if the query reads them under the stated filter. |

## The measured improvement

The same frozen 4,371,300-position run and 150 couriers produce equivalent full answers through history and prepared state. Each design/reader count has three 200-request repetitions, in a 2-CPU/2-GiB lab, with SQL result cache disabled and warm system caches.

At two readers, history client p95 is 1,625–1,969 ms and prepared state 266–281 ms. The one-second target is specific to the experiment. It does not identify a universal maximum or the highest concurrency of the prepared design. A closed-loop reader submits its next request as the previous one finishes; it is not a count of human website users or a fixed arrival rate.

The received query logs show median server durations of 561 ms for history with one reader and 6 ms for prepared state; median rows read are 4,371,336 and 150 respectively. Client latency includes transport/client work. Query CPU time, server wall time and query memory are distinct measures; memory per query is not total container RAM.

The materialized view maintains partial `argMax` states on insertion; the read view merges them. The 150 result rows do not promise 150 physical aggregate states in every part layout. Insert-time work and extra state storage are costs outside this read-only campaign.

## Data and recovery

[The host record](HOST-STATUS-2026-11-15.md) reports 37.31 million archived rows across five event tables, including GPS. The timed GPS subset and the public datasets have different scopes. The proposed 50-million milestone was not reached.

Immutable IDs/fingerprints support retry recovery. `FINAL` applies replacement semantics at query time, while exact ID-state aggregates avoid counting repeated immutable events twice. Monthly partitioning is not sharding; a queue and volume are not replicas. This single-node project demonstrates analytical design and bounded recovery, with those operating limits explicit.

Sources: [ClickHouse introduction](https://clickhouse.com/docs/get-started/about/intro), [INSERT guarantees](https://clickhouse.com/docs/concepts/features/operations/insert/transactions), [ReplacingMergeTree](https://clickhouse.com/docs/guides/developer/replacing-merge-tree), [PostgreSQL index-only scans](https://www.postgresql.org/docs/current/indexes-index-only-scans.html), applied project SQL and the raw evidence linked in [GPS-BENCHMARK.md](GPS-BENCHMARK.md).
