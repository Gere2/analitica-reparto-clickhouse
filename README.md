# Delivery Atlas — infraestructura analítica de una plataforma de reparto

Proyecto BD2 para diseñar la infraestructura analítica de una plataforma ficticia de comida a domicilio. El objetivo es recibir eventos de navegación masivos, conservar su procedencia y alimentar un dashboard con ClickHouse. La implementación actual, llamada Clickstream Lab en el panel OTTO, aporta el laboratorio de datos y rendimiento sobre el que desarrollamos ese caso.

**Actualización del 7 de octubre:** la plataforma ficticia ya tiene contrato validado, cola duradera, publicación por lotes, SQL aplicado en `delivery_atlas`, generador reproducible y dashboard de operación. La miniapp comercial es la siguiente entrega. [Plan para Jere, Anuar y Echenique](docs/PLAN-EQUIPO.md) y [guía completa de infraestructura](docs/INFRAESTRUCTURA-ATLAS.md).

**Para repartir el trabajo hoy:** [guía del equipo en PDF](output/pdf/Delivery-Atlas-Guia-Equipo.pdf). [Pruebas de la nueva base](docs/RESULTADOS-ATLAS.md): un millón de eventos sintéticos verificados, reintentos y recuperación tras reinicio. El agregado exacto conserva el resultado, pero aún no mejora la velocidad del detalle en esta prueba.

**Ampliación de operación en directo:** [datos conservados, columnas, ingesta y tracking](docs/DATOS-Y-TRACKING.md). Dashboard en **http://127.0.0.1:8001/**, con control de flota simulada de Madrid, posiciones cada dos segundos, pedidos/estados/importe ficticio, navegación y catálogo. Nuevas tablas en `sql/atlas_operations.sql`. Jere y Rayo continúan la implementación; el reparto del PDF anterior queda como propuesta para cuando se incorpore el equipo.

[Recorrido de demo y diagnóstico](docs/DEMO-TRACKING.md). Carga adicional comprobada: **100000 posiciones y 5965 estados sintéticos**, además de la navegación previa. El intervalo de dos segundos es una configuración: el panel muestra el retraso observado y no garantiza entrega instantánea.

### Empezar con la nueva plataforma, sin descargar datasets grandes

```bash
docker compose -f compose.yaml --profile atlas up -d --build --wait
python3 -m unittest discover -s tests -v
python3 scripts/check_atlas.py
python3 scripts/atlas.py generate --events 10000 --batch 1000 --seed 42
python3 scripts/atlas.py status
```

API en `http://127.0.0.1:8001`, SQL en [sql/atlas.sql](sql/atlas.sql), filtros en `/api/summary`. 202 confirma recepción en cola; la publicación en ClickHouse llega después. El laboratorio histórico y sus cifras se describen abajo y conservan su base `delivery`.

**Estructura de la base de datos:** [mapa del laboratorio y evolución](docs/ESTRUCTURA-BD.md). `sql/propuesta_delivery.sql` conserva el primer diseño; la implementación v1 usa `sql/atlas.sql` con un agregado de IDs únicos para manejar reintentos.

**Avance de 5 minutos, en inglés:** [presentación simplificada navegable](http://127.0.0.1:8000/avance-bd.html), [PowerPoint editable](presentaciones/Delivery-Atlas-Simple-EN.pptx) y [chuleta bilingüe en PDF](output/pdf/Delivery-Atlas-Cheat-Sheet-Simple-EN-ES.pdf). El recorrido presenta el proyecto, ClickHouse, las fuentes de datos, la propuesta de ingesta y esquema, una prueba de velocidad y los próximos pasos. También hay [notas editables](docs/NOTAS-PRESENTADOR.md). La [revisión frente a los apuntes del profesor](docs/REVISION-TEORIA.md) explica qué encaja y qué falta.

**Para el equipo:** [estado del proyecto y decisiones pendientes](docs/ESTADO-EQUIPO.md). El laboratorio histórico usa `compose.yaml`, la API Python `dashboard.py` y sus paneles de `web/`; la nueva infraestructura Atlas usa el perfil `atlas` del mismo Compose y `atlas/server.py`. El repositorio conserva también archivos de la implementación anterior con Flask/Grafana; seguir [INSTALACION.md](docs/INSTALACION.md) para elegir la ruta correcta.

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
docker compose -f compose.yaml up -d
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

## Compartir el dashboard

**Demo pública de solo lectura:** https://delivery-atlas-demo.vercel.app. La base de datos y el simulador siguen locales: el tracking se actualiza mientras el ordenador de Jere, Docker y el túnel permanezcan activos. Consultar [la guía de compartición](docs/COMPARTIR-VERCEL.md) para arranque, variables privadas, despliegue y parada.
