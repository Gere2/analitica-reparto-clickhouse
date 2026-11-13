# Reproducible installation of the data lab

**To install the current project (Delivery Atlas), follow [ATLAS-INSTALL.md](ATLAS-INSTALL.md).** The instructions below are only for the earlier large-dataset lab (OTTO, REES46, Ele.me), which needs tens of GB of downloads.

## Requirements

- Docker Desktop or OrbStack with `docker compose`.
- Python 3.10 or later; our scripts use its standard library.
- Local ports 8124 (ClickHouse) and 8000 (dashboard).
- For **OTTO only**, at least 20 GB free. For the seven REES46 CSV.gz files and the billion-row stress table, we recommend **60 GB free** before starting. The exact space depends on compression and part merges.
- Do the downloads and loads **before class**. They are not meant for the 10 minutes of demo.
- In Docker with about 4 GB of memory, run **REES46 and scale sequentially**, in the order below. The loaders temporarily pause merges on their table to reduce memory peaks and resume them when they finish. `clickhouse-config.xml` limits simultaneous merges to four when the server starts; this setting prevents merges of the large datasets from saturating memory during the demo.

## 1. Start ClickHouse

```bash
docker compose -f compose.yaml up -d
docker compose -f compose.yaml ps
```

The `bd2-clickhouse` container must show as `healthy`. The local configuration uses ClickHouse 25.8, the `delivery` database, the demo user/password `demo` and HTTP on `127.0.0.1:8124`.

## 2. OTTO: real clicks and materialized view

```bash
python3 scripts/otto.py download
python3 scripts/otto.py load
python3 scripts/rollup.py
```

The ZIP is read as a stream; it does not need to be fully decompressed. Its expected SHA-256 is `ae11a23676ba29eeeb6e1348b81e353c530da3bc059353cad67247e9616acb2f`. The original source is [OTTO/Kaggle](https://github.com/otto-de/recsys-dataset); for convenience a [public mirror](https://huggingface.co/datasets/hazemessam/otto-recsys) is used. **194,720,954** clicks, **16,896,191** carts and **5,098,951** orders are checked against the published figures. `rollup.py` creates the materialized view **after** the initial load and performs the backfill once, avoiding thousands of small parts during the import. The daily aggregate must have **87 day/type keys** adding up to **216,716,096** events; there may be more physical rows until the merges finish.

To rehearse with fewer rows, `python3 scripts/otto.py load --limit 1000000 --reset` replaces the archive and its aggregate. Afterwards, `python3 scripts/otto.py load --reset` loads the full dataset. Do not use `--reset` by accident once the load is complete.

## 3. REES46: seven months of another marketplace

```bash
python3 scripts/rees46.py download
python3 scripts/rees46.py load
python3 scripts/rees46.py status
```

The seven compressed files are saved in `data/rees46/`. The script verifies the size published by the server, full decompression and the counts per month. `data/rees46/manifest.json` records views, carts and purchases. Each file is read as a stream and inserted in batches of 200,000 rows to limit memory; the data is real, historical and anonymized. If ClickHouse hits its memory limit, the loader retries up to ten times from the last confirmed batch. After an external interruption, `load --resume-partial` skips the batches already confirmed, as long as the count is a multiple of 200,000; `--replace-partial` rebuilds **only the incomplete month** when there is no safe resume point. Months already verified are kept. A single month can also be downloaded or loaded with `--month 2019-Oct`.

## 4. Derived scale and benchmark

```bash
python3 scripts/scale.py
python3 scripts/benchmark.py
python3 scripts/check.py
python3 scripts/report.py
```

`scale.py` requires the full OTTO dataset and generates five labelled scenarios of **216,716,096 rows each** with `INSERT SELECT`. Its table is synthetic and kept separate. `benchmark.py` compares archive and aggregate, verifies that the result is identical and saves `data/query-benchmark.json` with time, rows read and bytes read. `check.py` audits the counts; `report.py` writes [RESULTS.md](RESULTS.md) from the manifests and the measurements. Run them **after** the loads finish so the measurements do not compete with them.

## 5. Dashboard and demo

To also enable the delivery-industry dashboard, run `python3 scripts/eleme.py init` and open [Ele.me](http://127.0.0.1:8000/eleme.html). The official download needs a Tianchi account; the procedure and the preliminary checks of the first ZIP are in [ELEME.md](ELEME.md). On this machine the first part, D1_0, has already been imported: 2,170,299 samples. On a new installation the dashboard shows the empty state until a load is completed; the 146 M declared are never shown as a local count.

```bash
python3 dashboard.py
```

Open [OTTO](http://127.0.0.1:8000/), [REES46](http://127.0.0.1:8000/rees46.html) and [scale](http://127.0.0.1:8000/scale.html). In another terminal:

```bash
python3 scripts/otto.py replay --rate 5000 --limit 200000 --reset
python3 scripts/crud_demo.py
```

`--rate` is a target; the effective speed depends on the machine. `--reset` in the replayer empties **only** `otto_replay`. The OTTO buttons insert new clicks into `live_clicks`.
The CRUD script temporarily pauses merges on the large tables and resumes them on exit. If that process is killed, run `SYSTEM START MERGES` for `otto_archive`, `rees46_events` and `otto_scale_benchmark` from the SQL client.

## SQL checks

```bash
docker exec -it bd2-clickhouse clickhouse-client --user demo --password demo --database delivery
```

```sql
SELECT event_type, count() FROM otto_archive GROUP BY event_type ORDER BY event_type;
SELECT sum(events), count() FROM otto_daily_rollup;
SELECT toYYYYMM(event_date) AS month, count() FROM rees46_events GROUP BY month ORDER BY month;
SELECT scenario, count() FROM otto_scale_benchmark GROUP BY scenario ORDER BY scenario;
SELECT table, sum(rows), formatReadableSize(sum(bytes_on_disk))
FROM system.parts WHERE database = 'delivery' AND active
  AND table IN ('otto_archive','otto_daily_rollup','rees46_events','otto_scale_benchmark')
GROUP BY table ORDER BY table;
```

## Common problems

- **The dashboard does not connect:** check `docker compose -f compose.yaml ps`, port 8124 and the `python3 dashboard.py` process. If port 8000 is taken: `PORT=8001 python3 dashboard.py`.
- **Not enough space:** run only OTTO and the rollup; they already make it possible to demonstrate 216.7 million real events. Do not delete data needed before the presentation.
- **Interrupted REES46 load:** `python3 scripts/rees46.py status` shows the finished months. Try `python3 scripts/rees46.py load --resume-partial`; if the output says the incomplete batch cannot be resumed, use `--replace-partial` to rebuild only that month. `load --reset` deletes and rebuilds the whole table.
- **Interrupted scale scenario:** `python3 scripts/scale.py --replace-partial` deletes and redoes only the incomplete scenario. If a mutation cannot finish because of lack of memory, `python3 scripts/scale.py --reset` rebuilds the complete test table.
- **Process killed:** if a loader was stopped without running its final cleanup, re-enable merges with `SYSTEM START MERGES delivery.rees46_events` and `SYSTEM START MERGES delivery.otto_scale_benchmark` from the SQL client once the loads have finished.
- **Benchmark without data:** it requires the full OTTO dataset, at least one REES46 month and the scale table. The full seven-month load provides the final presentation.
