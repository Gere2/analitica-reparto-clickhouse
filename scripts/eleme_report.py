"""Audit Ele.me and compare the same click count using a typed column vs raw JSON."""
from __future__ import annotations

import json
import argparse
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from statistics import median

ROOT = Path(__file__).resolve().parents[1]
CLIENT = ["docker", "exec", "bd2-clickhouse", "clickhouse-client", "--user", "demo", "--password", "demo"]


def query(sql: str) -> dict:
    output = subprocess.run(CLIENT + ["--query", sql + " FORMAT JSON"],
                            capture_output=True, text=True)
    if output.returncode:
        raise RuntimeError(output.stderr.strip())
    return json.loads(output.stdout)


def command(sql: str) -> None:
    subprocess.run(CLIENT + ["--query", sql], capture_output=True, text=True, check=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--include-raw', action='store_true',
                        help='Intentar además la lectura completa de JSON; puede superar la memoria de Docker.')
    args = parser.parse_args()
    metrics = query("SELECT count() AS samples, sum(clicked) AS positive_clicks, "
                    "uniqCombined64(user_id) AS users_approx, uniqCombined64(shop_id) AS shops_approx, "
                    "min(toUInt64OrNull(request_time_raw)) AS min_unix, "
                    "max(toUInt64OrNull(request_time_raw)) AS max_unix, "
                    "countIf(toUInt64OrNull(request_time_raw) IS NULL) AS invalid_unix "
                    "FROM delivery.eleme_samples SETTINGS max_threads=1")["data"][0]
    if not int(metrics["samples"]):
        raise SystemExit("Ele.me no tiene archivos completos publicados. Espera a terminar la carga.")
    settings = (" SETTINGS use_query_cache=0, max_threads=1, max_block_size=256, "
                "preferred_block_size_bytes=1048576, preferred_max_column_in_block_size_bytes=1048576, "
                "max_read_buffer_size=262144, max_read_buffer_size_local_fs=262144, "
                "max_memory_usage=1000000000")
    queries = {
        "typed_clicks": "SELECT sum(clicked) AS clicks FROM delivery.eleme_samples",
    }
    if args.include_raw:
        queries['raw_json_clicks'] = "SELECT countIf(JSONExtractString(raw_features, 'clicked')='1') AS clicks FROM delivery.eleme_samples"
    report = {"measured_at_utc": datetime.now(timezone.utc).isoformat(), "metrics": metrics,
              "conditions": "One local node; one query thread; SQL query cache off; filesystem caches not cleared; three sequential runs. Ele.me merges paused during measurement.",
              "queries": {}, "raw_requested_this_run": args.include_raw,
              "columns": query("SELECT name, type, data_compressed_bytes, data_uncompressed_bytes "
                               "FROM system.columns WHERE database='delivery' AND table='eleme_samples' "
                               "ORDER BY data_compressed_bytes DESC")["data"]}
    stopped = []
    try:
        for table in ("eleme_samples", "eleme_staging"):
            command(f"SYSTEM STOP MERGES delivery.{table}")
            stopped.append(table)
        for _ in range(60):
            active = query("SELECT count() AS merges FROM system.merges WHERE database='delivery' "
                           "AND table IN ('eleme_samples','eleme_staging')")["data"][0]["merges"]
            if not int(active):
                break
            time.sleep(1)
        else:
            raise RuntimeError("Persisten fusiones Ele.me; no se mide bajo esas condiciones.")
        # A completed archive is required. No partial fixture or generated rows are used.
        for name, sql in queries.items():
            runs = []
            for _ in range(3):
                try:
                    result = query(sql + settings)
                except RuntimeError as error:
                    report['queries'][name] = {'sql': sql + settings, 'runs': runs,
                                               'status': 'failed', 'error': str(error)}
                    print(name, 'failed:', str(error), flush=True)
                    break
                if int(result["data"][0]["clicks"]) != int(metrics["positive_clicks"]):
                    raise RuntimeError("El conteo bruto y el tipado no son iguales.")
                runs.append(result["statistics"])
            if len(runs) != 3:
                continue
            report["queries"][name] = {"sql": sql + settings, "runs": runs, "status": "success",
                                       "median_seconds": median(r["elapsed"] for r in runs)}
            print(name, report["queries"][name]["median_seconds"], flush=True)
    finally:
        for table in stopped:
            command(f"SYSTEM START MERGES delivery.{table}")
    report["same_result_verified"] = all(
        report['queries'].get(name, {}).get('status') == 'success'
        for name in ('typed_clicks', 'raw_json_clicks'))
    report['previous_raw_failure'] = query(
        "SELECT event_time, query_id, exception, memory_usage, read_rows, read_bytes "
        "FROM system.query_log WHERE type='ExceptionWhileProcessing' "
        "AND query LIKE 'SELECT countIf(JSONExtractString%' "
        "ORDER BY event_time DESC LIMIT 1")["data"]
    target = ROOT / "data/eleme-benchmark.json"
    target.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print("Informe:", target)


if __name__ == "__main__":
    main()
