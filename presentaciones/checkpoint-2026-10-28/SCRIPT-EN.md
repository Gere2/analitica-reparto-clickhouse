# Delivery Atlas — checkpoint script (English)

28 October 2026. Revised from Anuar’s supplied checkpoint. **10 slides, four speakers, 9:40 script including the demo, plus 0:20 buffer.**

| # | Slide | Speaker | Time |
|---:|---|---|---|
| 1 | Delivery Atlas | Geremi | 0:15 |
| 2 | A workload for analytical queries | Geremi | 0:35 |
| 3 | A column-oriented SQL database for OLAP | Geremi | 1:10 |
| 4 | The columns behind an analytical query | Juanro | 1:25 |
| 5 | The data path into ClickHouse | Anuar | 1:15 |
| 6 | Three origins, explicit meanings | Anuar | 1:10 |
| 7 | The map reads current state | Echenique | 1:15 |
| 8 | Read each view in its own scope | Echenique | 1:15 |
| 9 | Implemented, awaiting deployment, next checks | Juanro | 1:05 |
| 10 | ClickHouse in practice | Geremi | 0:15 |

Speaker totals: Geremi 2:15; Juanro 2:30; Anuar 2:25; Echenique 2:30. A complete group rehearsal is still required.

## Before speaking

- Use the verified shared dashboard for read-only presentation, or the prepared local dashboard on Anuar’s host. Localhost on another laptop is not Anuar’s server.
- Confirm the run ID, position age, pending queue and recent publication. The checked run was 01b38d23-ab9a-4d68-8e17-5d2b0c517669.
- Check `model_calls`, `max_model_calls` and `agent_state`. The checked model was at 120/120 (`limit_reached`); traffic was still running. There is no guaranteed five-minute model duration.
- If fresh model decisions are needed, the host operator must prepare a new run before the talk and verify actual decisions. Do not restart the active server during the presentation.
- Open the map and one known order. Use the English AI and downloaded-data views. Pre-open host SQL only if it has been rehearsed, without projecting credentials.
- Keep the prepared CRUD demonstration on a scratch table for the final talk. The public gateway is read-only.
- If a live step stalls for 15 seconds, use the recorded fallback and say explicitly that it is recorded. Screenshots do not prove current availability.

## Spoken script

### 1. Delivery Atlas — Geremi (0:15)

Good morning. We are Geremi, Anuar, Echenique and Juanro. Our assigned database is ClickHouse. Delivery Atlas is the fictional delivery platform we built to explore its analytical design.

Sources:
- Supplied checkpoint, slide 1

### 2. A workload for analytical queries — Geremi (0:35)

Our platform produces customer actions, order changes and courier positions. We verified a mixed run with one hundred fictional customers and fifty couriers. The interval is two seconds. Our question is how to turn an event history into useful views: current deliveries, customer behaviour and historical summaries. The map shows the application; the project explains the ClickHouse tables and queries behind it.

Sources:
- Authenticated read-only API check, 28 October 2026 at 10:36 UTC; run 01b38d23-ab9a-4d68-8e17-5d2b0c517669
- Anuar’s email, 28 October 2026

### 3. A column-oriented SQL database for OLAP — Geremi (1:10)

ClickHouse is an open-source SQL database designed for analytical processing, or OLAP. Column-oriented storage lets a query read the columns it needs. SQL gives us filters, grouping, joins and aggregate functions. These are different aspects: storage layout does not decide whether a database uses SQL. We therefore describe ClickHouse directly as a column-oriented SQL database, rather than calling it NoSQL simply because it stores columns. It is optimised for analytical reads and batched ingestion. Our demo does not use multi-statement transactions across the outbox and ClickHouse. That is different from saying ClickHouse has no transaction guarantees: some inserts are atomic under documented conditions. Juanro will connect the storage design to one of our queries.

Sources:
- https://clickhouse.com/docs/get-started/about/intro
- https://clickhouse.com/docs/concepts/features/operations/insert/transactions

