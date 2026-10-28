# ClickHouse checkpoint — 28 October 2026

Ten English slides with four speakers. The core script takes 9:40 including the two demo sections; 0:20 remains within ten minutes. The separate final presentation retains its twenty-minute format.

- `content.json`: slide titles, complete speaker notes, sources and dated read-only observations.
- `SCRIPT-EN.md`: spoken script, timing, demo preparation, fallback and questions.
- `build.mjs`: native slide objects, editable tables and data-path diagram for Artifact Session.
- `map-public-2026-10-28.png`: recorded capture after reconnecting the public demo, around 11:43 Europe/Madrid.
- The three `*-recorded.png` assets were extracted from Anuar's supplied PDF as reference/fallback evidence. The revised evidence slide uses native tables with the newly verified measurements.

Live Page: `page_ba10f0a072bc81919bedab6eec486def`. The original final-presentation Page is unchanged.

To rebuild a new connected presentation, use the returned Artifact Session reference. Run the module's `cover` callback first, then `build` with `{slides, start:1, end:4, assets}`, followed by ranges 4–7 and 7–10. `slides` comes from `content.json`; `assets` contains absolute paths for the three extracted images under keys `map`, `ai`, `datasets`. Finally run `verifiedEvidence` with the complete content object and `recordedMap` set to the absolute path of the new public map capture. Render and inspect every slide. Never point a rebuild at an unrelated existing deck.

The supplied script's unverified 22 October volume totals were replaced by checked configuration and dated query statistics. The revision distinguishes SQL/OLAP/storage layout, qualified transaction guarantees, retry identity and eventual replacement, model configuration and actual model activity, and server execution time versus page latency. No PostgreSQL benchmark or zero-data-loss guarantee is claimed.

The checked host still uses main `734374d`. Customer Journey and ClickHouse Performance are implemented in PR #9 and are pending integration and a joint backend/gateway rollout. The live checkpoint does not present those routes as deployed.
