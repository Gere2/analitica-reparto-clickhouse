"""Export every row of one Atlas simulation run from ClickHouse to gzip CSV files plus a summary.

Usage: python scripts/export_run.py <run_id> [--out data/runs/<date>_<run8>]

Stop the run and wait for the Atlas queue to reach pending 0 first, so every accepted event is in ClickHouse.
"""

from __future__ import annotations

import argparse
import base64
import json
import os
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
CLICKHOUSE = os.environ.get("CLICKHOUSE_URL", "http://127.0.0.1:8124/").rstrip("/")
AUTH = base64.b64encode((os.environ.get("CLICKHOUSE_USER", "demo") + ":"
                         + os.environ.get("CLICKHOUSE_PASSWORD", "demo")).encode()).decode()
TABLES = ("app_events", "customer_activity", "customer_orders", "order_events", "courier_positions")
WHERE = "simulation_run_id = {run:UUID}"


def query(run: str, sql: str, fmt: str, gzip: bool = False) -> bytes:
    params = {"param_run": run, **({"enable_http_compression": 1} if gzip else {})}
    headers = {"Authorization": "Basic " + AUTH, **({"Accept-Encoding": "gzip"} if gzip else {})}
    request = Request(CLICKHOUSE + "/?" + urlencode(params), data=f"{sql} FORMAT {fmt}".encode(), headers=headers)
    with urlopen(request, timeout=600) as response:
        return response.read()


def rows(run: str, sql: str) -> list[dict]:
    return json.loads(query(run, sql, "JSON"))["data"]


def export(run: str, target: Path) -> dict:
    # Write into <target>.partial and rename at the end, so a folder named like a run is always complete.
    if target.exists():
        raise SystemExit(f"{target} already exists; not overwriting a saved run")
    folder = target.with_name(target.name + ".partial")
    folder.mkdir(parents=True, exist_ok=True)
    summary = {"run_id": run, "tables": {}}
    for table in TABLES:
        data = query(run, f"SELECT * FROM delivery_atlas.{table} FINAL WHERE {WHERE} ORDER BY event_time",
                     "CSVWithNames", gzip=True)
        (folder / f"{table}.csv.gz").write_bytes(data)
        stats = rows(run, "SELECT count() AS rows, toString(min(event_time)) AS first, toString(max(event_time)) AS last "
                          f"FROM delivery_atlas.{table} FINAL WHERE {WHERE}")[0]
        summary["tables"][table] = {"rows": int(stats["rows"]), "first_event": stats["first"],
                                    "last_event": stats["last"], "file": f"{table}.csv.gz", "bytes": len(data)}
    activity = rows(run, "SELECT uniqExact(customer_id) AS customers, uniqExactIf(customer_id, decision_mode = 'ollama') "
                         "AS ai_customers, countIf(decision_mode = 'ollama') AS ai_decisions "
                         f"FROM delivery_atlas.customer_activity FINAL WHERE {WHERE}")[0]
    couriers = rows(run, f"SELECT uniqExact(courier_id) AS couriers FROM delivery_atlas.courier_positions WHERE {WHERE}")[0]
    summary["participants"] = {key: int(value) for key, value in {**activity, **couriers}.items()}
    summary["orders_by_status"] = rows(run, "SELECT status, count() AS orders FROM delivery_atlas.order_latest "
                                            f"WHERE {WHERE} GROUP BY status ORDER BY orders DESC")
    summary["orders_by_type"] = rows(run, "SELECT decision_mode, toString(source_kind) AS source_kind, count() AS orders, "
                                          "sum(amount_minor) AS amount_minor FROM delivery_atlas.customer_orders FINAL "
                                          f"WHERE {WHERE} GROUP BY decision_mode, source_kind ORDER BY orders DESC")
    (folder / "summary.json").write_bytes((json.dumps(summary, indent=2) + "\n").encode())
    folder.rename(target)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("run_id")
    parser.add_argument("--out", type=Path, help="target folder (default data/runs/<first event date>_<run8>)")
    args = parser.parse_args()
    folder = args.out
    if folder is None:
        day = rows(args.run_id, "SELECT toString(toDate(min(event_time))) AS day "
                                f"FROM delivery_atlas.courier_positions WHERE {WHERE}")[0]["day"]
        folder = ROOT / "data" / "runs" / f"{day}_{args.run_id[:8]}"
    summary = export(args.run_id, folder)
    total = sum(table["rows"] for table in summary["tables"].values())
    print(f"Saved {total:,} rows of run {args.run_id} to {folder}")


if __name__ == "__main__":
    main()
