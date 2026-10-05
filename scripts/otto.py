"""Download, validate, load and replay the real OTTO clickstream."""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import sys
import time
import zipfile
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "otto"
ARCHIVE = DATA / "train.zip"
SCHEMA = ROOT / "sql" / "schema.sql"
URL = "https://huggingface.co/datasets/hazemessam/otto-recsys/resolve/main/train.jsonl"
# SHA-256 advertised by the mirror as its linked ETag. The publisher's row counts
# are checked after the full import; the mirror is not represented as the publisher.
SHA256 = "ae11a23676ba29eeeb6e1348b81e353c530da3bc059353cad67247e9616acb2f"
EXPECTED = {"clicks": 194720954, "carts": 16896191, "orders": 5098951}
CH_URL = os.environ.get("CLICKHOUSE_URL", "http://127.0.0.1:8124/")
CH_USER = os.environ.get("CLICKHOUSE_USER", "demo")
CH_PASSWORD = os.environ.get("CLICKHOUSE_PASSWORD", "demo")


def ch(sql: str, body: bytes | None = None, *, timeout: int = 180) -> bytes:
    auth = base64.b64encode(f"{CH_USER}:{CH_PASSWORD}".encode()).decode()
    request = Request(CH_URL, data=(sql.encode() + (b"\n" + body if body else b"")),
                      headers={"Authorization": f"Basic {auth}", "Content-Type": "text/plain"})
    with urlopen(request, timeout=timeout) as response:
        return response.read()


def init() -> None:
    # Multi-statement execution is supported by clickhouse-client, already used by
    # the original project. Execute the new statements separately over HTTP.
    for statement in SCHEMA.read_text().split(";"):
        statement = statement.strip()
        # The daily view is created by rollup.py after the initial bulk load,
        # avoiding thousands of tiny target-table parts during that load.
        if "delivery.otto_daily_rollup_mv" in statement:
            continue
        if statement and ("delivery.otto_" in statement or "delivery.live_clicks" in statement):
            ch(statement)


def digest(path: Path) -> str:
    result = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(8 * 1024 * 1024), b""):
            result.update(chunk)
    return result.hexdigest()


def download() -> None:
    DATA.mkdir(parents=True, exist_ok=True)
    if ARCHIVE.exists() and digest(ARCHIVE) == SHA256:
        print("Archivo ya descargado; SHA-256 correcto.")
        return
    temp = ARCHIVE.with_suffix(".part")
    print("Descargando espejo público OTTO (~2 GB); fuente original: Kaggle/OTTO.", flush=True)
    with urlopen(Request(URL, headers={"User-Agent": "BD2-ClickHouse-demo/1.0"}), timeout=120) as source, temp.open("wb") as output:
        while chunk := source.read(8 * 1024 * 1024):
            output.write(chunk)
    actual = digest(temp)
    if actual != SHA256:
        raise RuntimeError(f"SHA-256 inesperado: {actual}; conserva {temp} para inspección")
    temp.replace(ARCHIVE)
    print(f"SHA-256 verificado: {actual}")


def session_rows(limit: int | None = None):
    if not ARCHIVE.is_file():
        raise FileNotFoundError(f"Falta {ARCHIVE}. Ejecuta: python3 scripts/otto.py download")
    with zipfile.ZipFile(ARCHIVE) as package:
        names = [name for name in package.namelist() if name.endswith(".jsonl")]
        if len(names) != 1:
            raise ValueError(f"El ZIP debe contener un JSONL de entrenamiento: {names}")
        seen = 0
        with package.open(names[0]) as source:
            for line in source:
                record = json.loads(line)
                session = int(record["session"])
                for position, event in enumerate(record["events"]):
                    kind = event["type"]
                    if kind not in EXPECTED:
                        raise ValueError(f"Evento OTTO desconocido: {kind}")
                    millis = int(event["ts"])
                    timestamp = f"{millis // 1000}.{millis % 1000:03d}"
                    yield f"{session}\t{int(event['aid'])}\t{timestamp}\t{kind}\t{position}\n".encode(), kind
                    seen += 1
                    if limit is not None and seen >= limit:
                        return


