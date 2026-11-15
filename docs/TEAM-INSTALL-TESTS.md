# Team installation tests

Log of Delivery Atlas installations on computers other than the development one, as requested in [TEAM-PLAN.md](TEAM-PLAN.md). Each test records system, versions, commands and results. Anyone who repeats the test on another computer can add it at the end using the same format.

The current reproduction path is Atlas without large datasets: [ATLAS-INSTALL.md](ATLAS-INSTALL.md). Dated tests below retain the commands and versions used at the time.

## Anuar: Windows 11, 19 October 2026

| Item | Version |
|---|---|
| System | Windows 11 Home 10.0.26300 |
| Docker | Docker Desktop with Engine 29.8.1 and Compose v5.5.1 |
| Python | 3.12.3 |
| Git | 2.42.0.windows.2 |
| Code | Commit `657c044` of the team branch |

Clean start, with new empty volumes. The base images were already downloaded from an earlier test. To avoid touching another Atlas installation on the same computer, the test used a separate Compose project (`-p atlas-prueba`) with a different container name; the commands are the same.

| Step | Command | Result |
|---|---|---|
| Start | `docker compose -f compose.yaml --profile atlas up -d --build --wait` | ClickHouse and the API `healthy` in 15 s |
| Tests | `python -m unittest discover -s tests -v` | 20 tests OK in 1.4 s |
| Integration | `python scripts/check_atlas.py` | 409 when reusing an ID with different content and 400 for an invalid action. The lost and resent response leaves 3 physical rows and 2 logical events. Detail and aggregate match |
| Generator | `python scripts/atlas.py generate --events 10000 --batch 1000 --seed 42` | 10000 events accepted in 1 s |
| Status | `python scripts/atlas.py status` and `GET /api/status` | 10002 events accepted and published (10000 from the generator and 2 from the integration check), 0 pending and 0 publishing errors |
| Operations | `python scripts/check_operations.py` | An old position does not replace the latest one and invalid coordinates return 400. After a failure injected between INSERTs: 4 physical rows, 2 logical positions and 2 logical orders |
| CRUD | `python scripts/crud_demo.py` | INSERT, SELECT, UPDATE and DELETE on `delivery.demo_events` |
| Web interfaces | http://127.0.0.1:8124/play and http://127.0.0.1:8124/dashboard | Both return 200 |

**Earlier test, 14 October 2026,** on the mini-app branch (`codex/atlas-miniapp`, commit `706ca29`): clean start, `/health` OK, dashboard and mini-app returning 200, `customer_orders.source_kind` accepts `demo_live`, checkout without a simulation returns 409, and all 28 tests pass, including the 8 mini-app tests.

## Anuar: Windows 11 as the demo server, 19 October 2026

Requested by Jere: run Atlas on this computer as the demo server, with its real local installation (not a separate test project), and record the results. These are this computer's results; they say nothing about the stability of other machines.

