# Instalación reproducible

Para desarrollar la plataforma ficticia sin descargar los datasets históricos, seguir [INFRAESTRUCTURA-ATLAS.md](INFRAESTRUCTURA-ATLAS.md). Las instrucciones siguientes corresponden al laboratorio de grandes datasets.

## Requisitos

- Docker Desktop u OrbStack con `docker compose`.
- Python 3.10 o posterior; los scripts propios utilizan su biblioteca estándar.
- Puertos locales 8124 (ClickHouse) y 8000 (dashboard).
- Para **OTTO solamente**, al menos 20 GB libres. Para los siete CSV.gz REES46 y la tabla de estrés de mil millones, recomendamos **60 GB libres** antes de empezar. El espacio exacto depende de la compresión y las fusiones de partes.
- Hacer las descargas y cargas **antes de clase**. No están pensadas para los 10 minutos de demo.
- En Docker con unos 4 GB de memoria, ejecutar **REES46 y escala de forma secuencial**, tal como están ordenados abajo. Los cargadores pausan temporalmente las fusiones de su tabla para reducir picos de memoria y las reanudan al terminar. `clickhouse-config.xml` limita a cuatro las fusiones simultáneas al arrancar el servidor; este ajuste evita que las fusiones de los conjuntos grandes saturen la memoria durante la demo.

## 1. Arrancar ClickHouse

```bash
docker compose -f compose.yaml up -d
docker compose -f compose.yaml ps
```

El contenedor `bd2-clickhouse` debe figurar como `healthy`. La configuración local usa ClickHouse 25.8, base `delivery`, usuario/contraseña de demostración `demo` y HTTP en `127.0.0.1:8124`.

## 2. OTTO: clics reales y vista materializada

```bash
python3 scripts/otto.py download
python3 scripts/otto.py load
python3 scripts/rollup.py
```

