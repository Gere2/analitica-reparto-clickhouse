# Presentación: 20 minutos + demo de 10 minutos

**Avance actual de 5 minutos:** [AVANCE-PRESENTACION.md](AVANCE-PRESENTACION.md). Este documento conserva el guion anterior de la exposición final y requiere adaptación al nuevo alcance de Delivery Atlas.

**Título:** Clickstream Lab: analítica de cientos de millones de eventos reales y prueba de mil millones de filas con ClickHouse.

**Tesis:** ClickHouse permite consultar y visualizar grandes tablas de eventos; el diseño físico, el agregado incremental y la procedencia de los datos se pueden medir y explicar.

**Nuevo encuadre para la siguiente versión:** presentar una plataforma ficticia de comida a domicilio y diseñar su infraestructura analítica para eventos masivos, con navegación y tráfico simulados, y adaptadores para datos reales futuros. El diseño está en [PLATAFORMA-FICTICIA.md](PLATAFORMA-FICTICIA.md). Las diapositivas actuales muestran la implementación anterior a esa integración: actualizar el recorrido cuando se implemente y mida. Los benchmarks existentes siguen siendo de OTTO/REES46/Ele.me, no de la plataforma ficticia.

Resultados verificados en este equipo: **628.425.832 eventos reales** de dos fuentes, **1.083.580.480 filas derivadas** y una comparación de **5,89 s frente a 0,21 s** para la misma pregunta diaria. Véase [RESULTADOS.md](RESULTADOS.md) para condiciones y límites.

[Diapositivas navegables](http://127.0.0.1:8000/otto-presentacion.html) (flechas y `F` para pantalla completa). [Demo reproducible](DEMO.md).

| Tiempo | Diapositivas | Qué explicar |
|---:|---:|---|
| 0–2 min | 1–2 | Una aplicación produce eventos al navegar. Un dashboard necesita agrupar por tiempo, tipo y producto, no recuperar un pedido aislado. |
| 2–4 min | 3–4 | OTTO: 216.716.096 eventos verificados, incluidos 194.720.954 clics; estructura JSONL de sesiones transformada a una fila por evento. |
| 4–7 min | 5–6 | ClickHouse como OLAP columnar que usa SQL. `MergeTree`, partes, compresión, índice disperso, particiones y lectura selectiva de columnas. Arquitectura ZIP/CSV → ETL Python → ClickHouse → API → dashboard. |
| 7–9 min | 7–8 | Dos relojes: suceso histórico e inserción durante el replay. Ventana de 30 segundos sobre `ingested_at`. |
| 9–11 min | 9–10 | Panel y modelo operativo de un nodo. `Distributed`, `ReplicatedMergeTree` y Keeper como explicación de escalado, sin fingir un clúster local. |
| 11–13 min | 11 | REES46: siete meses reales de marketplace con vistas, cesta y compras, categorías, marcas y precio. Geografía no publicada; no son eventos de Uber Eats/Glovo. |
| 13–15 min | 12 | Tabla de 1.083.580.480 filas derivadas, cinco escenarios etiquetados. Distinguir tamaño de workload de nuevos datos observados. |
| 15–17 min | 13–14 | Vista materializada y `SummingMergeTree`: 87 claves día/tipo. Comparación de consultas con misma respuesta y estadísticas de lecturas/tiempo del benchmark. |
| 17–20 min | 15–16 | Fortalezas, actualización/borrado, límites de los datasets, honestidad de métricas, y transición a la demo. |
| 20–30 min | — | Seguir [DEMO.md](DEMO.md). |

## Argumentos para preguntas

- **«¿Por qué ClickHouse y no una base tradicional?»** El caso dominante es `GROUP BY` repetido sobre eventos muy grandes. ClickHouse guarda y lee por columnas y ofrece agregados incrementales. PostgreSQL también puede almacenar eventos y construir agregados; la elección depende de la carga de trabajo. Los pedidos y cuentas individuales encajan mejor en un motor transaccional.
- **«¿Es NoSQL?»** Es un almacén columnar OLAP y usa SQL. Explicar la categoría sin ocultar ese matiz.
- **«¿Estos eventos son de Glovo o de España?»** No. OTTO son eventos comerciales anonimizados, y REES46 un marketplace anónimo de país no especificado. La analogía con delivery es el patrón de navegación y análisis.
- **«¿Los mil millones son datos reales?»** Son filas de prueba **derivadas de 216,7 millones de OTTO**. Nunca se presentan como nuevos usuarios o clics. Los otros dos datasets sí son observaciones publicadas.
- **«¿Es un feed en vivo?»** El replay inserta hoy eventos históricos a ritmo controlado; los clics de los botones son nuevos. No existe aquí una transmisión pública actual de OTTO, Glovo ni Uber Eats.
- **«¿Qué significa conversión?»** Hay que definir cohortes, sesión, ventana temporal y atribución; una simple razón entre recuentos de eventos no es una conversión de personas.
- **«¿Dónde está la escalabilidad?»** Una tabla local de mil millones de filas, una consulta medida y el diseño de particiones/orden. La demo no prueba tolerancia a fallos ni un clúster multi nodo.

## Fuentes

- [OTTO: descripción, conteos y licencia](https://github.com/otto-de/recsys-dataset)
- [REES46: datasets históricos del marketplace](https://data.rees46.com/)
- [ClickHouse: MergeTree](https://clickhouse.com/docs/engines/table-engines/mergetree-family/mergetree)
- [ClickHouse: materialized views](https://clickhouse.com/docs/materialized-views)
- [ClickHouse: escalado horizontal](https://clickhouse.com/docs/architecture/horizontal-scaling)
