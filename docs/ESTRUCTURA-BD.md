# Delivery Atlas: estructura de la base de datos

## Evolución del 7 de octubre

La infraestructura v1 ya aplica `sql/atlas.sql` en la base independiente `delivery_atlas`. Usa `app_events` con `ReplacingMergeTree`, `app_daily_rollup` con estados `uniqExact` y una vista de lectura `app_daily_counts`. La cola persistente de la API permite recuperar publicaciones pendientes y reconocer reintentos con contenido inmutable. Consultar [la infraestructura aplicada](INFRAESTRUCTURA-ATLAS.md).

El diseño de `delivery_proposal` descrito más abajo se conserva como propuesta inicial del 5 de octubre. No es el esquema utilizado por la API nueva. El agregado sencillo de contadores se ha sustituido en v1 por conjuntos de IDs para evitar doble conteo en reenvíos.

Avance del proyecto, 5 de octubre de 2026. Objetivo: infraestructura analítica para una plataforma ficticia de reparto, con eventos simulados y un procedimiento para incorporar fuentes reales compatibles.

## 1. Qué existe hoy

Un nodo ClickHouse 25.8 en Docker, base `delivery`, volumen persistente, carga y consultas con Python. La API consulta las tablas y el navegador representa los resultados. Los datasets permanecen separados por su significado y procedencia.

| Tabla | Grano de una fila | Papel | Motor |
|---|---|---|---|
| `otto_archive` | Evento de una sesión OTTO | Histórico real | MergeTree |
| `otto_replay` | Inserción de un evento OTTO reproducido | Ingesta durante la demo | MergeTree |
| `live_clicks` | Clic nuevo de un botón del dashboard | Interacción de la demo | MergeTree |
| `otto_daily_rollup` | Recuento parcial por día y tipo | Agregado incremental | SummingMergeTree |
| `rees46_events` | Vista, carrito o compra | Histórico de marketplace | MergeTree |
| `eleme_samples` | Muestra del recomendador con etiqueta de clic | Caso del sector | MergeTree |
| `eleme_staging` | Muestra de archivo en validación | Publicación por archivo completo | MergeTree |
| `glovo_products` | Muestra de producto de catálogo | Oferta del sector y España | MergeTree |
| `otto_scale_benchmark` | Evento OTTO en un escenario derivado | Estrés de volumen | MergeTree |

`demo_events` sirve para CRUD de ensayo. Las tablas `restaurants`, `foods`, `orders`, `order_items`, `clicks`, `click_summary` y `daily_clicks` pertenecen al primer enfoque Meituan y se mantienen como material previo. No representan el nuevo contrato de la plataforma ficticia.

## 2. OTTO: estructura sencilla con gran volumen

`sql/schema.sql` define `session_id UInt32`, `article_id UInt32`, `event_time DateTime64(3, 'UTC')`, `event_type LowCardinality(String)` y `event_position UInt16`.

- Grano: un evento dentro de una sesión.
- Partición: `toYYYYMM(event_time)`.
- Orden físico: `(event_time, session_id, event_position)`.
- Consulta típica: recuentos por fecha y tipo de evento.
- Una fila no contiene el nombre del producto ni su categoría: la fuente no los publica.

`otto_replay` añade `ingested_at`. Conserva el momento histórico y registra aparte cuándo entró el evento durante la demo. Un nuevo replay puede volver a insertar el mismo evento: esta tabla registra la reproducción, no cuenta nuevos usuarios observados.

## 3. Ele.me: contexto amplio y publicación controlada

`sql/eleme.sql` conserva usuario, restaurante, producto, ciudad anónima, hora, periodo de comida, etiqueta `clicked` y todas las características originales en `raw_features String` con JSON.

El cargador valida 39 campos y los rangos conocidos, publica solo archivos completos y registra su SHA-256. `source_id`, `source_file` y `source_row` permiten rastrear el archivo y la fila. `source_id` combina la huella del ZIP y el miembro para distinguir su contenido físico.

- Partición: `source_id`, para este corpus finito y la publicación por archivo.
- Orden: `(sample_day, city_id, request_hour, category_id, shop_id, source_row)`.
- Flujo: lectura del ZIP, lotes en staging, verificación completa y `MOVE PARTITION` hacia `eleme_samples`.
- Sin vista materializada de inserción sobre esta tabla: mover partes no activa ese tipo de vista.
- La etiqueta negativa no acredita una impresión y la proporción positiva no es el CTR de producción.

## 4. Diseño físico y agregados

