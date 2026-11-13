# Delivery Atlas · prepared checkpoint script

Original script retained. Geremi and Echenique have exchanged parts. The hand-off on slide 6 names Geremi accordingly. All other spoken text and original timings remain unchanged.

## 1. BD2 · Project checkpoint

Echenique · 0:30

Good morning. We are Geremi, Anuar, Echenique and Juanro, and this is a checkpoint of our project, Delivery Atlas. The database we were assigned is ClickHouse. In the next ten minutes we will explain what ClickHouse is, why it is fast, how we use it in our project, and then show it running live.

## 2. The problem

Echenique · 0:30

Imagine a food-delivery app like Glovo. Every second customers search and click, couriers send their GPS position, and orders change status. In one four-hour run of our own simulation, with a hundred customers and fifty couriers, we generated almost four hundred thousand GPS positions, a hundred and forty-five thousand customer actions and nearly eight thousand orders. The business wants to ask questions like "how many orders are running late right now?" over all that data, in milliseconds, while new data keeps coming in. A normal transactional database is not designed for that. That is the problem ClickHouse solves.

## 3. What is ClickHouse

Echenique · 1:00

So what is ClickHouse? It is an open-source database, created at Yandex and open source since 2016, designed for analytics. Three ideas. First, it is columnar: it stores each column separately and compressed. Second, it is analytical, or OLAP: it is made for counting, summing and grouping very large tables, and it likes data inserted in batches. Third, you query it with SQL, so it looks familiar, but it is not a classic relational database: it has no transactions and updating a row is expensive. A question we often get is whether it is NoSQL. Our answer: it belongs to the column-store family, so its storage model is not the relational one, but it keeps SQL as its language. Now Juanro will explain why this design makes it so fast.

## 4. Why it is fast

Juanro · 1:30

Why is it so fast? Take a simple question: the total amount of the orders, grouped by status. A row store, like PostgreSQL, keeps each order together, so it has to read every whole row, all five columns. ClickHouse keeps each column in its own file, so it only reads status and amount, and skips the rest. With millions of rows that is a huge difference. On top of that, three things from its main engine, MergeTree. One: rows are kept sorted by a key, so ClickHouse can skip whole blocks that cannot match the query. Two: every insert writes a new part, and ClickHouse merges those parts in the background; that is why it prefers inserting in batches. Three: similar values stored together compress very well. For example, fourteen million real rows from the Criteo dataset take only two hundred and sixty-two megabytes on disk. Now Anuar will show how we used all this in our project.

## 5. Delivery Atlas: how data reaches the dashboard

Anuar · 1:30

This is Delivery Atlas, a fictional food-delivery platform in Madrid that we built around ClickHouse. Read it from left to right. At the top, the live data: simulated customers, customers controlled by an AI model, and our own mini-app where we can order food by hand. Every event goes to our API, written in Python, which checks it and stores it in a small durable queue, so nothing is lost if ClickHouse is busy. A publisher then inserts the events into ClickHouse in batches, which is exactly how ClickHouse likes to receive data. Inside ClickHouse, the tables only receive inserts; materialized views keep the latest state of every courier and order, so the map reads one row per courier instead of the whole GPS history. At the bottom, the real public datasets, Criteo and Glovo, loaded once into a separate database. On the right, the dashboard and a public read-only website read everything through the same API.

## 6. Three kinds of data

Anuar · 1:00

We work with three kinds of data, and we never mix them. One: simulated customers, driven by rules and a fixed seed, so we can generate hundreds of customers and a lot of data. Two: AI agents. A small language model running locally on our computer decides what each customer does next, like opening a restaurant or buying, and writes a short reason. Python checks every decision before it becomes a click or an order. Three: real public datasets that we downloaded: an advertising experiment from Criteo, with fourteen million rows, and the product catalog of Glovo, with almost three million products. Every row keeps its origin, so we never present a simulated number as real, and we never join real data with fictional orders. The dashboard lets you switch between the three, and Geremi will show it now.

## 7. Live demo

Geremi · 1:15

Now the live demo. *[Switch to the browser tab 127.0.0.1:8001 and show the map.]* This is Madrid, with real streets. Every dot is a courier of our simulation; right now there are fifty couriers and a hundred customers. The positions come from ClickHouse and the page asks for them every two seconds. *[Click a courier.]* If I click one, I see the order it is carrying, the customer who bought it and the GPS path. *[Scroll up to the numbers.]* Up here, the live numbers: active orders, delivered orders and orders past their deadline. All these numbers are computed by ClickHouse at that moment.

