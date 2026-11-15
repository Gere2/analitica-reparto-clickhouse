# Sources and AI assistance

## Project and measurement sources

The applied model is defined in `sql/atlas.sql`, `atlas_operations.sql`, `atlas_agents.sql` and `atlas_miniapp.sql`; the Python API, publisher, simulation and analytical readers are in `atlas/`. Tests and dated installation/integration records support their documented behavior. [PROJECT-DECISIONS.md](PROJECT-DECISIONS.md) preserves the reasons for selecting the fictional platform and keeping public populations separate.

The completed GPS campaign is Anuar's 6 November experiment, with a frozen fictional export, repeated measurements and matching query IDs. Its original ZIP, source hash, commands, environment and measurement definitions are linked in [GPS-BENCHMARK.md](GPS-BENCHMARK.md). [HOST-STATUS-2026-11-15.md](HOST-STATUS-2026-11-15.md) attributes the later host/archive inventory to his dated report. Validation fixtures and historical tests are not substituted for that measured campaign.

## Public datasets

| Source | Meaning and project use | Reference |
|---|---|---|
| Criteo Uplift v2.1 | Public advertising experiment, separate from platform purchases | [Dataset card](https://huggingface.co/datasets/criteo/criteo-uplift), `scripts/criteo.py`, `sql/criteo.sql` |
| Glovo FooDI-ML | Public catalog, not observed orders or clicks | [Project data guide](GLOVO.md), `scripts/glovo.py` |
| OTTO Recommender Systems | Historical clicks/carts/orders used in the earlier lab | [Original dataset](https://github.com/otto-de/recsys-dataset), [legacy source guide](LEGACY-DATASETS.md) |
| REES46 | Historical marketplace events used in the earlier lab | [Source directory](https://data.rees46.com/), [legacy source guide](LEGACY-DATASETS.md) |
| Ele.me | Recommendation samples from Tianchi used in the earlier lab | [Access and interpretation](ELEME.md) |

Dataset loaders/source documents record their checks and usage conditions. Read the original terms before redistributing downloaded files. The delivery package contains code, small measurement evidence and source links, not the massive public datasets. Synthetic GPS/orders are fictional and labelled as such.

## AI assistance and human responsibility

Codex/ChatGPT assistance was used for implementation, code review, documentation, slide production and validation workflows. Claude assistance was also used for the mini-app, assignment checklist, Windows installation records, theory/English material and host-side work, as recorded in the dated project history. Earlier cover illustrations include AI-generated artwork. Exact model identifiers for every earlier session were not recorded; no version is invented here.

Geremi coordinated the project and integration; Anuar operated the host and supplied the GPS campaign and archive reports; Echenique and Juanro have the presentation/documentation responsibilities recorded in [PRESENTATION.md](PRESENTATION.md) and the final demo guide. AI assistance does not replace explaining the SQL, inspecting source semantics or verifying experimental answers. Claims remain tied to code, recorded tests, raw reports and the stated conditions.

The local Qwen/Ollama customers are a separate part of the application: they emit bounded fictional decisions that Python validates. Their model-call budget and `decision_mode` distinguish them from rule-driven traffic. They are not the source of all the generated rows or of the public datasets.

## Software and media attribution

The map retains Leaflet's license in `web/vendor/leaflet/LICENSE` and OpenStreetMap attribution in its interface. The prepared HTML embeds its font license/source media and remains unchanged. Preserve those notices when redistributing the package. No private token or browser authentication state belongs in the archive.

## Technical references

- [ClickHouse introduction and SQL/OLAP model](https://clickhouse.com/docs/get-started/about/intro).
- [MergeTree](https://clickhouse.com/docs/engines/table-engines/mergetree-family/mergetree), [ReplacingMergeTree](https://clickhouse.com/docs/engines/table-engines/mergetree-family/replacingmergetree) and [AggregatingMergeTree](https://clickhouse.com/docs/engines/table-engines/mergetree-family/aggregatingmergetree).
- [INSERT guarantees](https://clickhouse.com/docs/concepts/features/operations/insert/transactions) and [windowFunnel](https://clickhouse.com/docs/sql-reference/aggregate-functions/parametric-functions#windowfunnel).
- [Query log](https://clickhouse.com/docs/reference/system-tables/query_log) and [active parts](https://clickhouse.com/docs/reference/system-tables/parts).
- [PostgreSQL index-only scans](https://www.postgresql.org/docs/current/indexes-index-only-scans.html).
