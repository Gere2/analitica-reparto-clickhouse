# Delivery Atlas: five-minute speaker guide

6 slides, 5.0 planned minutes. Timing depends on delivery and questions.

[Browser presentation](http://127.0.0.1:8000/avance-bd.html). Use arrow keys to navigate, F for full screen and N for notes. The PowerPoint includes speaker notes and editable tables.

This guide covers the five-minute progress update. The detailed course review is in [REVISION-TEORIA.md](REVISION-TEORIA.md), in Spanish. PRESENTACION.md retains the earlier final-presentation outline and still needs adapting.

## 1. Delivery Atlas

Planned time: 30 seconds.

We are building the analytics infrastructure for a fictional food delivery platform. It will store navigation events and display activity in a dashboard. Our current lab contains 628 million public events from OTTO and REES46, representing separate sources. Ele.me adds food recommendation samples, and Glovo provides a catalogue. The delivery mini app and its shared event contract are still pending. The cover is a conceptual illustration generated with AI.

Sources: `docs/PLATAFORMA-FICTICIA.md`, `docs/ESTADO-EQUIPO.md`.

## 2. Current architecture and tables

Planned time: 45 seconds.

This structure follows the frontend, backend and data layers in the course notes. Scripts load batches, and the Python API queries ClickHouse over HTTP. OTTO stores one row per event. Ele.me stores labelled recommendation samples and uses staging to validate complete files before publication. We keep sources separate. A materialized view feeds the OTTO daily rollup. Docker provides persistent storage and a health check. The API currently runs on the host, and the database has one node. Replay preserves the historical timestamp and records when each event enters the demo.

Sources: `recursos/01_1_Components.md`, `recursos/01_3_Docker.md`, `sql/schema.sql`, `sql/eleme.sql`, `compose.yaml`, `dashboard.py`.

## 3. Proposed platform event model

Planned time: 75 seconds.

We propose app_events as the central table for the fictional platform. Each event has a stable ID, session, timestamps and context. source_kind distinguishes simulated traffic, new demo actions, historical data and replay. The design follows the access patterns: filtering by source, date, city and action. MergeTree stores columns in data parts. PARTITION BY groups months within the node. ORDER BY sorts the data and supports a sparse primary index, without enforcing uniqueness. A daily rollup will count events by dimension. The proposed sorting key still needs benchmarking. Safe retries require an ingestion protocol in addition to a UUID. The DDL exists, but it is not deployed or connected to the mini app.

Sources: `sql/propuesta_delivery.sql`, `docs/ESTRUCTURA-BD.md`, `recursos/01_4_Cross_cutting_concerns.md`, [Documentation](https://clickhouse.com/docs/reference/engines/table-engines/mergetree-family/mergetree).

## 4. Historical data vs daily rollup

Planned time: 50 seconds.

This comparison demonstrates an advantage for our analytical workload. Grouping the historical OTTO table took 5.8908 seconds. Querying the daily rollup took 0.2113 seconds, a 27.9 times speedup. Both queries returned the same result: 87 combinations of day and event type. These are medians of three local runs with the SQL query cache disabled. A persistent rollup reduces reading and computation. SummingMergeTree can retain partial rows for the same key before merging, so the query uses sum with GROUP BY. This follows the scaling ladder in the course notes: optimize queries before adding nodes. These timings do not compare database engines or establish API capacity or latency percentiles.

Sources: `data/query-benchmark.json`, `docs/RESULTADOS.md`, `scripts/benchmark.py`, `recursos/01_1_Components.md`, [Documentation](https://clickhouse.com/docs/reference/engines/table-engines/mergetree-family/summingmergetree).

## 5. Current guarantees and limitations

Planned time: 55 seconds.

The course theory helps us state what we have demonstrated. A persistent volume preserves data when a container is recreated, but it does not provide high availability. Date partitions do not distribute data across machines. We currently have one node without replicas. A future replicated setup must explain its configuration and replica lag, rather than assign a single CP or AP label to ClickHouse. The click API generates IDs on the server, so a repeated POST can insert two rows. We need idempotent ingestion before counting events in the materialized view. Our benchmarks measure queries. We still need request latency, events per second and dashboard lag under load.

Sources: `docs/REVISION-TEORIA.md`, `recursos/01_2_Concepts.md`, `recursos/01_4_Cross_cutting_concerns.md`, `dashboard.py`, [Documentation](https://clickhouse.com/docs/reference/engines/table-engines/mergetree-family/replication).

## 6. Next milestone

Planned time: 45 seconds.

The next milestone is to connect the minimal app journey and a reproducible traffic generator to the proposed contract. Acceptance means navigating the app, ingesting its events, retrying a submission without double counting, and seeing the daily rollup in the dashboard. We will also measure lag and errors and reproduce the environment on another machine. The current lab already provides enough data volume. We will prioritize these guarantees before adding more datasets, Kafka or microservices. The dashboard is available if the lecturer would like to see the current implementation after this update.

Sources: `docs/REVISION-TEORIA.md`, `docs/PLATAFORMA-FICTICIA.md`, `recursos/guia_bbdda.pdf`.