El ZIP se lee en streaming; no hay que descomprimirlo entero. Su SHA-256 esperado es `ae11a23676ba29eeeb6e1348b81e353c530da3bc059353cad67247e9616acb2f`. La fuente original es [OTTO/Kaggle](https://github.com/otto-de/recsys-dataset); por facilidad se usa un [espejo público](https://huggingface.co/datasets/hazemessam/otto-recsys). Se cotejan **194.720.954** clics, **16.896.191** carritos y **5.098.951** pedidos con lo publicado. `rollup.py` crea la vista materializada **después** de la carga inicial y hace el backfill una sola vez, evitando miles de partes pequeñas durante la importación. El agregado diario debe tener **87 claves día/tipo** que suman **216.716.096** eventos; puede haber más filas físicas antes de que terminen las fusiones.

Para ensayar con menos filas, `python3 scripts/otto.py load --limit 1000000 --reset` reemplaza el archivo y su agregado. Después, `python3 scripts/otto.py load --reset` carga el conjunto completo. No utilizar `--reset` por accidente una vez completada la carga.

## 3. REES46: siete meses de otro marketplace

```bash
python3 scripts/rees46.py download
python3 scripts/rees46.py load
python3 scripts/rees46.py status
```

Los siete archivos comprimidos se guardan en `data/rees46/`. El script verifica el tamaño publicado por el servidor, la descompresión completa y los recuentos por mes. `data/rees46/manifest.json` registra vistas, carritos y compras. Cada archivo se lee en streaming y se inserta en lotes de 200.000 filas para limitar memoria; los datos son reales, históricos y anonimizados. Si ClickHouse alcanza su límite de memoria, el cargador reintenta hasta diez veces desde el último lote confirmado. Tras una interrupción externa, `load --resume-partial` salta los lotes ya confirmados, siempre que el recuento sea múltiplo de 200.000; `--replace-partial` reconstruye **solo el mes incompleto** cuando no hay un punto de reanudación seguro. Los meses ya verificados se conservan. También se puede descargar o cargar un solo mes con `--month 2019-Oct`.

## 4. Escala derivada y benchmark

```bash
python3 scripts/scale.py
python3 scripts/benchmark.py
python3 scripts/check.py
python3 scripts/report.py
```

`scale.py` exige el OTTO completo y genera cinco escenarios etiquetados de **216.716.096 filas cada uno** mediante `INSERT SELECT`. Su tabla es sintética y se mantiene separada. `benchmark.py` compara archivo y agregado, verifica que el resultado sea idéntico y guarda `data/query-benchmark.json` con tiempo, filas leídas y bytes leídos. `check.py` audita los recuentos; `report.py` redacta [RESULTADOS.md](RESULTADOS.md) desde los manifiestos y las medidas. Ejecutadlos **después** de terminar las cargas para que las mediciones no compitan con ellas.

## 5. Panel y demo

Para habilitar también el panel del sector de reparto, ejecutar `python3 scripts/eleme.py init` y abrir [Ele.me](http://127.0.0.1:8000/eleme.html). La descarga oficial necesita cuenta Tianchi; el procedimiento y las comprobaciones previas del primer ZIP están en [ELEME.md](ELEME.md). En este equipo ya está importada la primera parte D1_0: 2.170.299 muestras. En una instalación nueva el panel muestra el estado vacío hasta completar una carga; los 146 M declarados nunca se muestran como un recuento local.

```bash
python3 dashboard.py
```

Abrir [OTTO](http://127.0.0.1:8000/), [REES46](http://127.0.0.1:8000/rees46.html) y [escala](http://127.0.0.1:8000/scale.html). En otro terminal:

```bash
python3 scripts/otto.py replay --rate 5000 --limit 200000 --reset
python3 scripts/crud_demo.py
```

`--rate` es una meta; la velocidad efectiva depende del equipo. `--reset` en el reproductor vacía **solo** `otto_replay`. Los botones de OTTO insertan clics nuevos en `live_clicks`.
El CRUD pausa temporalmente las fusiones de las tablas grandes y las reanuda al salir. Si se termina ese proceso a la fuerza, ejecutar `SYSTEM START MERGES` para `otto_archive`, `rees46_events` y `otto_scale_benchmark` desde el cliente SQL.

## Comprobaciones SQL

```bash
docker exec -it bd2-clickhouse clickhouse-client --user demo --password demo --database delivery
```

```sql
SELECT event_type, count() FROM otto_archive GROUP BY event_type ORDER BY event_type;
SELECT sum(events), count() FROM otto_daily_rollup;
SELECT toYYYYMM(event_date) AS mes, count() FROM rees46_events GROUP BY mes ORDER BY mes;
SELECT scenario, count() FROM otto_scale_benchmark GROUP BY scenario ORDER BY scenario;
SELECT table, sum(rows), formatReadableSize(sum(bytes_on_disk))
FROM system.parts WHERE database = 'delivery' AND active
  AND table IN ('otto_archive','otto_daily_rollup','rees46_events','otto_scale_benchmark')
GROUP BY table ORDER BY table;
```

## Problemas frecuentes

- **El dashboard no conecta:** comprobar `docker compose -f compose.yaml ps`, el puerto 8124 y el proceso `python3 dashboard.py`. Si el puerto 8000 está ocupado: `PORT=8001 python3 dashboard.py`.
- **Falta espacio:** ejecutar solo OTTO y el rollup; ya permiten demostrar 216,7 millones de eventos reales. No borrar datos necesarios antes de la presentación.
- **Carga REES46 interrumpida:** `python3 scripts/rees46.py status` indica los meses terminados. Probar `python3 scripts/rees46.py load --resume-partial`; si la salida indica que el lote incompleto no se puede reanudar, usar `--replace-partial` para reconstruir únicamente ese mes. `load --reset` borra y reconstruye toda la tabla.
- **Escenario de escala interrumpido:** `python3 scripts/scale.py --replace-partial` elimina y rehace solo el escenario incompleto. Si una mutación no puede concluir por falta de memoria, `python3 scripts/scale.py --reset` reconstruye la tabla de prueba completa.
- **Proceso terminado a la fuerza:** si se paró un cargador sin ejecutar su limpieza final, reactivar las fusiones con `SYSTEM START MERGES delivery.rees46_events` y `SYSTEM START MERGES delivery.otto_scale_benchmark` desde el cliente SQL cuando hayan acabado las cargas.
- **Benchmark sin datos:** requiere OTTO completo, al menos un mes REES46 y la tabla de escala. La carga completa de siete meses ofrece la presentación final.
