# ClickHouse in practice: English presenter notes

Core: **17 min 35 sec**, including dashboard exploration and operations/CRUD. Reserve **2 min 25 sec** for transitions and delays inside the 20-minute slot.

| Speaker | Slides | Target |
|---|---|---|
| Geremi | 1–8 | 5:25 |
| Anuar | 9–12 | 6:30 |
| Echenique | 13–16 | 5:40 |

## 1. ClickHouse in practice

Speaker: Geremi
Target: 20 seconds

Hello, we are Geremi, Anuar and Echenique. Our project uses Delivery Atlas, a fictional delivery platform, to show how ClickHouse stores event histories and answers analytical questions. We will use dashboards to explain the tables, queries and measured costs behind the application.



Sources: docs/ASSIGNMENT.md; docs/CLICKHOUSE-DASHBOARDS.md

## 2. Why ClickHouse fits our workload

Speaker: Geremi
Target: 40 seconds

The professor assigned ClickHouse to our group. Our decision was to choose a project that makes its strengths visible. A delivery application produces a long history of searches, carts, checkouts and courier positions. Analytical questions examine many of those events together. For example, we can count actions by day and compare the activity of different sources. These repeated summaries are a useful workload for ClickHouse. Choosing one courier from a short list would not explain why we needed a database for large-scale analytics. That is why the project focuses on the event history behind the application.



Sources: docs/ASSIGNMENT.md; docs/PROJECT-DECISIONS.md; https://clickhouse.com/docs/intro

## 3. What is ClickHouse?

Speaker: Geremi
Target: 40 seconds

ClickHouse is a column-oriented database for analytical queries, and we query it with SQL. Column-oriented means it stores values from the same column together. In this illustrative table, a query counting actions by day needs the date and action columns. It does not need every field in every record. This can reduce the data the query reads. OLAP means online analytical processing: analysing a history through counts, groups and trends. Our deployment uses ClickHouse 25.8 in Docker with one node. The application creates the events. ClickHouse stores and analyses them.

The table is an illustrative example, not an output from a measured run. If asked about NoSQL: the course assigned ClickHouse. Its precise model is a columnar analytical database with a typed schema and SQL. The label alone does not explain its behaviour.

Sources: compose.yaml; docs/FUNDAMENTALS.md; https://clickhouse.com/docs/intro

## 4. ClickHouse table structure

Speaker: Geremi
Target: 60 seconds

This is an excerpt from our actual app_events table. The engine is ReplacingMergeTree, with ingested_at as the version. We partition the table by month. A partition groups data inside a table, and it is different from a shard on another server. Within each data part, the sorting key starts with the fields used by our queries, including source, date and city. A sparse index helps the engine skip ranges it does not need. New inserts create data parts, and background merges combine them. ReplacingMergeTree can replace rows with the same sorting key during those merges. That replacement is eventual. ORDER BY does not enforce immediate uniqueness, so we also preserve stable event IDs in the application.

Hierarchy for follow-up: server, database, table, partitions, data parts and columns. The SQL excerpt shows the storage clauses, not the complete CREATE TABLE statement.

Sources: sql/atlas.sql; https://clickhouse.com/docs/reference/engines/table-engines/mergetree-family/mergetree; https://clickhouse.com/docs/reference/engines/table-engines/mergetree-family/replacingmergetree

## 5. Why we chose Delivery Atlas

Speaker: Geremi
Target: 35 seconds

We considered large public datasets, then Spanish mobility and courier assignment. Choosing one courier did not justify millions of analytical events. Delivery datasets also had gaps: catalogs, recommendation samples and purchase-linked sequences have different meanings. Delivery Atlas gives us a coherent live event contract, while the public archives remain separate analytical workloads.

These are discussed proposals, not benchmarks of every alternative. The professor assigned ClickHouse. Our choice was the project and workload.

Sources: docs/PROJECT-DECISIONS.md; docs/ASSIGNMENT.md

## 6. Three data origins in ClickHouse

Speaker: Geremi
Target: 40 seconds

Downloaded archives provide historical observations. A rule-based simulator provides repeatable event volume. A local model can supply bounded customer decisions, which Python validates. These are data origins, not three different kinds of database. We use delivery for the historical lab and delivery_atlas for our platform. Provenance fields keep the populations and decision methods explicit.

