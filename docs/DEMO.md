# Live demo script: 10 minutes (earlier lab)

**For the final presentation, use [DEMO-GUIDE.md](DEMO-GUIDE.md).** This script is the 10-minute demo of the earlier data lab, kept for reference.

## Direction for the next demo

The [fictional food-delivery platform](FICTIONAL-PLATFORM.md) would make it possible to show: a user's path → events and simulated load → dashboard → comparison of queries over the same dataset. That integrated path **is not implemented yet**. The sequence below is the demo that can be run now with the current tables; the OTTO timings are not attributed to the platform's future generator.

## Before going into class

Complete the loads by following [INSTALLATION.md](INSTALLATION.md). Have open the [OTTO dashboard](http://127.0.0.1:8000/), the [REES46 dashboard](http://127.0.0.1:8000/rees46.html), the [scale dashboard](http://127.0.0.1:8000/scale.html), the [slides](http://127.0.0.1:8000/otto-presentacion.html) and two terminals. Save `data/query-benchmark.json` after running `python3 scripts/benchmark.py` and run `python3 scripts/check.py` to verify the whole set. Do not download or load tens of GB during the talk.

SQL client:

```bash
docker exec -it bd2-clickhouse clickhouse-client --user demo --password demo --database delivery
```

## Sequence

**0:00–1:00 — Sources and volume.** Show the OTTO dashboard and count:

```sql
SELECT event_type, count() AS events
FROM otto_archive GROUP BY event_type ORDER BY event_type;
```

Expected result for the full dataset: 194,720,954 clicks, 16,896,191 carts, 5,098,951 orders. Point out that they are historical and real.

**1:00–2:00 — Second real source.** Open REES46. Filter one month, show the volume by month, category and brand. Explain that its `view` rows are product views, not OTTO clicks; each source is in its own table. The seven months provide a time dimension that OTTO does not have.

**Food-delivery alternative:** open [Ele.me](http://127.0.0.1:8000/eleme.html). Show 2,170,299 samples and 38,914 positive labels from the first complete ZIP; go through hours and meal periods. Explain that it is a Chinese platform, that 1.79 % is not the production CTR and that the 146 million announced by the source are not all loaded. The dashboard is historical. The typed click query was measured at 0.0581 s; reading the full JSON exhausted local memory, with no timing comparison completed. See [ELEME.md](ELEME.md).

**2:00–4:00 — Ingestion and simultaneous queries.** In the second terminal:

```bash
python3 scripts/otto.py replay --rate 5000 --limit 200000 --reset
```

See that the chart responds. In SQL, repeat this query a few seconds later:

```sql
SELECT event_type, count() AS events
FROM otto_replay
WHERE ingested_at >= now64(3) - INTERVAL 30 SECOND
GROUP BY event_type;
```

`event_time` is the real old date; `ingested_at` is the current insertion. Do not call the replay "new OTTO clicks".

**4:00–5:00 — A genuinely new click.** Click "Explorar producto" (Explore product) and check that only the `live_clicks` counter goes up:

```sql
SELECT section, action, clicked_at
FROM live_clicks ORDER BY clicked_at DESC LIMIT 5;
```

**5:00–7:00 — Raw vs aggregate experiment.** Show two queries with the same answer:

```sql
SELECT toDate(event_time) AS day, event_type, count() AS events
FROM otto_archive GROUP BY day, event_type ORDER BY day, event_type;

SELECT event_date AS day, event_type, sum(events) AS events
FROM otto_daily_rollup GROUP BY day, event_type ORDER BY day, event_type;
```

To avoid spending time printing 87 lines twice, `python3 scripts/benchmark.py` can be run before class and [RESULTS.md](RESULTS.md) or the [scale dashboard](http://127.0.0.1:8000/scale.html) opened during the demo. Show the measured `rows_read` and `bytes_read` and that the script compared the answers. The aggregate has 87 day/type keys, although `SummingMergeTree` may keep several physical rows per key before merging them.

**7:00–8:00 — A billion rows with clear provenance.**

```sql
SELECT scenario, count() AS events
FROM otto_scale_benchmark GROUP BY scenario ORDER BY scenario;
```

Each scenario contains 216,716,096 rows. The five scenarios are **derived from OTTO**, not five sets of real customers. Show `data/scale-benchmark.json` and the query report.

**8:00–9:00 — Python and CRUD.** Run:

```bash
python3 scripts/crud_demo.py
```

The scratch table shows insert, read, update and delete without altering the history. Point out why the main pattern in analytics is appending events and querying aggregates.
The script briefly pauses merges on the large tables so that the scratch table's synchronous mutation does not wait behind a massive compaction; it resumes them in `finally`.

**9:00–10:00 — Architecture and questions.** Show `sql/schema.sql`: `MergeTree`, monthly partitions, sort keys, materialized view. Remind the audience that one local node has been run; shards and replicas are explained options, not present here.

## If a part fails during class

- The replay is independent of the already loaded archive: the two historical dashboards keep working.
- If the benchmark takes too long, use the JSON measured before class and show the SQL query.
- If the derived table is not loaded on the presentation machine, keep the real OTTO + REES46 and clearly explain that the stress test was not run there.
- Avoid attributing data from delivery platforms or from Spain to the dataset.
