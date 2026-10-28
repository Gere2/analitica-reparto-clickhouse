# Project brief and delivery checklist

Date: 19 October 2026. This document summarizes, in our own words, what the BD2 final project brief asks for. For each requirement it shows where it is covered in the repository and its status. The original text belongs to the professor and is not copied here because the repository is public.

**Statuses:** **Done** (covered and documented), **Partial** (exists, but needs completing or updating), **Missing** and **Optional**.

## What the brief asks for

Each group researches a NoSQL database in depth, explains its fundamentals and shows a practical use case that highlights its advantages.

- **Presentation date:** 15 November 2026.
- **Format:** 30 minutes per group: 20 minutes of technical presentation, with the live demo included, and about 10 minutes of questions.
- **Deliverables:**
  1. The presentation with the demo.
  2. `.md` documents with the documentation, step-by-step installation and a guide to run the demo. They must be enough for another student to reproduce the demo and understand the fundamentals.
  3. Any additional files needed: code, images, `yml`, etc.
- **Minimum content:** context and motivation, main characteristics, architecture and operation, live demo and critical reflection. The brief's sub-points are suggestions; going further is valued.
- **Demo ideas it suggests:** a mini-app using the database as backend, a typical data flow, a real-time scenario or a visualization with filters and dashboards. Delivery Atlas combines all four.

## Decisions confirmed with the professor

| Topic | Decision |
|---|---|
| Technology | **ClickHouse**, assigned by the professor. This resolves the question about the "Personas" section raised in [TEAM-STATUS.md](TEAM-STATUS.md) and [THEORY-REVIEW.md](THEORY-REVIEW.md). The presentation should still explain the nuance: it is a columnar OLAP store that uses SQL ([FUNDAMENTALS.md](FUNDAMENTALS.md)). |
| Duration | 20 minutes of presentation **including the demo** and about 10 minutes of questions. |
| Multiple nodes | **Optional.** No cluster is set up; we explain how ClickHouse replicates and distributes data. |
| Use case | Fictional food-delivery platform with its analytics infrastructure ([TEAM-STATUS.md](TEAM-STATUS.md)). |

## Checklist by section

### 1. Context and motivation

| Requirement | Where | Status |
|---|---|---|
| Type of database | [FUNDAMENTALS.md](FUNDAMENTALS.md), "Fit with the BD2 course"; [PRESENTATION.md](PRESENTATION.md), "Is it NoSQL?" | Done |
| Problems it solves better than other databases | [FUNDAMENTALS.md](FUNDAMENTALS.md), "Experiment that justifies ClickHouse" and "Comparison with a transactional database" | Done |
| Scenarios where it is commonly used | [FUNDAMENTALS.md](FUNDAMENTALS.md), "Where ClickHouse is used": use-case families from the official documentation and companies from the official list of adopters, including some delivery companies | Done |

### 2. Main characteristics

| Requirement | Where | Status |
|---|---|---|
| Data model and representation | [FUNDAMENTALS.md](FUNDAMENTALS.md), "Data model"; [DATABASE-STRUCTURE.md](DATABASE-STRUCTURE.md); [ATLAS-INFRASTRUCTURE.md](ATLAS-INFRASTRUCTURE.md), section 3 | Done |
| Consistency, scalability and availability | [FUNDAMENTALS.md](FUNDAMENTALS.md), "Consistency and availability"; [APPLIED-THEORY.md](APPLIED-THEORY.md), CAP, PACELC, idempotency and fault tolerance in Atlas | Done |
| Replication, partitioning and fault tolerance | [FUNDAMENTALS.md](FUNDAMENTALS.md); [THEORY-REVIEW.md](THEORY-REVIEW.md), "P4"; [ATLAS-RESULTS.md](ATLAS-RESULTS.md), "Integrity and recovery" | Done (explained; running several nodes is optional) |

### 3. Architecture and operation

| Requirement | Where | Status |
|---|---|---|
| Install, deploy or access | [ATLAS-INFRASTRUCTURE.md](ATLAS-INFRASTRUCTURE.md), section 2, for Atlas without large downloads; [INSTALLATION.md](INSTALLATION.md) for the lab with the large datasets | Done. Clean start verified on Windows 11 ([TEAM-INSTALL-TESTS.md](TEAM-INSTALL-TESTS.md)) |
| Main commands and queries | `sql/atlas_consultas.sql`, `sql/atlas_tracking_consultas.sql`, [DEMO.md](DEMO.md), [TRACKING-DEMO.md](TRACKING-DEMO.md) | Done |
| Tools and client libraries | [FUNDAMENTALS.md](FUNDAMENTALS.md), "Interfaces, clients and tools": interfaces and ports, console, `/play` and `/dashboard`, official libraries, Grafana and why Atlas uses HTTP | Done |

### 4. Live demo

| Requirement | Where | Status |
|---|---|---|
| Real or semi-real datasets | OTTO, REES46, Ele.me and Glovo: [README](../README.md) and [RESULTS.md](RESULTS.md). In Atlas, simulated traffic (`synthetic`) and manual actions (`demo_live`); without the Glovo catalog a demo catalog is used | Done. The large datasets are only loaded on Jere's computer; the part that uses them must be run from there |
| Insert, query, update and delete | `scripts/crud_demo.py` on the scratch table `delivery.demo_events`. [TRACKING-DEMO.md](TRACKING-DEMO.md) explains why the history is not modified | Partial: the script works (verified on Windows on 19 October), but it still needs to be fitted into the Atlas demo script ([ATLAS-INFRASTRUCTURE.md](ATLAS-INFRASTRUCTURE.md), section 7) |
| Connection from a programming language | Python API and publisher (`atlas/`); loading and query scripts (`scripts/`) | Done |
| Simple but representative use case | Delivery Atlas: dashboard at `http://127.0.0.1:8001/`, GPS tracking, simulated and AI customers ([AI-CUSTOMERS.md](AI-CUSTOMERS.md)) and the commercial mini-app ([MINIAPP.md](MINIAPP.md)) | Done |
| Multiple nodes | [FUNDAMENTALS.md](FUNDAMENTALS.md) explains `ReplicatedMergeTree`, ClickHouse Keeper and `Distributed` tables | Optional (explained, not set up) |

