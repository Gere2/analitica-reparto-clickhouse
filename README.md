# Clickstream Lab — ClickHouse a escala de cientos de millones y mil millones de filas

Proyecto BD2 de analítica de comportamiento. La pregunta central es **cómo guardar, consultar y visualizar flujos de eventos masivos**. Incluye fuentes históricas de navegación y recomendaciones de comida a domicilio, más una prueba de estrés derivada, identificadas por separado.

**Dirección acordada para desarrollar:** una plataforma ficticia de comida a domicilio, inspirada en Uber Eats/Glovo, cuya infraestructura analítica pueda recibir eventos simulados ahora y datos reales compatibles en el futuro. El [diseño propuesto](docs/PLATAFORMA-FICTICIA.md) define el recorrido, la procedencia y los criterios de aceptación. Esa plataforma y su contrato común todavía no están implementados; las cargas y mediciones de este README corresponden al sistema actual.

**Para el equipo:** [estado del proyecto y decisiones pendientes](docs/ESTADO-EQUIPO.md). Esta versión usa `compose.yaml`, la API Python `dashboard.py` y los paneles de `web/`. El repositorio conserva también archivos de la implementación anterior con Flask/Grafana; para ejecutar esta versión, seguir [INSTALACION.md](docs/INSTALACION.md) y usar explícitamente `docker compose -f compose.yaml up -d`.

| Fuente | Qué representa | Volumen |
|---|---|---:|
| [OTTO Recommender Systems Dataset](https://github.com/otto-de/recsys-dataset) | Clics, carritos y pedidos reales anonimizados | **216.716.096 eventos**, incluidos **194.720.954 clics** |
| [REES46 Marketplace](https://data.rees46.com/) | Vistas, carritos y compras reales de un marketplace | **411.709.736 eventos** en siete archivos mensuales, octubre de 2019 a abril de 2020 |
| Escenarios de estrés | Cinco variantes de OTTO generadas con SQL para medir consultas; **no son usuarios ni clics nuevos** | **1.083.580.480 filas derivadas** |
| [Ele.me · Tianchi](https://tianchi.aliyun.com/dataset/131047) | Muestras de recomendación de comida a domicilio en China, con etiqueta binaria de clic | **2.170.299 muestras cargadas**, incluidas **38.914 etiquetas positivas de clic**, de la primera parte D1_0; 146 M declarados para el conjunto completo |

No son datos de Uber Eats, Glovo ni necesariamente de España. REES46 no identifica el país del marketplace. Una vista de REES46 tampoco equivale a un clic de OTTO. La relación con una app de reparto está en el **tipo de trabajo analítico**: registrar eventos de navegación, mostrarlos por tiempo, categoría y marca y consultar el almacén sin recorrer sus filas una por una.

Las dos fuentes suman **628.425.832 filas de eventos reales**, aunque representan poblaciones y acciones distintas. La tabla derivada de más de mil millones se usa únicamente para probar escala.

## Qué se puede enseñar en directo

- [Dashboard de clics OTTO](http://127.0.0.1:8000/): archivo real, reproducción histórica a ritmo configurable y clics genuinamente nuevos de la página, en tres tablas separadas.
- [Dashboard del marketplace REES46](http://127.0.0.1:8000/rees46.html): volumen mensual, tipo de acción, categorías, marcas y filtro por mes sobre ClickHouse.
- [Dashboard de escala](http://127.0.0.1:8000/scale.html): separa eventos reales y filas derivadas, muestra tamaño en disco y las mediciones del benchmark.
- [Panel Ele.me](http://127.0.0.1:8000/eleme.html): **2.170.299 muestras reales** del recomendador de comida a domicilio, agrupadas por día, hora, ciudad anónima y periodo de comida; [acceso, inspección y carga](docs/ELEME.md). Solo está cargado el primer ZIP oficial D1_0; no son 146 millones de clics.
- **Archivo frente a agregado:** una vista materializada resume 216.716.096 eventos OTTO en 87 claves de día y tipo, conservando el mismo resultado para esa pregunta. `scripts/benchmark.py` registra tiempo, filas y bytes leídos.
- **Prueba de mil millones:** `delivery.otto_scale_benchmark` permite consultar 1.083.580.480 filas derivadas en un equipo local, con `scenario` para señalar su origen.
- **Medición reproducible:** en este equipo, agrupar OTTO por día y tipo tomó 5,89 s desde el archivo frente a 0,21 s desde el agregado (misma respuesta, caché SQL desactivada); agrupar 1.083.580.480 filas por escenario tomó 1,44 s. Las condiciones y los bytes leídos están en [RESULTADOS.md](docs/RESULTADOS.md).
- Python conectado a ClickHouse para carga, reproducción, consultas, actualización y borrado de una tabla de ensayo.

## Arquitectura

```text
OTTO ZIP JSONL ── ETL Python ──→ otto_archive (216,7 M reales) ── MV ──→ otto_daily_rollup
                                       │
                                       ├─ SQL × 5 → otto_scale_benchmark (1.083.580.480 derivadas)
                                       └─ replay Python → otto_replay ───────┐
REES46 CSV.gz × 7 ── ETL Python → rees46_events ─────────────────────────────┤
Ele.me CSV ZIP → staging → validación completa → eleme_samples ─────────────┤
Usuario → botones web → API Python → live_clicks ────────────────────────────┤
                                                     API Python → dashboards ┘
```

ClickHouse 25.8 corre en un nodo Docker. Los datos se guardan en tablas `MergeTree`; la vista materializada diaria usa `SummingMergeTree`. El navegador consulta una API Python que a su vez consulta ClickHouse. La reproducción inserta eventos históricos **ahora**, con `ingested_at` distinto de la hora real antigua `event_time`; no se presenta como un feed público en vivo.

## Puesta en marcha

```bash
docker compose up -d
python3 scripts/eleme.py init
python3 scripts/otto.py download
python3 scripts/otto.py load
python3 scripts/rollup.py
python3 scripts/rees46.py download
python3 scripts/rees46.py load
python3 scripts/scale.py
python3 scripts/benchmark.py
python3 scripts/check.py
python3 scripts/report.py
python3 dashboard.py
```

Preparad las cargas antes de la clase. Para la demo:

```bash
python3 scripts/otto.py replay --rate 5000 --limit 200000 --reset
python3 scripts/crud_demo.py
```

La ruta corta ejecuta solo OTTO, rollup y dashboard. La ruta completa necesita espacio y tiempo adicionales; véase [INSTALACION.md](docs/INSTALACION.md). El ZIP OTTO procede de un [espejo público](https://huggingface.co/datasets/hazemessam/otto-recsys) y se verifica por SHA-256 y por los tres recuentos publicados por OTTO. Los siete CSV.gz REES46 se descargan del publicador y se comprueban por tamaño, descompresión y filas cargadas por mes.

**Material de clase:** [guía de instalación](docs/INSTALACION.md), [demo de 10 minutos](docs/DEMO.md), [guion de 20 minutos](docs/PRESENTACION.md), [fundamentos y límites](docs/FUNDAMENTOS.md), [resultados medidos](docs/RESULTADOS.md) y [diapositivas navegables](http://127.0.0.1:8000/otto-presentacion.html).