OTTO and REES46 have separately verified historical loads of 216,716,096 and 411,709,736 events. Do not imply all large archives are loaded on the public host. Manual miniapp actions remain a distinct provenance. An AI configuration alone does not prove a completed model decision.

Sources: sql/atlas.sql; sql/atlas_agents.sql; docs/AI-CUSTOMERS.md; docs/RESULTS.md

## 7. The data path into ClickHouse

Speaker: Geremi
Target: 45 seconds

Producers send events to the Python API. The API validates and commits them to a SQLite outbox. The publisher inserts batches into ClickHouse and retries failures. ClickHouse holds the event history and the prepared states used by the dashboards. The browser reads through an allowlisted gateway and Vercel proxy. The API and publisher are logical stages in one Python process. HTTP 202 confirms queue acceptance, while database visibility follows publication.

Public dataset loaders populate delivery separately. The public gateway permits reads and keeps its token server-side. SQLite is transport persistence, not an independent analytical replica.

Sources: atlas/server.py; atlas/store.py; atlas/clickhouse.py; api/proxy.js; docs/CLICKHOUSE-DASHBOARDS.md

## 8. One checkout, linked across the database

Speaker: Geremi
Target: 45 seconds

Here is the data model behind one purchase. app_events stores the checkout event. customer_orders connects checkout_event_id to order_id. order_events keeps the order's changing status. courier_positions records timestamped GPS samples linked to that order and courier. customer_activity stores the customer's action and its reason. We also keep simulation_run_id so different runs remain separate. These are application-level links. The histories retain the events, while latest-state views use argMax states to provide the current order and courier state. This lets the dashboard answer a current-state question without treating the latest row as the whole history.

 Money uses integer minor units. Timestamps use UTC. In a real trace show complete IDs in the data, even if the dashboard shortens labels.

Sources: sql/atlas.sql; sql/atlas_agents.sql; sql/atlas_operations.sql; atlas/clickhouse.py

Handover: “Anuar will now show the ClickHouse dashboards and their queries.”

## 9. Dashboards backed by ClickHouse

Speaker: Anuar
Target: 30 seconds

The portal contains eight views with a common English navigation. We will focus on Customer Journey and ClickHouse Performance, then explore the public sources and follow a delivery. Each analytics view exposes its source, fixed SQL and measured server work. The charts are entry points for explaining ClickHouse.

Dashboard list: live operations, Customer Journey, ClickHouse Performance, OTTO, REES46, Glovo, Ele.me and Criteo. Handover: Anuar takes over the dashboard tour here.

Sources: docs/CLICKHOUSE-DASHBOARDS.md; web/analytics.html

## 10. Customer Journey in ClickHouse

Speaker: Anuar
Target: 120 seconds

Customer Journey asks which steps a session reaches in order. The query reads customer_activity for one run, applies FINAL and groups by session. windowFunnel then checks session start, product opening, cart addition and checkout within thirty minutes. Strictly increasing millisecond timestamps make the ordering rule explicit. A missing next step can mean the session is still in progress. We show observed abandonments separately. The chart on this slide is the five-session integration-test cohort, not production customer behaviour. Now we can open the real dashboard, change the customer filter and inspect its SQL statistics.

Operator: 0:00–0:30 explain the grain and source. 0:30–1:10 open Journey, change all/simulated/AI and apply. An empty AI cohort can be correct for a traffic-only run. 1:10–2:00 expand the fixed query and explain FINAL, windowFunnel, rows read and elapsed time. windowFunnel receives UInt64 Unix milliseconds in ClickHouse 25.8, so its window is 1,800,000. Test data: 5 observed starts, 3 reach product, 1 reaches cart and checkout. Tests also cover an excluded orphan session, wrong order, equal timestamps, expiry and retries. Charts run as separate reads during continued ingestion.

Sources: atlas/analytics.py; tests/test_analytics.py; docs/CLICKHOUSE-DASHBOARDS.md; https://clickhouse.com/docs/sql-reference/aggregate-functions/parametric-functions#windowfunnel

## 11. Historical datasets, analytical SQL

Speaker: Anuar
Target: 120 seconds

The historical explorers show several different analytical questions. OTTO groups ecommerce events over time. REES46 adds month filters, categories and brands. Glovo describes catalog supply by location. Ele.me groups recommendation samples, and Criteo shows observed released-sample group outcomes. These sources are separate populations. We can change a meaningful filter and inspect the SQL that ClickHouse executes. The figures on this slide are dated verified loads, not a promise about what the current host contains.

