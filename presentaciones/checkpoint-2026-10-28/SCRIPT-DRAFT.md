# Delivery Atlas · Checkpoint presentation script, first draft (28 October 2026)

Anuar's first draft, kept for reference. The revised script used for the checkpoint is `SCRIPT-EN.md`; the volume figures on slide 2 below were not verified and were replaced there.

About 10 minutes, four speakers. The same text is in each slide's speaker notes.

| # | Slide | Speaker | Time |
|---|---|---|---|
| 1 | Delivery Atlas (cover) | Geremi | 0:30 |
| 2 | The problem | Geremi | 0:30 |
| 3 | What is ClickHouse | Geremi | 1:00 |
| 4 | Why it is fast | Juanro | 1:30 |
| 5 | How data reaches the dashboard | Anuar | 1:30 |
| 6 | Three kinds of data | Anuar | 1:00 |
| 7 | Live demo: the map | Echenique | 1:15 |
| 8 | Live demo: switch the view | Echenique | 1:15 |
| 9 | Status and next steps | Juanro | 1:30 |
| 10 | Thank you. Questions? | Geremi | 0:15 |
| | **Total** | | **≈ 10:15** |

If you run short of time, cut the optional `/play` query on slide 8 and shorten slide 9 to one sentence per column.

## Before the presentation (15 minutes before)

1. Open Docker Desktop and wait until it says the engine is running.
2. Start ClickHouse and Atlas: `docker compose -f compose.yaml --profile atlas up -d --wait`
3. Start Ollama for the AI agents: `docker compose -f compose.yaml --profile atlas --profile ai up -d --wait ollama`
4. Start a run at least 5 minutes before speaking, so there are orders and deliveries on screen. Either from the dashboard (Decisions "AI + mass traffic", 100 customers, 50 couriers, "Start customers and delivery") or with:
   `curl -X POST http://127.0.0.1:8001/api/simulation/start -H "Content-Type: application/json" -d "{\"mode\":\"customers\",\"agent_mode\":\"hybrid\",\"customers\":100,\"fleet\":50,\"interval\":2,\"seed\":2027}"`
   The AI agents stop deciding after 120 model calls (about 5 minutes); start the run 5–10 minutes before, not earlier, if you want their reasons on screen.
5. Open two browser tabs: `http://127.0.0.1:8001/?view=simulated` and `http://127.0.0.1:8124/play` (user `demo`, password `demo`).
6. Keep the laptop plugged in. Plan B: the screenshots in `screenshots/` are already on slides 7 and 8.

## What to say

### 1. Cover · Geremi (0:30)
Good morning. We are Geremi, Anuar, Echenique and Juanro, and this is a checkpoint of our project, Delivery Atlas. The database we were assigned is ClickHouse. In the next ten minutes we will explain what ClickHouse is, why it is fast, how we use it in our project, and then show it running live.

### 2. The problem · Geremi (0:30)
Imagine a food-delivery app like Glovo. Every second customers search and click, couriers send their GPS position, and orders change status. In one four-hour run of our own simulation, with a hundred customers and fifty couriers, we generated almost four hundred thousand GPS positions, a hundred and forty-five thousand customer actions and nearly eight thousand orders. The business wants to ask questions like "how many orders are running late right now?" over all that data, in milliseconds, while new data keeps coming in. A normal transactional database is not designed for that. That is the problem ClickHouse solves.

### 3. What is ClickHouse · Geremi (1:00)
So what is ClickHouse? It is an open-source database, created at Yandex and open source since 2016, designed for analytics. Three ideas. First, it is columnar: it stores each column separately and compressed. Second, it is analytical, or OLAP: it is made for counting, summing and grouping very large tables, and it likes data inserted in batches. Third, you query it with SQL, so it looks familiar, but it is not a classic relational database: it has no transactions and updating a row is expensive. A question we often get is whether it is NoSQL. Our answer: it belongs to the column-store family, so its storage model is not the relational one, but it keeps SQL as its language. Now Juanro will explain why this design makes it so fast.

### 4. Why it is fast · Juanro (1:30)
Why is it so fast? Take a simple question: the total amount of the orders, grouped by status. A row store, like PostgreSQL, keeps each order together, so it has to read every whole row, all five columns. ClickHouse keeps each column in its own file, so it only reads status and amount, and skips the rest. With millions of rows that is a huge difference. On top of that, three things from its main engine, MergeTree. One: rows are kept sorted by a key, so ClickHouse can skip whole blocks that cannot match the query. Two: every insert writes a new part, and ClickHouse merges those parts in the background; that is why it prefers inserting in batches. Three: similar values stored together compress very well. For example, fourteen million real rows from the Criteo dataset take only two hundred and sixty-two megabytes on disk. Now Anuar will show how we used all this in our project.

