"""Ele.me staged importer. D1_0.csv layout inspected against the published order.

No source data is generated. ZIP members are streamed without extraction.
Run inspect, verify the publisher's layout, then load with --confirm-layout.
"""
from __future__ import annotations

import argparse
import base64
import csv
import fcntl
import hashlib
import io
import json
import os
import re
import subprocess
import sys
import zipfile
from contextlib import contextmanager
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
CLIENT = ["docker", "exec", "bd2-clickhouse", "clickhouse-client", "--user", "demo", "--password", "demo"]
FIELDS = (
    "clicked user_id gender visit_city avg_price is_supervip ctr_30 ord_30 total_amt_30 "
    "shop_id item_id city_id district_id shop_aoi_id shop_geohash_6 shop_geohash_12 "
    "brand_id category_1_id merge_standard_food_id rank_7 rank_30 rank_90 "
    "shop_id_list item_id_list category_1_id_list merge_standard_food_id_list "
    "brand_id_list price_list shop_aoi_id_list shop_geohash6_list timediff_list "
    "hours_list time_type_list weekdays_list times hours time_type weekdays geohash12"
).split()
DELIMITERS = {"tab": "\t", "comma": ",", "pipe": "|", "ctrl-a": "\x01"}
csv.field_size_limit(16 * 1024 * 1024)


def run(sql: str) -> str:
    result = subprocess.run(CLIENT + ["--query", sql], capture_output=True, text=True)
    if result.returncode:
        raise RuntimeError(result.stderr.strip())
    return result.stdout.strip()


def init() -> None:
    result = subprocess.run(CLIENT[:2] + ["-i"] + CLIENT[2:] + ["--multiquery"], input=(ROOT / "sql/eleme.sql").read_text(),
                            capture_output=True, text=True)
    if result.returncode:
        raise RuntimeError(result.stderr.strip())


def member_names(path: Path) -> list[str | None]:
    if zipfile.is_zipfile(path):
        with zipfile.ZipFile(path) as archive:
            names = [n.filename for n in archive.infolist()
                     if not n.is_dir() and not n.filename.startswith(("__MACOSX/", "."))
                     and Path(n.filename).suffix.lower() in {".csv", ".tsv", ".txt"}]
        if not names:
            raise ValueError("ZIP sin miembros CSV/TSV/TXT. Inspecciona el archivo antes de cargar.")
        return names
    if path.suffix.lower() == ".zip":
        raise ValueError("ZIP inválido o descarga incompleta.")
    return [None]


@contextmanager
def open_text(path: Path, member: str | None):
    if member is None:
        with path.open(encoding="utf-8-sig", newline="") as source:
            yield source
    else:
        with zipfile.ZipFile(path) as archive, archive.open(member) as raw:
            with io.TextIOWrapper(raw, encoding="utf-8-sig", newline="") as source:
                yield source


def delimiter_for(path: Path, member: str | None, selected: str) -> str:
    if selected != "auto":
        return DELIMITERS[selected]
    candidates = []
    for name, delimiter in DELIMITERS.items():
        with open_text(path, member) as source:
            rows = list(next(csv.reader(source, delimiter=delimiter), []) for _ in range(3))
        if rows and all(len(row) == len(FIELDS) for row in rows if row):
            candidates.append(name)
    if len(candidates) != 1:
        raise ValueError("No se identifica un único separador con 39 campos. "
                         "El formato publicado debe comprobarse; no se adivinará otro esquema.")
    return DELIMITERS[candidates[0]]


def project(row: list[str], source_id: str, filename: str, index: int, day: int) -> dict:
    if len(row) != len(FIELDS):
        raise ValueError(f"Fila {index}: {len(row)} campos; se esperaban {len(FIELDS)}.")
    fields = dict(zip(FIELDS, row))
    if fields["clicked"] not in {"0", "1"}:
        raise ValueError(f"Fila {index}: etiqueta de clic distinta de 0/1.")
    try:
        hour = int(fields["hours"])
    except ValueError:
        raise ValueError(f"Fila {index}: hours no es un entero.") from None
    if not 0 <= hour <= 23:
        raise ValueError(f"Fila {index}: hours fuera de 0–23; verifica su codificación.")
    return {"source_id": source_id, "source_file": filename, "source_row": index,
            "sample_day": day, "clicked": int(fields["clicked"]),
            "user_id": fields["user_id"], "shop_id": fields["shop_id"], "item_id": fields["item_id"],
            "city_id": fields["city_id"], "district_id": fields["district_id"],
            "category_id": fields["category_1_id"], "request_hour": hour,
            "weekday": fields["weekdays"], "meal_period": fields["time_type"],
            "request_time_raw": fields["times"],
            "raw_features": json.dumps(fields, ensure_ascii=False, separators=(",", ":"))}


