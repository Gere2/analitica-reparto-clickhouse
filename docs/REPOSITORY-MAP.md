# Repository map

Updated for the final delivery on 15 November 2026. Start with [FINAL-DELIVERY.md](FINAL-DELIVERY.md). The approved presentation has 14 slides and four speakers; old lab/slide files remain historical material.

## Runtime paths

| Generation | Main files and database | Status |
|---|---|---|
| Delivery Atlas | `compose.yaml --profile atlas`, `atlas/`, `web/atlas-dashboard.*`, `web/analytics.*`, `web/delivery.*`; `delivery_atlas` plus public `delivery` tables | Current project, port 8001 |
| Clickstream Lab | `dashboard.py`, lab pages/loaders, `delivery` historical tables | Earlier large-dataset experiments, port 8000 |
| First Flask/Grafana app | `app/`, `docker-compose.yml`, original SQL/app files | Historical; not the Atlas reproduction route |

Do not start the earlier stack alongside Atlas without checking its project/container/port overlap. The Atlas installation does not require the optional massive datasets.

## Application and configuration

| Path | Purpose |
|---|---|
| `atlas/server.py` | HTTP routes, simulation controls, queue and batch publisher |
| `atlas/store.py` | Durable SQLite queue, fingerprints, retries and backpressure |
| `atlas/clickhouse.py` | HTTP SQL, schema startup, batch publication and operational reads |
| `atlas/analytics.py`, `atlas/analytics_filters.py` | Fixed Journey/Performance/historical queries, bounded reads and filter validation |
| `atlas/contract.py`, `operations.py` | Event and operational contracts |
| `atlas/commerce.py`, `customer_runtime.py`, `customer_agent.py`, `simulation.py`, `catalog.py` | Fictional shopping, rule/local-model decisions, fleet and catalog |
| `atlas/share.py` | Authenticated read-only gateway |
| `web/atlas-dashboard.*`, `web/atlas-map.js` | Operations, provenance switches and real Madrid basemap with fictional tracking |
| `web/analytics.*` | English Customer Journey, Performance and public dataset explorers |
| `web/delivery.*` | Local mini-app and tracking |
| `web/vendor/leaflet/` | Local map library/assets and license |
| `api/proxy.js`, `vercel.json`, `.vercelignore` | Server-side shared GET proxy and static deployment |
| `compose.yaml`, `Dockerfile.atlas`, `clickhouse-config.xml` | Main host services, named data/queue volumes and database settings |
| `compose.share.yaml`, `Dockerfile.share` | Gateway and tunnel services |

## SQL

| File | Applied objects |
|---|---|
| `sql/atlas.sql` | `app_events`, exact daily ID states, materialized view and read view |
| `sql/atlas_operations.sql` | Versioned catalog, GPS/order histories and latest states/views |
| `sql/atlas_agents.sql` | Customer decisions, purchases and latest customer state; browsing migration |
| `sql/atlas_miniapp.sql` | Additive manual-purchase provenance migration |
| `sql/atlas_consultas.sql`, `atlas_tracking_consultas.sql` | Illustrative analytical queries |
| `sql/criteo.sql`, `schema.sql`, `eleme.sql` | Public sources and historical lab objects |
| `sql/propuesta_delivery.sql` | Initial proposal, not applied by Atlas |

## Scripts and tests

| Path | Purpose |
|---|---|
| `scripts/atlas.py`, `operations.py` | Reproducible browsing/operational fixtures and status |
| `scripts/check_atlas.py`, `check_operations.py`, `check_customer_agent.py`, `check_traffic.py` | Checks that intentionally write labelled host data; operation check overwrites its evidence JSON |
| `scripts/crud_demo.py` | Scratch-row INSERT/SELECT/UPDATE/DELETE, with temporary legacy merge controls |
| `scripts/export_run.py`, `runs_report.py`, `simulation_watchdog.sh` | Verified run exports, manifest report and guarded generation recovery |
| `scripts/gps_benchmark.py`, `gps_benchmark_lab.py`, `gps_benchmark_report.py` | Isolated GPS loading, equal-answer repeated measurement and reports |
| `benchmarks/gps/` | Separate loopback port-18124 project/volume, complete Atlas bootstrap, read-only benchmark user and explicit resource budget |
| `scripts/build_shared.mjs`, `start_shared_demo.py` | Shared static build and tunnel/deployment helpers |
| Dataset loaders and historical benchmark/report scripts | Optional earlier lab; use the corresponding source guide |
| `tests/*.py`, `tests/*.cjs` | Queue/contracts, commerce/tracking, analytics, export/watchdog, isolated GPS, UI/map and public proxy behavior |

