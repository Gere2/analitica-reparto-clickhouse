# Resultados medidos en este equipo

Fecha UTC del benchmark: 2026-10-04T22:56:43.976300+00:00.

## Procedencia y magnitud

- OTTO: **216.716.096 eventos reales**, entre ellos **194.720.954 clics**. Fuente: [publicación OTTO](https://github.com/otto-de/recsys-dataset).
- REES46: **411.709.736 eventos reales** de siete meses. Fuente: [publicación REES46](https://data.rees46.com/).
  - Desglose: **385.746.849 vistas**, **19.114.063 carritos** y **6.848.824 compras**. Las vistas no son clics OTTO.
- Suma aritmética de ambos archivos reales: **628.425.832 filas** de **dos poblaciones distintas**; no son un único clickstream.
- Prueba de estrés: **1.083.580.480 filas derivadas**, cinco escenarios creados desde OTTO; no representan usuarios ni eventos nuevos.

| Archivo REES46 | Eventos | Vistas | Carritos | Compras | Comprimido |
|---|---:|---:|---:|---:|---:|
| 2019-Oct | 42.448.764 | 40.779.399 | 926.516 | 742.849 | 1.62 GiB |
| 2019-Nov | 67.501.979 | 63.556.110 | 3.028.930 | 916.939 | 2.69 GiB |
| 2019-Dec | 67.542.878 | 62.986.067 | 3.394.763 | 1.162.048 | 2.75 GiB |
| 2020-Jan | 55.967.041 | 52.490.785 | 2.641.249 | 835.007 | 2.23 GiB |
| 2020-Feb | 55.318.565 | 51.232.669 | 2.885.608 | 1.200.288 | 2.19 GiB |
| 2020-Mar | 56.341.241 | 52.347.910 | 2.968.397 | 1.024.934 | 2.25 GiB |
| 2020-Apr | 66.589.268 | 62.353.909 | 3.268.600 | 966.759 | 2.73 GiB |

Los tamaños comprimidos proceden de los archivos del publicador. El cargador leyó cada gzip hasta el final, validó el CSV y cotejó sus filas con ClickHouse.

## Consultas medidas

El benchmark desactivó la caché de consultas. Las consultas OTTO se ejecutaron tres veces y se indica la mediana; las otras consultas, una vez. El resultado diario del archivo y del agregado se comparó fila a fila antes de guardar el informe.

| Consulta | Segundos | Filas leídas | Bytes leídos |
|---|---:|---:|---:|
| OTTO bruto, día/tipo | 5.8908 | 216.716.096 | 1.82 GiB |
| OTTO agregado, día/tipo | 0.2113 | 87 | 0.98 KiB |
| REES46 octubre, tipos | 0.2378 | 42.448.764 | 121.45 MiB |
| Escenarios derivados | 1.4357 | 1.083.580.480 | 826.74 MiB |

En este equipo y para esta pregunta, el agregado fue **27.9 veces** más rápido por mediana de tiempo. La cifra es local y depende del almacenamiento, la caché del sistema operativo y la carga concurrente; el contraste principal también son las filas y bytes leídos.

## Espacio de las tablas

| Tabla | Filas | Disco comprimido |
|---|---:|---:|
| `otto_archive` | 216.716.096 | 2.59 GiB |
| `otto_daily_rollup` | 87 | 0.98 KiB |
| `otto_scale_benchmark` | 1.083.580.480 | 12.11 GiB |
| `rees46_events` | 411.709.736 | 11.05 GiB |

Condiciones adicionales: Las fusiones de fondo de REES46 y de la tabla derivada estuvieron pausadas durante estas mediciones; no había fusiones activas al empezar. Se reactivan al terminar la verificación.

## Plan de lectura para octubre REES46

```text
Expression ((Project names + Projection))
  Aggregating
    Expression (Before GROUP BY)
      Expression ((WHERE + Change column names to column identifiers))
        ReadFromMergeTree (delivery.rees46_events)
        Indexes:
          MinMax
            Keys:
              event_date
            Condition: and((event_date in (-Inf, 18200]), (event_date in [18170, +Inf)))
            Parts: 2/1235
            Granules: 5183/50981
          Partition
            Keys:
              toYYYYMM(event_date)
            Condition: and((toYYYYMM(event_date) in (-Inf, 201911]), (toYYYYMM(event_date) in [201910, +Inf)))
            Parts: 2/2
            Granules: 5183/5183
          PrimaryKey
            Keys:
              event_date
            Condition: and((event_date in (-Inf, 18200]), (event_date in [18170, +Inf)))
            Parts: 2/2
            Granules: 5183/5183
            Search Algorithm: binary search
            Ranges: 2
```

Entorno: local Docker ClickHouse 25.8; one node; query cache disabled; three warm runs for OTTO queries, one run for larger scans.

**Interpretación:** OTTO contiene clics; REES46 contiene vistas de producto, carritos y compras. La tabla de estrés son copias etiquetadas. El replay inserta eventos históricos hoy, sin cambiar su fecha original.
