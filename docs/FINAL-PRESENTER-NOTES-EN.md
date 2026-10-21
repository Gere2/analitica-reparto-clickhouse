# Final presenter notes (English)

Core talk: **18 min 10 sec**, including the **3 min 30 sec live demo**. Leave **1 min 50 sec** for transitions and small delays within the 20-minute slot; questions follow for about 10 minutes.

## 1. Delivery Atlas · 30 seconds

Introduce the team and the fictional platform. Explain that downloaded histories, rule-based events and AI decisions have different roles.

## 2. Why ClickHouse fits our workload · 55 seconds

ClickHouse was assigned by the professor, confirmed on 19 October. Our choice was the project and workload. We needed a workload where reading many events matters, rather than only choosing one courier from a short list. App analytics gives us large histories, continuous batch inserts and repeated aggregations. The operational simulation makes those events easy to explain. We do not claim that ClickHouse replaces every transactional database. Sources: docs/ASSIGNMENT.md; https://clickhouse.com/docs/intro

Key message: **ClickHouse was assigned to our group. We chose a use case that shows its strengths.**

## 3. What is ClickHouse? · 50 seconds

OLAP means online analytical processing. For example, counting purchases per day needs the event date and event type, rather than every field in each record. Column storage also helps compress similar values. ClickHouse uses SQL; describing it simply as a database that measures clicks would be inaccurate. Our project runs one server instance, not a distributed cluster. Sources: https://clickhouse.com/docs/intro; docker-compose.yml; docs/FUNDAMENTALS.md

Key message: **The application records a click. ClickHouse stores and analyses the event.**

## 4. How our ClickHouse tables are structured · 75 seconds

Start with the hierarchy: one ClickHouse server, databases, tables, partitions and sorted data parts containing columns. Our main event tables use ReplacingMergeTree(ingested_at). The sorting key is chosen around how the events are queried. ReplacingMergeTree replaces versions with the same sorting key during merges; background replacement is eventual. It is not an immediate uniqueness constraint. Our API preserves event identity and rejects conflicting retries. Aggregate tables use AggregatingMergeTree; incremental materialized views process inserted blocks. Sources: sql/atlas.sql; sql/atlas_operations.sql; https://clickhouse.com/docs/reference/engines/table-engines/mergetree-family/mergetree; https://clickhouse.com/docs/concepts/features/materialized-views/incremental-materialized-view

Key message: **A partition is not a shard. ORDER BY does not enforce a unique primary key.**

## 5. The project ideas we explored · 70 seconds

The project chat records the actual sequence. We first asked for ideas with millions of rows. Suggestions included NYC taxis and 311, GitHub and Wikipedia, then MovieLens, Lichess, cybersecurity, ListenBrainz and GDELT. We preferred Spain and a recognizable Uber/Cabify-style application. Ten mobility proposals included fleet repositioning, congestion, event pickups, courier assignment, charging, bicycle connections, transport coverage, accidents, prices and Chicago ride data. We developed courier assignment before redirecting to events. Sources: project chat ‘Proponer proyectos con millones de d’, turns 01a0e886-2f1f-70e2-a172-6a86f1d7c82c through 01a0e895-0d19-74e3-a39c-a99bde2d853a; documented in docs/PROJECT-DECISIONS.md.

Key message: **These were proposals we discussed. We did not implement or benchmark every alternative.**

## 6. Choosing a project: the hard parts · 65 seconds

Avoid claiming that no dataset exists anywhere; explain what our search found. Glovo matched the sector and Spain but lacked clicks and orders. Meituan provided food delivery behaviour in Beijing, but only click sequences linked to purchases, so it could not support a whole-app abandonment rate. OTTO provided massive full event sequences, but in general ecommerce. Ele.me matched food recommendations, but download access required a Tianchi account and the full JSON history query exceeded local memory. The datasets share no trustworthy joining identifiers. These constraints led us to keep each source separate and build a fictional platform with our own event contract. Sources: project chat turns 01a108a2-2eb3-7060-b192-0948fde201e9, 01a108b8-d6c5-7291-9de2-105bd18d784a, 01a10949-6d51-7c53-a858-81fc439d103f, 01a10c45-7bfb-7b22-9679-fee396cd2d68; docs/ELEME.md.