def load(limit: int | None, reset: bool) -> None:
    init()
    current = int(ch("SELECT count() FROM delivery.otto_archive FORMAT TabSeparated"))
    if reset:
        # The materialized view is active after init(); clear its previous
        # aggregate before replacing the archive to avoid double counting.
        ch("TRUNCATE TABLE delivery.otto_daily_rollup")
        ch("TRUNCATE TABLE delivery.otto_archive")
    elif current:
        if limit is None and current == sum(EXPECTED.values()):
            actual = json.loads(ch("SELECT event_type, count() AS events FROM delivery.otto_archive GROUP BY event_type FORMAT JSON"))
            found = {row["event_type"]: row["events"] for row in actual["data"]}
            if found == EXPECTED:
                print("Archivo OTTO ya cargado y verificado: 216.716.096 eventos.")
                return
        raise RuntimeError(f"otto_archive tiene {current:,} filas. Usa --reset para sustituirlas.")
    counts = dict.fromkeys(EXPECTED, 0)
    batch = []
    for row, kind in session_rows(limit):
        batch.append(row)
        counts[kind] += 1
        if len(batch) >= 100000:
            ch("INSERT INTO delivery.otto_archive (session_id, article_id, event_time, event_type, event_position) FORMAT TabSeparated", b"".join(batch))
            batch.clear()
            total = sum(counts.values())
            if total % 1000000 == 0:
                print(f"Cargados {total:,} eventos...", flush=True)
    if batch:
        ch("INSERT INTO delivery.otto_archive (session_id, article_id, event_time, event_type, event_position) FORMAT TabSeparated", b"".join(batch))
    actual = int(ch("SELECT count() FROM delivery.otto_archive FORMAT TabSeparated"))
    if actual != sum(counts.values()):
        raise RuntimeError(f"Carga incompleta: {actual} filas frente a {sum(counts.values())} procesadas")
    if limit is None and counts != EXPECTED:
        raise RuntimeError(f"El espejo no coincide con los recuentos publicados por OTTO: {counts}")
    print(f"Carga verificada: {actual:,} eventos; {counts}")


def replay(rate: int, limit: int, reset: bool) -> None:
    init()
    if reset:
        ch("TRUNCATE TABLE delivery.otto_replay")
    available = int(ch("SELECT count() FROM delivery.otto_archive FORMAT TabSeparated"))
    if not available:
        raise RuntimeError("Carga primero eventos en delivery.otto_archive")
    target = min(limit, available)
    auth = base64.b64encode(f"{CH_USER}:{CH_PASSWORD}".encode()).decode()
    sql = ("SELECT session_id, article_id, toUnixTimestamp64Milli(event_time), event_type, event_position "
           f"FROM delivery.otto_archive ORDER BY event_time, session_id, event_position LIMIT {target} FORMAT TabSeparated")
    request = Request(CH_URL, data=sql.encode(), headers={"Authorization": f"Basic {auth}"})
    count = 0
    started = time.monotonic()
    batch = []
    with urlopen(request, timeout=600) as response:
        for line in response:
            session, article, millis, kind, position = line.rstrip(b"\n").split(b"\t")
            value = int(millis)
            timestamp = f"{value // 1000}.{value % 1000:03d}".encode()
            batch.append(b"\t".join((session, article, timestamp, kind, position)) + b"\n")
            if len(batch) >= min(rate, 2000):
                ch("INSERT INTO delivery.otto_replay (session_id, article_id, event_time, event_type, event_position) FORMAT TabSeparated", b"".join(batch))
                count += len(batch)
                batch.clear()
                delay = count / rate - (time.monotonic() - started)
                if delay > 0:
                    time.sleep(delay)
                if count % 20000 == 0:
                    print(f"Reproducidos {count:,}/{target:,} eventos", flush=True)
    if batch:
        ch("INSERT INTO delivery.otto_replay (session_id, article_id, event_time, event_type, event_position) FORMAT TabSeparated", b"".join(batch))
        count += len(batch)
    print(f"Finalizado: {count:,} eventos históricos reproducidos en ClickHouse.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    actions = parser.add_subparsers(dest="action", required=True)
    actions.add_parser("download")
    loader = actions.add_parser("load")
    loader.add_argument("--limit", type=int, help="Carga parcial para ensayo; omitir para el conjunto completo")
    loader.add_argument("--reset", action="store_true")
    player = actions.add_parser("replay")
    player.add_argument("--rate", type=int, default=5000, help="Eventos por segundo")
    player.add_argument("--limit", type=int, default=200000)
    player.add_argument("--reset", action="store_true")
    args = parser.parse_args()
    if args.action == "download":
        download()
    elif args.action == "load":
        load(args.limit, args.reset)
    else:
        if args.rate <= 0 or args.limit <= 0:
            parser.error("--rate y --limit deben ser positivos")
        replay(args.rate, args.limit, args.reset)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Interrumpido; usa load --reset para reiniciar una carga parcial.", file=sys.stderr)
        raise SystemExit(130)
