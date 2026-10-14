"""Download and load the seven real REES46 marketplace event files."""

from __future__ import annotations

import argparse
import gzip
import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "rees46"
MANIFEST = DATA / "manifest.json"
SOURCE = "https://data.rees46.com/datasets/marketplace"
# Content-Length values checked against the publisher's server on 2026-10-04.
MONTHS = {
    "2019-Oct": 1741928540,
    "2019-Nov": 2890421023,
    "2019-Dec": 2951549375,
    "2020-Jan": 2390063923,
    "2020-Feb": 2347087112,
    "2020-Mar": 2417362205,
    "2020-Apr": 2929933389,
}
PARTITION = {"2019-Oct": 201910, "2019-Nov": 201911, "2019-Dec": 201912,
             "2020-Jan": 202001, "2020-Feb": 202002, "2020-Mar": 202003,
             "2020-Apr": 202004}
CLIENT = ["docker", "exec", "bd2-clickhouse", "clickhouse-client", "--user", "demo", "--password", "demo"]
INSERT = (
    "INSERT INTO delivery.rees46_events "
    "(event_time,event_type,product_id,category_id,category_code,brand,price,user_id,user_session) "
    "SELECT parseDateTimeBestEffort(event_time),event_type,product_id,category_id,"
    "category_code,brand,price,user_id,user_session "
    "FROM input('event_time String, event_type String, product_id UInt64, category_id UInt64, "
    "category_code String, brand String, price Decimal(12,2), user_id UInt64, user_session String') "
    "SETTINGS max_threads = 1, max_insert_threads = 1, max_memory_usage = 1000000000 "
    "FORMAT CSV"
)
BATCH_ROWS = 200_000
HEADER = b"event_time,event_type,product_id,category_id,category_code,brand,price,user_id,user_session"


def run(sql: str) -> str:
    result = subprocess.run(CLIENT + ["--query", sql], capture_output=True, text=True)
    if result.returncode:
        raise RuntimeError(result.stderr)
    return result.stdout.strip()


def download(months: list[str]) -> None:
    DATA.mkdir(parents=True, exist_ok=True)
    for month in months:
        path = DATA / f"{month}.csv.gz"
        expected = MONTHS[month]
        if path.is_file() and path.stat().st_size == expected:
            print(f"{month}: archivo completo ({expected:,} bytes)", flush=True)
            continue
        print(f"Descargando {month}...", flush=True)
        subprocess.run(["curl", "-fL", "--retry", "3", "-C", "-", "--output", str(path),
                        f"{SOURCE}/{month}.csv.gz"], check=True)
        if path.stat().st_size != expected:
            raise RuntimeError(f"{month}: tamaño {path.stat().st_size}, esperado {expected}")


def rows_for(month: str) -> int:
    return int(run(f"SELECT count() FROM delivery.rees46_events WHERE toYYYYMM(event_date) = {PARTITION[month]}"))


def insert_file(path: Path, month: str, start_rows: int = 0) -> int:
    inserted = start_rows
    batch: list[bytes] = []
    with gzip.open(path, "rb") as source:
        header = source.readline().rstrip(b"\r\n")
        if header != HEADER:
            raise RuntimeError(f"{month}: cabecera CSV inesperada: {header[:160]!r}")
        for _ in range(start_rows):
            if not source.readline():
                raise RuntimeError(f"{month}: el CSV termina antes del punto de reanudación {start_rows:,}")
        for line in source:
            batch.append(line)
            if len(batch) >= BATCH_ROWS:
                payload = b"".join(batch)
                loader = subprocess.run(["docker", "exec", "-i", "bd2-clickhouse", "clickhouse-client",
                                         "--user", "demo", "--password", "demo", "--query", INSERT],
                                        input=payload, capture_output=True)
                if loader.returncode:
                    raise RuntimeError(f"{month}: inserción fallida tras {inserted:,} filas: "
                                       f"{loader.stderr.decode(errors='replace')}")
                inserted += len(batch)
                batch.clear()
                if inserted % 5_000_000 < BATCH_ROWS:
                    print(f"{month}: {inserted:,} filas insertadas...", flush=True)
        if batch:
            loader = subprocess.run(["docker", "exec", "-i", "bd2-clickhouse", "clickhouse-client",
                                     "--user", "demo", "--password", "demo", "--query", INSERT],
                                    input=b"".join(batch), capture_output=True)
            if loader.returncode:
                raise RuntimeError(f"{month}: inserción final fallida tras {inserted:,} filas: "
                                   f"{loader.stderr.decode(errors='replace')}")
            inserted += len(batch)
    return inserted


