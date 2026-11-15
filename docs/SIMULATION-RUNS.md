# Simulation runs

This detailed log uses all 21 [committed run manifests](run-manifests/) supplied by Anuar in PR #13. It was rendered with `scripts/runs_report.py` from those `summary.json` records; the host exporter keeps the originals under `data/runs/`. Each run was exported with `python scripts/export_run.py <run_id>` after stopping it and waiting for the queue to reach pending 0: five gzip CSV files (one per table, `FINAL`, ordered by `event_time`) plus `summary.json`.

**21 runs, 37,310,637 rows, 2.90 GB compressed.** Compressed CSV files are not in Git. The first 19 published archives are in the [GitHub release](https://github.com/AnuarH16/analitica-reparto-clickhouse/releases/tag/simulation-runs-2026-11-01); the two 11 November exports remain on the host unless separately published. All the data is fictional and synthetic; the downloaded Criteo and Glovo datasets are not included.

Times are UTC. Event span is last minus first event, including any pauses; it is not continuous uptime. Customers and couriers are the distinct IDs that appear in the run; AI customers are those with at least one decision taken by the local model (`decision_mode = 'ollama'`), which stops after 120 model calls per run.

| Run | Start (UTC) | Event span | Customers (AI) | Couriers | GPS positions | Customer actions | Browsing events | Order events | Orders | Delivered | Total rows |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `2026-10-19_dde04b4a` | 2026-10-19 14:58 | 9 min | 24 (0) | 12 | 3,084 | 1,080 | 808 | 375 | 68 | 56 | 5,415 |
| `2026-10-19_6f5d9c10` | 2026-10-19 15:07 | < 1 min | 24 (0) | 12 | 96 | 108 | 84 | 6 | 3 | 0 | 297 |
| `2026-10-21_60a17065` | 2026-10-21 14:12 | 8 h 07 min | 24 (0) | 12 | 68,892 | 23,653 | 17,516 | 8,465 | 1,421 | 1,412 | 119,947 |
| `2026-10-21_1bcd5235` | 2026-10-21 14:50 | 2 min | 12 (3) | 6 | 288 | 134 | 103 | 32 | 8 | 0 | 565 |
| `2026-10-21_ec718664` | 2026-10-21 14:54 | 58 min | 12 (3) | 6 | 10,452 | 3,592 | 2,650 | 1,159 | 194 | 191 | 18,047 |
| `2026-10-22_2bf28040` | 2026-10-21 22:22 | 1 h 06 min | 12 (3) | 12 | 23,868 | 4,131 | 3,053 | 1,383 | 232 | 227 | 32,667 |
| `2026-10-22_1c7d14ad` | 2026-10-22 07:22 | 3 min | 12 (3) | 12 | 936 | 244 | 182 | 70 | 16 | 7 | 1,448 |
| `2026-10-22_b0ff283b` | 2026-10-22 07:24 | 4 h 16 min | 100 (3) | 50 | 384,650 | 145,792 | 108,143 | 47,076 | 7,876 | 7,800 | 693,537 |
| `2026-10-28_a4fa27e7` | 2026-10-28 09:32 | 44 min | 100 (3) | 50 | 66,300 | 25,203 | 18,719 | 8,077 | 1,377 | 1,300 | 119,676 |
| `2026-10-28_01b38d23` | 2026-10-28 10:17 | 1 h 56 min | 100 (3) | 50 | 174,700 | 66,409 | 49,231 | 21,358 | 3,577 | 3,527 | 315,275 |
| `2026-10-28_87fb364b` | 2026-10-28 14:50 | 1 h 16 min | 100 (3) | 50 | 88,250 | 33,728 | 25,024 | 10,850 | 1,827 | 1,777 | 159,679 |
| `2026-10-28_a12236a9` | 2026-10-28 16:06 | 44 h 01 min | 100 (3) | 50 | 467,650 | 178,177 | 132,174 | 57,732 | 9,697 | 9,620 | 845,430 |
| `2026-10-31_4f297d43` | 2026-10-31 15:05 | 8 h 06 min | 500 (3) | 150 | 4,371,300 | 1,175,872 | 875,118 | 271,406 | 45,397 | 45,150 | 6,739,093 |
| `2026-10-31_6bf38221` | 2026-10-31 15:10 | 8 h 01 min | 500 (0) | 150 | 4,328,250 | 1,163,808 | 866,103 | 268,632 | 44,950 | 44,700 | 6,671,743 |
| `2026-10-31_ce8625ad` | 2026-10-31 23:11 | 1 min | 500 (0) | 150 | 11,550 | 4,896 | 3,884 | 1,000 | 400 | 0 | 21,730 |
| `2026-11-01_2d08b7a9` | 2026-11-01 16:20 | 23 min | 500 (3) | 150 | 206,250 | 57,003 | 42,522 | 13,147 | 2,347 | 2,100 | 321,269 |
| `2026-11-01_31fdac6e` | 2026-11-01 16:20 | 23 min | 500 (0) | 150 | 206,100 | 56,570 | 42,200 | 13,126 | 2,350 | 2,100 | 320,346 |
| `2026-11-03_70861ccd` | 2026-11-03 02:20 | 11 h 05 min | 500 (3) | 150 | 5,988,150 | 1,610,503 | 1,198,489 | 371,796 | 62,196 | 61,800 | 9,231,134 |
| `2026-11-03_592f4a72` | 2026-11-03 02:20 | 11 h 05 min | 500 (0) | 150 | 5,988,000 | 1,609,204 | 1,197,495 | 371,637 | 62,179 | 61,800 | 9,228,515 |
| `2026-11-11_b6a982ca` | 2026-11-11 17:33 | 4 h 37 min | 500 (0) | 150 | 796,950 | 216,620 | 161,401 | 51,300 | 8,778 | 8,400 | 1,235,049 |
| `2026-11-11_f1dee148` | 2026-11-11 17:34 | 4 h 37 min | 500 (3) | 150 | 793,200 | 215,978 | 160,890 | 50,924 | 8,783 | 8,400 | 1,229,775 |

Column to table: GPS positions = `courier_positions`, customer actions = `customer_activity`, browsing events = `app_events`, order events = `order_events`, orders = `customer_orders`.

The [15 November inventory](INVENTORY-2026-11-15.md) reports **37,310,669 logical rows** in ClickHouse: the 37,310,637 archived rows plus **32 browsing events without a run ID**. The five per-table manifest sums match that inventory after this explicit difference. The [host record](HOST-STATUS-2026-11-15.md) distinguishes reported CSV verification from independent manifest/public checks.

## Notes on the runs

- **19–22 October:** first runs with 24 simulated customers and 12 couriers, then hybrid runs (3 AI customers + simulated traffic). Short runs were tests of the AI agents or were stopped to update the server.
- **28–30 October:** hybrid runs with 100 customers and 50 couriers prepared for the checkpoint presentation; `2026-10-28_a12236a9` spans almost two days, including a verified 17 h 56 min GPS gap; do not present that span as continuous generation.
- **31 October (big-data run):** two Atlas APIs writing to the same ClickHouse for 8 hours, each with 500 customers, 150 couriers and a 1-second tick: `2026-10-31_4f297d43` on port 8001 (hybrid, seed 31) and `2026-10-31_6bf38221` on a second container on port 18001 (traffic only, seed 62). Together about 13.4 million rows, roughly 1.7 million per hour. ClickHouse used about 40 % CPU when checked, and both queues drained to 0 when stopped. `scripts/simulation_watchdog.sh` was ready to reopen Docker Desktop and restart the runs, but no restart was needed. `2026-10-31_ce8625ad` is a one-minute run that the watchdog started by mistake after the planned stop.
- **1 November:** the same two-API setup (`2026-11-01_2d08b7a9` hybrid, `2026-11-01_31fdac6e` traffic) stopped after 23 minutes, when Docker Desktop closed and the watchdog closed with the session that ran it. The queues still published everything once Docker was back.
- **3 November (largest run):** the same setup again for about 11 hours, from 02:20 to 13:25 UTC: `2026-11-03_70861ccd` (hybrid, seed 1103) and `2026-11-03_592f4a72` (traffic only, seed 1104), together about 18.5 million rows. The watchdog ran the whole time without needing to restart anything, and the rows exported for each run equal the events its API accepted.
- **11 November:** hybrid `f1dee148` and traffic `b6a982ca` added 1,229,775 and 1,235,049 rows respectively. Their first/last event spans are in the table; Docker closed at 22:11 UTC. The 50-million generation milestone was not reached.
- The second API was a manual `docker run` of the Atlas image on port 18001 with its own queue volume. From Git Bash, prefix that command with `MSYS_NO_PATHCONV=1`; otherwise Git Bash rewrites `ATLAS_QUEUE_PATH=/state/outbox.sqlite` to a Windows path and the queue is not kept on the volume.
