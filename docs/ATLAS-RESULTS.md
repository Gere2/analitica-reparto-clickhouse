# Delivery Atlas v1: verified results

> Dated measurement record. Preserve the conditions and scope below. The current GPS campaign is documented separately in [GPS-BENCHMARK.md](GPS-BENCHMARK.md); the final project entry point is [FINAL-DELIVERY.md](FINAL-DELIVERY.md).

Date: 7 October 2026. Evidence exported for the team: [evidencia-atlas.json](evidencia-atlas.json). Local ClickHouse node **25.8.33.6**, Python API and persistent queue. These results describe the `delivery_atlas` database, not the OTTO lab.

## Loading one million events

```bash
python3 scripts/atlas.py generate --events 1000000 --batch 5000 --seed 42 --start 2026-10-06T10:00:00Z
```

- Run ID: `f1a78bc7-67f2-5a8a-af17-a6d9ca6bbfc9`.
- **1,000,000 events generated, accepted and verified in ClickHouse with `FINAL`**, filtering by that run ID. It is not just the number requested from the generator.
- 323.59 seconds of sending, about 3090 events/s. This includes generating, validating and confirming receipt in the queue; it is not an isolated measurement of ClickHouse's insert speed.
- At the end, pending = 0. There was one transient publishing error and the publisher recovered; the final error was null.
- Three cities and sessions of five complete steps. They are `synthetic` events, with simulated times and no abandonment. They do not describe real users, demand or conversion.

## Integrity and recovery

| Test | Result |
|---|---|
| Repeat the same event over HTTP | Second request: accepted 0, duplicates 1 |
| Reuse the ID with different content | HTTP 409; the change is not accepted |
| Unsupported action | HTTP 400 |
| Simulate a lost response after inserting and publish again | 3 physical rows, **2 logical events**; detail and aggregate match |
| Stop ClickHouse, accept an event into the queue and restart the API | The pending event arrived later, with a logical count of 1 |
| Repeat that event after the restart | Accepted 0, duplicates 1 |

The four contract/queue unit tests passed. The integration and recovery scripts checked the real path with ClickHouse. Recovery tested **orderly shutdowns with volumes preserved**, not disk loss, abrupt power cuts or high availability.

The lost-response test used a temporary publisher. As a result, the total in ClickHouse can exceed what the main queue published by one. Recovery added another event after the benchmark. Do not compare counters from different scopes or moments as if they were the same total.

## Detail vs aggregate: same answer, different cost

Benchmark with no concurrent load, empty queue, SQL cache disabled, three queries per alternative. **1,000,002 logical events, 16 groups**, before the recovery test.

| Query | Median wall-clock time | Rows read reported by ClickHouse |
|---|---:|---:|
| Detail `app_events FINAL`, grouping by dimensions | **0.498 s** | 1,331,610 |
| Exact aggregate `app_daily_counts` | **0.703 s** | 31 |

**The aggregate was not faster in this test.** The unique-ID states protect the count against resends, but they cost memory and merge work. Reading fewer rows does not guarantee taking less time. The server's byte/row counters do not represent all the memory used by the states. System cache and warm-up were not controlled; this is a local comparison, not a guaranteed capacity.

The 27.9× improvement measured earlier with OTTO belongs to a different schema and query. It is not attributed to Atlas. Jere's next task is to measure the size of these states and study an optimization that keeps the same retry guarantees.

## Status and limits of the delivery

**Implemented:** applied SQL, validation, queue, batch publishing, endpoints, generator, tests and containers with persistence.

**Pending (as of 7 October):** Anuar's mini-app, Echenique's dedicated dashboard, an independent run on another computer, latency up to the dashboard, a load with abandonment, and a rehearsal. The existing `scripts/crud_demo.py` script can show INSERT/SELECT/UPDATE/DELETE on `delivery.demo_events`; do not edit or delete the Atlas analytical flow as if its aggregates recomputed themselves.

One ClickHouse node, one API and one local queue. Replication, sharding and recovery from disk loss have not been demonstrated. The queue keeps published payloads and grows: its cleanup must be measured and designed before calling it a production solution.