Operator: use about 20 seconds per source view and 20 seconds for one filter plus SQL. If a source is missing, say so and use dated evidence. A page never downloads a dataset automatically. Criteo's non-uniform privacy subsampling prevents recovery of original campaign incrementality. Glovo catalog size is supply, not demand or sales.

Sources: docs/RESULTS.md; docs/ELEME.md; docs/GLOVO.md; docs/PR7-PR8-REVIEW.md; docs/CLICKHOUSE-DASHBOARDS.md; https://huggingface.co/datasets/criteo/criteo-uplift#privacy

## 12. ClickHouse Performance

Speaker: Anuar
Target: 120 seconds

This dashboard makes ClickHouse itself visible. system.parts reports physical storage. We can inspect engines, partition keys, sorting keys and compression. system.query_log reports completed query work, grouped by query family and table. Finally, two fixed queries compare detail with a prepared aggregate. We check complete answer equality before interpreting their times. The Atlas comparison uses one date across all runs because the aggregate does not store a run dimension. A live timing is a local observation. Query cache is disabled, but system caches and concurrent ingestion still affect it.

Operator: 0:00–0:35 inspect engine and sorting-key metadata. 0:35–1:00 inspect query families and server work. 1:00–2:00 choose a loaded workload, compare fixed queries, show answer equality, rows read and bytes. If answers differ, explain the displayed mismatch and do not interpret a ratio. Stop producers on the host and wait for pending=0 before rehearsal if a stable comparison is needed. The screenshot is a disposable validation environment with tiny seeded datasets, not a large-source benchmark. Raw historical query text is not exposed.

Sources: atlas/analytics.py; docs/CLICKHOUSE-DASHBOARDS.md; https://clickhouse.com/docs/reference/system-tables/parts; https://clickhouse.com/docs/reference/system-tables/query_log

Handover: “Echenique will compare these live observations with our documented results, then run the operations demo.”
Image evidence: docs/capturas/clickhouse-performance-validation.png, explicitly labelled validation environment.

## 13. Prepared aggregates: a measured trade-off

Speaker: Echenique
Target: 60 seconds

This chart shows one measured result from our historical lab. We ran the same daily OTTO aggregation against the detail table and a prepared aggregate. The median of three local runs was 5.8908 seconds for detail and 0.2113 seconds for the aggregate. The results matched. That is about 27.9 times faster for this query on this machine. We disabled the SQL query cache, although operating-system cache and other conditions still matter. This compares two designs inside ClickHouse. We did not benchmark PostgreSQL. The separate Atlas test is a useful counterexample: its exact-ID aggregate took 0.703 seconds, compared with 0.498 seconds for detail. Exact states protect retry-safe counts, but add work. An aggregate needs measurement.

OTTO: 216,716,096 detail rows versus 87 aggregate groups. Background merges paused for the documented large-table benchmark. Atlas: 1,000,002 logical events and 16 result groups, three queries per alternative, no concurrent workload. These are different schemas and queries. A billion-row stress table contains derived copies, not additional real observations.

Sources: docs/RESULTS.md; docs/ATLAS-RESULTS.md

## 14. Live operations and Python CRUD

Speaker: Echenique
Target: 180 seconds

We now follow one fictional order. We match its order ID to its courier and inspect the age of the latest GPS sample. The map shows real streets, while positions and paths remain synthetic. The latest-state view uses argMax states so the dashboard can read the current position while the detail table keeps history. We finish with the Python CRUD script on a scratch table, showing that the program connects directly to ClickHouse.

Operator: 0:00–1:15 select a prepared order and courier, then follow it. Explain recorded GPS and current-state views. 1:15–2:40 run python3 scripts/crud_demo.py on the intended host. Preconfigure its connection variables before projection. Use delivery.demo_events, not the analytical source histories. 2:40–3:00 return to the deck. The public gateway is read-only. Anuar prepares the host, Echenique controls the projected view and Geremi keeps time. Switch after a 15-second stall. Recorded evidence supports explanation but cannot be presented as a live demonstration.

Sources: sql/atlas_operations.sql; scripts/crud_demo.py; docs/TRACKING-DEMO.md; docs/capturas/mapa-madrid-escritorio.jpg
Map attribution: OpenStreetMap contributors, https://www.openstreetmap.org/copyright

## 15. Reliability and measured limits

Speaker: Echenique
Target: 40 seconds

