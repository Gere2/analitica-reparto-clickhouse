# Public demo reconnection — 28 October 2026

Anuar reported a new authenticated read-only gateway and a mixed customer run. Read verification confirmed run `01b38d23-ab9a-4d68-8e17-5d2b0c517669`, 100 fictional customers and 50 couriers. The model was at 120/120 calls (`limit_reached`) while rule-based traffic continued.

After explicit user authorization, only the production `ATLAS_SHARE_ORIGIN` was changed to the validated tunnel. The existing server token stayed server-side. Production deployment `dpl_6HDCqX3HKWHAEAk3DXLnJoaWTqji` is READY and retains main commit `734374dd955738eb6e6e98da48debbb444410a03`. PR #9 was not merged. No remote simulation controls were used.

The canonical public URL is https://delivery-atlas-demo.vercel.app/. Before reconnection, its simulation endpoint returned 503; afterward `simulation`, `status`, `operations` and `datasets` all returned 200. The unauthenticated direct gateway returned 401, and the new `journey` route remained outside that host's allowlist (400).

Browser checks confirmed 50 couriers on the Madrid street map, selection/following, fresh event times, the AI view's exhausted call budget and the separate Criteo/Glovo view. The recorded map capture is in `presentaciones/checkpoint-2026-10-28/`.

At 10:36 UTC the host's Criteo endpoint reported 13,979,592 rows read and 105.7 ms of ClickHouse execution; Glovo reported 2,887,444 rows and 67.0 ms. These are individual observations, not a controlled benchmark or total website latency. The publisher queue was empty at that snapshot; that is not a general durability guarantee.

The checkpoint now includes four speakers. Its script and supporting questions are in `presentaciones/checkpoint-2026-10-28/SCRIPT-EN.md`. A timed group rehearsal remains necessary. The tunnel and host must remain available for the public demo; a later tunnel change requires another origin update.