| Item | Version |
|---|---|
| System | Windows 11 Home 10.0.26300.9711 |
| Docker | Docker Desktop with Engine 29.8.1 and Compose v5.5.1, WSL2 kernel 6.18.54.1. Docker has 20 CPUs and 7.6 GiB of memory |
| ClickHouse | 25.8.33.6 |
| Python | 3.12.3 |
| Node | Not installed. The JavaScript tests run in the `node:22-alpine` image (v22.23.3) |
| Git | 2.42.0.windows.2 |
| Code | Commit `31bcef8` of the team branch (after PR #5) |

### Start

- Starting point: the old Flask/Grafana stack was stopped, ports 8001 and 8124 were free, and only this installation's `bd2-clickhouse` and `atlas` containers existed (stopped). The volumes were kept; `down -v` was not used.
- `docker compose -f compose.yaml --profile atlas up -d --build --wait`: both containers `healthy` in 20 s. `/`, `/delivery.html`, `/health`, `/api/status`, `/api/operations` and http://127.0.0.1:8124/play return 200.
- Catalog: this database had been seeded before the translation, so the three fallback dish names were still in Spanish. New versions of those rows were inserted with the English names; nothing was deleted. The table is a `ReplacingMergeTree(version)` read with `FINAL`, so the newest version wins. Restart the API afterwards so it reloads the names:

```bash
docker exec bd2-clickhouse clickhouse-client --user demo --password demo --query "INSERT INTO delivery_atlas.demo_products SELECT product_id, restaurant_id, multiIf(product_name='Bowl de verduras','Vegetable bowl', product_name='Menú de la casa','House menu', product_name='Ensalada del día','Salad of the day', product_name), price_minor, currency, price_kind, name_kind, source_table, source_row, version + 1 FROM delivery_atlas.demo_products FINAL WHERE product_name IN ('Bowl de verduras','Menú de la casa','Ensalada del día')"
docker compose -f compose.yaml --profile atlas restart atlas
```

### Simulation and manual purchase

| Check | Result |
|---|---|
| Run | "Traffic simulator", 24 customers, 12 couriers, 2 s interval, seed 42, without Ollama |
| Manual purchase in the mini-app, in the browser | Search "salad", filter "Dishes up to €10", restaurant Mesa Verde, two dishes, "Place order" |
| Double click on "Place order" | A single `POST /api/checkout` (202): the button is locked while the order is being placed |
| Retry of the same order (same IDs and time) | 200 `already_accepted`; still one manual order in `customer_orders` |
| Tracking | `created` (51 s waiting for a free courier) → `preparing` → `picked_up` → `en_route` → `delivered`, 2 min 27 s after checkout. `/api/order` reports `delivered` |
| GPS | 49 positions for the order, all from the same courier |
| Dashboard | Listed as "Mini-app (manual) · Delivered · €20.86", with no console errors |
| Queue at the end | 5423 events accepted and published, 0 pending, no publishing errors |
| Run totals | 68 orders: 56 delivered, 0 cancelled, the rest still in progress when the run was stopped |

### Concurrent reads

Eight viewers polled `/api/operations` once per second for 5 minutes while the simulation was running. Container health and memory were sampled every 30 s.

| Measure | Result |
|---|---|
| Requests | 2400, all 200, no failures |
| Latency | p50 0.024 s, p95 0.090 s, p99 0.100 s, max 0.616 s |
| Containers | `healthy` in every sample, 0 restarts during the session |
| Memory | ClickHouse 688 → 911 MiB, Atlas about 30 MiB |

### Tests

| Command | Result |
|---|---|
| `python -m unittest discover -s tests -v` | 38 tests; 1 skipped without `ATLAS_TEST_CLICKHOUSE_URL` |
| Same, with a disposable ClickHouse 25.8 (`--memory=1g --cpus=2`, `clickhouse-config.xml` mounted) and `ATLAS_TEST_CLICKHOUSE_URL=http://127.0.0.1:18124` | 38 tests OK, including the tracking integration test |
| `node --test tests/test_delivery_ui.cjs` in `node:22-alpine` | 7 tests OK |

### Fix found during the test

The dashboard's "Customers" selector did not offer 24, although the API accepts it and 24 customers with 12 couriers is the recommended starting point. A run started with 24 left the selector blank. The option has been added and checked from the dashboard: "Traffic simulator", 24 customers and 12 couriers start correctly.

### Not covered

- The AI modes with Ollama.
- Sharing through Vercel from this computer: it needs this computer's own token files and an authorized Vercel project, to be coordinated with Jere.
- Stability over a longer period than this session.

## Windows problems and how to solve them

| Problem | Solution |
|---|---|
| `python3` does not exist | Use `python` (or `py`) in every command of the documentation |
| Accented characters look wrong in the console | Before running the scripts: `$env:PYTHONUTF8=1` in PowerShell or `export PYTHONUTF8=1` in Git Bash |
| `docker compose` fails with `dockerDesktopLinuxEngine` | Open Docker Desktop and wait until the engine is running |
| A `.sh` script fails inside a container with `/bin/bash^M: bad interpreter` | Git for Windows can convert shell files to CRLF. Preserve local changes, pull the current `.gitattributes`, save the affected `.sh` file with LF in the editor and rerun it. Do not reset the checkout to repair line endings. |
| An earlier stack from the repository is running (`docker-compose.yml`, with Flask and Grafana) | It shares the Compose project name with Atlas. Stop it first with `docker compose -f docker-compose.yml down`, which keeps its volumes |

**Watch out:** `scripts/check_operations.py` overwrites `docs/evidencia-tracking.json` with the result of each run. If you do not want to commit that new evidence, restore it with `git checkout -- docs/evidencia-tracking.json`.

## Anuar: local CRUD after the 15 November rebuild

Anuar reports `python scripts/crud_demo.py` on the updated host: INSERT, UPDATE and DELETE correct, zero rows remaining, elapsed 0.75 s. The [host record](HOST-STATUS-2026-11-15.md) and [inventory](INVENTORY-2026-11-15.md) identify the environment. This is a host-side check, separate from Echenique's additional reproduction and the full group rehearsal.

## Status for the final presentation

Anuar reported another fresh Windows installation on 11 November in [ATLAS-INSTALL.md](ATLAS-INSTALL.md#tested), and a preserved-volume host/API/gateway rebuild on 15 November in [the host record](HOST-STATUS-2026-11-15.md). Long generated runs and archived exports are listed in [SIMULATION-RUNS.md](SIMULATION-RUNS.md). Those later checks supersede the earlier pending long-run/host-update items; they do not establish uninterrupted uptime.

The public tunnel connection was restored and checked on 15 November; its continued availability depends on the running host/tunnel. Echenique's additional installation/CRUD record and the full four-person timed rehearsal still need confirmation. A cold start without cached images has not been timed.
