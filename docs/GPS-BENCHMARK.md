# GPS history and prepared latest state comparison

This standalone lab compares the same current courier positions computed from `courier_positions` with the answer from `courier_latest`. It uses the existing Atlas SQL without changing the application, map, gateway, deployment or presentation. The runner is read-only and uses the Python standard library. The optional charts require Matplotlib.

The initial corpus is the already audited run `4f297d43-7255-4c72-8b4d-0dc108280f6c`: **4,371,300 GPS rows and 150 couriers**. The 13.4 million figure for the two large October runs includes five tables; it is not the number of GPS rows scanned by this run filter.

## Separate checkout and lab

Use a separate clone for these commands. This avoids changing the checkout serving the demo. During PR review, clone the branch explicitly:

```text
git clone --branch codex/gps-comparison-runner https://github.com/Gere2/analitica-reparto-clickhouse.git delivery-atlas-gps-lab
cd delivery-atlas-gps-lab
docker compose -f benchmarks/gps/compose.yaml up -d --wait --wait-timeout 120
```

Only a new ClickHouse service starts. It has its own Compose project and volume, loopback port **18124**, 2 CPUs, 2 GiB container memory and a 1.5 GiB server memory budget. These are explicit lab settings, not a claim about Anuar's whole machine. Merges remain active. Keep this project's resource budget within the free capacity of the host and run outside a presentation rehearsal.

The lab creates the actual `atlas.sql` and `atlas_operations.sql` schema and a marker in `gps_comparison_lab.identity`. It creates a SELECT-only reader. The public passwords in `benchmarks/gps/init.sql` are for this loopback lab only. Both scripts refuse the demo's port 8124, remote hosts, proxy forwarding and redirects. The identity marker must also match. Keep this port local.

Record the environment alongside the output:

```text
git rev-parse HEAD
docker info --format "{{.NCPU}} CPUs / {{.MemTotal}} bytes"
docker inspect --format "{{.Image}} / {{.HostConfig.NanoCpus}} nanoCPUs / {{.HostConfig.Memory}} memory bytes" atlas-gps-benchmark-clickhouse-1
docker stats --no-stream atlas-gps-benchmark-clickhouse-1
```

The runner records server version, query settings, table definitions, source fingerprint, active parts/merges, disk reserve, per-query CPU time and query-log memory. Capture `docker stats` separately every 2–5 seconds if container CPU/RAM time series are needed. Per-query memory and CPU time are not container memory or CPU percentage.

## Validate a tiny fixture first

```text
python scripts/gps_benchmark_lab.py fixture
```

This loads **12 fictional positions for three couriers**, deliberately out of insertion order. It prints the exact smoke command containing its new run UUID. Run that command, then generate the English summary:

```text
python scripts/gps_benchmark_report.py PATH_TO_OUTPUT/report.json
```

A smoke run has three measured requests per design, one reader and one warmup. Its report explicitly says it is validation, not a capacity result. Run the optional real-ClickHouse integration tests as well. On PowerShell:

```powershell
$env:GPS_BENCHMARK_TEST_URL = "http://127.0.0.1:18124/"
python -m unittest discover -s tests -p test_gps_benchmark_integration.py -v
```

On bash:

```bash
GPS_BENCHMARK_TEST_URL=http://127.0.0.1:18124/ python -m unittest discover -s tests -p test_gps_benchmark_integration.py -v
```

These tests insert only tiny, uniquely identified fixture runs into the marked lab. They never drop/truncate data or contact the demo. Without that environment variable, the integration class is skipped. Unit and HTTP transport checks run with:

```text
python -m unittest discover -s tests -p test_gps_benchmark.py -v
```

## Load the verified GPS export

Use the existing `courier_positions.csv.gz` from Anuar's export folder `2026-10-31_4f297d43`. Replace `PATH_TO_EXPORT` below. The file can stay outside this new checkout; the loader only reads it.

```text
python scripts/gps_benchmark_lab.py load --csv "PATH_TO_EXPORT/courier_positions.csv.gz" --run-id 4f297d43-7255-4c72-8b4d-0dc108280f6c --expected-rows 4371300
```

Before inserting, the loader validates the gzip/CSV through EOF, header, row count, run IDs, city, couriers and coordinate ranges. It records the source-file SHA-256. It refuses to load a run already present. Input is streamed in bounded chunks; it does not hold the large export in memory. The normal materialized view maintains `courier_latest_state`; do not load a second copy of those states.

An INSERT timeout or failure can leave partial data. The loader never retries, resets or deletes automatically. Inspect the lab counts before deciding how to repair a partial load. Changing the lab's bootstrap SQL does not re-run it on an existing volume.

## Run the comparison

First use `--smoke` on the real corpus:

```text
python scripts/gps_benchmark.py --run-id 4f297d43-7255-4c72-8b4d-0dc108280f6c --expected-rows 4371300 --expected-couriers 150 --label "Anuar Windows; lab 2 CPU / 2 GiB; record other workloads" --smoke
```

