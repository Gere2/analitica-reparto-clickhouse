"""Backfill and verify the OTTO daily materialized-view target."""

import argparse
import json

from otto import SCHEMA, ch, init


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reset", action="store_true", help="Rebuild the daily aggregate from the archive")
    args = parser.parse_args()
    init()
    for statement in SCHEMA.read_text().split(";"):
        if "delivery.otto_daily_rollup_mv" in statement:
            ch(statement.strip())
            break
    else:
        raise RuntimeError("No se encontró la definición de la vista materializada")
    archive = int(ch("SELECT count() FROM delivery.otto_archive"))
    current = int(ch("SELECT sum(events) FROM delivery.otto_daily_rollup"))
    if args.reset:
        ch("TRUNCATE TABLE delivery.otto_daily_rollup")
        current = 0
    if current == 0 and archive:
        ch("INSERT INTO delivery.otto_daily_rollup "
           "SELECT toDate(event_time) AS event_date, event_type, count() AS events "
           "FROM delivery.otto_archive GROUP BY event_date, event_type", timeout=600)
    result = json.loads(ch("SELECT sum(events) AS events, count() AS rows "
                           "FROM delivery.otto_daily_rollup FORMAT JSON"))["data"][0]
    if int(result["events"]) != archive:
        raise RuntimeError(f"Rollup {result['events']} != archivo {archive}; usa --reset")
    print(f"Archivo: {archive:,} eventos. Rollup: {result['rows']} filas, {result['events']:,} eventos.")


if __name__ == "__main__":
    main()
