# How we chose Delivery Atlas

Recovered on 21 October 2026 from the project chat **“Proponer proyectos con millones de d”** (`01a0e886-25d3-7370-9ef6-95d6bfcd15dd`). This records proposals and decisions, not a claim that we tested every suggested project. The slide deck summarizes this history in English.

| Stage | What we considered | What changed our direction |
|---|---|---|
| Initial large-data ideas | NYC taxis, NYC 311, GitHub activity and Wikipedia pageviews; then movies, chess, cyberattack traffic, music and news | Geremi asked for something more interesting, then preferred Spain and a recognizable Uber/Cabify context. No technical rejection or benchmark of all these options was recorded. |
| Spain and mobility | Madrid fines, Bicimad, traffic and air quality, vehicle registrations; Cabify journey estimates and fleet repositioning | General mobility and sensor data could supply volume, but they were not private Uber/Cabify trips or app clickstreams. |
| Ten fleet proposals | Repositioning, congestion, event pickups, courier assignment, EV charging, Bicimad/VTC connections, transport gaps, accident exposure, price estimates and Chicago VTC analytics | We developed the courier-assignment option, with real Madrid traffic/local-business context and simulated orders. |
| Courier assignment | Compare a nearby courier with one estimated to arrive sooner | Geremi pointed out that choosing among a small set of couriers did not require millions of rows or explain why ClickHouse was useful. We moved the focus to analytical events. |
| Radar Delivery / Meituan | Food-delivery dashboard using TRD orders, products and click sequences | The data came from Beijing, and the sequences were tied to completed orders. They could not establish whole-app abandonment or Spanish behaviour. |
| Glovo Atlas | Explore the real FooDI-ML catalog, including Spain | The catalog gave products and location context, not clicks, order history or live activity. Geremi explicitly asked for massive click data and a live demonstration. |
| Clickstream Lab | OTTO and REES46 histories, replay, new manual events and aggregate benchmarks; Ele.me added food-sector context | Large-scale analytics worked, but the sources had different populations and row meanings. We could not truthfully join them into one Spanish delivery journey. |
| Delivery Atlas | A fictional delivery platform with a defined event contract, repeatable simulation and tracking | The professor suggested inventing the platform and preparing infrastructure for future real data. Public histories remained separate evidence; our platform supplied the coherent live workflow. |
| Customer agents | Local AI customers making shopping decisions, linked to orders and GPS; hybrid mode adds fast traffic generation | AI supplies bounded decisions; rule-based simulation supplies volume. Their provenance remains explicit. |

## Chat evidence

- Initial candidates and Spanish alternatives: turns `01a0e886-2f1f-70e2-a172-6a86f1d7c82c` through `01a0e892-e418-7af1-afd9-b0750e75e756`.
- Courier-assignment design and Geremi's objection: `01a0e895-0d19-74e3-a39c-a99bde2d853a`, `01a0e89b-daa9-7ed0-ad4e-14486d40af71`.
- Professor's dashboard clarification and implemented Meituan version: `01a10889-f8db-73d3-b440-ea220aaf2b07`, `01a1088d-48d5-7dd2-a084-e0c654d76d3f`.
- Spain/Glovo selection and clickstream pivot: `01a108a2-2eb3-7060-b192-0948fde201e9`, `01a108b2-a3aa-7ff2-a97f-51d0c5d77a81`, `01a108b8-d6c5-7291-9de2-105bd18d784a`.
- Ele.me access, memory limits and data interpretation: `01a10949-6d51-7c53-a858-81fc439d103f`, `01a10967-7e69-77e2-81fd-9d2fcea3f4b9`.
- Assessment of the different sources and fictional-platform decision: `01a10c45-7bfb-7b22-9679-fee396cd2d68`, `01a10c50-d553-76b2-96f4-9e97f1be25d6`.
- Tracking and AI-customer decisions: `01a116b5-250d-7ed0-b25a-1eda1ad795d8`, `01a13aa4-6290-78e3-b976-40a8285e5cf0`, `01a13aa5-5d5a-7120-b3f1-2a38049fb73d`.

The newer [assignment decisions](ASSIGNMENT.md) take precedence over early chat assumptions: ClickHouse was assigned, and the final format is **20 minutes including the demo plus about 10 minutes for questions**.