The outbox and stable IDs help with retries and orderly restarts. They do not provide another host. We run one ClickHouse node, with no demonstrated disk-loss recovery or automatic failover. Partitions organise data within tables. Replicas and shards would require a separate design. Our measured results also show a trade-off: the exact-ID Atlas aggregate protected logical counts but took longer in its recorded query test.



Sources: docs/ATLAS-RESULTS.md; docs/FUNDAMENTALS.md; docs/CLICKHOUSE-DASHBOARDS.md

## 16. What we learned

Speaker: Echenique
Target: 60 seconds

Our first lesson was that the meaning of a row comes before its count. A catalog entry, a click and a recommendation label answer different questions. Second, database design follows the queries. Sorting keys, latest-state views and aggregate states solve different problems, and a smaller table is not automatically faster. Third, a live pipeline needs clear contracts: stable IDs, validation, retries and visible provenance. Delivery Atlas gave us a way to connect these lessons to one explainable workflow. Before the final presentation, our remaining work is a timed group rehearsal, a fresh host check and an independent reproduction test. Thank you. We are ready for questions.

End the core presentation here. Slides B1–B8 are hidden during the normal show and are available for questions or recovery. Their existence does not add to the 20-minute core slot.

Sources: docs/RESULTS.md; docs/ATLAS-RESULTS.md; docs/ASSIGNMENT.md; docs/TEAM-INSTALL-TESTS.md

# Hidden support slides

## B1. What each dataset can support

Suggested respondent: Anuar
Use for questions. Hidden from the core slideshow.

Q: Why keep these sources? They serve different educational tasks: large scans, recommendations, catalog context and grouped advertising outcomes.
Q: Why not join them? We do not have trustworthy shared identities or populations.
Q: Is Criteo causal? The publisher describes a randomized experiment, but non-uniform subsampling for privacy prevents recovery of the original incrementality. We describe observed released-sample differences.
Q: Can you redistribute all files? Source terms differ. The repository contains loaders and source links, rather than automatically redistributing every dataset. Ele.me access requires a Tianchi account and reviewing its terms.

Sources: docs/RESULTS.md; docs/ELEME.md; docs/GLOVO.md; docs/PR7-PR8-REVIEW.md; https://huggingface.co/datasets/criteo/criteo-uplift#privacy

## B2. A retry after a lost response

Suggested respondent: Geremi
Use for questions. Hidden from the core slideshow.

Q: Is delivery exactly once? We use retries and stable identity to protect logical results. We do not claim one physical write across API, SQLite and several ClickHouse tables.
Q: Does 202 mean published? It means the event committed to the local outbox.
Q: Why not count rows? Resends can create physical copies. The exact-ID aggregate uses uniqExactState and uniqExactMerge.
Q: Will a merge fix an already summed materialized view? Incremental views process inserted blocks. A plain sum would count a replay again. Our exact-ID design handles this specific retry pattern at a memory cost.

Sources: atlas/store.py; sql/atlas.sql; docs/ATLAS-RESULTS.md; https://clickhouse.com/docs/concepts/features/materialized-views/incremental-materialized-view

## B3. Partitions, shards and replicas

Suggested respondent: Geremi
Use for questions. Hidden from the core slideshow.

Q: Does a partition add a server? No. It is an organisation unit inside a table.
Q: How would you scale? First measure the bottleneck. A larger single node, better batching or better queries may help before sharding. A proposed multi-node design needs a sharding key, replicas, coordination and query routing.
Q: What happens during a network split? Our demo has no replicas, so we have not tested that scenario. Replicated deployments need explicit quorum and read-freshness choices.
Q: Is a replica a backup? Replication and independently recoverable backups address different failure cases. Neither has been demonstrated here.

Sources: docs/FUNDAMENTALS.md; docs/ATLAS-RESULTS.md; https://clickhouse.com/docs/reference/engines/table-engines/mergetree-family/mergetree; https://clickhouse.com/docs/reference/engines/table-engines/mergetree-family/replication

## B4. Python and SQL CRUD

Suggested respondent: Echenique
Use for questions. Hidden from the core slideshow.