## 8. Live demo

Geremi · 1:15

*[Click "AI agents".]* With these three buttons we change the kind of data. In the AI agents view we only see the three customers that the language model controls. Look at their reasons, for example: "I have purchased the Vegetable bowl for 10.90 euros, which fits within my budget of 22 euros." *[Click "Downloaded datasets".]* And this is the real data. ClickHouse reads the whole Criteo table, fourteen million rows, in about a tenth of a second, and the time you see is measured by ClickHouse itself. *[Optional, only if there is time: in the /play tab run the query on the slide.]* This is the kind of query that would be slow in a row database, and here it takes milliseconds. *[Go back to the slides.]*

## 9. Where we are

Juanro · 1:30

To finish, where we are. Done: the whole path works, from the app to the API, to ClickHouse, to the dashboard; the three data views, with the real datasets loaded and checked; a public read-only website; and automated tests plus an installation guide. Next, before the final presentation on the fifteenth of November: a final talk centred on ClickHouse, two new dashboards, Customer Journey and ClickHouse Performance, showing insert, update and delete live, and testing the installation on another computer. And the limits we found, which are also what we learned. Updating or deleting rows in ClickHouse is expensive, so our design only inserts: a change is a new row. Duplicates are removed later, when ClickHouse merges parts in the background, so we read with FINAL when we need exact results. We use one node; we can explain replication but we did not deploy it. And in long runs Docker closed twice on our demo computer, so we keep backups of every run.

## 10. Thank you. Questions?

Echenique · 0:15

Thank you. To sum up: ClickHouse is the analytics engine of our delivery platform, it answers questions over millions of rows in milliseconds, and the code and documentation are in our GitHub repository. We are happy to take your questions.



# Appended experiments — new speaking parts

## 11. Experiment · setup

Anuar · 1:00

We used a frozen GPS run with just over four million positions and 150 couriers. We asked the same question in two ways: calculate the latest position from the history, or read the prepared latest state. Both returned the same positions.

Anuar ran each design separately, with one and two concurrent readers. Each point has three repetitions of 200 requests. The lab was limited to two CPUs and two gibibytes of container memory. This is a warm test with the SQL result cache disabled.

Our target is that 95 percent of successful requests finish within one second, with zero errors. That is our presentation target for this workload; it is not a universal ClickHouse limit. These results come from Anuar’s summary and phase CSV. We still need to inspect the complete request logs.

## 12. Experiment · result

Juanro · 1:10

With one reader, both designs meet our target. The history query has a p95 between 704 and 750 milliseconds. The prepared state is 125 milliseconds in all three repetitions.

With two readers, the difference becomes clear. The history query takes between 1.625 and 1.969 seconds at p95, while the prepared state takes between 266 and 281 milliseconds. All 2,400 measured requests completed without errors.

The bars show the median of the three p95 values, and the dots show each repetition. This is a practical latency boundary for this machine, query and resource budget. It does not mean ClickHouse can only serve two users: a reader here repeatedly sends a query as soon as the previous one finishes. Higher concurrency was not tested in this campaign because the runner stopped after a design missed the target.

## 13. Experiment · explanation

Anuar · 1:10

The key change is how much data each request needs to read. Anuar’s query-log summary reports about 4.37 million rows read by the history query and 150 by the prepared state. With one reader, the median server time is about 560 milliseconds for history and six milliseconds for prepared state.

The existing materialized view updates aggregate states when batches arrive. The latest-state view merges those states when it is queried. It is important to distinguish the 150 result positions from the physical number of stored partial states.

Anuar attributes the history slowdown with two readers to competition for the two CPUs. That explanation is consistent with his reported CPU time, but we will inspect the full server logs before treating the diagnosis as independently verified. Client and server time are different measures, and peak query memory is not the container’s total memory.

We have measured the read improvement here. We have not measured the insertion and storage cost of maintaining the view in this comparison.

## 14. Next experiment · planned

Echenique · 1:00

The next question is how the same workload behaves in another database. We propose PostgreSQL first, and DuckDB if the available time and hardware allow it. We do not have cross-database performance results yet.

We will use the same frozen exports and verify that every engine returns equivalent results. We will document the schema, indexes, ordering, cache conditions, versions and resource limits. We will compare history queries first, and prepared designs separately.

Then we will increase the corpus in stages, including all the useful history we have. More rows on the server only matter if the query actually reads them: the current GPS runner filters a single run.

The presentation will show the observed boundary, the evidence for its cause, and the improvement under the same workload. If a boundary is not reached, we will report that honestly.
