# Delivery Atlas: datos conservados y seguimiento en directo

Actualización: 7 de octubre de 2026. Decisión de Jere: continuar la implementación con Rayo; repartir trabajo cuando los compañeros se incorporen. Primera demo: **Madrid, repartidores simulados y posiciones cada dos segundos**, confirmado por Jere.

## 1. Qué estamos construyendo ahora

Un dashboard que combina navegación, pedidos simulados, posiciones de repartidores, métricas de cola e inventario de fuentes. Los movimientos aparecen después de publicarse en ClickHouse. No se animan posiciones inventadas solamente en el navegador.

El plano es una proyección local de latitud/longitud en el área de Madrid, sin mapa de calles. La línea azul representa posiciones recibidas de ese pedido; no calcula una ruta óptima ni comprueba calles transitables. Coordenadas, velocidad y precisión GPS son sintéticas. La API y el panel consultan con frecuencia de dos segundos, **pero esa frecuencia no es una garantía de demora de dos segundos**.

## 2. Inventario: qué conservar y para qué

Se inspeccionaron las tablas y columnas de la instancia activa, no solo los archivos de propuesta. [auditoria-esquemas.json](auditoria-esquemas.json) recoge el inventario anterior a esta ampliación. No se borraron las fuentes.

| Fuente / tabla | Filas observadas antes de ampliar | Campos que conservamos | Uso adecuado |
|---|---:|---|---|
| OTTO `otto_archive` | 216.716.096 | session_id, article_id, event_time, event_type, event_position | Navegación real de comercio electrónico y benchmarks |
| REES46 `rees46_events` | 411.709.736 | fecha, acción, product_id, categoría, marca, precio, user_id, user_session | Análisis histórico de vistas/carritos/compras |
| Ele.me `eleme_samples` | 2.170.299 | source_id/file/row, clicked, user/shop/item, ciudad/distrito/categoría, hora y meal_period, raw_features | Muestras de recomendación, no sesiones completas |
| Glovo `glovo_products` | 2.887.444 | source_row, country/city, store_name, product_name, collection_section, descripción y campos originales | Catálogo; España tiene 415.137 productos en nuestra carga |
| TRD / Meituan `orders` | 1.068.495 | order_id, user_id, restaurant_id, area_id, price_band, ordered_at, periodo y fecha | Pedidos históricos; price_band no es un importe exacto |
| TRD `clicks` / `click_summary` | 4.021.488 / 517.353 | fecha, pedido, posición, restaurant_id; conteos derivados | Secuencia registrada de restaurantes, no hora GPS por clic |
| TRD `restaurants` / `foods` | 29.072 / 179.778 | ID, categoría, área/score; precio/categoría del producto | Dimensiones del mismo dataset, no negocios españoles |
| TRD `order_items` | 3.445.180 | fecha, order_id, food_id | Detalle de pedidos del mismo origen |
| `otto_replay` | 1.200.000 | evento original + ingested_at | Reproducción histórica; no usuarios nuevos |
| `otto_scale_benchmark` | 1.083.580.480 | scenario y campos derivados OTTO | Estrés, sin observaciones nuevas |
| Atlas `app_events` | 1.000.003 filas físicas en el inventario | contrato v1 completo, ID, sesión, ambas horas, acción, ciudad y procedencia | Nuestra navegación manual/sintética; separar por origen |

Las tablas pequeñas de prueba, staging y agregados se conservan también. Una fila de un agregado no representa un evento. Las cifras del inventario físico pueden cambiar durante fusiones; las pruebas lógicas usan `FINAL` o IDs únicos.

Los primeros documentos mencionan Criteo, MT-LIFT y un censo de Madrid. **No hay tablas de esas fuentes en la instancia activa inspeccionada.** Los archivos de aquellas propuestas permanecen en el repositorio como contexto; no se anuncian como fuentes disponibles del nuevo dashboard. El esquema TRD usado está en `sql/schema.sql`; su ETL enlaza el origen en `scripts/prepare.py`.

## 3. No unir poblaciones que no comparten IDs

OTTO no conoce los productos de Glovo; Ele.me no identifica nuestros negocios ficticios en España. Dentro de TRD sí se pueden unir pedidos, productos y clics por sus claves y fechas. Entre datasets no existe una unión fiable que convierta todo en pedidos de una misma app.

Por eso se conservan dos bases lógicas en el mismo nodo: **delivery** (laboratorio histórico) y **delivery_atlas** (modelo propio). No son dos servidores. Los paneles antiguos siguen usando el puerto 8000; Atlas usa 8001.

## 4. Qué columnas y estructuras reutilizamos

### Navegación: contrato v1 conservado

`app_events` mantiene schema_version, event_id, session_id, event_time, event_date, ingested_at, event_type, section, city_id, user_id, restaurant_id, product_id, source, source_kind, source_record_id y simulation_run_id. Las referencias opcionales desconocidas siguen siendo null.

Su agregado exacto y la deduplicación siguen funcionando. El generador grande original y las acciones manuales siguen admitidos. No añadimos posiciones a esa tabla: una posición GPS no es un clic.