def inspect(path: Path, selected: str) -> None:
    for member in member_names(path):
        delimiter = delimiter_for(path, member, selected)
        with open_text(path, member) as source:
            reader = csv.reader(source, delimiter=delimiter)
            rows = [row for _, row in zip(range(3), reader)]
        print(json.dumps({"file": path.name, "member": member, "delimiter": repr(delimiter),
                          "field_counts": [len(row) for row in rows],
                          "expected_fields": FIELDS,
                          "warning": "39 campos no prueban el orden. Verifica cabecera o documentación del archivo."},
                         ensure_ascii=False, indent=2))


def insert(batch: list[bytes]) -> None:
    columns = ("source_id,source_file,source_row,sample_day,clicked,user_id,shop_id,item_id,"
               "city_id,district_id,category_id,request_hour,weekday,meal_period,request_time_raw,raw_features")
    sql = (f"INSERT INTO delivery.eleme_staging ({columns}) "
           "SETTINGS max_threads=1, max_insert_threads=1, max_memory_usage=1000000000, "
           "max_insert_block_size=4096, max_block_size=4096, input_format_parallel_parsing=0 "
           "FORMAT JSONEachRow")
    payload = sql.encode() + b"\n" + b"".join(batch)
    user = os.environ.get("CLICKHOUSE_USER", "demo")
    password = os.environ.get("CLICKHOUSE_PASSWORD", "demo")
    auth = base64.b64encode(f"{user}:{password}".encode()).decode()
    request = Request(os.environ.get("CLICKHOUSE_URL", "http://127.0.0.1:8124/"), data=payload,
                      headers={"Authorization": f"Basic {auth}", "Content-Type": "text/plain"})
    try:
        with urlopen(request, timeout=120) as response:
            body = response.read()
            if body.strip():
                raise RuntimeError(body.decode(errors="replace"))
    except HTTPError as error:
        raise RuntimeError(error.read().decode(errors="replace")) from None