### 4. The columns behind an analytical query — Juanro (1:25)

This query groups the Criteo records by treatment and computes the average observed visit label. It needs the treatment and visit columns, rather than all the feature columns. Column storage reduces unnecessary reads for this kind of analysis. MergeTree adds a physical sort order and a sparse index, so a useful filter may skip data granules. New batches create parts, and background merges consolidate them. Compression can also reduce storage and read volume. These are mechanisms, not a promise that every query takes milliseconds. PostgreSQL can use indexes, including index-only scans, so this picture is not a PostgreSQL benchmark. In our project we inspect the actual rows read, server time and query result. The right question is which design answers our workload correctly, with less work.

Sources:
- https://clickhouse.com/docs/get-started/about/intro
- https://clickhouse.com/docs/primary-indexes
- https://www.postgresql.org/docs/current/indexes-index-only-scans.html
- atlas/clickhouse.py: datasets
- The displayed two-column query is illustrative. The measured /api/datasets Criteo query also aggregates exposure and conversion; the timing is not attributed to this simplified SQL.

### 5. The data path into ClickHouse — Anuar (1:15)

Follow the top path. Fictional events come from rule-based traffic, model decisions and the mini-app. Python validates them and commits accepted events to a local SQLite outbox. The publisher sends batches into delivery_atlas. ClickHouse keeps event histories, while materialized views build aggregate states. The read API merges those states to obtain the latest courier or order. This avoids rebuilding current state from the complete GPS history on every refresh. The lower path is separate: public datasets are loaded into delivery. They support historical questions and retain their own meanings. The outbox helps retry publication after a temporary outage. It does not provide replication, a cross-system transaction or protection against loss of the host disk.

Sources:
- atlas/server.py
- atlas/store.py
- sql/atlas_operations.sql
- docs/ATLAS-INFRASTRUCTURE.md

### 6. Three origins, explicit meanings — Anuar (1:10)

We distinguish three origins. Rule-based traffic generates repeatable fictional activity. Model-controlled customers make bounded decisions through a local model, and Python validates the results. Downloaded sources contain public observations, such as Criteo user records and Glovo catalog entries. All generated customers, purchases and GPS positions remain fictional, including those controlled by the model. The current hybrid configuration assigns three customers to the model and ninety-seven to traffic. A customer appears in the AI metrics after a model decision is recorded, so configuration alone is not proof that it acted. Public records are not joined to our fictional customer journeys. In particular, Glovo catalog size measures supply, and the released Criteo sample supports observed group summaries, not recovery of the original campaign incrementality.

Sources:
- Anuar's email, 28 October 2026
- atlas/customer_runtime.py
- atlas/clickhouse.py: customers and datasets
- https://huggingface.co/datasets/criteo/criteo-uplift#privacy

### 7. The map reads current state — Echenique (1:15)

We now switch to the dashboard. These are real Madrid street tiles, with fictional couriers and GPS samples. I select one courier and follow its order. The latest position comes from a ClickHouse latest-state view using argMax aggregate states. The recorded path is a separate read of that courier's history. The line joins recorded samples; it is not a road-routing result. The browser polls periodically, and cached reads reduce duplicate work for viewers. I check the event time and position age before describing anything as current. Polling every two seconds does not guarantee two-second end-to-end freshness. If this is the recorded fallback, I will say so explicitly.

Demo actions:
- Open the working host or verified shared dashboard
- Select one courier and activate Follow courier
- Point to event time, position age and the linked order
- Explain latest-state read versus GPS history; return to slides within 75 seconds

Sources:
- web/atlas-map.js
- sql/atlas_operations.sql
- atlas/clickhouse.py: operations and history
- Recorded browser capture of the verified public demo, 28 October 2026 at about 11:43 Europe/Madrid; fictional courier positions; OpenStreetMap/Leaflet attribution remains visible.

### 8. Read each view in its own scope — Echenique (1:15)

