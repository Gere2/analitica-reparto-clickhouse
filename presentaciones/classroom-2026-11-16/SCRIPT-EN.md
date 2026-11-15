# Delivery Atlas · Classroom rehearsal

## 1. Delivery Atlas

Echenique · 0:30

Good morning. We’re Geremi, Anuar, Echenique and Juanro. Our project is Delivery Atlas. We’ll show how ClickHouse powers a courier map, then test how quickly two queries can find the same couriers as their GPS history grows.

*[Invite the class to scan the QR and choose a nickname and a dish. The host opens ordering after starting the customer simulation.]*

## 2. A delivery app never stops writing, and the business wants answers now

Echenique · 0:30

Imagine a food-delivery app like Glovo. Every second customers search and click, couriers send their GPS position, and orders change status. In one four-hour run of our own simulation, with a hundred customers and fifty couriers, we generated almost four hundred thousand GPS positions, a hundred and forty-five thousand customer actions and nearly eight thousand orders. The business wants to ask questions like "how many orders are running late right now?" over all that data, in milliseconds, while new data keeps coming in. A normal transactional database is not designed for that. That is the problem ClickHouse solves.

## 3. An open-source, column-oriented database built for analytics

Echenique · 1:00

So what is ClickHouse? It is an open-source database, created at Yandex and open source since 2016, designed for analytics. Three ideas. First, it is columnar: it stores each column separately and compressed. Second, it is analytical, or OLAP: it is made for counting, summing and grouping very large tables, and it likes data inserted in batches. Third, it speaks SQL. ClickHouse stores data by column and supports atomic inserts under specific conditions. In Atlas, each change in order status becomes a new event. Juanro will show why the column layout matters for our queries.

## 4. To sum amounts by status, read 2 columns, not 5

Juanro · 1:30

Why is it so fast? Take a simple question: the total amount of the orders, grouped by status. In this example PostgreSQL scans a table where all five fields sit in the same row. A suitable covering index can change that access pattern. ClickHouse keeps each column in its own file, so it only reads status and amount, and skips the rest. With millions of rows that is a huge difference. On top of that, three things from its main engine, MergeTree. One: rows are kept sorted by a key, so ClickHouse can skip whole blocks that cannot match the query. Two: every insert writes a new part, and ClickHouse merges those parts in the background; that is why it prefers inserting in batches. Three: similar values stored together compress very well. For example, fourteen million real rows from the Criteo dataset take only two hundred and sixty-two megabytes on disk. Now Anuar will show how we used all this in our project.

## 5. Delivery Atlas: how data reaches the dashboard

Anuar · 1:30

This is Delivery Atlas, a fictional food-delivery platform in Madrid that we built around ClickHouse. Read it from left to right. At the top, the live data: simulated customers, customers controlled by an AI model, and our own mini-app where we can order food by hand. Every event goes to our API, written in Python, which checks it and stores it in a small durable queue, so nothing is lost if ClickHouse is busy. A publisher then inserts the events into ClickHouse in batches, which is exactly how ClickHouse likes to receive data. Inside ClickHouse, the tables only receive inserts; materialized views keep the latest state of every courier and order, so the map reads one row per courier instead of the whole GPS history. At the bottom, the real public datasets, Criteo and Glovo, loaded once into a separate database. On the right, the dashboard and a public read-only website read everything through the same API.

## 6. One ClickHouse, three kinds of data, never mixed

Anuar · 1:00

We work with three kinds of data, and we never mix them. One: simulated customers, driven by rules and a fixed seed, so we can generate hundreds of customers and a lot of data. Two: AI agents. A small language model running locally on our computer decides what each customer does next, like opening a restaurant or buying, and writes a short reason. Python checks every decision before it becomes a click or an order. Three: real public datasets that we downloaded: an advertising experiment from Criteo, with fourteen million rows, and the product catalog of Glovo, with almost three million products. Every row keeps its origin, so we never present a simulated number as real, and we never join real data with fictional orders. The dashboard lets you switch between the three, and Geremi will show it now.

## 7. 50 couriers on real Madrid streets

Geremi · 1:15

Now the live demo. *[Switch to the browser tab 127.0.0.1:8001 and show the map.]* This is Madrid, with real streets. Every dot is a courier of our simulation; our demo scenario has fifty couriers and a hundred customers. *[Check the active run. If showing the saved image, describe it as a recording.]* The positions come from ClickHouse and the page asks for them every two seconds. *[Click a courier.]* If I click one, I see the order it is carrying, the customer who bought it and the GPS path. *[Scroll up to the numbers.]* Up here, the live numbers: active orders, delivered orders and orders past their deadline. All these numbers are computed by ClickHouse at that moment.

