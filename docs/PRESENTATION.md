# Delivery Atlas: final presentation

English slides and speaker notes, prepared 21 October 2026. This replaces the earlier Clickstream Lab final script; the six-slide progress decks remain historical artifacts.

**Format:** 20 minutes including demo, then about 10 minutes of questions. The core script totals 18 min 10 sec, leaving 1 min 50 sec for transitions.

| Slide | Topic | Target |
|---:|---|---:|
| 1 | Delivery Atlas | 0:30 |
| 2 | Why ClickHouse fits our workload | 0:55 |
| 3 | What is ClickHouse? | 0:50 |
| 4 | How our ClickHouse tables are structured | 1:15 |
| 5 | The project ideas we explored | 1:10 |
| 6 | Choosing a project: the hard parts | 1:05 |
| 7 | Why we built Delivery Atlas | 0:45 |
| 8 | 1 · Downloaded data: scale and context | 1:05 |
| 9 | 2 · Simulated data: a repeatable workload | 0:45 |
| 10 | 3 · Agents create customer decisions | 1:00 |
| 11 | How the project connects | 1:05 |
| 12 | One checkout, linked across the database | 1:05 |
| 13 | What our measurements actually show | 1:15 |
| 14 | Reliability and scaling: our limits | 0:55 |
| 15 | Live demo · follow one order | 3:30 |
| 16 | What we learned | 1:00 |

[Speaker notes](FINAL-PRESENTER-NOTES-EN.md) · [Editable content source](FINAL-PRESENTATION-EN.json) · [Project selection evidence](PROJECT-DECISIONS.md) · [Assignment](ASSIGNMENT.md)

## Rehearsal

Use the local miniapp and a host terminal for controls/CRUD. The public Vercel link only exposes reads. Test `python3 scripts/crud_demo.py` against the intended ClickHouse host before class; this command uses the historical-lab connection defaults, so set `CLICKHOUSE_URL`, `CLICKHOUSE_USER` and `CLICKHOUSE_PASSWORD` for a different host. Use the scratch table, not the real source tables, for CRUD.

Show one linked checkout/order/courier. Explain event age and the difference between a real street map and synthetic GPS. If the tunnel or tiles fail, switch to saved screenshots and recorded query results, clearly labelled as evidence.

## Claims to defend accurately

ClickHouse was assigned to the group. We implemented one node. Public histories are not live Spanish Uber/Glovo customer data. The OTTO 27.9× result compares two designs in ClickHouse, not two database products. The Atlas aggregate did not improve its measured query. Rule-based traffic is not AI. Queue acceptance is not yet ClickHouse visibility.