Run the actual Python script. It uses the standard-library HTTP client and Basic authentication to reach the host's ClickHouse endpoint. It creates a MergeTree scratch table if needed, inserts a unique event ID, reads it, changes the action and removes the event. mutations_sync = 2 waits for the demonstration's mutations. Preconfigure CLICKHOUSE_URL, CLICKHOUSE_USER and CLICKHOUSE_PASSWORD without projecting secret values. The defaults target the old lab on 127.0.0.1:8124, so check the intended host.
Q: Why append new order events instead of editing history? The analytical flow records changes as events. Incremental materialized views do not automatically undo previous aggregates after a source mutation.
Q: Does the script only change this table? When the historical large tables exist, it temporarily pauses their merges and restores them in finally. Rehearse its full behaviour on the selected host.

Sources: scripts/crud_demo.py; docs/DEMO.md; docs/ATLAS-INFRASTRUCTURE.md; https://clickhouse.com/docs/concepts/features/materialized-views/incremental-materialized-view

## B5. Benchmark conditions and trade-offs

Suggested respondent: Echenique
Use for questions. Hidden from the core slideshow.

OTTO: 216,716,096 detail rows and 87 aggregate groups. Same daily output, median of three local runs, SQL query cache disabled. Background merges paused for the documented large-table benchmark. Operating-system cache and concurrent conditions affect timings.
Atlas: 1,000,002 logical events, 16 groups, three queries per alternative, no concurrent load and empty queue. The query cache was disabled. System cache and warm-up were not controlled. Exact unique-ID states have memory and merging cost.
Q: Does fewer rows read mean faster? Our Atlas result shows why the answer needs measurement.
Q: Where is PostgreSQL? We made a qualitative workload comparison, not a measured performance claim.
Q: Did you have a billion real events? The billion-row stress table contains labelled copies derived from OTTO.

Sources: docs/RESULTS.md; docs/ATLAS-RESULTS.md

## B6. AI decisions and metric scope

Suggested respondent: Anuar
Use for questions. Hidden from the core slideshow.

Q: Are all customers AI? No. Traffic and policy modes use rules. Hybrid mode combines a configured small AI subset with faster simulated traffic.
Q: Is the AI realistic? We demonstrate a constrained integration. We have not validated human realism, economic predictions or a gain over policies.
Q: Why can the AI list and metrics differ? A configured customer enters the AI metric after its first recorded model decision. A waiting customer may already appear in the list.
Q: Is an empty AI view an error? It may be a traffic-only run, a model not yet producing decisions, or a host version without per-kind metrics. Check the current run and server.
Q: Is AI making the GPS path? No. The simulator generates delivery movement after accepted actions.

Sources: docs/AI-CUSTOMERS.md; docs/PR7-PR8-REVIEW.md; atlas/customer_runtime.py; web/atlas-dashboard.js

## B7. Demo recovery paths

Suggested respondent: Echenique
Use for questions. Hidden from the core slideshow.

Pre-open the local miniapp, the dashboard and a host terminal. Prepare one linked order ID and a known courier. Run CRUD once during rehearsal. Verify the intended ClickHouse connection and keep credentials off the projected screen.
Echenique controls and narrates the projected demo. Anuar monitors the host and prepares the miniapp. Geremi keeps time.
If one step stalls for 15 seconds, use the prepared order or local dashboard. If no live path works, use dated evidence and say explicitly that it is recorded. Recorded material supports explanation but cannot be presented as meeting the live-demo requirement.
Do not download datasets, launch an unprepared model or change the infrastructure during the talk. The group still needs a complete timed rehearsal on the actual presentation setup.

Sources: docs/PRESENTATION.md; docs/DEMO.md; docs/TRACKING-DEMO.md; docs/TEAM-INSTALL-TESTS.md

## B8. Workload fit and production extensions

Suggested respondent: Geremi
Use for questions. Hidden from the core slideshow.

Q: Why not use only PostgreSQL? Our analysis compares workload needs qualitatively. We did not measure a PostgreSQL baseline or prove ClickHouse is faster for every task. A production commerce system may separate transactional state from analytical history.
Q: Why SQLite? It gives this single-host demo a durable local outbox with a simple startup. It is not an independent replica or a multi-consumer broker.
Q: What would you change first? Rehearse and measure. Then address host reliability, backups, access control, retention and memory cost before claiming production readiness.
Q: What about CAP? Discuss the chosen topology, operations, failure and settings. The current one-node demo does not measure behaviour under a replica network partition.

Sources: docs/FUNDAMENTALS.md; docs/APPLIED-THEORY.md; docs/ATLAS-INFRASTRUCTURE.md; docs/ATLAS-RESULTS.md
