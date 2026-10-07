"""Load the prepared Meituan data into the local ClickHouse container."""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FILES = (
    ("restaurants", "restaurants.tsv"),
    ("foods", "foods.tsv"),
    ("orders", "orders.tsv"),
    ("order_items", "order_items.tsv"),
    ("click_summary", "click_summary.tsv"),
    ("clicks", "clicks.tsv"),
)
CLIENT = ["docker", "exec", "-i", "bd2-clickhouse", "clickhouse-client",
          "--user", "demo", "--password", "demo"]


def command(query: str, *, input_file: Path | None = None, multiquery: bool = False) -> str:
    args = CLIENT + (["--multiquery"] if multiquery else ["--query", query])
    if input_file:
        with input_file.open("rb") as stream:
            result = subprocess.run(args, stdin=stream, text=False, capture_output=True, check=False)
    else:
        result = subprocess.run(args, input=query.encode() if multiquery else None,
                                capture_output=True, check=False)
    if result.returncode:
        raise RuntimeError(result.stderr.decode(errors="replace"))
    return result.stdout.decode().strip()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--reset", action="store_true", help="Truncate only the demo tables before reloading")
    options = parser.parse_args()
    manifest = json.loads((ROOT / "data" / "processed" / "manifest.json").read_text())
    expected = manifest["counts"]
    command("", input_file=ROOT / "sql" / "schema.sql", multiquery=True)

    def target_count(table: str) -> int:
        return expected["click_summaries" if table == "click_summary" else table]

    existing = {table: int(command(f"SELECT count() FROM delivery.{table}")) for table, _ in FILES}
    if all(existing[table] == target_count(table) for table, _ in FILES):
        print("Datos ya cargados y verificados.")
        return
    if any(existing.values()) and not options.reset:
        raise SystemExit("Carga parcial o diferente; vuelve a ejecutar con --reset para limpiar solo estas tablas.")
    if options.reset:
        for table in ("clicks", "daily_clicks", "click_summary", "order_items", "orders", "foods", "restaurants"):
            command(f"TRUNCATE TABLE delivery.{table}")

    for table, filename in FILES:
        path = ROOT / "data" / "processed" / filename
        print(f"Cargando {table}...", flush=True)
        command(f"INSERT INTO delivery.{table} FORMAT TabSeparated", input_file=path)
        actual = int(command(f"SELECT count() FROM delivery.{table}"))
        if actual != target_count(table):
            raise RuntimeError(f"{table}: se esperaban {target_count(table)}, hay {actual}")
        print(f"  {actual:,} filas verificadas", flush=True)
    materialized = int(command("SELECT sum(clicks) FROM delivery.daily_clicks"))
    if materialized != expected["clicks"]:
        raise RuntimeError(f"La vista materializada suma {materialized}, se esperaban {expected['clicks']}")
    print(f"Vista materializada verificada: {materialized:,} clics.")


if __name__ == "__main__":
    main()