*[Show Class orders. Select one classmate’s order and follow the labelled courier. Explain the change from accepted in the queue to published in ClickHouse.]*

## 8. Switch the view: AI agents, then real data

Geremi · 1:15

*[Click "AI agents".]* With these three buttons we change the kind of data. In the AI agents view we only see the three customers that the language model controls. Look at their reasons, for example: "I have purchased the Vegetable bowl for 10.90 euros, which fits within my budget of 22 euros." *[Click "Downloaded datasets".]* And this is the real data. ClickHouse reads the whole Criteo table, fourteen million rows, in about a tenth of a second, and the time you see is measured by ClickHouse itself. *[Optional, only if there is time: in the /play tab run the query on the slide.]* Anuar, can you show us how customers move through a session and how much work those queries do?

*[Anuar opens Customer Journey and ClickHouse Performance (2 min), then hands back to Juanro on slide 9.]*

## 9. What we built and what we learned

Juanro · 1:30

We’ve seen the whole path, from incoming events to a moving map. Customer Journey groups actions into sessions, while Performance tells us how many rows a query reads. We’ve also tested the installation on Windows and checked that Python can insert, read, update and delete a test row.

We learned two things from running it. We keep the GPS history by appending new positions, which leaves us a choice about how to read the latest one. And our demo runs on one machine. When Docker stopped during long runs, the saved exports let us keep the data. Echenique will introduce the question we tested on that history.

## 10. Can the map keep up?

Echenique · 0:15

Think back to the dots on the map. Each courier gets one dot, even when we have thousands of earlier positions for that courier. Anuar, how did we test the cost of finding the latest one?

## 11. One GPS dataset. Two ways to get the same positions.

We used a frozen GPS run with just over four million positions and 150 couriers. We asked the same question in two ways: calculate the latest position from the history, or read the prepared latest state. Both returned the same positions.

I ran each design separately, with one and two concurrent readers. Each point has three repetitions of 200 requests. The lab was limited to two CPUs and two gibibytes of container memory. This is a warm test with the SQL result cache disabled.

Our target is that 95 percent of successful requests finish within one second, with zero errors. That is our presentation target for this workload; it is not a universal ClickHouse limit. We checked all 2,400 requests against the server logs. Juanro will show what happened when we added a second reader.

## 12. At two readers, history misses our 1-second target

With one reader, both designs meet our target. The history query has a p95 between 704 and 750 milliseconds. The prepared state is 125 milliseconds in all three repetitions.

With two readers, the difference becomes clear. The history query takes between 1.625 and 1.969 seconds at p95, while the prepared state takes between 266 and 281 milliseconds. All 2,400 measured requests completed without errors.

The bars show the median of the three p95 values, and the dots show each repetition. This is a practical latency boundary for this machine, query and resource budget. It does not mean ClickHouse can only serve two users: a reader here repeatedly sends a query as soon as the previous one finishes. Higher concurrency was not tested in this campaign because the runner stopped after a design missed the target.

## 13. The answer is the same. The amount of work changes.

The key change is how much data each request needs to read. Our query logs show about 4.37 million rows read by the history query and 150 by the prepared state. With one reader, the median server time is about 560 milliseconds for history and six milliseconds for prepared state.

The existing materialized view updates aggregate states when batches arrive. The latest-state view merges those states when it is queried. It is important to distinguish the 150 result positions from the physical number of stored partial states.

The CPU times in the logs are consistent with the two readers competing for the same two CPUs. The test did not isolate that cause. Client and server time are different measures, and peak query memory is not the container’s total memory.

We have measured the read improvement here. We have not measured the insertion and storage cost of maintaining the view in this comparison.

## 14. How fresh are the positions on our map?

Echenique · 1:00

Three couriers last reported two, six and eighteen seconds ago. Our map flags positions older than ten seconds. We could add a count above it: “1 of 3 couriers has an old GPS position.” Click it to find Courier C.

*[Advance to the database comparison.]*

Could PostgreSQL serve the same map? Here’s the test we’d use. Load the same GPS history, index it by courier, time and event ID, and ask for the latest point per courier. First check that all 150 answers match. Then compare the history queries with the same readers, memory and CPU budget. Our timings on screen are from ClickHouse. A comparison of prepared tables would be a separate test.

Let’s finish by changing a row from Python.

*[Run the one-minute CRUD demo locally. Show the insert, update and final zero matching rows. Return to the comparison and advance to the closing screen.]*

Preparing the latest position kept our ClickHouse query under one second at p95 with two readers. Thank you. We’re happy to take your questions.
