"""Download and verify the public Meituan TRD text files from Zenodo."""

from __future__ import annotations

import hashlib
import shutil
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
FILES = {
    "orders_poi_session.txt": "849461d015b120e04ea0d6dba94e1e40",
    "orders_train.txt": "35484a39dec675b235a4a05e7df2cc6c",
    "orders_spu_train.txt": "9cadbaf108713763a09096708e16b7b2",
    "pois.txt": "d948ba9500e3aefbcb054885b65ee5f6",
    "spus.txt": "d31f025e3dfd6ddadca39ead4e64292c",
}


def md5(path: Path) -> str:
    digest = hashlib.md5()  # noqa: S324 - Zenodo's published file checksum, not cryptographic security
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    RAW.mkdir(parents=True, exist_ok=True)
    for filename, checksum in FILES.items():
        target = RAW / filename
        if target.exists() and md5(target) == checksum:
            print(f"OK {filename}: ya descargado y verificado", flush=True)
            continue
        temp = target.with_suffix(".part")
        url = f"https://zenodo.org/records/8025855/files/{filename}?download=1"
        print(f"Descargando {filename}...", flush=True)
        with urlopen(Request(url, headers={"User-Agent": "BD2-ClickHouse-academic-demo/1.0"}), timeout=90) as source, temp.open("wb") as dest:
            shutil.copyfileobj(source, dest, length=1024 * 1024)
        actual = md5(temp)
        if actual != checksum:
            temp.unlink(missing_ok=True)
            raise RuntimeError(f"Checksum incorrecto para {filename}: {actual}")
        temp.replace(target)
        print(f"  MD5 verificado: {checksum}", flush=True)


if __name__ == "__main__":
    main()
