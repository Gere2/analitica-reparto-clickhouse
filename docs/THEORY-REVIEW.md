# Review of the project against the professor's theory

The course resource filenames below identify classroom materials; those files are not redistributed in this repository. [ASSIGNMENT.md](ASSIGNMENT.md) contains the project brief summary used for the current delivery.

> Historical record: dates, results, speaker allocations and pending statements below describe their original stage. For the current implemented project, 14-slide route and delivery status use [FINAL-DELIVERY.md](FINAL-DELIVERY.md), [DATABASE-STRUCTURE.md](DATABASE-STRUCTURE.md) and [DEMO-GUIDE.md](DEMO-GUIDE.md).

Date: 5 October 2026. This review compares the materials in `recursos/` with `compose.yaml`, `dashboard.py`, the DDL in `sql/` and the saved measurements. The course guide describes the subject. The notes explain concepts and examples, and do not turn every component of the examples into a requirement for our project.

## Conclusion

**The project fits as an event analytics infrastructure for a fictional food-delivery platform.** The guide covers column storage, modelling, ingestion, data warehouses and streaming. The current work demonstrates storage and massive queries. The next step must complete the contract and the ingestion of the fictional application, and measure its guarantees. There is already enough volume.

ClickHouse is a column-oriented analytical system with SQL and a typed schema. It should be presented as OLAP, and that choice justified by its read and aggregation patterns. ClickHouse's columnar storage and Cassandra's wide-column model are different concepts. The resources provided do not include the **Personas** section that assigns the technologies, but the professor confirmed ClickHouse for the group (19 October 2026).

## Comparison with the course notes

| Concept and reference | Project evidence | Assessment and adjustment |
|---|---|---|
| Model for access patterns. Guide, pages 1–2 and 4 | An OTTO row is an event. Ele.me keeps samples. Glovo keeps a catalog | Fits. Document the grain of each table and keep sources separate |
| Frontend, API and backend. `01_1_Components.md` | Browser, Python HTTP API and ClickHouse | Fits. The current API is small and monolithic, with no gateway or load balancer |
| Scaling ladder. `01_1_Components.md` | Physical keys and a daily aggregate before adding nodes | Fits. The benchmark shows a local optimization, not horizontal scaling |
| Docker, persistence and health. `01_3_Docker.md` | Image 25.8, volume and healthcheck | Partial. The API of the current path runs on the host. The whole path still needs packaging so it can be reproduced with one command |
| Availability. `01_2_Concepts.md` | One node and one Docker volume | No redundancy. Persistence does not imply high availability nor replace a backup |
| Consistency, CAP and PACELC. `01_2_Concepts.md` | No replicas in the current deployment | Explain what happens on insert and on read. Do not give the product a CP/AP label without stating topology and configuration |
| Sharding and replication. `01_4_Cross_cutting_concerns.md` | Local partitions by month or file | Make clear these are table partitions within one node. Sharding spreads data across nodes and replication keeps copies |
| Warehouse and lake. `01_4_Cross_cutting_concerns.md` | Source files and typed tables with aggregates | Analytical layer similar to a warehouse. Local input files alone do not demonstrate a data lake or a lakehouse |
| Streaming. `01_4_Cross_cutting_concerns.md` | Python batch replay and buttons with new actions | Incremental ingestion. The replay is historical and the dashboard refresh uses periodic queries. A durable log with offsets is missing to demonstrate stream guarantees |
| Idempotency. `01_1_Components.md` | `/api/live-click` inserts a server-generated UUID. The future DDL proposes a stable ID | Retries still need solving. Repeating the POST can produce two rows. `event_id` and `ORDER BY` do not enforce uniqueness |
| Resilience. `01_4_Cross_cutting_concerns.md` | HTTP timeouts and basic validation | Partial. Acknowledgement, resumption, batch/queue limits and the response to saturation still need defining |
| Percentiles and observability. `01_1_Components.md`, `01_4_Cross_cutting_concerns.md` | Median of three queries and read metadata | Useful as a local comparison. It does not establish p95/p99, API capacity or full latency from event to dashboard |
| Docker security. `01_3_Docker.md` | Demo ports limited to localhost, configuration with `demo` values and optional variables in Python | Lab configuration. For a shared deployment, externalize credentials and separate ingestion and read permissions |
| Critical reflection and comparison. Assignment brief | Historical vs aggregate, same answer | Comparison within ClickHouse. There is no benchmark against PostgreSQL or another engine yet |

## Changes we applied to the scope and the presentation

1. Use **Delivery Atlas** for the fictional case and mark the tables of its contract as proposals. The public lab already works, but it does not yet demonstrate the performance of the future model.
2. Focus the **5-minute** progress update on architecture, event grain, physical design and one measured query improvement. OTTO demonstrates scale. Ele.me and Glovo add industry context. REES46 and the stress test remain supplementary material.
3. Describe the three times precisely: historical event time, ingestion time and dashboard refresh time. Only the buttons record new actions in the current demo.
4. Show the operational limitations: single node, no sharding or replica, and no general idempotency protocol demonstrated.
5. Keep the future DDL off the server until its publishing is implemented and tested. The incremental view must receive events without retry duplicates.

## Next implementation, by priority

### P1. A complete path for the new contract

Minimal mini-app, batch publisher and `app_events`. Define actions and fields per event type, maximum size, validation and traceability. Use a stable identifier created before sending. Rehearse a retry after losing a response and demonstrate a single logical event and a single increment in the aggregate.

Choose and document the delivery guarantee. If recovery after a crash is intended, the publisher needs durable state and a deduplication mechanism consistent with storage and the view. An in-memory cache of IDs does not establish that guarantee. Do not present exactly-once delivery until the full path is verified.

### P2. Measure the infrastructure

Record accepted events per second, rows and bytes per batch, rejections, errors, memory and delay from `event_time`/`ingested_at` to the dashboard. Measure request latency under enough load to compute percentiles. Distinguish API cache, SQL cache and persistent aggregate.

### P3. Reproducibility and failures

Package the API and ClickHouse of the current path in Compose with healthchecks, networking by service name, and declared versions and limits. Reproduce from a clean machine with a reduced dataset. Rehearse a crash and recovery, compare counts and document backup/restore. A volume keeps data after recreating a container, but it does not cover disk loss.

### P4. Optional distributed experiment

If there is time, try replicas with `ReplicatedMergeTree` and ClickHouse Keeper, or sharding with local tables and `Distributed`. Each experiment must answer a measured requirement. Replication improves redundancy and can introduce lag between copies. Distributing data increases capacity and requires choosing a key and coordinating queries. The current design has not run either experiment.

## Academic preparation

The guide, page 5, asks us to justify and cite AI assistance and to verify its results. This work has used Codex for code review, documentation and slide creation. Claude (Anthropic) has also been used for the mini-app, the assignment checklist, the Windows installation tests, the extended theory and the English translation. The cover is an AI-generated illustration. The measurements come from the project's reports and the decisions must be defended by the group. The exact model identifier of each earlier run is not recorded in these files, and no invented version is attributed.

## Sources

- `Course guide`, pages 1–5.
- `Components`.
- `Concepts`.
- `Docker` and `examples`.
- `Cross-cutting concerns`.
- [Current and proposed structure](DATABASE-STRUCTURE.md), [results](RESULTS.md) and the repository code.
- [Replication in ClickHouse](https://clickhouse.com/docs/reference/engines/table-engines/mergetree-family/replication).
- [ClickHouse analytical architecture](https://clickhouse.com/docs/get-started/about/why-clickhouse-is-so-fast).