### Catálogo de demo: campos ficticios explícitos

- **demo_restaurants:** restaurant_id, name, city_id, latitude, longitude, location_kind, source_kind, version. Doce establecimientos ficticios; ubicaciones e identidad sintéticas.
- **demo_products:** product_id, restaurant_id, product_name, price_minor, currency, price_kind, name_kind, source_table, source_row, version. Treinta y seis productos.
- Si Glovo Madrid está disponible al sembrar la demo, se copia el nombre de una muestra y su fila de origen. Si no, se usan nombres ficticios. **El precio siempre es ficticio** y no se atribuye a Glovo. Asignar el producto a un negocio ficticio tampoco demuestra que lo venda ese negocio real.
- Se siembra al primer arranque. Una actualización futura del catálogo debe ser una operación explícita con validación; reiniciar no debe cambiar lo que presentábamos antes.

### Nuevos hechos operativos

| Tabla | Una fila es | Campos principales |
|---|---|---|
| **courier_positions** | Una posición sintética del repartidor | event_id, run, ambas horas, city, courier_id, order_id, latitude, longitude, speed_kmh, accuracy_m, source/kind |
| **order_events** | Foto completa de un pedido en un estado | event_id/run/horas, order_id, courier_id, restaurant_id, status, amount_minor, currency, recogida/entrega lat/lon, order_created_at, promised_delivery_at, source/kind |

Las horas están en UTC. `amount_minor` son céntimos enteros, nunca un precio flotante. El panel los formatea en EUR. Estados: created, preparing, picked_up, en_route, delivered y cancelled. Los campos de GPS se validan por rango y finitud. La API actual solo admite operación `synthetic`; conectar un GPS real exige revisar contrato, procedencia y acceso, no quitar una etiqueta.

El modelo conserva IDs propios para relacionar pedidos y repartidores **dentro de una ejecución**. ClickHouse no impone claves foráneas; el simulador mantiene esas relaciones. La API de telemetría comprueba el formato, no es un motor transaccional de asignación de repartos.

## 5. Cómo se obtiene la última posición

`ReplacingMergeTree(ingested_at)` guarda el histórico de posiciones/estados. Las tablas `courier_latest_state` y `order_latest_state` usan `AggregatingMergeTree`; sus vistas materializadas calculan `argMaxState` y las vistas de lectura usan `argMaxMerge`.

