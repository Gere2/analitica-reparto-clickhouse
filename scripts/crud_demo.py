"""Demonstrate Python -> ClickHouse INSERT, SELECT, UPDATE and DELETE."""

from __future__ import annotations

import base64
import json
import os
import time
from urllib.request import Request, urlopen

URL = os.environ.get("CLICKHOUSE_URL", "http://127.0.0.1:8124/")
USER = os.environ.get("CLICKHOUSE_USER", "demo")
PASSWORD = os.environ.get("CLICKHOUSE_PASSWORD", "demo")


def execute(sql: str, select: bool = False):
    auth = base64.b64encode(f"{USER}:{PASSWORD}".encode()).decode()
    request = Request(URL, data=(sql + (" FORMAT JSON" if select else "")).encode(),
                      headers={"Authorization": f"Basic {auth}", "Content-Type": "text/plain"})
    with urlopen(request, timeout=90) as response:
        payload = response.read()
    return json.loads(payload)["data"] if select else None


def main() -> None:
    # The billion-row load can keep the small background pool busy with merges.
    # Reserve a short window for the synchronous mutations used in this lesson.
    large_tables = execute(
        "SELECT name FROM system.tables WHERE database = 'delivery' "
        "AND name IN ('otto_archive','otto_scale_benchmark','rees46_events')", True
    )
    paused = []
    try:
        for row in large_tables:
            table = row["name"]
            execute(f"SYSTEM STOP MERGES delivery.{table}")
            paused.append(table)

        execute("CREATE TABLE IF NOT EXISTS delivery.demo_events (event_id UInt64, "
                "recorded_at DateTime DEFAULT now(), section String, action String) "
                "ENGINE = MergeTree ORDER BY event_id")
        event_id = time.time_ns()
        execute(f"INSERT INTO delivery.demo_events (event_id, section, action) VALUES ({event_id}, 'restaurante', 'abrir')")
        print("INSERT:", execute(f"SELECT event_id, section, action FROM delivery.demo_events WHERE event_id = {event_id}", True), flush=True)

        execute(f"ALTER TABLE delivery.demo_events UPDATE action = 'abrir_menu' WHERE event_id = {event_id} SETTINGS mutations_sync = 2")
        print("UPDATE:", execute(f"SELECT event_id, section, action FROM delivery.demo_events WHERE event_id = {event_id}", True), flush=True)

        execute(f"ALTER TABLE delivery.demo_events DELETE WHERE event_id = {event_id} SETTINGS mutations_sync = 2")
        remaining = execute(f"SELECT event_id FROM delivery.demo_events WHERE event_id = {event_id}", True)
        print("DELETE: filas restantes =", len(remaining), flush=True)
        if remaining:
            raise RuntimeError("La eliminación no se reflejó en la consulta")
    finally:
        for table in paused:
            execute(f"SYSTEM START MERGES delivery.{table}")


if __name__ == "__main__":
    main()
