"""Download, verify, and load the public Criteo Uplift v2.1 dataset."""

from __future__ import annotations

import argparse
import base64
import gzip
import hashlib
import json
import os
import shutil
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "criteo"
SOURCE = DATA / "criteo-research-uplift-v2.1.csv.gz"
URL = "https://huggingface.co/datasets/criteo/criteo-uplift/resolve/main/criteo-research-uplift-v2.1.csv.gz"
SIZE = 311_422_618
SHA256 = "2716e1bf0fd157a93b5bf86924d9088419dfbac2022c6cd90030220634f616dc"
EXPECTED_ROWS = 13_979_592
COLUMNS = [f"f{i}" for i in range(12)] + ["treatment", "conversion", "visit", "exposure"]
CLICKHOUSE = os.environ.get("CLICKHOUSE_URL", "http://127.0.0.1:8124/").rstrip("/")
AUTH = base64.b64encode((os.environ.get("CLICKHOUSE_USER", "demo") + ":"
                         + os.environ.get("CLICKHOUSE_PASSWORD", "demo")).encode()).decode()


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def verify_source() -> None:
    if not SOURCE.is_file() or SOURCE.stat().st_size != SIZE:
        raise RuntimeError(f"Incomplete Criteo file: expected {SIZE} bytes in {SOURCE}")
    actual = digest(SOURCE)
    if actual != SHA256:
        raise RuntimeError(f"Unexpected SHA-256 for the Criteo file: {actual}")
    with gzip.open(SOURCE, "rt", encoding="utf-8") as stream:
        header = stream.readline().strip().split(",")
    if header != COLUMNS:
        raise RuntimeError(f"Unexpected columns: {header}")
    print(f"Official file verified: {SIZE:,} bytes, SHA-256 {actual}", flush=True)


def download() -> None:
    DATA.mkdir(parents=True, exist_ok=True)
    if SOURCE.is_file() and SOURCE.stat().st_size == SIZE and digest(SOURCE) == SHA256:
        print("Criteo file already downloaded and verified.")
        return
    temp = DATA / (SOURCE.name + ".part")
    print("Downloading the public Criteo file (311 MB)...", flush=True)
    request = Request(URL, headers={"User-Agent": "BD2-ClickHouse-academic-demo/1.0"})
    with urlopen(request, timeout=90) as response, temp.open("wb") as output:
        shutil.copyfileobj(response, output, length=1024 * 1024)
    temp.replace(SOURCE)
    verify_source()


def execute(sql: str, body=None, headers=None) -> str:
    query = {"query": sql} if body is not None else {}
    request = Request(CLICKHOUSE + "/?" + urlencode(query), data=sql.encode() if body is None else body,
                      headers={"Authorization": "Basic " + AUTH, **(headers or {})})
    try:
        with urlopen(request, timeout=900) as response:
            return response.read().decode().strip()
    except HTTPError as error:
        raise RuntimeError("ClickHouse: " + error.read().decode(errors="replace")[:1600]) from error


def count() -> int:
    return int(execute("SELECT count() FROM delivery.criteo_uplift"))


def load(reset: bool) -> None:
    verify_source()
    schema = (ROOT / "sql" / "criteo.sql").read_text(encoding="utf-8")
    execute("\n".join(line for line in schema.splitlines() if not line.lstrip().startswith("--")))
    rows = count()
    if rows == EXPECTED_ROWS and not reset:
        print(f"Criteo already loaded: {rows:,} rows.")
        return
    if rows and not reset:
        raise RuntimeError("Partial or different load. Repeat with 'load --reset'.")
    if reset:
        execute("TRUNCATE TABLE delivery.criteo_uplift")
    print(f"Loading {EXPECTED_ROWS:,} rows into ClickHouse...", flush=True)
    # ClickHouse decompresses the request body itself, so the 3.2 GB CSV never touches the disk.
    with SOURCE.open("rb") as stream:
        execute("INSERT INTO delivery.criteo_uplift FORMAT CSVWithNames", body=stream,
                headers={"Content-Encoding": "gzip", "Content-Length": str(SIZE)})
    rows = count()
    if rows != EXPECTED_ROWS:
        raise RuntimeError(f"Unexpected count: {rows:,} rows")
    groups = json.loads(execute("SELECT treatment, count() AS rows FROM delivery.criteo_uplift "
                                "GROUP BY treatment ORDER BY treatment FORMAT JSON"))["data"]
    print(f"Load verified: {rows:,} rows; "
          + ", ".join(f"treatment={g['treatment']}: {int(g['rows']):,}" for g in groups) + ".")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)
    sub.add_parser("download")
    loader = sub.add_parser("load")
    loader.add_argument("--reset", action="store_true")
    options = parser.parse_args()
    if options.action == "download":
        download()
    else:
        load(options.reset)


if __name__ == "__main__":
    main()