El valor de comparación es `(event_time,event_id)`: gana la hora de evento más reciente; si empatan, el UUID decide de forma determinista. No gana simplemente lo último que llegó al servidor. El estado completo se guarda en una tupla, para que latitud, longitud, pedido y hora procedan de la misma fila. Esto sigue el patrón documentado de [argMax](https://clickhouse.com/docs/reference/functions/aggregate-functions/argMax) y [AggregatingMergeTree](https://clickhouse.com/docs/reference/engines/table-engines/mergetree-family/aggregatingmergetree).

Los grupos incluyen run, ciudad y repartidor/pedido para separar ejecuciones. El simulador detenido deja su histórico visible. Al reiniciar la API se recuerda el último run, pero **no se reinicia automáticamente la generación**.

## 6. Dónde se ingesta cada cosa

```text
Fuentes públicas -> ETL existente -> delivery (tablas originales)
Navegación propia -> POST /api/events -> cola -> app_events
GPS simulado -> POST /api/operations, kind=courier_positions -> cola -> courier_positions
Estados simulados -> POST /api/operations, kind=order_events -> cola -> order_events
Simulador integrado -> misma validación y cola -> esas tres tablas
Catálogo pequeño -> sembrado explícito al primer arranque -> demo_restaurants/products
```

`POST /api/operations` acepta `{"kind":"courier_positions","events":[...]}` o `order_events`. El ejemplo completo se obtiene del generador `atlas/simulation.py`. Máximo 5000 eventos o 5 MiB. ID y contenido se conservan al reintentar; 202 confirma la cola y 200 reconoce un reintento. `_stream` es metadato interno: no se envía desde un cliente.

Si un lote mezcla tipos dentro de la cola, el publicador hace un INSERT por tabla. **No hay una transacción entre esos INSERTs.** Si falla después del primero, el lote queda pendiente y se vuelve a enviar. Puede haber copias físicas; las lecturas y agregados lógicos resuelven los reintentos para contenidos inmutables. Las lecturas de GPS y pedidos también son consultas separadas y pueden mostrar diferencias breves durante una publicación.

La cola no es una base analítica ni una réplica. Sigue limitada a 200000 pendientes y conserva payloads publicados: hay que medir su crecimiento y diseñar limpieza/backup antes de producción. La telemetría aún no tiene TTL; no se borraron históricos automáticamente.

## 7. Qué enseña el dashboard y qué tiempo mide

- Mapa: posiciones publicadas, seleccionables, con recorrido del pedido actual.
- Pedidos: activos, entregados, cancelados, fuera del plazo ficticio e importe ficticio entregado. No hay ingresos comerciales reales.
- GPS: recuento de IDs únicos por intervalos de cinco segundos, últimos dos minutos del run seleccionado.
- Frescura: diferencia entre hora del evento y consulta. Si falla una consulta, se avisa y se conservan posiciones anteriores.
- Hasta recibir en API: `ingested_at - event_time`, **no** el tiempo hasta publicación. No llamar a ese valor latencia total.
- Navegación: recuentos de Madrid desde el agregado, con selector synthetic/demo_live y botón de búsqueda manual. Se identifica como todo el histórico Atlas. Esta sección consulta cada diez segundos para no hacer competir el agregado de un millón de IDs con el seguimiento; al cambiar procedencia se solicita de nuevo.
- Inventario y muestra Glovo: metadatos de tablas y catálogo, separados de la operación sintética. El inventario no ejecuta un count completo de todos los datasets cada dos segundos.

## 8. Arranque y demo

```bash
docker compose -f compose.yaml --profile atlas up -d --build --wait
python3 -m unittest discover -s tests -v
python3 scripts/check_operations.py
```

Abrir **http://127.0.0.1:8001/**. Pulsar Iniciar simulación. Elegir un repartidor, observar las coordenadas y el histórico, esperar un cambio de estado, registrar una búsqueda manual y cambiar procedencia a acciones manuales. Parar conserva los datos y detiene la generación. Cambiar flota requiere parar y comenzar un nuevo run.

Rutas de lectura: `/api/simulation`, `/api/operations?run_id=UUID`, `/api/track?run_id=UUID&courier_id=UUID`, `/api/demo-catalog`, `/api/catalog`, `/api/inventory`, `/api/summary`, `/api/status`. Control: `POST /api/simulation/start` con fleet/interval/seed, `POST /api/simulation/stop` con `{}`.

Carga histórica GPS opcional:

```bash
python3 scripts/operations.py --positions 100000 --fleet 12 --seed 42 --start 2026-10-06T10:00:00Z
python3 scripts/atlas.py status
```

Es una carga distinta de la flota que genera posiciones ahora. Repetir los parámetros conserva el run y los IDs. El informe de envío no prueba por sí solo publicación; comprobar run en ClickHouse. Los primeros pedidos de la flota empiezan en fases escalonadas y su historial inicial puede ser parcial. Un ciclo dura 160 s y puede cancelarse; los parámetros no están calibrados con reparto real. Las sesiones de navegación generadas son un escenario independiente con abandonos: no se relacionan con una compra real ni sirven para calcular conversión de esos pedidos.

**Carga comprobada en este equipo:** 100000 posiciones y 5965 fotos de estado, ambas verificadas en ClickHouse por run ID. Envío de 105965 registros: 435,887 s, durante una ejecución concurrente de flota y consultas. No es un benchmark de capacidad de ClickHouse. [Evidencia de carga](evidencia-carga-gps.json). [Pruebas de reintentos y orden temporal](evidencia-tracking.json). Consultas para clase: `sql/atlas_tracking_consultas.sql`.

En una muestra anterior a los ajustes, durante carga concurrente, `/api/operations` tardó 8,36 s y devolvió posiciones de 52,6 s de antigüedad. Se separó la lectura de navegación del seguimiento, se evitó repetir el agregado para calcular totales y se limitó el paralelismo a cuatro hilos. No hay todavía una prueba sostenida que garantice una latencia bajo carga. Si el publicador se atrasa, mostrarlo forma parte de la demo; la cola no convierte el retraso en tiempo real instantáneo.

La API mantiene ahora una conexión SQLite compartida y protegida por un bloqueo, con WAL y `synchronous=FULL`; evita reabrir la conexión y perder su caché en cada lote. Tras estos ajustes, **tres muestras locales sin carga histórica concurrente** devolvieron los 12 repartidores con antigüedad máxima de 1,761–2,279 s al consultar y consultas de 0,177–0,855 s. Son observaciones puntuales, no una garantía de rendimiento sostenido ni una prueba aislada del efecto de cada ajuste. [Evidencia de frescura](evidencia-frescura.json).

## 9. Qué base de datos usar y qué ampliar después

**Ahora:** ClickHouse para eventos, históricos y lecturas agregadas; SQLite como transporte persistente local. Encaja con la asignatura y con [analítica en tiempo real](https://clickhouse.com/use-cases/real-time-analytics). No necesitamos otro motor para demostrar este flujo.

**Si se convierte en una app de reparto real:** una base transaccional para aceptar/cancelar/asignar pedidos con reglas y transacciones, y un sistema de transporte distribuido si crece la ingesta. Es una ampliación arquitectónica, no algo instalado hoy. No prometemos asignación operativa fiable, alta disponibilidad ni precisión GPS real por tener un mapa.

Siguientes pasos con mayor valor: miniapp comercial conectada, relación explícita entre su checkout y un pedido simulado, medición sostenida de demora bajo carga, limpieza/backup de cola e historial, y reproducción en otra máquina. Un segundo nodo es un experimento posterior; la evidencia actual corresponde a uno.
