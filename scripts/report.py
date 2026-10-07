"""Write the measured class handout from verified manifests and benchmarks."""

import json
from pathlib import Path

from rees46 import MANIFEST, MONTHS
from scale import REPORT as SCALE_REPORT
from benchmark import REPORT as QUERY_REPORT

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "docs" / "RESULTADOS.md"


def fmt(value: int) -> str:
    return f"{int(value):,}".replace(",", ".")


def gib(value: int) -> str:
    return f"{int(value) / 2**30:.2f} GiB"


def readable_bytes(value: int) -> str:
    size = int(value)
    if size >= 2**30:
        return gib(size)
    if size >= 2**20:
        return f"{size / 2**20:.2f} MiB"
    return f"{size / 2**10:.2f} KiB"


def main() -> None:
    manifest = json.loads(MANIFEST.read_text())
    scale = json.loads(SCALE_REPORT.read_text())
    benchmark = json.loads(QUERY_REPORT.read_text())
    if set(manifest) != set(MONTHS):
        raise RuntimeError("El manifiesto REES46 no contiene los siete meses")
    months = [manifest[month] for month in MONTHS]
    rees_total = sum(int(item["rows"]) for item in months)
    rees_views = sum(int(item["views"]) for item in months)
    rees_carts = sum(int(item["carts"]) for item in months)
    rees_purchases = sum(int(item["purchases"]) for item in months)
    otto_total = int(benchmark["counts"]["otto_real"])
    if int(benchmark["counts"]["rees46_real"]) != rees_total:
        raise RuntimeError("REES46 en el benchmark y el manifiesto no coinciden")
    if int(benchmark["counts"]["scale_derived"]) != int(scale["stress_rows"]):
        raise RuntimeError("La tabla de estrés y el benchmark no coinciden")

    lines = [
        "# Resultados medidos en este equipo", "",
        f"Fecha UTC del benchmark: {benchmark['measured_at_utc']}.", "",
        "## Procedencia y magnitud", "",
        f"- OTTO: **{fmt(otto_total)} eventos reales**, entre ellos **194.720.954 clics**. Fuente: [publicación OTTO](https://github.com/otto-de/recsys-dataset).",
        f"- REES46: **{fmt(rees_total)} eventos reales** de siete meses. Fuente: [publicación REES46](https://data.rees46.com/).",
        f"  - Desglose: **{fmt(rees_views)} vistas**, **{fmt(rees_carts)} carritos** y **{fmt(rees_purchases)} compras**. Las vistas no son clics OTTO.",
        f"- Suma aritmética de ambos archivos reales: **{fmt(otto_total + rees_total)} filas** de **dos poblaciones distintas**; no son un único clickstream.",
        f"- Prueba de estrés: **{fmt(scale['stress_rows'])} filas derivadas**, cinco escenarios creados desde OTTO; no representan usuarios ni eventos nuevos.",
        "", "| Archivo REES46 | Eventos | Vistas | Carritos | Compras | Comprimido |", "|---|---:|---:|---:|---:|---:|",
    ]
    for month, item in zip(MONTHS, months):
        lines.append(f"| {month} | {fmt(item['rows'])} | {fmt(item['views'])} | "
                     f"{fmt(item['carts'])} | {fmt(item['purchases'])} | {gib(item['compressed_bytes'])} |")
    lines += ["", "Los tamaños comprimidos proceden de los archivos del publicador. El cargador leyó cada gzip hasta el final, validó el CSV y cotejó sus filas con ClickHouse.",
              "", "## Consultas medidas", "",
              "El benchmark desactivó la caché de consultas. Las consultas OTTO se ejecutaron tres veces y se indica la mediana; las otras consultas, una vez. El resultado diario del archivo y del agregado se comparó fila a fila antes de guardar el informe.",
              "", "| Consulta | Segundos | Filas leídas | Bytes leídos |", "|---|---:|---:|---:|" ]
    titles = {"otto_raw_daily": "OTTO bruto, día/tipo", "otto_rollup_daily": "OTTO agregado, día/tipo",
              "rees46_month": "REES46 octubre, tipos", "scale_scenarios": "Escenarios derivados"}
    for name, title in titles.items():
        result = benchmark["queries"][name]
        first = result["runs"][0]
        lines.append(f"| {title} | {result['median_seconds']:.4f} | {fmt(first['rows_read'])} | "
                     f"{readable_bytes(first['bytes_read'])} |")
    raw = benchmark["queries"]["otto_raw_daily"]
    rollup = benchmark["queries"]["otto_rollup_daily"]
    ratio = raw["median_seconds"] / rollup["median_seconds"] if rollup["median_seconds"] else 0
    lines += ["", f"En este equipo y para esta pregunta, el agregado fue **{ratio:.1f} veces** más rápido por mediana de tiempo. La cifra es local y depende del almacenamiento, la caché del sistema operativo y la carga concurrente; el contraste principal también son las filas y bytes leídos.",
              "", "## Espacio de las tablas", "", "| Tabla | Filas | Disco comprimido |", "|---|---:|---:|"]
    for part in benchmark["table_parts"]:
        lines.append(f"| `{part['table']}` | {fmt(part['rows'])} | {readable_bytes(part['bytes_on_disk'])} |")
    if benchmark.get("measurement_notes"):
        lines += ["", f"Condiciones adicionales: {benchmark['measurement_notes']}"]
    lines += ["", "## Plan de lectura para octubre REES46", "", "```text",
              benchmark["explain_rees46_october_partition"].rstrip(), "```", "",
              f"Entorno: {benchmark['environment']}.", "",
              "**Interpretación:** OTTO contiene clics; REES46 contiene vistas de producto, carritos y compras. La tabla de estrés son copias etiquetadas. El replay inserta eventos históricos hoy, sin cambiar su fecha original.", ""]
    OUTPUT.write_text("\n".join(lines))
    print(f"Informe escrito: {OUTPUT}")


if __name__ == "__main__":
    main()
