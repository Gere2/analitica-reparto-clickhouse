# Rehearsal and live demo guide

Use the **14-slide web presentation dated 11 November**, [Delivery-Atlas.html](../presentaciones/final-2026-11-11/Delivery-Atlas.html), and its [English script](../presentaciones/final-2026-11-11/SCRIPT-EN.md). [PRESENTATION.md](PRESENTATION.md) has the exact four-speaker allocation and timings. The old 16-slide outline is archived; its slides 10–14 do not describe this version.

Install first with [ATLAS-INSTALL.md](ATLAS-INSTALL.md). Anuar's computer is the **host**: ClickHouse, API, queue, simulation and authenticated gateway run there. Vercel hosts the read-only frontend and GET proxy. Rebuilding Vercel cannot add routes to an old API or gateway.

## Which slide uses which screen

| Slide | Speaker | Action | ClickHouse point |
|---:|---|---|---|
| 1–3 | Echenique | Slides | Workload, column storage and analytical SQL |
| 4 | Juanro | Slides | Read selected columns, sorted parts and compression |
| 5–6 | Anuar | Slides; use diagram focus if helpful | Queue → batch inserts → history and prepared states; separate data origins |
| **7** | **Geremi** | Local dashboard and Madrid map | Latest courier state computed from inserted GPS history |
| **8** | **Geremi** | AI agents, then downloaded Criteo/Glovo views | Validated AI actions; timed analytical queries on real public data |
| 9 | Juanro | Slides | Retained checkpoint status and lessons |
| 10 | Echenique | Slides | Retained checkpoint closing; continue to the appendix |
| 11 | Anuar | Experiment setup slide | Frozen 4,371,300 GPS rows, 150 couriers, 2 CPU / 2 GiB lab |
| 12 | Juanro | Received p95 plot | Same answers/load: history crosses the target at 2 readers; prepared state passes |
| 13 | Anuar | Server work table | Rows read, server time and query memory; view-maintenance cost remains separate |
| 14 | Echenique | Planned comparison slide | Common corpus and resource budget; no PostgreSQL/DuckDB timing claimed |

The prepared slides and notes stay in English. Add Customer Journey/Performance and the scratch-table CRUD in the remaining presentation time, without replacing the rehearsed parts or renumbering slides. The map already belongs to the core script.

**20-minute slot:** the prepared core totals 14:35. Budget about 2 minutes for Journey/Performance (Anuar, after slide 8), 1 minute for the required CRUD demonstration (Echenique, after slide 14), and 2:25 for transitions and delays. Time this complete route together. An extra mini-app order or additional SQL belongs to questions if time is short.

## One day before: update the host without losing its runs

Use the **existing checkout and Compose project serving the demo**. Another clone/project can select new empty volumes. Do not remove volumes or recreate the manually started second API with a different queue path.

1. Pause every watchdog before stopping runs. In Git Bash, from that checkout:

   ```bash
   mkdir -p data/runs
   touch data/runs/WATCHDOG-PAUSE
   ```

   Stop the watchdog process too if you are updating its script. A manual pause stops automation; it does not stop an already running simulation.
2. Stop each simulation from its own dashboard: ports **8001 and 18001** if both are active. Keep Docker, ClickHouse and the publisher alive. Record each `run_id` from `/api/simulation`, and wait for **pending: 0 on both `/api/status` endpoints**. If a queue fails to drain, investigate; do not restart/rebuild yet.
3. Export each stopped run with `python3 scripts/export_run.py RUN_UUID`. Use `python` on Windows. Each completed archive is verified for gzip CRC, CSV record count, run identity and source counts; new archives also contain SHA-256. Failed staging folders remain separate and do not count as saved runs. Never treat a folder name as evidence of success.
4. Check local changes and update main:

   ```bash
   git status --short
   git fetch origin main
   git switch main
   git merge --ff-only origin/main
   git rev-parse HEAD
   ```

   If the checkout has local changes or cannot fast-forward, preserve them and resolve the issue. Do not use `reset --hard` or delete data to make the command work.
