# Project brief and delivery checklist

Updated 15 November 2026. This maps the BD2 project requirements to the submitted Atlas code and documentation. The original professor's brief is summarised rather than republished. [Start with the final delivery index](FINAL-DELIVERY.md).

## Assignment scope

The group researches its assigned technology, ClickHouse, explains its fundamentals and demonstrates a practical use case. The presentation date is 15 November 2026. The slot is **20 minutes including the demo, followed by about 10 minutes for questions**. Required files are the presentation, Markdown documentation with installation and demo instructions, and supporting code/resources sufficient for another student to reproduce the example.

Minimum content covers context/motivation, characteristics, architecture/operation, live demonstration and critical reflection. Multiple nodes and a cross-database benchmark are not mandatory in the recorded brief. A qualitative comparison is included; PostgreSQL/DuckDB timings remain future work.

## Requirement mapping

| Requirement | Current material | Completion and scope |
|---|---|---|
| Context and motivation | [Fundamentals](FUNDAMENTALS.md), [project decisions](PROJECT-DECISIONS.md), slides 1–2/5–6 | Implemented fictional delivery workload; public and generated data stay distinct |
| Type, characteristics and analytical use | [Fundamentals](FUNDAMENTALS.md), slides 3–4 | Column-oriented SQL/OLAP; clarifications accompany the retained checkpoint wording |
| Model, physical order, partitions and views | [Current structure](DATABASE-STRUCTURE.md), four `sql/atlas*.sql` files | Applied Atlas schema, not the initial `delivery_proposal` |
| Consistency, availability and scaling | [Applied theory](APPLIED-THEORY.md) and [fundamentals](FUNDAMENTALS.md) | One node demonstrated; replicas/shards explained, not deployed |
| Step-by-step installation | [ATLAS-INSTALL.md](ATLAS-INSTALL.md) | Small path without large datasets; Anuar reported a fresh Windows test on 11 November |
| Programming-language integration | `atlas/`, Python scripts and HTTP/SQL | Durable queue, batch publication, typed reads and bounded analytical requests |
| Representative live demo | [DEMO-GUIDE.md](DEMO-GUIDE.md), operations/map, Journey, Performance, Criteo and Glovo | Implemented; local host checks reported by Anuar and five public data routes independently validated after reconnection on 15 November |
| Insert, read, update and delete | `scripts/crud_demo.py`, [demo guide](DEMO-GUIDE.md) | Scratch-table mutations and readback; assigned one-minute slot after slide 14, with host rehearsal to confirm |
| Data provenance | [Current structure](DATABASE-STRUCTURE.md), [host inventory](HOST-STATUS-2026-11-15.md), [source record](AI-USE-AND-SOURCES.md) | Fictional platform data, public advertising and catalog rows have separate meanings |
| Measurement and critical reflection | [GPS-BENCHMARK.md](GPS-BENCHMARK.md), [fundamentals](FUNDAMENTALS.md), slides 11–14 | Equal answers, repeated reader levels, raw evidence and limits; no cross-engine or universal-capacity claim |
| Reproduction and tests | [Installation records](TEAM-INSTALL-TESTS.md), [integration review](INTEGRATION-REVIEW-2026-11-13.md) | 82 Python and 33 JavaScript tests recorded on 13 November, including real ClickHouse integration; final packaging checks recorded separately |
| Sources and AI assistance | [AI-USE-AND-SOURCES.md](AI-USE-AND-SOURCES.md) | Source/measurement attribution and human responsibility for generated work |

## Deliverables

| Item | Entry point |
|---|---|
| Approved presentation and English script | [14-slide HTML](../presentaciones/final-2026-11-11/Delivery-Atlas.html), [SCRIPT-EN.md](../presentaciones/final-2026-11-11/SCRIPT-EN.md) |
| Speaking allocation and timing | [PRESENTATION.md](PRESENTATION.md): four speakers, 14:35 prepared core |
| Technical documentation | [FUNDAMENTALS.md](FUNDAMENTALS.md), [DATABASE-STRUCTURE.md](DATABASE-STRUCTURE.md), [ATLAS-INFRASTRUCTURE.md](ATLAS-INFRASTRUCTURE.md), [APPLIED-THEORY.md](APPLIED-THEORY.md) |
| Installation and demo | [ATLAS-INSTALL.md](ATLAS-INSTALL.md), [DEMO-GUIDE.md](DEMO-GUIDE.md) |
| Results and operating record | [GPS-BENCHMARK.md](GPS-BENCHMARK.md), [SIMULATION-RUNS.md](SIMULATION-RUNS.md), [HOST-STATUS-2026-11-15.md](HOST-STATUS-2026-11-15.md) |
| Code/configuration/assets | `atlas/`, `web/`, `api/`, `sql/`, `scripts/`, `benchmarks/gps/`, `tests/`, Compose, Dockerfiles and Leaflet/license |

The delivery archive must contain the application/SQL/configuration as well as the deck and guides. The 13 November email bundle was rehearsal/documentation material and did not contain all source code. Private credentials, Docker volumes and massive datasets are excluded; loaders/source links and small evidence reports are retained.

## Final rehearsal and runtime checks

The prepared HTML/script remain unchanged. Allocate 14:35 to that route, 2:00 to Journey/Performance after slide 8, 1:00 to CRUD after slide 14 and 2:25 to transitions/buffer. The complete four-person rehearsal must fit 20 minutes. The checkpoint closing on slide 10 leads into the experiment appendix.

Anuar confirms that the integrated host and the offline presentation are available. The earlier failed tunnel was recreated, and the production connection was restored with five public data reads returning 200 at 19:28 UTC on 15 November. The host/tunnel must remain running for the talk; recheck before speaking and retain the local/recorded fallback. Deployment state and actual data access are recorded separately in [FINAL-VALIDATION.md](FINAL-VALIDATION.md).

Anuar has provided independent Windows installation evidence. Echenique's additional installation/CRUD record and the complete group rehearsal still need confirmation; their absence is not presented as a failed test. The 21 run manifests and dated inventory are included; their checked sums distinguish the archive total from the 32 additional browsing events without a run ID.

Historical plans, validation reports and slide decks retain their original dates and results. They are labelled as historical and do not override the current index, guides, schema or four-speaker allocation.
