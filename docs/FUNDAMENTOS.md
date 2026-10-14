# ClickHouse: fundamentos, arquitectura y reflexión crítica

## Encaje en BD2

ClickHouse es una **base de datos columnar OLAP con SQL**. En una clasificación de NoSQL suele tratarse como almacén analítico de columnas, pero no debe presentarse como motor «sin SQL»: utiliza un dialecto SQL. Conviene explicar al profesor este matiz al principio. Su problema central aquí es responder agregaciones sobre cientos de millones de eventos mientras entran lotes nuevos.

La idea de producto se inspira en la analítica de navegación que necesitaría una plataforma de reparto: volumen por tiempo, exploración de productos o categorías, acciones de cesta y compra. **Las fuentes reales disponibles no son Uber Eats ni Glovo**. OTTO sí contiene clics explícitos; REES46 contiene vistas, carritos y compras. No se suman como si fueran el mismo suceso o la misma población.

## Modelo de datos

| Tabla | Procedencia | Grano | Motor y orden |
|---|---|---|---|
| `otto_archive` | OTTO real | Un clic, carrito o pedido de una sesión | `MergeTree`, mes; `(event_time,session_id,event_position)` |
| `otto_replay` | OTTO real reinsertado | Un evento reproducido con `ingested_at` nuevo | `MergeTree`, día de inserción |
| `live_clicks` | Esta página | Un clic de un visitante de la demo | `MergeTree` |
| `rees46_events` | REES46 real | Una vista, carrito o compra | `MergeTree`, mes; `(event_date,event_type,category_id,product_id)` |
| `otto_scale_benchmark` | Derivado | Una copia etiquetada de un evento OTTO | `MergeTree`, mes; `scenario` explicita origen |
| `otto_daily_rollup` | Agregado de OTTO | Recuento parcial por fecha y tipo | `SummingMergeTree` + vista materializada |

El ETL OTTO convierte cada sesión JSONL en varias filas, una por evento. REES46 se lee desde siete CSV.gz sin extraerlos a disco: `gzip` alimenta a `clickhouse-client`. Los archivos temporales comprimidos y las tablas persistentes tienen usos distintos.

En `MergeTree`, el `ORDER BY` determina el orden físico y el índice primario disperso de los datos. Las particiones ayudan a eliminar meses enteros cuando un filtro coincide con ellas; el orden ayuda a localizar rangos dentro de las partes. `LowCardinality(String)` resulta apropiado para tipos de evento y marcas repetidas. Leer solo las columnas necesarias reduce bytes frente a una lectura de filas completas. No todo `WHERE` será igual de eficiente: hay que comprobar la consulta y los índices con `EXPLAIN indexes = 1`.

La vista materializada recibe los lotes **insertados después de su creación** y añade sus recuentos a `otto_daily_rollup`. Para un archivo ya cargado, `scripts/rollup.py` hace el backfill explícito. En `SummingMergeTree` puede haber varias filas físicas con la misma clave hasta que se fusionen partes; por eso la consulta utiliza `sum(events) GROUP BY event_date,event_type`, en lugar de asumir que cada clave ocupa exactamente una fila física. Las 87 combinaciones día/tipo de OTTO son la unidad lógica del agregado.

## Consistencia y disponibilidad

La demo usa **un solo nodo** con volumen Docker persistente. Tras una inserción confirmada, una consulta puede leer las nuevas filas; las fusiones de partes ocurren luego en segundo plano. No hay réplicas ni alta disponibilidad: si el contenedor está caído, el dashboard no responde. El reproductor reenvía eventos históricos a otra tabla, y sus consultas por `ingested_at` no cambian la fecha original del suceso.