Key message: **Many rows are useful only when we can explain what one row means.**

## 7. Why we built Delivery Atlas · 45 seconds

The professor suggested inventing the platform and building infrastructure that could accept future real data. That is the turning point documented in the chat. Public datasets remain evidence for large-scale analytics, while our own simulated platform provides a coherent live story. Future real integrations would still require adapters, validation and compatible semantics. We are not connected to a private Uber Eats or Glovo operational feed. Sources: project chat turn 01a10c50-d553-76b2-96f4-9e97f1be25d6; docs/FICTIONAL-PLATFORM.md; docs/ATLAS-INFRASTRUCTURE.md.

Key message: **A platform we control lets us demonstrate ingestion and explain every event.**

## 8. 1 · Downloaded data: scale and context · 65 seconds

These are the loaded counts documented in the historical lab, not a promise that the live Windows server contains every large dataset. OTTO and REES46 together contain 628,425,832 events from different populations. Ele.me is the first complete D1_0 ZIP we loaded, not the full 146 million samples advertised by the publisher. Glovo contains catalog entries, not clicks, GPS or sales. Our billion-row stress test is derived from OTTO and is not additional real observations. Sources: docs/RESULTS.md; docs/ELEME.md; docs/GLOVO.md; docs/TEAM-STATUS.md. Original sources: https://github.com/otto-de/recsys-dataset ; https://data.rees46.com/ ; https://tianchi.aliyun.com/dataset/131047 ; https://github.com/Glovo/foodi-ml-dataset

Key message: **Separate populations and meanings. We do not join them into one customer journey.**

## 9. 2 · Simulated data: a repeatable workload · 45 seconds

We control budgets, product prices, allowed actions and the simulation seed. Fictional GPS samples connect the story visually, but they are not real courier traces or street routing. The simulation can create more activity than a local language model can cheaply generate. One million events were verified in the documented Atlas test; this is a separate test from the current live run. Manual actions from our miniapp use demo_live provenance; they are human actions in a fictional commerce environment. Sources: atlas/commerce.py; atlas/customer_agent.py; docs/ATLAS-RESULTS.md; docs/DATA-AND-TRACKING.md.

Key message: **Rule-based traffic is labelled as simulation. It is not an AI model.**

## 10. 3 · Agents create customer decisions · 60 seconds

The model receives structured context and a bounded list of choices. Python enforces the contract; the model does not receive direct SQL access. Hybrid configuration defaults to 3 AI customers and 197 rule-based customers, with 80 couriers. These are supported defaults, not a claim about every deployment. Ollama is optional and is not enabled on Anuar’s current traffic-only server. There are call limits, validation and visible errors. Sources: docs/AI-CUSTOMERS.md; atlas/customer_agent.py; atlas/customer_runtime.py; web/atlas-dashboard.html.

Key message: **AI adds decisions. The simulator adds volume. Both generate explicitly synthetic data.**

## 11. How the project connects · 65 seconds

First explain the ingestion direction: producers call the Python API, the API validates and commits to a persistent SQLite outbox, then a publisher inserts batches into ClickHouse. The browser reads through the API. For the shared demo, Vercel proxies an allowlist of GET routes through a temporary Cloudflare gateway to the host server. The gateway token stays server-side. Public viewers cannot start the simulator or submit orders through that gateway. HTTP 202 means accepted into the queue, not already visible in ClickHouse. SQLite is an outbox, not a ClickHouse replica. Sources: docs/ATLAS-INFRASTRUCTURE.md; docs/SHARING-VERCEL.md; atlas/store.py; api/proxy.js.