### 5. How data reaches the dashboard · Anuar (1:30)
This is Delivery Atlas, a fictional food-delivery platform in Madrid that we built around ClickHouse. Read it from left to right. At the top, the live data: simulated customers, customers controlled by an AI model, and our own mini-app where we can order food by hand. Every event goes to our API, written in Python, which checks it and stores it in a small durable queue, so nothing is lost if ClickHouse is busy. A publisher then inserts the events into ClickHouse in batches, which is exactly how ClickHouse likes to receive data. Inside ClickHouse, the tables only receive inserts; materialized views keep the latest state of every courier and order, so the map reads one row per courier instead of the whole GPS history. At the bottom, the real public datasets, Criteo and Glovo, loaded once into a separate database. On the right, the dashboard and a public read-only website read everything through the same API.

### 6. Three kinds of data · Anuar (1:00)
We work with three kinds of data, and we never mix them. One: simulated customers, driven by rules and a fixed seed, so we can generate hundreds of customers and a lot of data. Two: AI agents. A small language model running locally on our computer decides what each customer does next, like opening a restaurant or buying, and writes a short reason. Python checks every decision before it becomes a click or an order. Three: real public datasets that we downloaded: an advertising experiment from Criteo, with fourteen million rows, and the product catalog of Glovo, with almost three million products. Every row keeps its origin, so we never present a simulated number as real, and we never join real data with fictional orders. The dashboard lets you switch between the three, and Echenique will show it now.

### 7. Live demo: the map · Echenique (1:15)
Now the live demo. *[Switch to the browser tab 127.0.0.1:8001 and show the map.]* This is Madrid, with real streets. Every dot is a courier of our simulation; right now there are fifty couriers and a hundred customers. The positions come from ClickHouse and the page asks for them every two seconds. *[Click a courier.]* If I click one, I see the order it is carrying, the customer who bought it and the GPS path. *[Scroll up to the numbers.]* Up here, the live numbers: active orders, delivered orders and orders past their deadline. All these numbers are computed by ClickHouse at that moment.

### 8. Live demo: switch the view · Echenique (1:15)
*[Click "AI agents".]* With these three buttons we change the kind of data. In the AI agents view we only see the three customers that the language model controls. Look at their reasons, for example: "I have purchased the Vegetable bowl for 10.90 euros, which fits within my budget of 22 euros." *[Click "Downloaded datasets".]* And this is the real data. ClickHouse reads the whole Criteo table, fourteen million rows, in about a tenth of a second, and the time you see is measured by ClickHouse itself. *[Optional, only if there is time: in the /play tab run the query on the slide.]* This is the kind of query that would be slow in a row database, and here it takes milliseconds. *[Go back to the slides.]*

### 9. Status and next steps · Juanro (1:30)
To finish, where we are. Done: the whole path works, from the app to the API, to ClickHouse, to the dashboard; the three data views, with the real datasets loaded and checked; a public read-only website; and automated tests plus an installation guide. Next, before the final presentation on the fifteenth of November: a final talk centred on ClickHouse, two new dashboards, Customer Journey and ClickHouse Performance, showing insert, update and delete live, and testing the installation on another computer. And the limits we found, which are also what we learned. Updating or deleting rows in ClickHouse is expensive, so our design only inserts: a change is a new row. Duplicates are removed later, when ClickHouse merges parts in the background, so we read with FINAL when we need exact results. We use one node; we can explain replication but we did not deploy it. And in long runs Docker closed twice on our demo computer, so we keep backups of every run.

### 10. Thank you · Geremi (0:15)
Thank you. To sum up: ClickHouse is the analytics engine of our delivery platform, it answers questions over millions of rows in milliseconds, and the code and documentation are in our GitHub repository. We are happy to take your questions.

## Likely questions and short answers

- **Is ClickHouse NoSQL?** It is a column store, a non-relational storage model, but it uses SQL. It is closer to an analytical (OLAP) engine than to MongoDB or Redis.
- **Why not PostgreSQL?** PostgreSQL is better for transactions and frequent updates of single rows. For counting and grouping millions of rows, a column store reads far less data.
- **How do you update an order's status if updates are expensive?** We never update: every change is a new row with its time, and ClickHouse keeps the latest (ReplacingMergeTree, and `argMax` in materialized views).
- **What happens if the same event arrives twice?** Every event has an ID. The queue rejects a different payload with the same ID, and ClickHouse collapses exact duplicates; we read with `FINAL` when we need exact results.
- **Is the data real?** The orders, customers and GPS are fictional. The Criteo and Glovo datasets are real and public, and they are never mixed with the simulation.
- **What if the server fails?** Accepted events wait in a durable SQLite queue and are published when ClickHouse is back. We saw this when Docker closed: nothing was lost.
- **Does it scale to several servers?** Yes: ReplicatedMergeTree with ClickHouse Keeper for copies, and Distributed tables to split data across servers. We explain it but run a single node.
