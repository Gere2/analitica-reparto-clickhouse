# Delivery Atlas: team work plan

> Historical record: dates, results, speaker allocations and pending statements below describe their original stage. For the current implemented project, 14-slide route and delivery status use [FINAL-DELIVERY.md](FINAL-DELIVERY.md), [DATABASE-STRUCTURE.md](DATABASE-STRUCTURE.md) and [DEMO-GUIDE.md](DEMO-GUIDE.md).

Date: 7 October 2026. Team: Jere, Anuar and Echenique.

**Later change of scope:** Jere decided to continue with Rayo for now and split the work when the teammates join. The split below is a proposal for that moment, not work we are waiting on. The operations dashboard and synthetic Madrid tracking are already being implemented. Current status: [DATA-AND-TRACKING.md](DATA-AND-TRACKING.md). The earlier PDF guide describes the first infrastructure delivery.

## What we are building

A fictional food-delivery platform to demonstrate how ClickHouse receives and analyses many events. An action in the application produces a record; the Python API validates it, stores it and makes it queryable from a dashboard. We do not operate real deliveries or payments.

There is already a lab with OTTO, REES46, Ele.me and the Glovo catalog, with its dashboards and measurements. Those sources keep their tables and meanings. Our own application will have its `delivery_atlas` database, with manual and simulated actions labelled as such.

## Initial agreed split

| Person | Main responsibility | Verifiable deliverable |
|---|---|---|
| **Jere, with Rayo** | ClickHouse, SQL, ingestion API, generator and retry tests | A request reaches ClickHouse, repeating it does not increase the logical count, and the environment starts with Compose |
| **Anuar** | Mini-app and action logging | A path through city, restaurant, product, cart and simulated order emits the right events |
| **Echenique** | Dashboard, independent check and demo guide | The dashboard queries the API, filters by source/city/date, and another machine reproduces the small path |

## Jere: database and ingestion

1. Implement `sql/atlas.sql`: events, aggregates and read queries.
2. Implement `atlas/`: contract, durable receipt log, batch publishing and endpoints.
3. Package the API in `Dockerfile.atlas` and the `atlas` profile of `compose.yaml`.
4. Create `scripts/atlas.py` to generate a reproducible load and `scripts/check_atlas.py` to verify the full path.
5. Save our own measurements of the new database. The old benchmarks do not describe its performance.

**Database implemented and verified on 7 October.** Events are validated, incorrect data is rejected, the same ID with different content returns a conflict and a retry keeps the logical count. One million synthetic events were loaded and verified, and queue recovery after restarting services was tested. [Results and conditions](ATLAS-RESULTS.md).

Jere's next tasks: support the two interfaces, measure delay and disk usage, improve the generator with abandonment, and optimize the exact aggregate (it does not yet beat the detail table in the local measurement). Then document backup/restore and consider a second node as an extension.

## Anuar: mini-app

Work on `web/delivery.html`, `web/delivery.js` and `web/delivery.css` (new files). Coordinate with Jere on serving those files from the API.

1. Start with a small, stable fictional catalog, with no login or payments.
2. Allow selecting a city, searching, opening a restaurant and a product, adding to the cart and confirming a simulated order.
3. Create a `session_id` when the session starts and an `event_id` before each send. A retry reuses the same complete event.
4. Send to `POST /api/events`. Use `source=delivery-miniapp` and `source_kind=demo_live`. These are new interactions with a fictional business.
5. Show a send failure without pretending the event was saved. Do not record impressions until it is defined when a product is visible.

Done when: Echenique goes through a path and can find his actions and his session in the database, with no double counting on retries.

## Echenique: dashboard and reproduction

Work on `web/atlas-dashboard.html`, `web/atlas-dashboard.js`, `web/atlas-dashboard.css`, `docs/DEMO-ATLAS.md` and `docs/TEAM-INSTALL-TESTS.md` (new files).

1. Query `GET /api/summary`, `GET /api/recent` and `GET /api/status`.
2. Show events by day, city and action; distinguish `synthetic` from `demo_live`.
3. Refresh every 2 seconds, show when the last response was received and display errors.
4. Show the pending queue and published events. Do not call a division of orders by clicks "conversion".
5. Follow the reduced installation on his computer, run the tests and record system, version, commands and results.
6. Prepare a demo of ingestion, querying and comparison between events and the aggregate. Keep CRUD on a scratch table.

Done when: the dashboard shows ClickHouse data, an action appears after publishing, and the guide makes it possible to repeat it without the large datasets.

## Integration order

1. Jere fixes the contract and delivers a sample, the endpoints and the reduced path.
2. Anuar and Echenique work on their files with the API already available.
3. Echenique checks Anuar's path and Jere's retry.
4. Jere runs a measured load; the three of us review its conditions and rehearse.

Use the branches `codex/atlas-base`, `codex/atlas-miniapp` and `codex/atlas-dashboard`. These are suggested names; they have not been created and no messages have been sent to the team. Review changes together before merging. Each person keeps to their own files to avoid overwriting someone else's work.

## Common agreement

- Historical, simulated and manual data are identified by their provenance.
- A catalog contains no clicks. Ele.me samples are not a complete session.
- The event identifier stays the same across retries.
- A node means one ClickHouse instance. A volume keeps data, but it does not provide a replica or a backup.
- Do not download hundreds of millions of rows on the other computers to get started: first the reduced path.
- Figures and guarantees are presented only after they have been verified.