def _load_unmanaged(months: list[str], reset: bool, replace_partial: bool, resume_partial: bool) -> None:
    DATA.mkdir(parents=True, exist_ok=True)
    run("CREATE DATABASE IF NOT EXISTS delivery")
    schema = (ROOT / "sql" / "schema.sql").read_text().split("CREATE TABLE IF NOT EXISTS delivery.rees46_events", 1)[1]
    run("CREATE TABLE IF NOT EXISTS delivery.rees46_events" + schema.split(";", 1)[0])
    manifest = json.loads(MANIFEST.read_text()) if MANIFEST.exists() else {}
    if reset:
        run("TRUNCATE TABLE delivery.rees46_events")
        manifest = {}
        MANIFEST.unlink(missing_ok=True)
    for month in months:
        path = DATA / f"{month}.csv.gz"
        if not path.is_file() or path.stat().st_size != MONTHS[month]:
            raise FileNotFoundError(f"Falta {path} completo. Ejecuta: python3 scripts/rees46.py download")
        current = rows_for(month)
        if current and manifest.get(month, {}).get("rows") == current:
            manifest[month]["compressed_bytes"] = MONTHS[month]
            MANIFEST.write_text(json.dumps(manifest, indent=2) + "\n")
            print(f"{month}: {current:,} filas ya verificadas", flush=True)
            continue
        if current:
            if resume_partial:
                if current % BATCH_ROWS:
                    raise RuntimeError(f"{month}: {current:,} filas no coincide con un lote completo; "
                                       "usa --replace-partial para reconstruir el mes")
                print(f"{month}: reanudando desde {current:,} filas verificadas en ClickHouse", flush=True)
            elif not replace_partial:
                raise RuntimeError(f"{month}: hay {current:,} filas sin manifiesto válido. "
                                   "Usa --resume-partial si todos los lotes terminaron o "
                                   "--replace-partial para reconstruir este mes.")
            else:
                print(f"{month}: eliminando únicamente la partición parcial ({current:,} filas)", flush=True)
                run(f"ALTER TABLE delivery.rees46_events DROP PARTITION {PARTITION[month]}")
                if rows_for(month):
                    raise RuntimeError(f"{month}: la partición parcial no quedó vacía")
                current = 0
        print(f"Cargando {month}...", flush=True)
        inserted = insert_file(path, month, current)
        counts = json.loads(run("SELECT count() AS rows, countIf(event_type = 'view') AS views, "
                               "countIf(event_type = 'cart') AS carts, "
                               "countIf(event_type = 'remove_from_cart') AS removals, "
                               "countIf(event_type = 'purchase') AS purchases "
                               f"FROM delivery.rees46_events WHERE toYYYYMM(event_date) = {PARTITION[month]} "
                               "FORMAT JSON"))["data"][0]
        if int(counts["rows"]) != inserted:
            raise RuntimeError(f"{month}: ClickHouse tiene {counts['rows']:,} filas y el CSV {inserted:,}")
        counts["compressed_bytes"] = MONTHS[month]
        manifest[month] = counts
        MANIFEST.write_text(json.dumps(manifest, indent=2) + "\n")
        print(f"{month}: {counts['rows']:,} filas; {counts['views']:,} vistas; "
              f"{counts['purchases']:,} compras", flush=True)
    print(f"Total verificado: {sum(item['rows'] for item in manifest.values()):,} eventos", flush=True)


def load(months: list[str], reset: bool, replace_partial: bool, resume_partial: bool) -> None:
    DATA.mkdir(parents=True, exist_ok=True)
    run("CREATE DATABASE IF NOT EXISTS delivery")
    schema = (ROOT / "sql" / "schema.sql").read_text().split("CREATE TABLE IF NOT EXISTS delivery.rees46_events", 1)[1]
    run("CREATE TABLE IF NOT EXISTS delivery.rees46_events" + schema.split(";", 1)[0])
    run("SYSTEM STOP MERGES delivery.rees46_events")
    try:
        retries = 0
        while True:
            try:
                _load_unmanaged(months, reset, replace_partial, resume_partial)
                break
            except RuntimeError as error:
                if "MEMORY_LIMIT_EXCEEDED" not in str(error) or retries >= 10:
                    raise
                retries += 1
                print(f"ClickHouse llegó al límite de memoria; reanudando desde el último "
                      f"lote completo (intento {retries}/10).", flush=True)
                reset, replace_partial, resume_partial = False, False, True
                time.sleep(2)
    finally:
        run("SYSTEM START MERGES delivery.rees46_events")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("download", "load", "status"))
    parser.add_argument("--month", choices=MONTHS, help="Un mes; por defecto todos")
    parser.add_argument("--reset", action="store_true", help="Solo para load: vacía la tabla REES46")
    recovery = parser.add_mutually_exclusive_group()
    recovery.add_argument("--replace-partial", action="store_true", help="Reconstruye solo los meses con filas no verificadas")
    recovery.add_argument("--resume-partial", action="store_true", help="Reanuda desde el último lote completo de 200.000 filas")
    args = parser.parse_args()
    months = [args.month] if args.month else list(MONTHS)
    if args.action == "download":
        download(months)
    elif args.action == "load":
        load(months, args.reset, args.replace_partial, args.resume_partial)
    else:
        print(MANIFEST.read_text() if MANIFEST.exists() else "Todavía no hay meses verificados.")


if __name__ == "__main__":
    try:
        main()
    except (RuntimeError, FileNotFoundError, subprocess.CalledProcessError) as error:
        print(error, file=sys.stderr)
        raise SystemExit(1)
