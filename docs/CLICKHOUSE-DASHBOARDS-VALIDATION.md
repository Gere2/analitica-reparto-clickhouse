# Dashboard validation — 27 October 2026

The English portal adds Customer Journey, ClickHouse Performance and five historical source explorers beside the existing operations dashboard. The Madrid map implementation is unchanged.

## Automated checks

- 50 Python tests passed, including eight integration tests against a disposable ClickHouse **25.8.33.6** instance. No tests were skipped.
- 33 JavaScript tests passed, including map behaviour, analytics rendering and public proxy validation.
- The shared frontend build and `git diff --check` passed.
- The rebuilt gateway image imports the shared filter validator and accepts the canonical analytical routes.
- HTTP checks through the authenticated local gateway returned 200 for Journey, Performance, OTTO comparison and a filtered Glovo query; arbitrary SQL returned 400, missing authentication 401 and a write request 405.

The SQL tests cover ordering, equal millisecond timestamps, the 30-minute window, retry copies, run isolation, AI classification, empty cohorts, historical filters and mismatched detail/aggregate answers. A mismatch never displays a timing ratio.

## Browser checks

Real API → disposable ClickHouse → rendered dashboard checks used 1280 × 900 and 375 × 844 viewports. The five source explorers rendered their three charts. The AI-only selection on a traffic-only run showed an empty cohort. A fixed OTTO comparison verified all 15 result groups before displaying measurements. The map retained 12 courier markers, selection, following and both zoom controls. There was no body overflow at mobile width and no browser warning/error output during the checked flow.

Screenshots are explicitly labelled validation evidence:

- [Customer Journey](capturas/customer-journey-validation.png)
- [ClickHouse Performance](capturas/clickhouse-performance-validation.png)
- [Madrid map on mobile](capturas/analytics-map-mobile-validation.png)

These checks used generated traffic and tiny seeded historical datasets. They do not establish production source counts, model behaviour, large-table latency or public-server availability. The separate documented historical benchmark remains distinct from these observations.

## Presentation and release dependency

The English presentation contains 16 core slides and eight supporting slides. Its 17:35 script includes the dashboard exploration and operations/CRUD demo, leaving 2:25 within 20 minutes. Speaker notes assign Geremi slides 1–8, Anuar 9–12 and Echenique 13–16. All 24 slides were rendered and visually reviewed; the PDF reading copy was checked for page count, dimensions and rendering.

The new API, gateway and shared frontend must be released together. Rebuild both `atlas` and `share-gateway`; an older host cannot serve these four new routes. This validation does not claim a production deployment. A complete timed rehearsal and Echenique's independent installation check remain pending.
