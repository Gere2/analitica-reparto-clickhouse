# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

Jere, Anuar and Echenique are preparing a BD2 project; the professor and other students must understand it and reproduce the demo. The implementation is being continued by Rayo with Jere until the team joins.

## Product Purpose

Delivery Atlas demonstrates the analytics infrastructure of a fictional food-delivery platform. It must represent massive events, explain the schema and show ingestion and tracking during the demo.

## ClickHouse-first presentation — 27 October 2026

Geremi confirmed that ClickHouse is the main subject. Every dashboard must explain a concrete analytical question, its source tables and the database mechanisms used to answer it. The English analytics portal unifies Customer Journey, ClickHouse Performance and the historical dataset analyses, alongside the existing live operations map. Customer Journey uses a run-scoped ordered session funnel. Performance exposes storage engines, sorting keys, physical parts, completed query statistics and fixed detail/aggregate comparisons with answer equality checks. Public viewers keep read-only access. Missing datasets remain explicit host dependencies, without substituting invented counts.

## Operating Context

Local demo in the browser and Docker Compose, Python/ClickHouse integration. The user confirmed Madrid and simulated couriers with positions every two seconds on 7 October 2026. We keep the public datasets and the historical dashboards.

## Capabilities and Constraints

One ClickHouse 25.8 node, a standard-library Python API and a persistent SQLite transport queue. Historical data and our own events keep their provenance. There is no observed GPS and no live operational data from Uber Eats/Glovo. Positions and orders are simulations; routes do not follow a real road network. There are no payments and no real deliveries.

## Brand Commitments

Name: Delivery Atlas. Documentation and interface in English, because the course is taught in English (decided on 19 October 2026). Respect the existing look of the lab dashboards when extending the website.

## Evidence on Hand

docs/auditoria-esquemas.json contains the inspected tables and columns. docs/ATLAS-RESULTS.md records one million simulated events and retry/recovery tests. The OTTO measurements are not attributed to Atlas. Glovo provides a catalog; Ele.me, samples; Meituan, historical orders and sequences. None of those sources contains our GPS fleet.

## Product Principles

- Keep history, simulation and manual actions separate.
- Read from the real store: do not move couriers in the browser without ingestion.
- Show delay, errors and position age.
- Make the small path reproducible without downloading the massive datasets.

## Customer Agent Extension — 14 October 2026

Fictional customers use Qwen3:0.6b on local Ollama to choose catalog actions. Python validates options and budgets; a purchase links customer_id, session_id, checkout_event_id and order_id with the basket, statuses and GPS. The dashboard reads the decisions and purchases published to ClickHouse. The local policy and the previous fleet have different labels. Evidence: docs/evidencia-clientes.json and docs/AI-CUSTOMERS.md.

## Concurrent traffic extension

Hybrid mode: 3 AI customers and 197 traffic-simulator customers, with 80 couriers. Traffic uses batches and varied pauses; it keeps budget, checkout, session and order. Profiles that browse and abandon keep clicking while buyers wait for deliveries. Summary of twelve customers and smaller markers for large fleets. Up to 500 customers and 150 couriers can be configured; the 200/80 scenario has evidence in docs/evidencia-trafico.json.
