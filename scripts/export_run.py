"""Export every row of one Atlas simulation run from ClickHouse to gzip CSV files plus a summary.

Usage: python scripts/export_run.py <run_id> [--out data/runs/<date>_<run8>]

Stop the run and wait for the Atlas queue to reach pending 0 first, so every accepted event is in ClickHouse.
"""

from __future__ import annotations

import argparse
import base64
import csv
import gzip
import hashlib
import json
import os
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from uuid import UUID, uuid4

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


def inspect_csv(path: Path, run: str) -> int:
    """Read through gzip CRC/EOF and count CSV records, including quoted newlines."""
    count = 0
    with gzip.open(path, "rt", encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        if not reader.fieldnames or "simulation_run_id" not in reader.fieldnames:
            raise ValueError(f"Missing run column in {path.name}")
        if len(set(reader.fieldnames)) != len(reader.fieldnames):
            raise ValueError(f"Duplicate CSV columns in {path.name}")
        for row in reader:
            if None in row or None in row.values() or row["simulation_run_id"] != run:
                raise ValueError(f"Malformed or wrong-run CSV record in {path.name}")
            count += 1
    return count


def verify_saved(target: Path, run: str) -> dict:
    summary = json.loads((target / "summary.json").read_text(encoding="utf-8"))
    if summary["run_id"] != run or set(summary["tables"]) != set(TABLES):
        raise ValueError(f"{target}: incomplete or wrong-run manifest")
    for table in TABLES:
        info = summary["tables"][table]
        if info["file"] != f"{table}.csv.gz":
            raise ValueError("Unexpected export filename")
        path = target / info["file"]
        if path.stat().st_size != info["bytes"] or inspect_csv(path, run) != info["rows"]:
            raise ValueError(f"{path}: export does not match its manifest")
        if info.get("sha256"):
            with path.open("rb") as stream:
                digest = hashlib.file_digest(stream, "sha256").hexdigest() if hasattr(hashlib, "file_digest") else None
            if digest is None:
                check = hashlib.sha256()
                with path.open("rb") as stream:
                    for block in iter(lambda: stream.read(1024 * 1024), b""): check.update(block)
                digest = check.hexdigest()
            if digest != info["sha256"]:
                raise ValueError(f"{path}: SHA-256 differs")
    return summary


def table_stats(run: str, table: str) -> dict:
    return rows(run, "SELECT count() AS rows, toString(min(event_time)) AS first, toString(max(event_time)) AS last "
                f"FROM delivery_atlas.{table} FINAL WHERE {WHERE}")[0]


def stream_table(run: str, table: str, path: Path) -> tuple[int, str]:
    params = {"param_run": run, "enable_http_compression": 1}
    sql = f"SELECT * FROM delivery_atlas.{table} FINAL WHERE {WHERE} ORDER BY event_time FORMAT CSVWithNames"
    request = Request(CLICKHOUSE + "/?" + urlencode(params), data=sql.encode(),
                      headers={"Authorization": "Basic " + AUTH, "Accept-Encoding": "gzip"})
    digest, size = hashlib.sha256(), 0
    with urlopen(request, timeout=600) as response, path.open("wb") as output:
        if response.headers.get("Content-Encoding", "").lower() != "gzip":
            raise ValueError("Expected gzip HTTP response; export is not complete")
        for block in iter(lambda: response.read(1024 * 1024), b""):
            output.write(block); digest.update(block); size += len(block)
    return size, digest.hexdigest()


def export(run: str, target: Path) -> dict:
    run = str(UUID(run))
    target.parent.mkdir(parents=True, exist_ok=True)
    lock = target.with_name(target.name + ".export-lock")
    # Never let two watchdogs/exporters write the same final archive concurrently.
    lock.mkdir()
    try:
        if target.exists():
            return verify_saved(target, run)
        return export_new(run, target)
    finally:
        lock.rmdir()


def export_new(run: str, target: Path) -> dict:
    # Failed attempts remain separate for inspection; a retry never reuses their files.
    folder = target.with_name(target.name + ".partial-" + uuid4().hex[:8])
    folder.mkdir()
    summary = {"run_id": run, "tables": {}}
    for table in TABLES:
        stats = table_stats(run, table)
        path = folder / f"{table}.csv.gz"
        size, digest = stream_table(run, table, path)
        if inspect_csv(path, run) != int(stats["rows"]) or table_stats(run, table) != stats:
            raise ValueError(f"{table}: CSV count differs or source changed during export")
        summary["tables"][table] = {"rows": int(stats["rows"]), "first_event": stats["first"],
                                    "last_event": stats["last"], "file": path.name, "bytes": size,
                                    "sha256": digest}
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
    if target.exists():
        raise FileExistsError(f"{target} appeared during export; not replacing it")
    folder.rename(target)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("run_id", type=lambda value: str(UUID(value)))
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
