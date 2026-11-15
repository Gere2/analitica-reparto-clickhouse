# Results measured on this machine

> Dated measurement record. Preserve the conditions and scope below. The current GPS campaign is documented separately in [GPS-BENCHMARK.md](GPS-BENCHMARK.md); the final project entry point is [FINAL-DELIVERY.md](FINAL-DELIVERY.md).

Benchmark date (UTC): 2026-10-04T22:56:43.976300+00:00.

## Provenance and size

- OTTO: **216,716,096 real events**, including **194,720,954 clicks**. Source: [OTTO publication](https://github.com/otto-de/recsys-dataset).
- REES46: **411,709,736 real events** over seven months. Source: [REES46 publication](https://data.rees46.com/).
  - Breakdown: **385,746,849 views**, **19,114,063 carts** and **6,848,824 purchases**. Views are not OTTO clicks.
- Arithmetic sum of both real archives: **628,425,832 rows** from **two different populations**; they are not a single clickstream.
- Stress test: **1,083,580,480 derived rows**, five scenarios created from OTTO; they do not represent new users or events.

| REES46 file | Events | Views | Carts | Purchases | Compressed |
|---|---:|---:|---:|---:|---:|
| 2019-Oct | 42,448,764 | 40,779,399 | 926,516 | 742,849 | 1.62 GiB |
| 2019-Nov | 67,501,979 | 63,556,110 | 3,028,930 | 916,939 | 2.69 GiB |
| 2019-Dec | 67,542,878 | 62,986,067 | 3,394,763 | 1,162,048 | 2.75 GiB |
| 2020-Jan | 55,967,041 | 52,490,785 | 2,641,249 | 835,007 | 2.23 GiB |
| 2020-Feb | 55,318,565 | 51,232,669 | 2,885,608 | 1,200,288 | 2.19 GiB |
| 2020-Mar | 56,341,241 | 52,347,910 | 2,968,397 | 1,024,934 | 2.25 GiB |
| 2020-Apr | 66,589,268 | 62,353,909 | 3,268,600 | 966,759 | 2.73 GiB |

The compressed sizes come from the publisher's files. The loader read each gzip to the end, validated the CSV and cross-checked its rows with ClickHouse.

## Measured queries

The benchmark disabled the query cache. The OTTO queries were run three times and the median is shown; the other queries, once. The daily result of the archive and of the aggregate was compared row by row before saving the report.

| Query | Seconds | Rows read | Bytes read |
|---|---:|---:|---:|
| Raw OTTO, day/type | 5.8908 | 216,716,096 | 1.82 GiB |
| Aggregated OTTO, day/type | 0.2113 | 87 | 0.98 KiB |
| REES46 October, types | 0.2378 | 42,448,764 | 121.45 MiB |
| Derived scenarios | 1.4357 | 1,083,580,480 | 826.74 MiB |

On this machine and for this question, the aggregate was **27.9 times** faster by median time. The figure is local and depends on storage, the operating system cache and concurrent load; the main contrast is also the rows and bytes read.

## Table sizes

| Table | Rows | Compressed on disk |
|---|---:|---:|
| `otto_archive` | 216,716,096 | 2.59 GiB |
| `otto_daily_rollup` | 87 | 0.98 KiB |
| `otto_scale_benchmark` | 1,083,580,480 | 12.11 GiB |
| `rees46_events` | 411,709,736 | 11.05 GiB |

Additional conditions: background merges of REES46 and of the derived table were paused during these measurements; there were no active merges at the start. They are re-enabled when the verification finishes.

## Read plan for REES46 October

```text
Expression ((Project names + Projection))
  Aggregating
    Expression (Before GROUP BY)
      Expression ((WHERE + Change column names to column identifiers))
        ReadFromMergeTree (delivery.rees46_events)
        Indexes:
          MinMax
            Keys:
              event_date
            Condition: and((event_date in (-Inf, 18200]), (event_date in [18170, +Inf)))
            Parts: 2/1235
            Granules: 5183/50981
          Partition
            Keys:
              toYYYYMM(event_date)
            Condition: and((toYYYYMM(event_date) in (-Inf, 201911]), (toYYYYMM(event_date) in [201910, +Inf)))
            Parts: 2/2
            Granules: 5183/5183
          PrimaryKey
            Keys:
              event_date
            Condition: and((event_date in (-Inf, 18200]), (event_date in [18170, +Inf)))
            Parts: 2/2
            Granules: 5183/5183
            Search Algorithm: binary search
            Ranges: 2
```

Environment: local Docker ClickHouse 25.8; one node; query cache disabled; three warm runs for OTTO queries, one run for larger scans.

**Interpretation:** OTTO contains clicks; REES46 contains product views, carts and purchases. The stress table contains labelled copies. The replay inserts historical events today, without changing their original date.