Run `python3 -m unittest discover -s tests -v` and `node --test tests/*.cjs`. Optional SQL integration tests need the documented disposable ClickHouse variables and are skipped otherwise. Do not point test/load tools at the live demo as a shortcut. [FINAL-VALIDATION.md](FINAL-VALIDATION.md) records the release checks rather than maintaining changing per-file test counts here.

## Documentation and presentation

| Entry | Scope |
|---|---|
| [FINAL-DELIVERY.md](FINAL-DELIVERY.md) | Single delivery entry point, reproduction and runtime status |
| [ASSIGNMENT.md](ASSIGNMENT.md) | Requirement mapping and real remaining operating/rehearsal checks |
| [ATLAS-INSTALL.md](ATLAS-INSTALL.md), [DEMO-GUIDE.md](DEMO-GUIDE.md) | Current installation and prepared demo route |
| [FUNDAMENTALS.md](FUNDAMENTALS.md), [APPLIED-THEORY.md](APPLIED-THEORY.md), [DATABASE-STRUCTURE.md](DATABASE-STRUCTURE.md) | Current ClickHouse theory/model and tradeoffs |
| [ATLAS-INFRASTRUCTURE.md](ATLAS-INFRASTRUCTURE.md), [AI-CUSTOMERS.md](AI-CUSTOMERS.md), [MINIAPP.md](MINIAPP.md) | Pipeline, local agents and mini-app contracts |
| [CLICKHOUSE-DASHBOARDS.md](CLICKHOUSE-DASHBOARDS.md) | SQL, cohorts, metadata and measurement/cache definitions |
| [GPS-BENCHMARK.md](GPS-BENCHMARK.md) | Completed isolated comparison and reproducible commands |
| [SIMULATION-RUNS.md](SIMULATION-RUNS.md), [INVENTORY-2026-11-15.md](INVENTORY-2026-11-15.md), [HOST-STATUS-2026-11-15.md](HOST-STATUS-2026-11-15.md) | All 21 small manifests, live inventory and dated host/public checks |
| [TEAM-INSTALL-TESTS.md](TEAM-INSTALL-TESTS.md), [FINAL-VALIDATION.md](FINAL-VALIDATION.md) | Dated reproduction and release verification |
| [PRESENTATION.md](PRESENTATION.md), [DEFENCE-NOTES-EN.md](DEFENCE-NOTES-EN.md) | Four-speaker route and technical clarifications alongside the frozen deck/script |
| [AI-USE-AND-SOURCES.md](AI-USE-AND-SOURCES.md) | Attribution, data sources, software/media and AI assistance |
| [SHARING-VERCEL.md](SHARING-VERCEL.md) | Read-only host gateway, origin and production proxy |
| [PROJECT-DECISIONS.md](PROJECT-DECISIONS.md), [history/README.md](history/README.md) | Project selection and historical documents |

The approved files are `presentaciones/final-2026-11-11/Delivery-Atlas.html`, `SCRIPT-EN.md` and `gps-phases.csv`. Older `.pptx`, content JSON and presenter notes retain their bytes but are not the current route, even where an older filename contains FINAL. Screenshots and `evidencia-*.json` are dated records; they are not today's live counters.

## Data and package output

Large datasets, run archives, queue state, secrets and build caches stay outside version control. Export/report paths live under `data/`; completed `.partial-*` attempts must not be counted as saved runs. Package outputs are separate from source and identify their commit/hashes. The final ZIP includes source/configuration as well as the approved deck and Markdown guides; it excludes private host files and massive inputs.
