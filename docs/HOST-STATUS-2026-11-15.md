# Host verification on 15 November 2026

Anuar's update records the demo host around **01:45 UTC on 15 November**. The source is his two emails sent at 01:47 UTC to Geremi/the team. The local Docker checks and archive verification below are his reported results; the public checks are recorded separately.

## Update and preservation

The serving checkout was clean and fast-forwarded to `c7d4ca11abd2c4be0d1609805b94910d8cb886a4`. Anuar rebuilt Atlas with the `atlas`/`ai` profiles and rebuilt `share-gateway` without recreating its dependencies. Atlas, ClickHouse, Ollama and the gateway were healthy. Existing data/queue volumes and token files were retained. GPS count was **23,978,916 before and after** the rebuild.

The manually created `atlas-sim2` API on port 18001 retained its older image and stopped simulation; it is left out of the rehearsal route. The watchdog is paused. No simulation was running at the time of that report.

The public Performance endpoint independently confirmed **ClickHouse 25.8.33.6** at 19:28 UTC after reconnection. The Compose tag is `25.8`; record the resolved version/image on later runs rather than treating a minor tag as an immutable digest.

## Exported simulations

The two 11 November runs were stopped when Docker closed at 22:11 UTC that day. Both queues subsequently reported pending zero. Anuar exported them and checked all 21 saved archives using `verify_saved` from the updated exporter: **21 correct, zero failures, 37,310,637 archived rows**.

| Run UUID | Export folder | API and mode | Archived rows |
|---|---|---|---:|
| `f1dee148-dff5-49b3-966c-17b2ca3b6103` | `2026-11-11_f1dee148` | 8001, hybrid | 1,229,775 |
| `b6a982ca-6754-4c7c-bfcf-7dac8a00fef1` | `2026-11-11_b6a982ca` | 18001, traffic | 1,235,049 |

The previous 19-run manifest table totals 34,845,813 rows. Adding these two reported totals gives 37,310,637. All 21 small manifests and their first/last event times are now included in [run-manifests/](run-manifests/) and tabulated in [SIMULATION-RUNS.md](SIMULATION-RUNS.md). Their per-table totals were checked against [the supplied inventory](INVENTORY-2026-11-15.md) and public physical metadata; no missing counts were reconstructed. The recorded stop time is not a claim of uninterrupted generation.

Anuar explicitly states that the **50-million milestone was not reached**. The live logical inventory is 37,310,669 rows, including 32 `app_events` without a run ID that cannot be exported by run. Its other per-table counts match the archive sums. Physical part/state counts remain a different metric.

## Local pages and data

Anuar reports HTTP 200 for `/`, `/analytics.html`, `/delivery.html`, `/api/status`, `/api/journey`, `/api/performance`, `/api/datasets` and `/api/operations` on the local host.

| Table or scope | Reported value | Meaning |
|---|---:|---|
| `delivery_atlas.courier_positions` | 23,978,916 | Fictional GPS positions in ClickHouse |
| 21 exported runs, five event tables | 37,310,637 | Archived rows, including the GPS component |
| `delivery.criteo_uplift` | 13,979,592 | Public advertising experiment records |
| `delivery.glovo_products` | 2,887,444 | Public catalog records |

OTTO, REES46 and Ele.me are not loaded on this host. The GPS benchmark's 4,371,300-position run is a frozen subset used in a separate laboratory. These figures are not added into a single customer/order total.

## Shared access

Anuar reports protected tunnel reads returning 200, no-token reads 401 and rejected control routes after rebuilding his gateway. In the later public check on 15 November at **14:48 UTC**, the supplied new hostname returned NXDOMAIN in Google and Cloudflare DNS. Vercel `/api/status`, `/api/journey` and `/api/performance` returned 503. Public map/Leaflet assets still matched the reviewed source.

At **19:24 UTC** Anuar supplied a recreated active tunnel. At **19:26 UTC** the five protected reads were independently checked: all returned 200 with the existing token and 401 without it. Only the production `ATLAS_SHARE_ORIGIN` was updated; `ATLAS_SHARE_TOKEN` was preserved server-side.

At **19:28 UTC**, production deployment `dpl_4uUyS8LYVqpYApBD38tjX6Ru14sk` served `c7d4ca1` and public status, operations, Journey, Performance and datasets all returned 200. Map/Leaflet assets matched the reviewed source. Browser checks showed 150 historical courier positions, courier selection and zoom. The interface explicitly reported the stopped run and old position ages. The host and tunnel must remain active for later use; see [the validation record](FINAL-VALIDATION.md) for the release check scope.

## Rehearsal

Anuar confirms the 14-slide HTML opens offline and that he has the matching English script. His prepared parts remain 5, 6, 11 and 13, plus Journey/Performance after 8. He will start the 100-customer/50-courier, two-second hybrid run near the agreed rehearsal time so the bounded AI budget is useful. Recorded decisions remain distinguishable from new model calls.
