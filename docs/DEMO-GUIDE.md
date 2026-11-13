# Live demo guide

How to run the live part of the final presentation, step by step, and which ClickHouse idea each step shows. It follows slides 9–14 of [PRESENTATION.md](PRESENTATION.md); the spoken text is in [CLICKHOUSE-PRESENTER-NOTES-EN.md](CLICKHOUSE-PRESENTER-NOTES-EN.md).

You need a working installation first: [ATLAS-INSTALL.md](ATLAS-INSTALL.md). Everything below runs on one computer, the **host**. The public read-only website can show the dashboards, but the controls, the mini-app checkout and the CRUD script only work on the host.

## What the demo shows

| Step | Where | ClickHouse idea |
|---|---|---|
| 1. Customer Journey | Analytics portal | `FINAL` to collapse retried rows, `windowFunnel` for ordered steps per session |
| 2. Historical explorers | Analytics portal | Columnar reads over millions of rows; only the needed columns are read |
| 3. ClickHouse Performance | Analytics portal | `system.parts` (storage, compression, sort keys), `system.query_log` (work per query), detail vs prepared aggregate |
| 4. Live map | Dashboard | Append-only history plus a materialized view that keeps the latest state (`argMax`) |
| 5. Follow one order | Mini-app and dashboard | Ingestion path: API, durable queue, batch INSERT, then reads of the new rows |
| 6. Python CRUD | Terminal | INSERT and SELECT are cheap; UPDATE and DELETE are mutations that rewrite parts |
| 7. SQL by hand (optional) | ClickHouse `/play` | The same ideas as SQL you can type and time |

The order follows the slides: Anuar presents steps 1–3 (slides 10–12) and Echenique steps 4–6 (slide 14).

## Before the presentation

**One day before**

1. Update the host and rebuild, so the API has the analytics portal:

   ```bash
   git pull
   docker compose -f compose.yaml --profile atlas --profile ai up -d --build --wait
   ```

   Check that http://127.0.0.1:8001/analytics.html opens. If the shared website is used, rebuild its gateway as well ([SHARING-VERCEL.md](SHARING-VERCEL.md)).
