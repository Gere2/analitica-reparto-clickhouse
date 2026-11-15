# Data inventory, 15 November 2026

Read-only snapshot of the demo server (Anuar's computer), taken on **15 November 2026 at about 19:25 UTC** for the final delivery. It records what the demo ClickHouse holds today, the 21 archived simulation runs and the environment of the GPS comparison of 6 November. Nothing was loaded, deleted or regenerated to produce it.

Two different data sets appear below. Do not mix them:

- **Current inventory:** everything the demo ClickHouse holds today, 21 simulation runs, **37,310,669 logical Atlas rows**, of which **23,978,916** are GPS positions.
- **Frozen GPS corpus:** one run only (`4f297d43…`, 31 October), **4,371,300 GPS positions from 150 couriers**, copied into a separate ClickHouse lab on 6 November for the history vs. prepared-state comparison. That comparison measured this corpus, not the current 24 million positions.

A comparison with PostgreSQL or DuckDB has **not** been run; it remains future work.

## Demo server

| Item | Value |
|---|---|
| Checkout serving the demo | `main` at `c7d4ca11abd2c4be0d1609805b94910d8cb886a4`, clean |
| ClickHouse | `clickhouse/clickhouse-server:25.8`, image `sha256:0152dd511befe6a2c2ef53e930726179669b08116da78500b37c51c96ff5ee77`, server version **25.8.33.6**, timezone UTC; no container CPU or memory limit |
| Atlas API (port 8001) | image built from `c7d4ca1` on 15 November (`sha256:bb8ec9802e9b…`) |
| Second Atlas API `atlas-sim2` (port 18001) | manual container on the older image (`sha256:82445c2544bb…`); its simulation is stopped and it stays stopped during the rehearsal |
| Share gateway and tunnel | gateway built from `c7d4ca1`; `cloudflare/cloudflared:2026.3.0` Quick Tunnel (its URL changes when the tunnel is recreated) |
| Ollama | `ollama/ollama@sha256:926d40fd6eee…`, model `qwen3:0.6b` |
| Docker | Docker Desktop 29.8.1, 20 CPUs and 8.17 GB memory visible to Docker |
| Host | Intel Core i7-12700H (14 cores, 20 threads), 15.7 GB RAM, Windows 11; 263 GB free of 1,022 GB on the data drive |
| Generation | no simulation running; watchdog paused (`data/runs/WATCHDOG-PAUSE`); no merges in progress |

## Current inventory in ClickHouse

Logical rows are `count() FINAL`. For every Atlas table it equals the plain `count()`, so there are no pending duplicates. Size is the compressed size of the active parts on disk.

| Table (`delivery_atlas`) | Engine | Logical rows | Runs | Compressed | Uncompressed | First event (UTC) | Last event (UTC) |
|---|---|---:|---:|---:|---:|---|---|
| `courier_positions` | ReplacingMergeTree | 23,978,916 | 21 | 953.5 MB | 2,613.8 MB | 2026-10-19 14:58:03 | 2026-11-11 22:11:20 |
| `customer_activity` | ReplacingMergeTree | 6,592,705 | 21 | 226.2 MB | 1,774.5 MB | 2026-10-19 14:58:03 | 2026-11-11 22:11:20 |
| `app_events` | ReplacingMergeTree | 4,905,821 | 21 | 273.2 MB | 751.0 MB | 2026-10-19 14:58:03 | 2026-11-11 22:11:20 |
| `order_events` | ReplacingMergeTree | 1,569,551 | 21 | 59.1 MB | 251.5 MB | 2026-10-19 14:58:14 | 2026-11-11 22:11:20 |
| `customer_orders` | ReplacingMergeTree | 263,676 | 21 | 24.5 MB | 49.5 MB | 2026-10-19 14:58:14 | 2026-11-11 22:11:20 |
| **Event tables** | | **37,310,669** | | **1,536.5 MB** | **5,440.4 MB** | | |
| `courier_latest_state` | AggregatingMergeTree | 1,672 | | 0.13 MB | | | |
| `customer_latest_state` | AggregatingMergeTree | 5,182 | | 0.46 MB | | | |
| `order_latest_state` | AggregatingMergeTree | 263,812 | | 24.1 MB | | | |
| `app_daily_rollup` | AggregatingMergeTree | 115 | | 78.8 MB | | | |

The whole `delivery_atlas` database uses 1.64 GB compressed (5.57 GB uncompressed). The downloaded datasets in the `delivery` database are `criteo_uplift` with 13,979,592 rows and `glovo_products` with 2,887,444 rows (397 MB compressed together). OTTO, REES46 and Ele.me are not loaded on this server.

The 37,310,669 rows in ClickHouse are 32 more than the 37,310,637 in the archives. They are 32 `app_events` with no simulation run (`simulation_run_id` is NULL), which `export_run.py` cannot export because it exports by run. Every other table matches the archives row for row.

## The 21 archived runs

Each run was exported with `scripts/export_run.py` after its queue reached pending 0. On 15 November all 21 archives in `data/runs/` passed `verify_saved`, which checks the size of each file, its CSV record count and the run of every record (these manifests have no SHA-256, so none is compared): **21 correct, 0 failures, 37,310,637 rows**. The manifests (`summary.json`, a few KB each) are in [`run-manifests/`](run-manifests/); the CSV files are not in Git. The first 19 are in the GitHub release `simulation-runs-2026-11-01`.

The two runs of 11 November ran from 17:34 to 22:11 UTC, when Docker Desktop closed, so the planned 50-million-row milestone was not reached:

- `2026-11-11_f1dee148`: API 8001, hybrid (3 AI customers, 120 model decisions), 500 customers and 150 couriers;
- `2026-11-11_b6a982ca`: API 18001, traffic only, 500 customers and 150 couriers.

| Manifest | First event (UTC) | Last event (UTC) | GPS | Customer actions | Browsing | Order events | Orders | Total rows | CSV.gz bytes |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|
| [`2026-10-19_dde04b4a`](run-manifests/2026-10-19_dde04b4a.json) | 2026-10-19 14:58:03 | 2026-10-19 15:06:34 | 3,084 | 1,080 | 808 | 375 | 68 | 5,415 | 245,112 |
| [`2026-10-19_6f5d9c10`](run-manifests/2026-10-19_6f5d9c10.json) | 2026-10-19 15:07:12 | 2026-10-19 15:07:25 | 96 | 108 | 84 | 6 | 3 | 297 | 15,759 |
| [`2026-10-21_60a17065`](run-manifests/2026-10-21_60a17065.json) | 2026-10-21 14:12:29 | 2026-10-21 22:19:33 | 68,892 | 23,653 | 17,516 | 8,465 | 1,421 | 119,947 | 5,402,790 |
| [`2026-10-21_1bcd5235`](run-manifests/2026-10-21_1bcd5235.json) | 2026-10-21 14:50:33 | 2026-10-21 14:52:05 | 288 | 134 | 103 | 32 | 8 | 565 | 28,326 |
| [`2026-10-21_ec718664`](run-manifests/2026-10-21_ec718664.json) | 2026-10-21 14:54:35 | 2026-10-21 15:52:35 | 10,452 | 3,592 | 2,650 | 1,159 | 194 | 18,047 | 799,440 |
| [`2026-10-22_2bf28040`](run-manifests/2026-10-22_2bf28040.json) | 2026-10-21 22:22:53 | 2026-10-21 23:29:07 | 23,868 | 4,131 | 3,053 | 1,383 | 232 | 32,667 | 1,286,396 |
| [`2026-10-22_1c7d14ad`](run-manifests/2026-10-22_1c7d14ad.json) | 2026-10-22 07:22:15 | 2026-10-22 07:24:47 | 936 | 244 | 182 | 70 | 16 | 1,448 | 64,644 |
| [`2026-10-22_b0ff283b`](run-manifests/2026-10-22_b0ff283b.json) | 2026-10-22 07:24:55 | 2026-10-22 11:41:17 | 384,650 | 145,792 | 108,143 | 47,076 | 7,876 | 693,537 | 32,610,992 |
| [`2026-10-28_a4fa27e7`](run-manifests/2026-10-28_a4fa27e7.json) | 2026-10-28 09:32:32 | 2026-10-28 10:16:40 | 66,300 | 25,203 | 18,719 | 8,077 | 1,377 | 119,676 | 5,683,446 |
| [`2026-10-28_01b38d23`](run-manifests/2026-10-28_01b38d23.json) | 2026-10-28 10:17:27 | 2026-10-28 12:13:51 | 174,700 | 66,409 | 49,231 | 21,358 | 3,577 | 315,275 | 14,859,938 |
| [`2026-10-28_87fb364b`](run-manifests/2026-10-28_87fb364b.json) | 2026-10-28 14:50:24 | 2026-10-28 16:06:46 | 88,250 | 33,728 | 25,024 | 10,850 | 1,827 | 159,679 | 7,610,841 |
| [`2026-10-28_a12236a9`](run-manifests/2026-10-28_a12236a9.json) | 2026-10-28 16:06:48 | 2026-10-30 12:07:41 | 467,650 | 178,177 | 132,174 | 57,732 | 9,697 | 845,430 | 40,230,417 |
| [`2026-10-31_4f297d43`](run-manifests/2026-10-31_4f297d43.json) | 2026-10-31 15:05:24 | 2026-10-31 23:11:03 | 4,371,300 | 1,175,872 | 875,118 | 271,406 | 45,397 | 6,739,093 | 534,861,977 |
| [`2026-10-31_6bf38221`](run-manifests/2026-10-31_6bf38221.json) | 2026-10-31 15:10:11 | 2026-10-31 23:11:03 | 4,328,250 | 1,163,808 | 866,103 | 268,632 | 44,950 | 6,671,743 | 528,255,897 |
| [`2026-10-31_ce8625ad`](run-manifests/2026-10-31_ce8625ad.json) | 2026-10-31 23:11:36 | 2026-10-31 23:12:52 | 11,550 | 4,896 | 3,884 | 1,000 | 400 | 21,730 | 1,740,434 |
| [`2026-11-01_2d08b7a9`](run-manifests/2026-11-01_2d08b7a9.json) | 2026-11-01 16:20:22 | 2026-11-01 16:43:22 | 206,250 | 57,003 | 42,522 | 13,147 | 2,347 | 321,269 | 25,757,297 |
| [`2026-11-01_31fdac6e`](run-manifests/2026-11-01_31fdac6e.json) | 2026-11-01 16:20:24 | 2026-11-01 16:43:22 | 206,100 | 56,570 | 42,200 | 13,126 | 2,350 | 320,346 | 25,618,484 |
| [`2026-11-03_70861ccd`](run-manifests/2026-11-03_70861ccd.json) | 2026-11-03 02:20:08 | 2026-11-03 13:25:24 | 5,988,150 | 1,610,503 | 1,198,489 | 371,796 | 62,196 | 9,231,134 | 736,286,299 |
| [`2026-11-03_592f4a72`](run-manifests/2026-11-03_592f4a72.json) | 2026-11-03 02:20:08 | 2026-11-03 13:25:25 | 5,988,000 | 1,609,204 | 1,197,495 | 371,637 | 62,179 | 9,228,515 | 735,432,330 |
| [`2026-11-11_b6a982ca`](run-manifests/2026-11-11_b6a982ca.json) | 2026-11-11 17:33:53 | 2026-11-11 22:11:20 | 796,950 | 216,620 | 161,401 | 51,300 | 8,778 | 1,235,049 | 99,583,748 |
| [`2026-11-11_f1dee148`](run-manifests/2026-11-11_f1dee148.json) | 2026-11-11 17:34:24 | 2026-11-11 22:11:20 | 793,200 | 215,978 | 160,890 | 50,924 | 8,783 | 1,229,775 | 99,204,365 |
| **21 runs** | | | **23,978,916** | **6,592,705** | **4,905,789** | **1,569,551** | **263,676** | **37,310,637** | **2,895,578,932** |

Columns: GPS = `courier_positions`, customer actions = `customer_activity`, browsing = `app_events`, order events = `order_events`, orders = `customer_orders`. The first and last event span every table of the run and include any pauses; they are not continuous uptime.

## GPS comparison environment (6 November 2026)

The full method is in [GPS-BENCHMARK.md](GPS-BENCHMARK.md). The raw results are in the GitHub release `gps-benchmark-2026-11-06` (ZIP SHA-256 `3ed1f911283fd9afccaa222550754dda238a9df12ac8dbe701bd5861ab91d5d7`).

| Item | Value |
|---|---|
| Checkout | separate clone, branch `codex/gps-comparison-runner` at `da99591cc2f35bca6a5362c3ccb0b4e65fcf29b7` |
| ClickHouse lab | own Compose project, loopback port 18124, same image `clickhouse/clickhouse-server:25.8` (`sha256:0152dd51…`), server **25.8.33.6** |
| Lab budget | **2 CPUs** (2,000,000,000 nanoCPUs), **2 GiB** container memory (2,147,483,648 bytes), 1.5 GiB server memory budget; per query: `max_threads` 2, `max_memory_usage` 256 MiB, `max_execution_time` 8 s, query cache off |
| Frozen corpus | run `4f297d43-7255-4c72-8b4d-0dc108280f6c`, **4,371,300 GPS rows, 150 couriers**, 31 October 15:05–23:11 UTC; source file `courier_positions.csv.gz`, SHA-256 `02b411804845be0a186fff3621fd081411685d22d985e16ac2700f383107fbe8` |
| Lab tables | `courier_positions`: 4,371,336 physical rows in 7 parts, 170.2 MB on disk. The 36 extra rows are fictional test fixtures, outside the measured run. `courier_latest_state`: 159 rows, 14 KB |
| Loader change | 262,144-row insert blocks (`loader-insert-blocks.patch`), because the default blocks hit the 512 MiB loader limit. Before each retry, the lab was checked to hold no rows of that run |
| Host during the runs | Docker 29.8.1 with 20 CPUs and 8.17 GB visible to Docker; i7-12700H, 15.7 GB RAM; Python 3.12.3. Demo containers up but idle: no simulation and no watchdog |
| Runs | smoke `gps_20261106T012425Z_7151c843`; exploration `gps_20261106T012445Z_158eb8ee` (stopped by the runner rule after history crossed the 1 s target at 2 readers); confirmation `gps_20261106T012610Z_c68e4b4c` (1 and 2 readers, 200 requests × 3 repetitions, 2,400 requests, all found in `query_log`) |
| Correctness | history and prepared state returned the same 150 couriers (result SHA-256 `e639f31b…`) |

The lab volume `atlas-gps-benchmark_gps_lab_data` still exists on the host, and its container is stopped. The demo ClickHouse was never used for the measurements.

## How to repeat this snapshot

All the commands are read-only:

```sql
SELECT version();
SELECT count(), (SELECT count() FROM delivery_atlas.courier_positions FINAL),
       uniqExact(simulation_run_id), min(event_time), max(event_time)
FROM delivery_atlas.courier_positions;  -- repeat for the other four event tables
SELECT table, sum(rows), sum(data_compressed_bytes), sum(data_uncompressed_bytes)
FROM system.parts WHERE active AND database = 'delivery_atlas' GROUP BY table;
```

```text
docker inspect -f "{{.Config.Image}} {{.Image}}" bd2-clickhouse
docker info --format "{{.ServerVersion}} / {{.NCPU}} CPUs / {{.MemTotal}} bytes"
```

To verify the archives, call `verify_saved(folder, run_id)` from `scripts/export_run.py` for each folder in `data/runs/`, as the watchdog does through `export_run.py <run_id>`.
