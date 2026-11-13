# Delivery Atlas: presentation for rehearsal

Current version: **11 November 2026, 14 English slides and English notes, four speakers**. This is the branded web version sent to Anuar for rehearsal. It retains the prepared ten-slide checkpoint, then appends four experiments. The older 16-slide proposal is [archived](PRESENTATION-OUTLINE-2026-10-27.md); its numbering and three-person allocation do not apply.

[Open/download the presentation](../presentaciones/final-2026-11-11/Delivery-Atlas.html) · [Speaking script](../presentaciones/final-2026-11-11/SCRIPT-EN.md) · [Live demo guide](DEMO-GUIDE.md)

Download or clone the repository and open the HTML in a browser. GitHub's file page shows source; the HTML itself is self-contained, with embedded fonts and images, and works offline. The live application is separate.

| Slide | Topic | Speaker | Target |
|---:|---|---|---|
| 1 | Delivery Atlas | Echenique | 0:30 |
| 2 | A delivery app never stops writing, and the business wants answers now | Echenique | 0:30 |
| 3 | An open-source, column-oriented database built for analytics | Echenique | 1:00 |
| 4 | To sum amounts by status, read 2 columns, not 5 | Juanro | 1:30 |
| 5 | Delivery Atlas: how data reaches the dashboard | Anuar | 1:30 |
| 6 | One ClickHouse, three kinds of data, never mixed | Anuar | 1:00 |
| 7 | 50 couriers on real Madrid streets | Geremi | 1:15 |
| 8 | Switch the view: AI agents, then real data | Geremi | 1:15 |
| 9 | Status and next steps before 15 November | Juanro | 1:30 |
| 10 | Thank you. Questions? | Echenique | 0:15 |
| 11 | One GPS dataset. Two ways to get the same positions. | Anuar | 1:00 |
| 12 | At two readers, history misses our 1-second target | Juanro | 1:10 |
| 13 | The answer is the same. The amount of work changes. | Anuar | 1:10 |
| 14 | Next: compare databases on the same frozen corpus | Echenique | 1:00 |

Prepared timings total **14:35**, before extra questions or optional dashboard detours. Rehearse the full route with a clock on Anuar's computer.

## Speaking and demo route

- Echenique: 1, 2, 3, 10 and 14.
- Juanro: 4, 9 and 12.
- Anuar: 5, 6, 11 and 13.
- Geremi: 7 and 8.

The map and view switches belong to **slides 7–8**. Slide 10 closes the retained checkpoint; continue to 11–14 for the experiment appendix. Slide 14 describes the planned cross-database comparison; it is not a live operations/CRUD slide. The demo guide budgets Customer Journey/Performance after slide 8 and the required scratch-table CRUD after slide 14 within the 20-minute slot, without changing the prepared slide content or notes. Extra demonstrations belong to Q&A if time is short.

Controls: arrows/Space advance a build; Shift+arrow changes slide; N opens notes; O opens the full-title index; P hides/restores controls; F requests fullscreen; Escape closes an overlay or restores controls. Reduced-motion preferences are respected. There is no automatic advance or idle animation.

## Evidence boundaries

The first ten slides retain the checkpoint's original dated figures and script. They describe a 100-customer, 50-courier run; do not silently substitute today's accumulated inventory. The appendix uses the frozen 4,371,300-position GPS run with 150 couriers, not every row in the server's five tables.

The GPS p95 values are client times from three repetitions of 200 requests per design and reader count; the 1-second line is the experiment's target, not a universal ClickHouse limit. Server duration and query memory are separate metrics. The raw ZIP is linked from [GPS-BENCHMARK.md](GPS-BENCHMARK.md). PostgreSQL/DuckDB results, ingestion cost and replicated availability are not claimed.

Criteo and Glovo are the public datasets available on Anuar's host. OTTO, REES46 and Ele.me are optional legacy explorers and are not required for this rehearsal. The shared website is read-only; simulation controls, checkout, SQL and CRUD stay on the host. Never project credentials.