### 5. Critical reflection

| Requirement | Where | Status |
|---|---|---|
| Strengths and limitations observed | [FUNDAMENTALS.md](FUNDAMENTALS.md), "Data quality and limits"; [APPLIED-THEORY.md](APPLIED-THEORY.md), "Advantages and disadvantages of ClickHouse here"; [ATLAS-RESULTS.md](ATLAS-RESULTS.md), where the aggregate was not faster | Done |
| Comparison with other approaches or traditional databases | [FUNDAMENTALS.md](FUNDAMENTALS.md), "Comparison with a transactional database"; [PRESENTATION.md](PRESENTATION.md), "Talking points for questions" | Done, qualitatively. There is no benchmark against PostgreSQL; the brief does not require one |
| Projects it fits best | [FUNDAMENTALS.md](FUNDAMENTALS.md), comparison table | Done |

## Deliverables

| Deliverable | Where | Status |
|---|---|---|
| 20-minute presentation with the demo | [PRESENTATION.md](PRESENTATION.md), [English speaker notes](CLICKHOUSE-PRESENTER-NOTES-EN.md) and [slide content](CLICKHOUSE-PRESENTATION-EN.json) | Draft ready: 17:35 including dashboards, map and CRUD, plus 2:25 buffer. Full group rehearsal still pending |
| Documentation | [FUNDAMENTALS.md](FUNDAMENTALS.md), [DATABASE-STRUCTURE.md](DATABASE-STRUCTURE.md), [ATLAS-INFRASTRUCTURE.md](ATLAS-INFRASTRUCTURE.md), [TEAM-TECHNICAL-GUIDE.md](TEAM-TECHNICAL-GUIDE.md) | Done |
| Step-by-step installation | [ATLAS-INFRASTRUCTURE.md](ATLAS-INFRASTRUCTURE.md), section 2, and [INSTALLATION.md](INSTALLATION.md) | Done. Windows test with system, commands, results and common problems in [TEAM-INSTALL-TESTS.md](TEAM-INSTALL-TESTS.md). Echenique's test on his computer is still missing |
| Guide to run the demo | [DEMO.md](DEMO.md) is the old OTTO lab demo; [TRACKING-DEMO.md](TRACKING-DEMO.md) covers Atlas tracking; [MINIAPP.md](MINIAPP.md), the mini-app | Partial: a single guide following the order of the final demo is missing |
| Additional files | `compose.yaml`, `Dockerfile.atlas`, `sql/`, `atlas/`, `scripts/`, `web/`, `tests/` and screenshots in `docs/capturas/` | Done |

## Evaluation criteria

| Criterion | How we cover it |
|---|---|
| Clarity and structure of the presentation | Depends on the final script and a timed rehearsal |
| Technical understanding | [FUNDAMENTALS.md](FUNDAMENTALS.md) and [DATABASE-STRUCTURE.md](DATABASE-STRUCTURE.md): `MergeTree` engines, physical order, partitions, materialized views and queue idempotency |
| Real-world use cases, rigorous data use and strong arguments | Separate provenance: real, derived, `synthetic` and `demo_live`. Figures with their conditions in [RESULTS.md](RESULTS.md) and [ATLAS-RESULTS.md](ATLAS-RESULTS.md) |
| Quality and relevance of the demo | Full path: mini-app → API → ClickHouse → dashboard, with an order delivered and tracked by GPS |
| Clear and reproducible documentation | Atlas starts with one command and without large datasets; Windows test recorded ([TEAM-INSTALL-TESTS.md](TEAM-INSTALL-TESTS.md)) |
| Real datasets, programming language and scalability | OTTO, REES46, Ele.me and Glovo; Python; a billion derived rows and an explanation of replicas and shards |
| Creativity of the use case | Fictional delivery platform with AI customers, concurrent traffic and GPS tracking |
| Answering questions and discussion | Eight supporting slides and the questions in [English speaker notes](CLICKHOUSE-PRESENTER-NOTES-EN.md) |

## Pending before the presentation

By priority:

1. **Timed group rehearsal** of the [final 20-minute script](PRESENTATION.md), including the new ClickHouse dashboards, map and CRUD. Confirm the host and gateway run the new analytical routes before the rehearsal.
2. **A single guide for the final demo**, step by step, with CRUD included and a plan B in case something fails.
3. **Echenique's installation test** on his computer, added to [TEAM-INSTALL-TESTS.md](TEAM-INSTALL-TESTS.md).

Done on 19 October: common uses and clients of ClickHouse in [FUNDAMENTALS.md](FUNDAMENTALS.md); [APPLIED-THEORY.md](APPLIED-THEORY.md) updated for Atlas; Windows installation test; LF line endings for `*.sh` in `.gitattributes`; technology confirmed in [TEAM-STATUS.md](TEAM-STATUS.md) and [THEORY-REVIEW.md](THEORY-REVIEW.md); Claude added to the AI-use statement; documentation and the app's interface translated into English.

Written with Claude's help from the project brief and the repository documents; reviewed by Anuar.
