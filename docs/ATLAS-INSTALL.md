# Install Delivery Atlas step by step

This guide installs the current project from zero on another computer: ClickHouse, the Atlas API, the live operations dashboard with the Madrid map, the ClickHouse analytics portal and the mini-app. Then it fills the database with simulated data. It does not need the large public datasets; they are optional (step 6).

When you finish, follow [DEMO-GUIDE.md](DEMO-GUIDE.md) to run the live demo. To understand the database itself, read [FUNDAMENTALS.md](FUNDAMENTALS.md).

## What you will have running

| Service | Address | What it is |
|---|---|---|
| ClickHouse 25.8 | http://127.0.0.1:8124/play (user `demo`, password `demo`) | The database. `/play` is ClickHouse's built-in SQL page |
| Atlas API and dashboard | http://127.0.0.1:8001/ | Live operations, Madrid map, simulation controls |
| Analytics portal | http://127.0.0.1:8001/analytics.html | Customer Journey, ClickHouse Performance and the historical explorers |
| Mini-app | http://127.0.0.1:8001/delivery.html | A small delivery app where a person can place an order |
| Ollama (optional) | inside Docker only | Local AI model that decides for three customers |

Both ports listen only on your own computer (`127.0.0.1`). The `demo`/`demo` credentials are for this local lab only.

## 0. Requirements

- **Docker Desktop** (Windows or macOS) or Docker Engine with the Compose plugin (Linux). On Windows it uses WSL 2. Give Docker at least **4 GB of RAM**, or **6 GB** if you will use the AI step.
- **Git**.
- **Python 3.10 or newer**. The scripts use only the standard library: there is nothing to `pip install`.
- Free ports **8124** and **8001**.
- Disk: about **2 GB** for the images and a first simulation. The optional AI step needs about **10 GB** more (the Ollama image takes 9.4 GB once unpacked, the model 523 MB). The optional Criteo and Glovo datasets need about **2 GB** more.

**Windows:** write `python` where this guide says `python3`. In PowerShell, run `$env:PYTHONUTF8=1` once per window so accents print correctly.

## 1. Get the code

```bash
git clone https://github.com/Gere2/analitica-reparto-clickhouse.git
cd analitica-reparto-clickhouse
```

Every command below runs from this folder.

## 2. Start ClickHouse and Atlas

Open Docker Desktop and wait until it says the engine is running. Then:

```bash
docker compose -f compose.yaml --profile atlas up -d --build --wait
docker compose -f compose.yaml --profile atlas ps
```

The first start downloads the ClickHouse and Python images and builds the Atlas image (a few minutes, depending on the connection). `--wait` returns when both services are **healthy**.

What happens:

- `bd2-clickhouse` starts ClickHouse with the `demo` user and a volume `clickhouse_data`.
- `atlas` starts the Python API. On start-up it applies the SQL in `sql/atlas*.sql` (idempotent: running it again changes nothing) and creates the `delivery_atlas` database, its tables and materialized views.
- The API keeps a small durable queue in the volume `atlas_queue`. Events are first stored there, then published to ClickHouse in batches.

## 3. Check the installation

```bash
python3 -m unittest discover -s tests
python3 scripts/check_atlas.py
```

- The unit tests need no database. Some integration tests are **skipped** unless you point them at a disposable ClickHouse; skipped is expected.
- `check_atlas.py` sends real events to the API, sends one again as a retry and checks in ClickHouse that the retry did not create a second logical event. It writes its result to `data/atlas/checks.json`.

Then open:

1. http://127.0.0.1:8001/: the dashboard loads, with no error banner.
2. http://127.0.0.1:8001/analytics.html: the portal loads. Its views are empty until there is data.
3. http://127.0.0.1:8124/play: enter user `demo` and password `demo` at the top right and run:

```sql
SHOW TABLES FROM delivery_atlas
```

You should see tables such as `app_events`, `courier_positions`, `courier_latest`, `customer_activity`, `customer_orders`, `order_events` and `order_latest`.

## 4. Generate data with a simulation

1. Open http://127.0.0.1:8001/.
2. In **Live customers and delivery**, choose **Traffic simulator** under *Decisions* (it needs no AI). Set **200 customers** and **80 couriers**.
3. Click **Start customers and delivery**.

After a few seconds couriers move on the Madrid map and orders change status. The simulation keeps running until you click **Stop**. Each start creates a new run with its own `run_id`; earlier runs stay in ClickHouse.

After about five minutes, check in http://127.0.0.1:8124/play:

```sql
SELECT 'GPS positions' AS data, count() AS rows FROM delivery_atlas.courier_positions
UNION ALL SELECT 'customer actions', count() FROM delivery_atlas.customer_activity
UNION ALL SELECT 'orders', count() FROM delivery_atlas.customer_orders
```

Larger runs: the controls accept up to **500 customers and 150 couriers**. As a reference, on the demo host that size produced about 1.7 million rows per hour.

