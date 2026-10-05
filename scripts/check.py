"""Audit counts, provenance and aggregate integrity before the live demo."""

import json

from otto import EXPECTED, ch
from rees46 import DATA, MANIFEST, MONTHS, PARTITION
from scale import BASE, COPIES


def rows(sql: str) -> list[dict]:
    return json.loads(ch(sql + " FORMAT JSON", timeout=600))["data"]


def main() -> None:
    otto = {item["event_type"]: int(item["events"]) for item in rows(
        "SELECT event_type, count() AS events FROM delivery.otto_archive GROUP BY event_type")}
    if otto != EXPECTED:
        raise RuntimeError(f"OTTO no coincide con la publicación: {otto}")
    total_otto = sum(otto.values())
    rollup = int(rows("SELECT sum(events) AS events FROM delivery.otto_daily_rollup")[0]["events"])
    if rollup != total_otto:
        raise RuntimeError(f"Vista materializada: {rollup} frente a {total_otto}")
    logical_keys = len(rows("SELECT event_date, event_type FROM delivery.otto_daily_rollup "
                            "GROUP BY event_date, event_type"))
    if logical_keys != 87:
        raise RuntimeError(f"Se esperaban 87 claves día/tipo y hay {logical_keys}")

    manifest = json.loads(MANIFEST.read_text())
    if set(manifest) != set(MONTHS):
        raise RuntimeError(f"REES46 incompleto: {list(manifest)}")
    monthly = {int(item["month"]): int(item["events"]) for item in rows(
        "SELECT toYYYYMM(event_date) AS month, count() AS events "
        "FROM delivery.rees46_events GROUP BY month")}
    for month in MONTHS:
        path = DATA / f"{month}.csv.gz"
        if not path.is_file() or path.stat().st_size != MONTHS[month]:
            raise RuntimeError(f"{month}: archivo de origen ausente o tamaño distinto")
        expected = int(manifest[month]["rows"])
        if int(manifest[month].get("compressed_bytes", 0)) != MONTHS[month]:
            raise RuntimeError(f"{month}: tamaño comprimido ausente o incorrecto en manifiesto")
        found = monthly.get(PARTITION[month], 0)
        if found != expected:
            raise RuntimeError(f"{month}: ClickHouse {found} != manifiesto {expected}")
    total_rees = sum(monthly.values())

    scenarios = {int(item["scenario"]): int(item["events"]) for item in rows(
        "SELECT scenario, count() AS events FROM delivery.otto_scale_benchmark GROUP BY scenario")}
    if scenarios != {i: BASE for i in range(COPIES)}:
        raise RuntimeError(f"La tabla derivada está incompleta: {scenarios}")
    print(f"OTTO real: {total_otto:,} eventos ({otto['clicks']:,} clics)")
    print(f"REES46 real: {total_rees:,} eventos en 7 meses")
    print(f"Total de ambas fuentes reales: {total_otto + total_rees:,} eventos separados")
    print(f"Agregado OTTO: {logical_keys} claves y {rollup:,} eventos")
    print(f"Prueba derivada: {sum(scenarios.values()):,} filas en {COPIES} escenarios")
    print("Todos los recuentos y procedencias verificados.")


if __name__ == "__main__":
    main()