Then explore, with a frozen source and no simulator/watchdog writing to the lab. Run only one benchmark process at a time; other lab readers or writers would compete for its resource budget:

```text
python scripts/gps_benchmark.py --run-id 4f297d43-7255-4c72-8b4d-0dc108280f6c --expected-rows 4371300 --expected-couriers 150 --label "Anuar Windows; lab 2 CPU / 2 GiB; record other workloads" --concurrency 1,2,4,8 --requests 30 --repetitions 1
```

The runner checks equal full position tuples before measuring and compares every response with that frozen answer. It checks row count, courier count and a source fingerprint between phases. Any changed answer or corpus stops the experiment. The hash is a change detector, not a universal proof of event-ID uniqueness.

Each design runs separately with identical settings and fixed closed-loop concurrency. Readers send their next request when the previous one finishes. There is no artificial batch barrier between requests. Both designs get five warmups at each concurrency; warmups are excluded. For repeated phases, order alternates history/prepared, then prepared/history. The SQL query-result cache is disabled; the OS cache remains uncontrolled. This is a warm comparison.

Defaults: 8 seconds and 256 MiB per query, two query threads, 180 seconds per phase, 30 minutes for workload/control queries, at least 5 GiB free disk. Timeouts are cooperative; in-flight queries may finish after a workload deadline, bounded by their query/client timeout. Final read-only query-log collection has a short separate grace period. The runner does not issue SYSTEM/KILL or mutate settings globally.

The exploratory SLO is **successful-request client p95 ≤ 1,000 ms and zero errors**. Failures remain counted, even though latency percentiles use successful requests only. A phase that runs out of time or stops on a query/error/correctness issue is incomplete, not a clean latency boundary. No requests are automatically retried. The next concurrency is not attempted after a completed level crosses the SLO. Both designs and repetitions at that level are measured unless a query error or invalid corpus stops the experiment first.

To investigate a candidate at concurrency 4 and 8, for example:

```text
python scripts/gps_benchmark.py --run-id 4f297d43-7255-4c72-8b4d-0dc108280f6c --expected-rows 4371300 --expected-couriers 150 --label "Anuar Windows; same lab budget and frozen data" --concurrency 4,8 --requests 200 --repetitions 3 --phase-seconds 600 --max-seconds 3600
```

Choose levels from the exploration; 4 and 8 are examples, not a measured boundary. If the lowest tested level already fails, include a lower passing point in another bounded run. If every point passes, report **boundary not reached in the tested range**. If the two designs behave inconsistently across repetitions, repeat before drawing a conclusion. A configured memory rejection is a configured resource limit, not an absolute ClickHouse maximum. Client overhead can dominate very fast prepared reads; successful QPS is not automatically a database capacity figure.

## Results for Anuar and the presentation

Each run prints its fresh directory under `data/gps-benchmark/` (already ignored by Git):

- `report.json`: all parameters, SQL, correctness digest, table definitions, snapshots, requests and query-log coverage.
- `reference-output.json`: the actual frozen position answer.
- `phases.csv`: sample counts, failures, client p50/p95, QPS and phase completion.
- `samples.csv`: each request joined by query ID to server duration, rows/bytes read, query memory, exceptions and CPU time.

The SELECT-only reader waits for asynchronous query-log records instead of issuing SYSTEM FLUSH LOGS. Missing server records remain missing; they are never presented as zero memory. CLI exit 0 requires a completed valid run and complete query-log coverage; otherwise inspect the saved report. An observed latency-SLO failure can still be a successful experiment (exit 0), unlike an incomplete phase.

Generate the English summary with the report command above. For optional charts, install Matplotlib in a separate plotting environment and use:

```text
python -m pip install "matplotlib>=3.8,<4"
python scripts/gps_benchmark_report.py PATH_TO_OUTPUT/report.json --plot
```

This adds `summary.md`, `comparison.png` and `comparison.svg`. The plot shows the median of per-phase p95 values across repetitions, not a confidence interval. Smoke/incomplete plots are visibly labelled. Send the complete output directory, resource observations, exact commit and commands. Do not replace the measured corpus size with the total of unrelated runs/tables.

For the final presentation: show equal positions, the history query at an already tested load, the prepared query at that same load, then rows read, timing, errors and memory. Explain the cause supported by those measurements. Maintaining materialized states also has ingestion/storage cost; measure that separately later. Do not describe these read-only trials as an ingestion benchmark or a high-availability test.

Stop only this lab when finished:

```text
docker compose -f benchmarks/gps/compose.yaml stop
```

References: [ClickHouse read-only settings](https://clickhouse.com/docs/operations/settings/permissions-for-queries), [query log](https://clickhouse.com/docs/operations/system-tables/query_log), [repeatable query diagnosis](https://clickhouse.com/docs/guides/clickhouse/performance-and-monitoring/isolate-query-bottlenecks).
