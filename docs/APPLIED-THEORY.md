# Course theory applied to Delivery Atlas

Updated 15 November 2026 for the implemented Atlas schema, analytical portal and isolated GPS campaign. [The final index](FINAL-DELIVERY.md) and [current model](DATABASE-STRUCTURE.md) define the delivery scope.

| Concept | Implemented decision and consequence | Code or evidence |
|---|---|---|
| Service boundaries | One Python API process validates input, manages a local queue, publishes batches and serves reads. Multiple API producers need distinct queue volumes; two were used on Anuar's host. | `atlas/server.py`, `atlas/store.py`, [host record](HOST-STATUS-2026-11-15.md) |
| Durable queue | SQLite WAL, transactions and `synchronous=FULL` commit accepted events before a 202 response. Pending events can be published after an ordinary API/ClickHouse restart. This does not provide disk-loss protection or replicated availability. | `atlas/store.py`, [recovery evidence](ATLAS-RESULTS.md) |
| Multi-table publication | The publisher issues separate INSERTs to the destination tables. Partial success is recovered by resending the immutable batch; it is not one transaction across all tables. Specific ClickHouse INSERTs have their own documented guarantees. | `atlas/clickhouse.py`, [INSERT guarantees](https://clickhouse.com/docs/concepts/features/operations/insert/transactions) |
| Idempotency | Stable event IDs and content fingerprints recognise retries; conflicting content returns 409. Replacement reads and exact ID states preserve logical answers even when physical retry copies exist. | `atlas/store.py`, `sql/atlas.sql`, operations/agent SQL |
| Backpressure | The queue has a configurable pending limit (200,000 by default). Reaching it causes 503 rather than unlimited acceptance. A 202 confirms receipt, not dashboard visibility. | `ATLAS_MAX_PENDING`, `atlas/server.py` |
| Analytical modelling | Histories use `ReplacingMergeTree`; prepared exact-ID/latest-state tables use `AggregatingMergeTree` and incremental materialized views. Query access patterns determine the sort/grouping keys. | Four `sql/atlas*.sql` files |
| Event time | Latest-state weights include event time and event ID. Out-of-order arrival is tested so an old event cannot replace a newer position merely because it arrived later. | `sql/atlas_operations.sql`, operation integration tests |
| Partitioning and sharding | Monthly partitions organise parts/maintenance in one server. Sharding across servers and replicated high availability are explained but not deployed. | SQL `PARTITION BY`, [fundamentals](FUNDAMENTALS.md) |
| Availability and consistency | During ClickHouse unavailability, the API can accept events while queue capacity remains, and reads lag/fail. With one node there is no replica-partition experiment; CAP/PACELC labels alone do not describe every configuration. | Queue/status behavior, [host and public checks](HOST-STATUS-2026-11-15.md) |
| Source semantics | AI/rule/manual platform actions and public advertising/catalog data retain different meanings. A catalog entry is not a purchase; public populations have no shared journey IDs. | Contracts, `decision_mode`, `source_kind`, dataset readers |
| Observability | Queue status, publication errors, position age, physical parts and completed query logs expose different stages of the pipeline. Query logs flush asynchronously and shared reads may use a dated cache entry. | `/api/status`, `atlas/analytics.py`, [dashboard definitions](CLICKHOUSE-DASHBOARDS.md) |
| Repeatable experiments | The GPS lab freezes input, verifies full answers and joins query IDs to server records before interpreting repeated bounded reader levels. The live dashboard's single detail/aggregate comparison is a different observation. | [GPS-BENCHMARK.md](GPS-BENCHMARK.md), `benchmarks/gps/` |
| Shared access | Loopback host services are exposed through an authenticated read-only gateway and server-side GET proxy. Tokens remain on the server. Local controls/checkout/SQL are not exposed by that proxy. | `atlas/share.py`, `api/proxy.js`, [sharing guide](SHARING-VERCEL.md) |

## Observed advantages and tradeoffs

The completed GPS campaign demonstrates less read work from prepared latest state with equal answers under the tested concurrency and resource budget. Column storage and typed SQL support analytical reads; batch publication avoids treating each telemetry sample as an isolated small insert.

The improvement has costs: extra state storage and insertion-time computation, neither separately measured in that read campaign. Exact ID sets also consume memory; the older one-million-event test found its daily aggregate slower than detail for that question. These outcomes concern different workloads and do not contradict each other.

Background replacement is eventual, while exact queries require `FINAL` or suitable aggregate logic. Updates/deletes can rewrite parts and do not automatically reverse an incremental view's earlier contributions. The CRUD example uses a scratch table and temporarily pauses/restores merges on existing large legacy tables; avoid running it during a benchmark.

The queue retains published IDs/payloads for retry recognition and grows with history; it has no automatic pruning policy. One host, one database node and a changing Quick Tunnel are operational limitations. The paused watchdog, verified exports and local/recorded fallback reduce disruption within this classroom setup; they do not turn it into a replicated production service.

## Future work

Measure the insertion/storage tradeoff of prepared views, compare databases on equivalent frozen answers/resources, and design a bounded queue-retention policy. Replicas/shards, backup restoration under additional failure modes and production authentication/resource isolation need their own implementation and evidence. The [retained presentation clarifications](DEFENCE-NOTES-EN.md) keep those distinctions explicit.