2. Check which public datasets the host has. In http://127.0.0.1:8124/play:

   ```sql
   SELECT name, total_rows FROM system.tables
   WHERE database = 'delivery' AND total_rows > 0
   ORDER BY total_rows DESC
   ```

   An explorer whose table is missing shows a message instead of data. Present only the loaded ones, or load them now ([ATLAS-INSTALL.md, step 6](ATLAS-INSTALL.md#6-optional-public-datasets)). Never download during the talk.
3. Run the whole demo once, including the CRUD script, and time it.

**30 minutes before**

1. Open Docker Desktop and wait for the engine. Then `docker compose -f compose.yaml --profile atlas --profile ai up -d --wait`.
2. Start a run from the dashboard: *Decisions* **AI + mass traffic**, **200 customers**, **80 couriers**, **Start customers and delivery**. Start it 10–15 minutes before speaking, so there are delivered orders and a Journey cohort. The AI stops after 120 model calls (a few minutes); if you want to show fresh AI reasons, start the run closer to the talk.
3. Open these tabs, in this order:
   - http://127.0.0.1:8001/analytics.html?panel=journey
   - http://127.0.0.1:8001/?view=simulated#tracking
   - http://127.0.0.1:8001/delivery.html
   - http://127.0.0.1:8124/play, signed in as `demo` (do not show the password on screen)
   - A terminal in the repository folder, with the command `python3 scripts/crud_demo.py` typed but not run.
4. Note one order ID and its courier from the dashboard, as a backup if the live order is slow.
5. Keep the laptop plugged in, notifications off, and sleep disabled.

## During the demo

### 1. Customer Journey (slide 10)

Open `analytics.html?panel=journey`.

1. Change **Customers** between all, simulated and AI and click **Apply filters**. An empty AI cohort is correct for a traffic-only run.
2. Open **The ClickHouse queries behind this view**.
3. Explain the query: it reads `customer_activity` for one run with `FINAL` (so a retried event counts once) and uses `windowFunnel` to check, per session, *session start → open product → add to cart → checkout* within 30 minutes. Under the query, ClickHouse reports elapsed time, rows read and bytes read.

### 2. Historical explorers (slide 11)

Use the links on the left: **OTTO Events**, **Marketplace Trends** (REES46), **Catalog Explorer** (Glovo), **Recommendation Samples** (Ele.me) and **Advertising Groups** (Criteo). About 20 seconds each, only for the datasets the host has.

- Change one filter, click **Apply filters**, and show the SQL and the rows read.
- Each source keeps its own meaning: a catalog row is a product offered, not a sale; Criteo groups are observed differences in a privacy-protected sample, not a campaign effect.

### 3. ClickHouse Performance (slide 12)

Open **ClickHouse Performance**.

1. Table inventory: engine, partition key, sort key, rows, compressed and uncompressed size. Explain that each column is stored and compressed separately.
2. Query history: query families from `system.query_log`, with count, duration, rows read and memory.
3. Choose a workload and click **Compare fixed queries**: the same question on the detail table and on the prepared aggregate. The page first checks that both answers are equal; only then it shows the times. If they differ (data is still arriving), it says so and shows no ratio.

For a stable comparison, stop the simulation and wait until the queue is empty (`pending: 0` at http://127.0.0.1:8001/api/status), then compare.

### 4. Live map (slide 14)

Open the dashboard at `/?view=simulated#tracking`.

- Each dot is a courier of the simulation on real Madrid streets. The page asks the API every two seconds.
- Click a courier: the **Selected courier** panel shows the order it carries and its **recorded GPS path** (straight lines between GPS samples, not street routing).
- Point at the numbers at the top: active, delivered and late orders, computed by ClickHouse at that moment.

**What to say about ClickHouse:** `courier_positions` keeps every GPS point and only receives inserts. A materialized view stores the latest point per courier as an `argMax` state, so the map reads one row per courier (`courier_latest`) instead of scanning the history. In a measured comparison on the demo computer (6 November, a separate ClickHouse limited to 2 CPUs), reading the latest position of 150 couriers from 4.37 million GPS rows took about 560 ms of server time; from `courier_latest` it took about 6 ms, with the same answer.

### 5. Follow one order from the mini-app (slide 14)

1. In http://127.0.0.1:8001/delivery.html, open a restaurant, click a dish, **Add to cart**, then **View order** and **Place order**. A simulation must be running. The dark panel on the right lists every event the app sent, each answered with `202` (queued).
2. The tracking screen reads the order from ClickHouse every two seconds: *Order received → In the kitchen → Picked up by the courier → On the way → Delivered*. It can wait at "looking for a courier" while every courier is busy.
3. Click **See the order on the operations dashboard** to find the same order and its courier on the map.

**What to say:** the click went to the API, which stored it in a durable queue (SQLite) and answered at once. A publisher inserts queued events into ClickHouse in batches, which is how ClickHouse prefers to receive data. The order then appears in `app_events`, `customer_orders` and `order_events`, linked by the same `order_id`. A retry with the same IDs does not create a second order.

If the order takes more than 15 seconds, switch to the order you noted before the talk.

### 6. Python CRUD (slide 14)

In the terminal:

```bash
python3 scripts/crud_demo.py
```

On Windows, type `python` instead of `python3`. It prints three lines: `INSERT` and `UPDATE` with the row read back after each step, and `DELETE: rows left = 0`. It works on a scratch table, `delivery.demo_events`, never on the project's histories.

**What to say:** INSERT and SELECT are what ClickHouse is built for. `ALTER TABLE … UPDATE` and `… DELETE` are **mutations**: ClickHouse rewrites the affected data parts in the background (here we wait for them with `mutations_sync = 2`). That is why Atlas never updates an order: every status change is a new row, and the latest state comes from the materialized view.

The script reads `CLICKHOUSE_URL`, `CLICKHOUSE_USER` and `CLICKHOUSE_PASSWORD`; the defaults point to this installation. Set them before projecting if the host is different, and keep their values off the screen.

### 7. SQL by hand (optional, for questions)

In http://127.0.0.1:8124/play. After each query, `/play` shows the elapsed time and the rows read.

The same question two ways, latest position of each courier of the last run:

```sql
-- From the full GPS history
SELECT courier_id, argMax((latitude, longitude, event_time), (event_time, event_id)) AS latest
FROM delivery_atlas.courier_positions
WHERE simulation_run_id = (SELECT simulation_run_id FROM delivery_atlas.courier_positions ORDER BY event_time DESC LIMIT 1)
GROUP BY courier_id
ORDER BY courier_id;

-- From the state prepared by the materialized view
SELECT courier_id, (latitude, longitude, event_time) AS latest
FROM delivery_atlas.courier_latest
WHERE simulation_run_id = (SELECT simulation_run_id FROM delivery_atlas.courier_positions ORDER BY event_time DESC LIMIT 1)
ORDER BY courier_id;
```

Storage and compression per table:

```sql
SELECT table, sum(rows) AS total_rows,
       formatReadableSize(sum(data_compressed_bytes)) AS compressed,
       formatReadableSize(sum(data_uncompressed_bytes)) AS uncompressed,
       round(sum(data_uncompressed_bytes) / sum(data_compressed_bytes), 1) AS ratio
FROM system.parts
WHERE active AND database = 'delivery_atlas'
GROUP BY table
ORDER BY total_rows DESC;
```

Engines and sort keys:

```sql
SELECT name, engine, partition_key, sorting_key
FROM system.tables
WHERE database = 'delivery_atlas' AND engine NOT IN ('View', 'MaterializedView')
ORDER BY name;
```

More queries: `sql/atlas_consultas.sql` and `sql/atlas_tracking_consultas.sql`.

## If something fails

| Symptom | What to do |
|---|---|
| A page does not load | `docker compose -f compose.yaml --profile atlas ps`; if a service is not healthy, `docker compose -f compose.yaml --profile atlas logs --tail 40 atlas` |
| Map empty or frozen | The simulation stopped. Check the error on the dashboard and start a new run |
| `pending` keeps growing at `/api/status` | ClickHouse is behind; the data on screen is older. Wait or reduce the run size; nothing is lost |
| An explorer says the dataset is missing | That table is not loaded on this host. Say so and move on |
| Any step stalls for 15 seconds | Use the prepared order or the screenshots in `presentaciones/checkpoint-2026-10-28/`, and say clearly that they are recorded |

## After the demo

Click **Stop** in the dashboard. The data stays in ClickHouse. To shut everything down: `docker compose -f compose.yaml --profile atlas --profile ai stop` (without `down -v`).