5. Rebuild the existing Atlas stack, preserving its named volumes:

   ```bash
   docker compose -f compose.yaml --profile atlas --profile ai up -d --build --wait
   ```

   This does not update a manually created second API container. Leave it stopped during rehearsal; update its image and existing queue-volume mapping separately before resuming long-run generation.
6. Rebuild the authenticated gateway if sharing is used:

   ```bash
   docker compose -f compose.yaml -f compose.share.yaml --profile atlas up -d --build --no-deps share-gateway
   ```

   Wait for its health check. Preserve the existing token files; never print or email their values. If the Quick Tunnel is running, rebuilding the gateway alone need not replace its address. If the tunnel was stopped/recreated, start it, take its **current** HTTPS address from its logs and follow [SHARING-VERCEL.md](SHARING-VERCEL.md) to validate and publish that origin. A Vercel deployment being READY alone does not prove the host connection works.
7. Check all three pages on the host: `/`, `/analytics.html`, `/delivery.html`. Check `/api/status`, `/api/journey`, `/api/performance`, and the read-only shared equivalents. A 404 means old API/gateway code; a 503 on the public site can mean the tunnel or host is unavailable. The public proxy is deliberately read-only.
8. Confirm Criteo and Glovo are loaded. OTTO, REES46 and Ele.me are not required on Anuar's host. Missing datasets must remain labelled missing; do not download large files during the talk.
9. Rehearse all fourteen slides with a clock, on the host and actual projector/browser if available. Keep the original recorded captures as fallback and label them as recorded.

The `WATCHDOG-PAUSE` flag stays present during rehearsal and benchmarks. A `.reserve-pending` marker means the reserve-triggered stop/export is incomplete and will be retried; keep Docker and the APIs available. Only clear maintenance flags after checking stopped runs, archive integrity, free disk and which generators should resume. A stale `.export-lock` is never removed automatically: confirm no exporter is running before removing that lock directory alone. Failed `.partial-*` directories are excluded from run reports.

## 30 minutes before

1. Start Docker and the updated Atlas stack. Keep long-run producers and the watchdog paused.
2. For the prepared 7–8 demonstration, start a fresh **hybrid run with 100 customers and 50 couriers**, with a 2-second tick if using the API. That matches the prepared narration. The old figures on slide 2 remain a dated checkpoint measurement; they are not today's live counters. If using another fleet size, state the actual value rather than claiming 50.
3. Start near the rehearsal: the 3 AI customers have a 120-call budget and stop making model decisions after that budget. Traffic continues. Verify Ollama is available before speaking; distinguish model decisions from rule-generated actions.
4. Open these tabs:
   - `http://127.0.0.1:8001/?view=simulated#tracking`
   - `http://127.0.0.1:8001/analytics.html?panel=journey` (optional questions)
   - `http://127.0.0.1:8001/delivery.html` (optional order)
   - `http://127.0.0.1:8124/play` (local SQL only)
   - the offline 14-slide HTML presentation.
5. Choose a courier/order that is already published in ClickHouse. Keep the recorded map/AI/dataset images ready. Keep the computer awake and plugged in.

## Slide 7 — Geremi: Madrid map

1. Switch to the local dashboard's simulated view and tracking map.
2. Point out that the couriers and orders are fictional. The street basemap is real; the recorded GPS path joins samples with straight lines and is **not street routing**.
3. Select a courier. Show its order, customer and recorded GPS path, then the active/delivered/late totals.
4. Explain that GPS history is append-only. The materialized view maintains partial `argMax` states; `courier_latest` merges them into the latest answer. A 150-courier result does not imply only 150 physical stored aggregate states.
5. Return to the presentation and advance through its manual focus builds. If data is stale, show its age rather than implying invented movement.

## Slide 8 — Geremi: AI and public datasets

1. Switch to **AI agents**. Show the available decisions and reasons from the local model, noting the fixed budget. An empty AI view on a traffic-only run is expected.
2. Switch to **Downloaded datasets**. Show **Criteo** and **Glovo**, which are loaded on the host.
3. Show the SQL/read statistics if time permits. The Criteo grouping time is server query time, not browser latency. A Glovo catalog entry is an offered product, not an order. Keep real datasets separate from the fictional GPS and purchases.
4. Return to the slides. Keep unrelated missing legacy explorers out of this short prepared route.