## 5. Optional: AI customers with a local model

This adds Ollama and a small model, Qwen3 0.6B (download of about 523 MB). It runs on your computer; there is no paid API.

```bash
docker compose -f compose.yaml --profile atlas --profile ai up -d --build --wait
docker compose -f compose.yaml --profile ai exec -T ollama ollama pull qwen3:0.6b
```

In the dashboard, choose **AI + mass traffic** under *Decisions* and start a run. Three customers are decided by the model, which writes a short reason for each action; the rest are simulated. The first decision can take a while as the model loads. The AI stops after **120 model calls** per run (a few minutes); simulated customers continue. The **AI agents** view of the dashboard shows only those three customers and their reasons.

## 6. Optional: public datasets

The analytics portal also has explorers for real public datasets. Opening a view never downloads anything; a missing dataset shows a clear message. Load only the ones you need:

| Dataset | Command | Download | Rows |
|---|---|---|---|
| Criteo Uplift v2.1 (advertising experiment) | `python3 scripts/criteo.py download` then `python3 scripts/criteo.py load` | 311 MB | 13,979,592 |
| Glovo FooDI-ML (product catalog) | `python3 scripts/glovo.py download`, `python3 scripts/glovo.py prepare`, `python3 scripts/glovo.py load` | 565 MB | 2,887,444 |
| OTTO, REES46, Ele.me | see [INSTALLATION.md](INSTALLATION.md) (the earlier data lab) | tens of GB | hundreds of millions |

Each loader checks the file size and SHA-256 before loading and the row count afterwards. The files stay in `data/`, which Git ignores. Each source has its own terms: read [LEGACY-DATASETS.md](LEGACY-DATASETS.md) and [GLOVO.md](GLOVO.md) before redistributing anything.

## 7. Stop, restart and update

```bash
# Stop everything; data and queue are kept
docker compose -f compose.yaml --profile atlas --profile ai stop

# Start again
docker compose -f compose.yaml --profile atlas up -d --wait

# After pulling new code (Python, SQL or web files changed)
git pull
docker compose -f compose.yaml --profile atlas up -d --build --wait
```

A restart keeps ClickHouse data and the pending queue, but it does not resume a simulation: start a new run from the dashboard.

**Never use `docker compose down -v`** unless you really want to delete everything: `-v` removes the volumes with all ClickHouse data and the queue.

If you also run the shared read-only website, rebuild its gateway too after an update. See [SHARING-VERCEL.md](SHARING-VERCEL.md).

## Common problems

| Problem | Solution |
|---|---|
| `docker compose` fails with `dockerDesktopLinuxEngine` or "cannot connect" | Docker Desktop is not running yet. Open it and wait for the engine |
| Port 8124 or 8001 already in use | Another program, or an earlier copy of this project, uses it. `docker ps` shows which container; stop it with `docker stop <name>` |
| `container name "/bd2-clickhouse" is already in use` | Another clone of this repository already created that container. Use that clone, or stop and remove the old container (`docker stop bd2-clickhouse`, `docker rm bd2-clickhouse`): its data volume stays |
| An old stack with Flask and Grafana is running | It is the first version of the project (`docker-compose.yml`). Stop it with `docker compose -f docker-compose.yml down` (without `-v`) |
| `python3` not found | On Windows use `python` |
| `analytics.html` returns 404 | The Atlas image is older than the code. Run the update command of step 7 with `--build` |
| The map is empty | No simulation is running. Start one (step 4). Positions refresh every two seconds |
| The AI customers do nothing | The `ai` profile is not running or the model was not pulled (step 5), or the run already used its 120 model calls |
| A `.sh` script fails with `bad interpreter` on Windows | Line-ending conversion by Git. With no local changes: `git rm -r --cached . -q` then `git reset --hard` |

## Tested

On 11 November 2026 every step of this guide was run in a fresh clone of `main` (`0f9fb83`) with its own Compose project, on Windows 11 with Docker Desktop 29.8.1 and Python 3.12:

| Step | Result |
|---|---|
| 2. Start | Both services healthy in 28 s. The images were already on the computer, so the first download time was not measured |
| 3. Check | 50 unit tests passed (8 integration tests skipped); `check_atlas.py` passed; dashboard, portal, mini-app and `/play` opened |
| 4. Simulation | Started from the dashboard with 200 customers and 80 couriers; rows appeared within seconds |
| 5. AI | Model pulled in 46 s; the first AI decision arrived about 5 s after starting a hybrid run |
| 6. Criteo | 13,979,592 rows loaded and verified in 10 s, from an already downloaded file |

More details: [ATLAS-INFRASTRUCTURE.md](ATLAS-INFRASTRUCTURE.md) (architecture, SQL and API), [TEAM-INSTALL-TESTS.md](TEAM-INSTALL-TESTS.md) (earlier Windows tests) and [AI-CUSTOMERS.md](AI-CUSTOMERS.md).