First I select AI agents and inspect a recorded decision. In our verification the model had reached its limit of one hundred and twenty calls. Traffic was still running, so moving couriers did not prove that the model was still deciding. Then I switch to downloaded datasets. Our Criteo read processed thirteen million nine hundred and seventy-nine thousand five hundred and ninety-two rows in one hundred and five point seven milliseconds of ClickHouse execution time. This is one dated observation of the endpoint query, not a benchmark against another database or a guaranteed latency. I report the current timestamp and rows read with the time. The released sample supports observed group summaries. Server time excludes browser and gateway latency, and a shared response can be cached.

Demo actions:
- Select AI agents and inspect one decision and model state
- Select Downloaded datasets; point to query timestamp, rows read and elapsed time
- Do not run /play unless the presenter is on the prepared host
- Use the recorded screenshots if the live path stalls for 15 seconds

Sources:
- atlas/customer_runtime.py: model call budget
- atlas/share.py: cache
- atlas/clickhouse.py: datasets
- https://github.com/Gere2/analitica-reparto-clickhouse/pull/9
- Recorded screenshots extracted from the supplied checkpoint
- Authenticated /api/simulation and /api/datasets reads, 28 October 2026 at 10:36 UTC. One observation; no cache-control experiment.

### 9. Implemented, awaiting deployment, next checks — Juanro (1:05)

The core event path and map are implemented. The public-data views are separate from fictional activity. Customer Journey and ClickHouse Performance are already implemented in PR nine, with tests; the next step is deployment, not starting their development. Anuar reports that his host is still on main seven-three-four-three-seven-four-d, which does not contain those routes. Before the final talk we need the backend and gateway updated together, a prepared CRUD demonstration on a scratch table, an independent installation check and a timed rehearsal. The main limits remain one node, finite model calls and dependence on the host and tunnel. ReplacingMergeTree replacement happens during merges or at query time with FINAL. It does not enforce a unique key or automatically repair aggregates fed by duplicate inserts.

Sources:
- https://github.com/Gere2/analitica-reparto-clickhouse/pull/9
- Anuar's email, 28 October 2026
- https://clickhouse.com/docs/reference/engines/table-engines/mergetree-family/replacingmergetree
- docs/ATLAS-RESULTS.md

### 10. ClickHouse in practice — Geremi (0:15)

Our main lesson is to connect each analytical question to its data grain, storage design and measured query cost. Delivery Atlas makes those choices visible. Thank you. We are ready for your questions.

Sources:
- Project synthesis

## Questions and precise answers

**Is it NoSQL?** We describe it as a column-oriented SQL DBMS for OLAP. Column layout and relational/SQL capabilities are different dimensions.

**Does it have transactions?** Some inserts have documented atomicity/isolation guarantees. Our application does not use a multi-statement transaction spanning SQLite and ClickHouse.

**Why not PostgreSQL?** We chose a columnar analytical workload. PostgreSQL supports indexes and index-only scans. We did not run a PostgreSQL comparison.

**How are retries counted?** Event identity and a payload fingerprint protect acceptance. ReplacingMergeTree replacement uses the sorting key and a version, during merges or with FINAL. Exact-ID aggregate states handle logical counts where implemented. Replacement does not automatically repair arbitrary materialized aggregates.

**Is current state one physical row?** The logical latest view merges argMax aggregate states by entity. Several physical states can exist in parts before merges.

**Can the queue guarantee no data loss?** It supports retries for locally committed accepted events during temporary outages, while that storage survives. It does not protect against disk loss, supply a replica or create a cross-system transaction.

**Does 105.7 ms mean the whole website loads in that time?** No. It is ClickHouse execution time for one dated Criteo endpoint query; it excludes gateway and browser latency. Shared responses can be cached.

**Are the advertising results causal uplift?** They are observed summaries of the privacy-sampled released groups. The publisher says the original campaign incrementality cannot be recovered.

**Are the new dashboards missing?** Their implementation is in PR #9. Anuar’s current main-based host does not expose the new routes. Backend and gateway must be updated together after integration.
