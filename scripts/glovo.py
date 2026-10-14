"""Download, prepare, and load Glovo's public FooDI-ML catalog."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import shutil
import subprocess
from collections import Counter
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "glovo"
SOURCE = DATA / "foodi-ml.csv"
PREPARED = DATA / "foodi-ml.tsv"
MANIFEST = DATA / "manifest.json"
URL = "https://glovo-products-dataset-d1c9720d.s3.amazonaws.com/glovo-foodi-ml-dataset.csv"
SIZE = 565_423_032
SHA256 = "09180fb4d34347dc210138bed9ef8bab588bc541824223a546d19e139a42f683"
EXPECTED_ROWS = 2_887_444
CLIENT = ["docker", "exec", "-i", "bd2-clickhouse", "clickhouse-client",
          "--user", "demo", "--password", "demo"]


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def verify_source() -> None:
    if not SOURCE.is_file() or SOURCE.stat().st_size != SIZE:
        raise RuntimeError(f"CSV de Glovo incompleto: se esperan {SIZE} bytes en {SOURCE}")
    actual = digest(SOURCE)
    if actual != SHA256:
        raise RuntimeError(f"SHA-256 inesperado para el CSV de Glovo: {actual}")
    print(f"CSV oficial verificado: {SIZE:,} bytes, SHA-256 {actual}", flush=True)


def download() -> None:
    DATA.mkdir(parents=True, exist_ok=True)
    if SOURCE.is_file() and SOURCE.stat().st_size == SIZE and digest(SOURCE) == SHA256:
        print("CSV de Glovo ya descargado y verificado.")
        return
    temp = DATA / "foodi-ml.csv.part"
    print("Descargando el CSV público de Glovo (565 MB)...", flush=True)
    request = Request(URL, headers={"User-Agent": "BD2-ClickHouse-academic-demo/1.0"})
    with urlopen(request, timeout=90) as response, temp.open("wb") as output:
        shutil.copyfileobj(response, output, length=1024 * 1024)
    temp.replace(SOURCE)
    verify_source()


def escape(value: str) -> str:
    return (value.replace("\\", "\\\\").replace("\t", "\\t")
            .replace("\n", "\\n").replace("\r", "\\r").replace("\0", "\\0"))


def prepare() -> None:
    verify_source()
    countries: Counter[str] = Counter()
    spanish_cities: Counter[str] = Counter()
    described_es = 0
    temp = DATA / "foodi-ml.tsv.part"
    with SOURCE.open(newline="", encoding="utf-8-sig") as source, temp.open("w", encoding="utf-8", newline="") as output:
        reader = csv.DictReader(source)
        required = {"", "country_code", "city_code", "store_name", "product_name",
                    "collection_section", "product_description", "aux_store", "HIER"}
        if not required.issubset(reader.fieldnames or []):
            raise RuntimeError(f"Columnas inesperadas: {reader.fieldnames}")
        for index, row in enumerate(reader):
            if index != int(row[""]):
                raise RuntimeError(f"Índice inesperado en fila {index}")
            country = row["country_code"]
            city = row["city_code"]
            description = row["product_description"]
            countries[country] += 1
            if country == "ES":
                spanish_cities[city] += 1
                described_es += bool(description)
            values = [str(index), country, city, row["store_name"], row["product_name"],
                      row["collection_section"], description, str(int(bool(description))),
                      str(int(row["aux_store"] == "True")), str(int(row["HIER"] == "True"))]
            output.write("\t".join(map(escape, values)) + "\n")
            if (index + 1) % 500_000 == 0:
                print(f"Preparadas {index + 1:,} filas...", flush=True)
    total = sum(countries.values())
    if total != EXPECTED_ROWS:
        temp.unlink(missing_ok=True)
        raise RuntimeError(f"Se esperaban {EXPECTED_ROWS:,} productos y se encontraron {total:,}")
    temp.replace(PREPARED)
    manifest = {"source": URL, "sha256": SHA256, "products": total,
                "countries": dict(countries), "spanish_cities": dict(spanish_cities),
                "spanish_descriptions": described_es}
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    print(f"Productos: {total:,}; España: {countries['ES']:,}; ciudades españolas: {len(spanish_cities):,}")


def command(sql: str, *, input_file: Path | None = None, multiquery: bool = False) -> str:
    args = CLIENT + (["--multiquery"] if multiquery else ["--query", sql])
    if input_file:
        with input_file.open("rb") as stream:
            result = subprocess.run(args, stdin=stream, capture_output=True, check=False)
    else:
        result = subprocess.run(args, input=sql.encode() if multiquery else None,
                                capture_output=True, check=False)
    if result.returncode:
        raise RuntimeError(result.stderr.decode(errors="replace"))
    return result.stdout.decode().strip()


def load(reset: bool) -> None:
    if not PREPARED.is_file() or not MANIFEST.is_file():
        raise RuntimeError("Ejecuta primero: python3 scripts/glovo.py prepare")
    manifest = json.loads(MANIFEST.read_text())
    expected = manifest["products"]
    command("", input_file=ROOT / "sql" / "schema.sql", multiquery=True)
    count = int(command("SELECT count() FROM delivery.glovo_products"))
    if count == expected and not reset:
        print(f"Glovo ya cargado: {count:,} productos.")
        return
    if count and not reset:
        raise RuntimeError("Carga parcial o diferente. Repite con 'load --reset'.")
    if reset:
        command("TRUNCATE TABLE delivery.glovo_products")
    print(f"Cargando {expected:,} productos en ClickHouse...", flush=True)
    command("INSERT INTO delivery.glovo_products FORMAT TabSeparated", input_file=PREPARED)
    actual = int(command("SELECT count() FROM delivery.glovo_products"))
    spanish = int(command("SELECT count() FROM delivery.glovo_products WHERE country_code = 'ES'"))
    if actual != expected or spanish != manifest["countries"]["ES"]:
        raise RuntimeError(f"Recuentos inesperados: global={actual}, ES={spanish}")
    print(f"Carga verificada: {actual:,} productos; España: {spanish:,}.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)
    sub.add_parser("download")
    sub.add_parser("prepare")
    loader = sub.add_parser("load")
    loader.add_argument("--reset", action="store_true")
    options = parser.parse_args()
    if options.action == "download":
        download()
    elif options.action == "prepare":
        prepare()
    else:
        load(options.reset)


if __name__ == "__main__":
    main()
