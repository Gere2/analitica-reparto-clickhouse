# ClickHouse dashboards

27 October 2026. ClickHouse is the subject of the project. Delivery Atlas supplies an event workload for explaining its analytical behaviour.

The canonical English portal is `/analytics.html?panel=journey`. The live operations dashboard and Madrid map remain at `/?view=simulated#tracking`. Older standalone lab HTML remains in the repository as historical source. The portal provides its analyses through the Atlas API, with one navigation and visual system.

| Dashboard | ClickHouse source | Database mechanism |
|---|---|---|
| Live operations and map | Position/order histories and latest-state views | Append history, `argMax` states, current-state reads |
| Customer Journey | `delivery_atlas.customer_activity FINAL` | Ordered sessions with `windowFunnel`, exact counts, time grouping |
| ClickHouse Performance | `system.parts`, `system.tables`, `system.query_log`, detail and aggregate tables | Engines, sort keys, physical parts, compression and query work |
| OTTO Events | `delivery.otto_archive` | Column selection and large historical aggregations |
| Marketplace Trends | `delivery.rees46_events` | Monthly filtering, categories and brands |
| Catalog Explorer | `delivery.glovo_products` | Location filters and grouped catalog counts |
| Recommendation Samples | `delivery.eleme_samples` | Relative days, hours and sample labels |
| Advertising Groups | `delivery.criteo_uplift` | Observed group summaries with the publisher's privacy limitation |

Every view exposes fixed, parameterised SQL and ClickHouse JSON statistics: elapsed time, rows read and bytes read. Exact chart values are available in accessible tables. Browser requests accept no arbitrary SQL or table names.

## Customer Journey

The API selects the active simulation run, or an explicit UUID. The cohort contains distinct sessions with an observed `session_started` action. The funnel then requires `open_product`, `add_to_cart` and `checkout` in order within 30 minutes. This is different from dividing unrelated event totals.

ClickHouse 25.8 does not accept this table's `DateTime64` directly as the first `windowFunnel` argument. The query converts it with `toUInt64(toUnixTimestamp64Milli(event_time))` and uses **1,800,000 milliseconds**. `strict_increase` preserves increasing millisecond timestamps. Equal timestamps do not advance multiple steps.

`FINAL` removes replacement copies before the funnel. Retries preserve the logical session count. Unfinished progression differs from an explicit `abandon` action. Sessions without an observed start appear as exclusions. Manual miniapp browsing is a different stream and is not included.

AI classification follows the existing contract: a customer counts as AI after a recorded model decision in that run. Configured customers waiting for that first decision can still count as simulated. Charts use separate queries while ingestion continues, so totals can advance between reads. Minute-level activity is not a cohort conversion rate.

## ClickHouse Performance

The inventory reads active parts in the two project databases. Physical counts include detail and aggregate storage. They are not one combined business-event total. Compression is uncompressed column bytes divided by compressed column bytes, separate from total disk size.

The history groups completed initial `SELECT` queries involving project databases during the last hour by normalised query hash and source tables. It shows execution counts, median and slowest duration, average rows read and peak memory. It does not expose arbitrary historical SQL text. Logging can be unavailable or not yet flushed, which differs from zero latency.

The comparison button runs two fixed reads:

- **Atlas:** exact counts by section and event type for the latest loaded synthetic Madrid date. Both reads include every run on that date because `app_daily_rollup` has no run dimension. Detail uses `uniqExact(event_id)` after `FINAL`; the prepared view merges exact ID states.
- **OTTO:** daily counts by event type over the loaded archive and its matching daily rollup.

The API compares complete result rows before displaying a ratio. A mismatch suppresses that ratio. For a stable rehearsal comparison, stop producers on the host and wait for an empty queue.

Each design gets one read, detail first, with SQL query cache disabled. Queries use an 8-second / 256-MiB per-read budget and a 20-second budget across analytical reads in a response. System caches, order and concurrent work still affect observations. This live comparison is separate from the older experiments in `RESULTS.md` and `ATLAS-RESULTS.md`. It does not compare database products.

## Deployment dependencies

The shared build includes analytics HTML, CSS and JavaScript alongside the map and local Leaflet assets. Four new GET routes cross the existing authenticated gateway and Vercel proxy: `journey`, `performance`, `benchmark` and `historical`. The gateway image now packages the shared analytical-filter validator as an `atlas` module. Rebuild **both `atlas` and `share-gateway`**.

Existing token and tunnel configuration can remain unchanged. A frontend-only update does not add routes to an older backend. Opening a view never downloads a dataset. Missing tables produce an explicit host-dependency message. Large archive loads remain deliberate, optional host operations.

Shared cache windows are 5 seconds for Journey, 10 for Performance and 60 for historical views and comparisons. A refresh can reuse the same dated result during that window. Public access stays GET-only. Simulation controls, checkout and CRUD stay on the host.

## Validation

The disposable ClickHouse 25.8 tests cover wrong event order, equal timestamps, the 30-minute window, duplicate records, another run, missing starts, AI classification, empty cohorts, historical SQL and filters, physical metadata and a deliberately mismatched aggregate.

Browser verification uses the real API and disposable database with a visible validation banner. Seeded records do not represent production source loads or actual model calls. Production availability still depends on Anuar's running host and its loaded datasets.

References: [windowFunnel](https://clickhouse.com/docs/sql-reference/aggregate-functions/parametric-functions#windowfunnel), [query log](https://clickhouse.com/docs/reference/system-tables/query_log), [parts](https://clickhouse.com/docs/reference/system-tables/parts), [Criteo data card](https://huggingface.co/datasets/criteo/criteo-uplift#privacy).