def load(path: Path, selected: str, day: int | None, confirmed: bool, resume: bool = False) -> None:
    if not confirmed:
        raise ValueError("Carga pendiente de comprobar el orden real: primero inspect; "
                         "usa --confirm-layout solo después de verificar los 39 campos.")
    match = re.search(r"(?:^|[_-])D([1-8])(?:[_\.-]|$)", path.name, re.I)
    if match and day is not None and day != int(match[1]):
        raise ValueError("--day no coincide con el día del nombre de archivo oficial.")
    day = day or (int(match[1]) if match else None)
    if day not in range(1, 9):
        raise ValueError("Indica --day 1..8; el día relativo no se convierte en una fecha inventada.")
    init()
    archive_hash = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(8 * 1024 * 1024), b""):
            archive_hash.update(chunk)
    manifest_path = ROOT / "data/eleme/manifest.json"
    manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else {}
    for member in member_names(path):
        token = hashlib.sha256((archive_hash.hexdigest() + "\0" + (member or "")).encode()).hexdigest()
        existing = int(run(f"SELECT count() FROM delivery.eleme_samples WHERE source_id='{token}'"))
        if existing:
            print(f"{path.name}/{member or ''}: ya publicado, {existing:,} filas; omitido.", flush=True)
            continue
        resume_row = 0
        total = 0
        if resume:
            stats = json.loads(run(f"SELECT count() AS rows, uniqExact(source_row) AS unique_rows, "
                                   f"min(source_row) AS first_row, max(source_row) AS last_row "
                                   f"FROM delivery.eleme_staging WHERE source_id='{token}' FORMAT JSONEachRow"))
            total = int(stats["rows"])
            if total:
                if (total != int(stats["unique_rows"]) or
                    total != int(stats["last_row"]) - int(stats["first_row"]) + 1 or
                    int(stats["first_row"]) not in {1, 2}):
                    raise RuntimeError("Staging no es una secuencia completa sin duplicados; no se reanuda.")
                resume_row = int(stats["last_row"])
                print(f"Reanudando {total:,} filas confirmadas; saltando hasta source_row={resume_row}.", flush=True)
        else:
            run(f"ALTER TABLE delivery.eleme_staging DROP PARTITION '{token}'")
        delimiter = delimiter_for(path, member, selected)
        batch = []
        batch_bytes = 0
        with open_text(path, member) as source:
            for index, row in enumerate(csv.reader(source, delimiter=delimiter), 1):
                # Exact known headers only. Other layouts fail rather than dropping rows.
                if index == 1 and row in [FIELDS, ["label"] + FIELDS[1:], ["ctr"] + FIELDS[1:]]:
                    continue
                if index <= resume_row:
                    continue
                projected = project(row, token, path.name + (":" + member if member else ""), index, day)
                encoded = (json.dumps(projected, ensure_ascii=False, separators=(",", ":")) + "\n").encode()
                batch.append(encoded)
                batch_bytes += len(encoded)
                total += 1
                if len(batch) >= 25_000 or batch_bytes >= 32 * 1024 * 1024:
                    insert(batch)
                    batch.clear()
                    batch_bytes = 0
                    print(f"{path.name}: {total:,} filas validadas en staging", flush=True)
            if batch:
                insert(batch)
        if total == 0:
            raise ValueError("Archivo sin muestras.")
        staged = int(run(f"SELECT count() FROM delivery.eleme_staging WHERE source_id='{token}'"))
        if staged != total:
            raise RuntimeError(f"Recuento staging {staged} distinto de leídas {total}; no se publica.")
        run(f"ALTER TABLE delivery.eleme_staging MOVE PARTITION '{token}' TO TABLE delivery.eleme_samples")
        manifest[token] = {"archive_sha256": archive_hash.hexdigest(), "file": path.name,
                           "member": member, "rows": total, "day": day, "layout_confirmed_by_operator": True}
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
        print(f"Publicado: {total:,} muestras del archivo aportado.", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["init", "inspect", "load", "status"])
    parser.add_argument("path", nargs="?", type=Path)
    parser.add_argument("--delimiter", choices=["auto", *DELIMITERS], default="auto")
    parser.add_argument("--day", type=int, choices=range(1, 9))
    parser.add_argument("--confirm-layout", action="store_true")
    parser.add_argument("--resume-staging", action="store_true")
    args = parser.parse_args()
    if args.command in {"inspect", "load"} and (not args.path or not args.path.is_file()):
        parser.error("Se necesita la ruta a un archivo descargado de Tianchi.")
    data_dir = ROOT / "data/eleme"
    data_dir.mkdir(parents=True, exist_ok=True)
    with (data_dir / "import.lock").open("w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if args.command == "init":
            init()
        elif args.command == "inspect":
            inspect(args.path, args.delimiter)
        elif args.command == "load":
            init()
            tables = run("SELECT name FROM system.tables WHERE database='delivery' AND "
                         "name IN ('otto_archive','rees46_events','otto_scale_benchmark','eleme_samples','eleme_staging')").splitlines()
            stopped = []
            try:
                for table in tables:
                    run(f"SYSTEM STOP MERGES delivery.{table}")
                    stopped.append(table)
                load(args.path, args.delimiter, args.day, args.confirm_layout, args.resume_staging)
            finally:
                for table in stopped:
                    run(f"SYSTEM START MERGES delivery.{table}")
        else:
            init()
            print(run("SELECT sample_day, count() AS samples, sum(clicked) AS positive_clicks "
                      "FROM delivery.eleme_samples GROUP BY sample_day ORDER BY sample_day FORMAT PrettyCompact"))


if __name__ == "__main__":
    try:
        main()
    except (ValueError, RuntimeError, OSError, zipfile.BadZipFile) as error:
        print(f"Ele.me: {error}", file=sys.stderr)
        sys.exit(1)