## Slides 11–14 — experiment appendix

Use the received frozen evidence, not a new stress run while the demo is generating data. [GPS-BENCHMARK.md](GPS-BENCHMARK.md) documents the separate port-18124 lab and commands. It does not use the production port or gateway.

With one reader, history client p95 is 704–750 ms and prepared state 125 ms. With two readers, history is 1,625–1,969 ms and prepared state 266–281 ms. There are three 200-request repetitions per design/reader level: 2,400 measured requests, zero errors. The 1-second line is an experimental latency target, not an absolute ClickHouse capacity. Higher reader counts were not attempted after history crossed it.

Server time is a different measure: the one-reader history median is 560–562 ms and prepared state 6 ms. Explain the recorded rows read and CPU budget; query memory is not total container RAM. Do not claim that all current server rows were scanned by a query filtering a single run. The cost of maintaining views during ingestion and the cross-database comparison are separate experiments.

## Extra live demonstration and questions

- **Customer Journey:** open `/analytics.html?panel=journey`, filter one run/cohort, expand its ClickHouse SQL and read statistics. Explain unique sessions, `FINAL` and ordered `windowFunnel` steps. Empty AI cohorts are valid for traffic-only runs.
- **Performance:** open the performance panel, show engines/sort keys and `system.parts`, then query families from `system.query_log`. For **Compare fixed queries**, stop generators and wait for pending 0. Both answers must match before a ratio is shown. A general detail/aggregate comparison is not the separate GPS boundary experiment.
- **One order:** on the host mini-app place an order while a customer simulation is active, then follow its ID on the dashboard. A 202 response means queued, not yet visible in ClickHouse. Switch to the prepared order after 15 seconds rather than waiting through a delivery.
- **CRUD:** `python3 scripts/crud_demo.py` uses only the scratch table `delivery.demo_events`. Explain insert/read versus part-rewriting mutations. Keep credentials out of the projector. If the assignment requires all four operations live, include this 1-minute example after slide 14. It is an add-on, not slide 14's prepared content.

### Optional SQL on the local host

For a stable latest-position comparison, set the **same frozen run UUID** in both queries. Do not discover the latest run by scanning the history inside only one timed path.

```sql
SELECT courier_id,
       argMax((latitude, longitude, event_time), (event_time, event_id)) AS latest
FROM delivery_atlas.courier_positions
WHERE simulation_run_id = toUUID('4f297d43-7255-4c72-8b4d-0dc108280f6c')
  AND city_id = 'madrid'
GROUP BY courier_id
ORDER BY courier_id;

SELECT courier_id, (latitude, longitude, event_time) AS latest
FROM delivery_atlas.courier_latest
WHERE simulation_run_id = toUUID('4f297d43-7255-4c72-8b4d-0dc108280f6c')
  AND city_id = 'madrid'
ORDER BY courier_id;
```

Use a run present in that local instance; the benchmark lab and demo have independent volumes. The runner compares full position tuples, validates every answer and collects query IDs; these short illustrative SQL statements do not replace that experiment.

## Fallback and shutdown

| Symptom | Action |
|---|---|
| Local analytics page is 404 | Rebuild Atlas from current main; refresh the gateway too for shared routes |
| Public data routes are 503 | Check host, authenticated gateway and current tunnel address; use the host demo |
| Map empty/stale | Check run state, queue and the displayed position age; use the recorded capture if necessary |
| Queue grows | Wait or reduce the workload; pending data is not a proof of permanent loss or successful publication |
| A query stalls beyond 15 s | Switch to the prepared screenshot/output, clearly marked recorded |
| A public dataset is missing | Skip it or show its missing state; never present simulation as that dataset |

After rehearsal, stop the fresh run, wait for pending 0 and keep its archive. Restore long-run generation only intentionally; never delete ClickHouse or queue volumes to reset the demo. To stop services while keeping data, use `docker compose -f compose.yaml --profile atlas --profile ai stop`.
