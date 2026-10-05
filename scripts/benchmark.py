"""Measure reproducible ClickHouse analytics over raw and aggregated event tables."""

from __future__ import annotations

import json
import statistics
from datetime import datetime, timezone
from pathlib import Path

from otto import ch

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "data" / "query-benchmark.json"
SETTINGS = " SETTINGS use_query_cache = 0, max_threads = 4 FORMAT JSON"
QUERIES = {
    "otto_raw_daily": (
        "SELECT toDate(event_time) AS day, event_type, count() AS events "
        "FROM delivery.otto_archive GROUP BY day, event_type ORDER BY day, event_type"
    ),
    "otto_rollup_daily": (
        "SELECT event_date AS day, event_type, sum(events) AS events "
        "FROM delivery.otto_daily_rollup GROUP BY day, event_type ORDER BY day, event_type"
    ),
    "rees46_month": (
        "SELECT event_type, count() AS events FROM delivery.rees46_events "
        "WHERE event_date >= '2019-10-01' AND event_date < '2019-11-01' "
        "GROUP BY event_type ORDER BY event_type"
    ),
    "scale_scenarios": (
        "SELECT scenario, count() AS events FROM delivery.otto_scale_benchmark "
        "GROUP BY scenario ORDER BY scenario"
    ),
}


def measure(sql: str, repeats: int) -> dict:
    runs = []
    reference = None
    for _ in range(repeats):
        response = json.loads(ch(sql + SETTINGS, timeout=600))
        if reference is None:
            reference = response["data"]
        elif reference != response["data"]:
            raise RuntimeError("La misma consulta devolvió resultados diferentes")
        stats = response["statistics"]
        runs.append({"seconds": round(float(stats["elapsed"]), 4),
                     "rows_read": int(stats["rows_read"]),
                     "bytes_read": int(stats["bytes_read"])})
    return {"runs": runs, "median_seconds": round(statistics.median(x["seconds"] for x in runs), 4),
            "result": reference}


def main() -> None:
    counts = {
        "otto_real": int(ch("SELECT count() FROM delivery.otto_archive")),
        "rees46_real": int(ch("SELECT count() FROM delivery.rees46_events")),
        "scale_derived": int(ch("SELECT count() FROM delivery.otto_scale_benchmark")),
    }
    if counts["otto_real"] != 216_716_096:
        raise RuntimeError("Falta el archivo OTTO completo")
    if not counts["rees46_real"] or not counts["scale_derived"]:
        raise RuntimeError("Faltan datos REES46 o la tabla de estrés")
    results = {}
    for name, sql in QUERIES.items():
        result = measure(sql, 3 if name.startswith("otto_") else 1)
        results[name] = result
        print(f"{name}: {result['median_seconds']:.4f} s, "
              f"{result['runs'][0]['rows_read']:,} filas leídas", flush=True)
    if results["otto_raw_daily"]["result"] != results["otto_rollup_daily"]["result"]:
        raise RuntimeError("El agregado diario no coincide con el archivo OTTO")
    parts = json.loads(ch("SELECT table, sum(rows) AS rows, sum(bytes_on_disk) AS bytes_on_disk "
                          "FROM system.parts WHERE active AND database = 'delivery' "
                          "AND table IN ('otto_archive','otto_daily_rollup','rees46_events',"
                          "'otto_scale_benchmark') GROUP BY table ORDER BY table FORMAT JSON"))["data"]
    explain = ch("EXPLAIN indexes = 1 SELECT sum(price) FROM delivery.rees46_events "
                 "WHERE event_date >= '2019-10-01' AND event_date < '2019-11-01'").decode()
    report = {"measured_at_utc": datetime.now(timezone.utc).isoformat(), "counts": counts,
              "environment": "local Docker ClickHouse 25.8; one node; query cache disabled; "
                             "three warm runs for OTTO queries, one run for larger scans",
              "queries": results, "table_parts": parts,
              "explain_rees46_october_partition": explain}
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(f"Informe: {REPORT}")


if __name__ == "__main__":
    main()