Key message: **Browser → read-only Vercel proxy → gateway → Python API → ClickHouse views.**

## 12. One checkout, linked across the database · 65 seconds

Trace a single confirmed purchase. The customer action and browsing event describe what happened. customer_orders provides the explicit relationship from checkout to order. order_events is append-oriented status history, while courier_positions is append-oriented GPS history. Latest-state aggregates let the dashboard show one current state while detail tables retain history. event_id supports retry recognition; order_id and simulation_run_id keep the live story linked. The model stores money in integer minor units and timestamps in UTC. Sources: sql/atlas.sql; sql/atlas_agents.sql; sql/atlas_operations.sql; atlas/clickhouse.py.

Key message: **delivery_atlas holds our platform. delivery keeps the historical lab separate.**

## 13. What our measurements actually show · 75 seconds

The chart shows the median of three local runs of the same daily OTTO aggregation, with SQL query cache disabled: 5.8908 seconds reading the 216,716,096-row detail table, versus 0.2113 seconds querying 87 aggregate groups. Results were identical. It is not a benchmark against PostgreSQL. The separate Atlas exact-ID aggregate did not improve speed in its measured test: 0.703 seconds versus 0.498 seconds for detail. This is why we measure rather than assume. The billion-row OTTO stress workload contains derived copies and cannot be presented as a billion independent observations. Sources: docs/RESULTS.md; docs/ATLAS-RESULTS.md. Hardware, query and run conditions are documented there.

Key message: **OTTO: 27.9× faster locally with the prepared aggregate. Same engine, same result.**

## 14. Reliability and scaling: our limits · 55 seconds

Accepted events are committed to the outbox before the API confirms them. A restart recovery was tested, but that does not imply surviving a lost disk or machine. ClickHouse visibility follows publisher progress; background replacement can be eventual, and logical counts use stable IDs. Scaling to multiple shards or replicas is explained, not implemented or benchmarked. A Distributed table can route queries to shards, and ReplicatedMergeTree uses Keeper/ZooKeeper coordination; cluster consistency settings would need explicit design. Sources: docs/ATLAS-RESULTS.md; docs/FUNDAMENTALS.md; https://clickhouse.com/docs/reference/engines/table-engines/mergetree-family/replication

Key message: **Monthly partitions, a Docker volume and a persistent queue do not create a replicated cluster.**

## 15. Live demo · follow one order · 210 seconds

Rehearse before class. 0:00–1:00: submit one fictional miniapp order, or use an already generated checkout if the flow is slow; display its order ID. 1:00–2:00: select that delivery, explain pickup/dropoff, recorded path and event age. Real street tiles do not make the simulated GPS a real street route. 2:00–3:10: run python3 scripts/crud_demo.py and show insert, read, update and delete in the scratch table delivery.demo_events. 3:10–3:30: show a prepared analytical query and return to the deck. Check the exact CRUD command in docs/DEMO.md before rehearsal. If the host/tunnel or tiles are unavailable, use the saved map screenshot and documented query outputs; label them as recorded evidence. Sources: docs/DEMO.md; scripts/crud_demo.py; docs/TEAM-INSTALL-TESTS.md.

Key message: **Public link: read-only. Controls, SQL and CRUD run on the host computer.**

## 16. What we learned · 60 seconds

The strongest lesson was to choose a coherent workload rather than chase row counts. We learned to separate historical evidence from synthetic operations, and rule-based traffic from actual model decisions. We also learned that an aggregate is not automatically faster, persistence is not high availability, and a polling interval is not an end-to-end latency guarantee. The final rehearsal should cover the CRUD script, the tunnel, a reproducible linked purchase and an offline evidence fallback. Invite questions about source semantics, event identity, MergeTree, replication and what we would change in production. Sources: docs/RESULTS.md; docs/ATLAS-RESULTS.md; docs/TEAM-INSTALL-TESTS.md.

Key message: **Our next steps: rehearse the full demo, test on both hosts and plan durable hosting.**
