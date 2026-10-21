# PR #7 and PR #8 integration review

21 October 2026. The combined version keeps the Madrid Leaflet map, zoom, courier selection, follow mode and locally served vendor assets from #8, and adds the simulated / AI / downloaded-data selector and read-only datasets route from #7.

## Corrections made during review

- Resolved overlaps in the proxy copy, shared build, dashboard styles and dashboard JavaScript. Both view switching and the FleetMap initialization/lifecycle remain present.
- Older servers return whole-run totals rather than per-type metrics. These totals are never attributed to AI agents. A traffic-only run can still show simulated totals; a mixed run waits for the server update rather than displaying misleading counts. A run-ID mismatch also prevents that fallback.
- Criteo's publisher says the released data was non-uniformly sampled for privacy and does not reveal the original incrementality. The UI now labels **observed group differences**, rather than the original campaign effect. [Publisher's data card](https://huggingface.co/datasets/criteo/criteo-uplift#privacy).
- Zero/missing control rates no longer produce infinite or NaN percentages. Failed dataset refreshes clear old timing labels and explain the server-update dependency.

## Validation

- 43 Python tests, including three integrations with a disposable ClickHouse 25.8 limited to 1 GB / 2 CPUs. The added integration reads Criteo and Glovo fixture tables through the real SQL summaries and checks ClickHouse timing statistics.
- 19 JavaScript tests passed. Regression coverage includes checkout/tracking, geographic validation, view switching, compatibility with old servers and shared-proxy route/method restrictions.
- The local browser validation uses the real new API and authenticated gateway with an explicitly labelled fixture environment. It does not claim fixture counts or model decisions are production observations.
- Browser verification: desktop 1280×900 and mobile 375×844, all three views, return from datasets to tracking, courier selection and follow mode. Mobile document width stayed 375 px; no warning/error console entries were observed.
- The UI detector reports the same two inspected advisories as #8: empty-value em-dashes and the GPS legend line.
- Compose configuration passed with `--no-env-resolution`; syntax checks, the read-only build and diff checks passed.
- Production retains Anuar's existing connection until he rebuilds `atlas` and `share-gateway`. The datasets view may be unavailable until then; the live map remains usable. A changed tunnel origin must be coordinated before changing Vercel.

The existing documented classification limit remains: customer metrics count a customer as AI after its first recorded model decision. Configured AI customers can appear in the list before that decision.
