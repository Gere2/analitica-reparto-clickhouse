# ClickHouse in practice: final presentation

Updated 27 October 2026. English slides and notes. Delivery Atlas supplies the workload; ClickHouse is the main subject.

**Format:** 20 minutes including dashboard exploration and the operations/CRUD demo, then about 10 minutes of questions. Core script: **17:35**, with **2:25** for transitions and small delays.

| Slide | Topic | Speaker | Target |
|---:|---|---|---|
| 1 | ClickHouse in practice | Geremi | 0:20 |
| 2 | Why ClickHouse fits our workload | Geremi | 0:40 |
| 3 | What is ClickHouse? | Geremi | 0:40 |
| 4 | ClickHouse table structure | Geremi | 1:00 |
| 5 | Why we chose Delivery Atlas | Geremi | 0:35 |
| 6 | Three data origins in ClickHouse | Geremi | 0:40 |
| 7 | The data path into ClickHouse | Geremi | 0:45 |
| 8 | One checkout, linked across the database | Geremi | 0:45 |
| 9 | Dashboards backed by ClickHouse | Anuar | 0:30 |
| 10 | Customer Journey in ClickHouse | Anuar | 2:00 |
| 11 | Historical datasets, analytical SQL | Anuar | 2:00 |
| 12 | ClickHouse Performance | Anuar | 2:00 |
| 13 | Prepared aggregates: a measured trade-off | Echenique | 1:00 |
| 14 | Live operations and Python CRUD | Echenique | 3:00 |
| 15 | Reliability and measured limits | Echenique | 0:40 |
| 16 | What we learned | Echenique | 1:00 |

[English notes](CLICKHOUSE-PRESENTER-NOTES-EN.md) · [Editable content](CLICKHOUSE-PRESENTATION-EN.json) · [Dashboard guide](CLICKHOUSE-DASHBOARDS.md) · [Selection history](PROJECT-DECISIONS.md)

## Rehearsal route

Geremi explains the workload, storage and event model. Anuar shows Journey, the historical explorers and Performance. Echenique distinguishes the documented measurements from current observations, follows one order and runs Python CRUD on the scratch table.

Journey: inspect one run and its unique-session grain, then expand windowFunnel SQL and actual read statistics. Source explorers: demonstrate a meaningful filter while preserving each source’s row meaning. Performance: inspect engines/sort keys, query history and a fixed comparison with matching answers. Operations: connect the latest-state view to the event history and map.

The presentation keeps eight hidden slides for source semantics, retry identity, shards/replicas, CRUD, benchmark conditions, AI scope, recovery and production alternatives.

## Host preparation and fallback

Rebuild both atlas and share-gateway for the new read routes. The frontend alone cannot add them to an old backend. Confirm which datasets exist on the presentation host; opening a dashboard never downloads them. The public gateway permits reads. Controls, miniapp checkout and SQL/CRUD run on the host.

Preconfigure CLICKHOUSE_URL, CLICKHOUSE_USER and CLICKHOUSE_PASSWORD for the actual CRUD host without projecting values. The script defaults target the old lab on port 8124. Use delivery.demo_events. Rehearse its temporary pause and restoration of large-table merges when those tables exist.

For a stable detail/aggregate comparison, stop producers on the host and wait until the queue is empty. Concurrent publication can change answers between reads. An equality failure suppresses the timing ratio.

If a step stalls for 15 seconds, switch to a prepared order or the local dashboard. If no live path works, clearly label dated screenshots and saved query outputs as recorded evidence. They support explanation but do not replace the live-demo requirement.

## Evidence boundaries

The native five-session funnel is an explicitly labelled integration-test cohort, not production customer behaviour. The new Performance screenshot shows a disposable validation environment with tiny seeded datasets. The older Madrid capture is dated 21 October. The OTTO 27.9× result compares two ClickHouse designs under documented local conditions. Atlas exact-ID counts were slower in their separate measured experiment. No PostgreSQL performance benchmark or replicated cluster is claimed.

A complete timed group rehearsal and the independent installation check still remain. Earlier FINAL-PRESENTATION-EN and FINAL-PRESENTER-NOTES-EN files are the previous working version.