ClickHouse almacena datos por columnas. `MergeTree` organiza partes que fusiona en segundo plano. `ORDER BY` determina el orden físico y, si no se declara `PRIMARY KEY` aparte, su índice primario disperso. La clave no impone unicidad. Las particiones dividen el almacenamiento y facilitan operaciones sobre grupos completos.

La vista `otto_daily_rollup_mv` agrega cada bloque insertado por fecha y tipo. `scripts/rollup.py` realiza el backfill de las filas anteriores a su creación. La tabla conserva 87 claves lógicas. Se consulta con `sum(events) GROUP BY event_date,event_type` porque una clave puede ocupar varias filas físicas hasta que se fusionen.

Comparación verificada de la misma respuesta: 5,8908 s desde 216.716.096 eventos frente a 0,2113 s desde el agregado, mediana de tres ejecuciones. Son resultados locales y no comparan motores distintos.

## 5. Modelo de la plataforma ficticia, todavía propuesto

`sql/propuesta_delivery.sql` contiene un DDL revisable en `delivery_proposal`. **No se ha aplicado al servidor ni conectado a la API.**

| Objeto | Función | Estado |
|---|---|---|
| `app_events` | Una acción de navegación con contexto y procedencia | DDL propuesto |
| `app_daily_rollup` | Recuentos por día, ciudad, sección, acción y procedencia | DDL propuesto |
| `app_daily_rollup_mv` | Alimentar el agregado con nuevas inserciones | Propuesta condicionada a deduplicar reintentos |
| Miniapp y generador | Emitir ese contrato de eventos | Pendientes de implementación |
| Adaptadores reales | Validar correspondencia de una fuente y su contrato | Pendientes de implementación |

La tabla central contiene:

- Identidad: `event_id UUID`, `schema_version UInt16` y `session_id UUID`.
- Tiempo: `event_time`, `ingested_at` y `event_date MATERIALIZED`.
- Acción: `event_type` y `section`.
- Contexto: usuario opcional, ciudad y referencias opcionales de restaurante/producto.
- Procedencia: `source`, `source_kind`, `source_record_id` y `simulation_run_id`.

Particiones mensuales y orden propuesto `(source_kind, event_date, city_id, event_type, event_time, session_id)`. Ese orden prioriza filtros por procedencia y fecha, después ciudad y acción. Su rendimiento está pendiente de medir contra alternativas sobre la misma carga.

El agregado almacena recuentos de eventos, no sesiones únicas ni un embudo de usuarios. Para esas métricas harán falta definiciones de ventana y sesión y consultas que respeten el orden temporal.

## 6. Integridad e integración futura

La API debe validar tipos, acciones, versión y campos obligatorios. Un ID estable permite reconocer reintentos, pero `MergeTree` no los elimina por declarar ese campo. El protocolo del publicador debe evitar contar el mismo evento lógico dos veces antes de actualizar el agregado. Esa parte todavía está pendiente de diseñar, implementar y probar.

Para una nueva fuente, comprobar semántica, zona horaria, estabilidad de IDs, cobertura y condiciones de uso. Asignar espacio de nombres y preservar campos desconocidos como ausentes. Conservar el original para cotejar recuentos. Ele.me seguirá como muestras separadas mientras no exista una correspondencia válida con eventos de la nueva app.

No se requieren joins entre los datasets actuales: no comparten claves. La nueva miniapp referenciará su propio catálogo. Un catálogo basado en Glovo tendrá identificadores internos y documentará cómo trata nombres de tienda repetidos.

## 7. Estado operativo y siguientes pasos

Existen carga real, dashboards, replay, clics de la demo, CRUD y benchmarks. Falta el recorrido de reparto integrado y el generador del nuevo contrato. La demo corre en un nodo, con unos 4 GiB de memoria de Docker y límite total de servidor de unos 3,50 GiB. La lectura completa del JSON Ele.me agotó ese límite y no produjo una comparación finalizada.

Siguiente entrega: recorrido manual, contrato validado, prueba de reintento, publicación por lotes y dashboard de la plataforma. Después, medir una carga grande y comparar histórico/agregado con la misma respuesta. Dos nodos y un nuevo orden físico son experimentos posteriores.

## Referencias

- Código del proyecto: `sql/schema.sql`, `sql/eleme.sql`, `dashboard.py` y scripts.
- Medidas: [RESULTADOS.md](RESULTADOS.md), [ELEME.md](ELEME.md) e informes en `data/`.
- [MergeTree](https://clickhouse.com/docs/reference/engines/table-engines/mergetree-family/mergetree).
- [SummingMergeTree](https://clickhouse.com/docs/reference/engines/table-engines/mergetree-family/summingmergetree).
- [Vistas materializadas incrementales](https://clickhouse.com/docs/concepts/features/materialized-views/incremental-materialized-view).
