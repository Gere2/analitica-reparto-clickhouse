"""Build a labelled one-billion-row workload from the verified OTTO archive."""

from __future__ import annotations

import argparse
import json
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "data" / "scale-benchmark.json"
BASE = 216_716_096
COPIES = 5
EXPECTED = BASE * COPIES
CLIENT = ["docker", "exec", "bd2-clickhouse", "clickhouse-client", "--user", "demo", "--password", "demo"]


def run(sql: str) -> str:
    result = subprocess.run(CLIENT + ["--query", sql], capture_output=True, text=True)
    if result.returncode:
        raise RuntimeError(result.stderr)
    return result.stdout.strip()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reset", action="store_true", help="Vacía únicamente la tabla de benchmark")
    parser.add_argument("--replace-partial", action="store_true", help="Borra y reconstruye un escenario incompleto")
    args = parser.parse_args()
    source = int(run("SELECT count() FROM delivery.otto_archive"))
    if source != BASE:
        raise RuntimeError(f"Antes de escalar, OTTO debe tener {BASE:,} filas verificadas; tiene {source:,}")
    schema = (ROOT / "sql" / "schema.sql").read_text().split("CREATE TABLE IF NOT EXISTS delivery.otto_scale_benchmark", 1)[1]
    run("CREATE TABLE IF NOT EXISTS delivery.otto_scale_benchmark" + schema.split(";", 1)[0])
    if args.reset:
        run("TRUNCATE TABLE delivery.otto_scale_benchmark")
    print(f"Objetivo: {EXPECTED:,} filas de estrés desde {BASE:,} eventos reales; "
          "los cinco escenarios son sintéticos y se etiquetan por scenario.", flush=True)
    started = time.monotonic()
    # Mutations run in the background and can wait for merges, so repair any
    # partial scenario before pausing ordinary merges for bulk insertion.
    if args.replace_partial:
        for scenario in range(COPIES):
            actual = int(run(f"SELECT count() FROM delivery.otto_scale_benchmark WHERE scenario = {scenario}"))
            if 0 < actual < BASE:
                print(f"Escenario {scenario}: eliminando {actual:,} filas parciales", flush=True)
                run(f"ALTER TABLE delivery.otto_scale_benchmark DELETE WHERE scenario = {scenario} "
                    "SETTINGS mutations_sync = 2")
                if int(run(f"SELECT count() FROM delivery.otto_scale_benchmark WHERE scenario = {scenario}")):
                    raise RuntimeError(f"Escenario {scenario}: la mutación no terminó")
    run("SYSTEM STOP MERGES delivery.otto_scale_benchmark")
    try:
        for scenario in range(COPIES):
            actual = int(run(f"SELECT count() FROM delivery.otto_scale_benchmark WHERE scenario = {scenario}"))
            if actual == BASE:
                print(f"Escenario {scenario}: {actual:,} filas ya verificadas", flush=True)
                continue
            if actual:
                raise RuntimeError(f"Escenario {scenario}: {actual:,} filas parciales. "
                                   "Usa --replace-partial para reconstruirlo o --reset para empezar de cero.")
            query = (
                "INSERT INTO delivery.otto_scale_benchmark "
                f"SELECT toUInt8({scenario}), toUInt64(session_id) + {scenario} * 20000000, "
                f"article_id, addDays(event_time, {scenario} * 35), event_type "
                "FROM delivery.otto_archive SETTINGS max_execution_time = 0, "
                "max_threads = 1, max_insert_threads = 1, max_memory_usage = 1000000000"
            )
            run(query)
            actual = int(run(f"SELECT count() FROM delivery.otto_scale_benchmark WHERE scenario = {scenario}"))
            if actual != BASE:
                raise RuntimeError(f"Escenario {scenario}: se esperaban {BASE:,}, hay {actual:,}")
            print(f"Escenario {scenario}: {actual:,} filas · total {(scenario + 1) * BASE:,}", flush=True)
    finally:
        run("SYSTEM START MERGES delivery.otto_scale_benchmark")
    total = int(run("SELECT count() FROM delivery.otto_scale_benchmark"))
    if total != EXPECTED:
        raise RuntimeError(f"Total incorrecto: {total:,} de {EXPECTED:,}")
    seconds = round(time.monotonic() - started, 2)
    report = {"source": "OTTO historical real events; 5 labelled derived scenarios",
              "observed_real_events": BASE, "scenario_count": COPIES,
              "stress_rows": total, "build_seconds": seconds}
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(report, indent=2) + "\n")
    print(f"Verificado: {total:,} filas derivadas en {seconds} s.")


if __name__ == "__main__":
    main()