Con este volumen, las fusiones también forman parte de la operación: compiten por CPU, disco y memoria con las consultas. En esta máquina de unos 4 GB, el valor inicial permitía hasta 32 fusiones simultáneas; `clickhouse-config.xml` fija cuatro y ajusta los umbrales internos de MergeTree para que las mutaciones sigan siendo válidas. Se sacrifica velocidad de compactación para mantener recursos disponibles al panel. [La documentación oficial](https://clickhouse.com/docs/reference/settings/server-settings/settings/background) indica que reducir el pool exige reiniciar el servidor, y [explica](https://clickhouse.com/docs/reference/settings/server-settings/settings/background-merges) cómo el ratio multiplica la concurrencia.

Para un despliegue distribuido se pueden distribuir fragmentos mediante tablas `Distributed` y conservar copias con `ReplicatedMergeTree` y ClickHouse Keeper. Eso requiere configuración adicional y tiene consecuencias de consistencia y latencia; **no se demuestra ni se simula con el contenedor local**. Se explica con el diagrama y con la limitación observada de un nodo.

## Experimento que justifica ClickHouse

`scripts/benchmark.py` formula exactamente la misma pregunta al archivo de 216.716.096 eventos OTTO y al agregado diario. Compara resultados antes de aceptar la medición. Registra tiempo, `rows_read` y `bytes_read` de la respuesta JSON de ClickHouse, con caché de consultas desactivada. Ejecuta tres veces cada consulta OTTO y toma la mediana. También cuenta tipos en un mes REES46 y agrupa la tabla derivada de 1.083.580.480 filas por escenario. El informe queda en `data/query-benchmark.json`.

El resultado medido pertenece a **este equipo, estas tablas y esta pregunta**. No implica que ClickHouse siempre gane a PostgreSQL ni que un agregado equivalente en PostgreSQL sea lento. La ventaja que se ilustra es concreta: calcular una respuesta repetida una vez durante la ingestión evita volver a leer millones de eventos para cada petición del panel.

## Inserción, lectura, actualización y borrado

- Inserción: el ETL usa lotes; el dashboard envía un evento nuevo por clic; el reproductor ingresa lotes pequeños.
- Lectura: `SELECT` con filtros temporales, `GROUP BY`, `countIf`, `uniqCombined64` y agregados.
- Actualización y borrado: `scripts/crud_demo.py` ejecuta `ALTER TABLE ... UPDATE/DELETE` en una tabla de ensayo. Son mutaciones más costosas que el patrón de añadir eventos y consultar agregados; no se modifica masivamente el archivo histórico para mostrar CRUD.

## Calidad del dato y límites

- OTTO publica IDs de artículos anónimos, sin nombre, precio ni categoría. Su archivo de entrenamiento tiene **216.716.096** eventos: **194.720.954** clics, **16.896.191** carritos y **5.098.951** pedidos. El archivo de clase se valida por SHA-256 y por estos recuentos.
- REES46 publica siete meses de eventos de un marketplace sin identificar su país. Sus vistas de producto **no son clics OTTO**. El manifiesto local conserva el tamaño del archivo y los recuentos por mes.
- La tabla de mil millones **es una prueba de estrés derivada**, no un conjunto de observaciones nuevas; se muestran siempre las filas originales y derivadas por separado.
- `uniqCombined64` estima usuarios/sesiones distintos; los recuentos de filas son exactos. La razón entre número de vistas y compras no es una tasa de conversión de personas sin definir ventana, sesión y atribución.
- La reproducción de OTTO muestra ingesta en tiempo real, pero los sucesos ocurrieron en el pasado. Los clics de los botones del dashboard son las únicas acciones nuevas originadas en la demo.

## Comparación con una base transaccional

| Necesidad | Elección razonable |
|---|---|
| Guardar pedidos, cobros y cuentas que cambian individualmente | Sistema transaccional como PostgreSQL |
| Explorar años de eventos y agrupar cientos de millones de filas | ClickHouse |
| Mostrar métricas frecuentes en un dashboard | ClickHouse con vista materializada/rollup |
| Buscar o modificar una fila individual como operación principal | PostgreSQL u otro motor orientado a transacciones |

Fuentes técnicas: [MergeTree](https://clickhouse.com/docs/engines/table-engines/mergetree-family/mergetree), [materialized views](https://clickhouse.com/docs/materialized-views), [horizontal scaling](https://clickhouse.com/docs/architecture/horizontal-scaling), [HTTP](https://clickhouse.com/docs/interfaces/http). Datos: [OTTO](https://github.com/otto-de/recsys-dataset) y [REES46](https://data.rees46.com/).
