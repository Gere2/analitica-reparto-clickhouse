# Infraestructura Delivery Atlas v1

**Ampliación de esta versión:** el contrato de navegación v1 se conserva y se añaden pedidos/GPS en `sql/atlas_operations.sql`, un catálogo de demo y el dashboard de seguimiento. La raíz del puerto 8001 sirve ahora ese dashboard. Documentación vigente de las nuevas rutas, campos y procedencia: [DATOS-Y-TRACKING.md](DATOS-Y-TRACKING.md). La miniapp comercial continúa pendiente.

Fecha: 7 de octubre de 2026. Implementación: `compose.yaml`, `Dockerfile.atlas`, `atlas/` y `sql/atlas.sql`. El laboratorio anterior conserva su base `delivery`. La propuesta anterior `delivery_proposal` no es la base aplicada por esta versión.

## 1. Explicación corta para el equipo

Anuar construye una pequeña app ficticia. Cada acción crea un evento con un ID. Python comprueba el evento y lo apunta en una cola persistente. Un publicador recoge lotes y los inserta en ClickHouse. ClickHouse guarda los detalles y prepara recuentos diarios. El dashboard de Echenique consulta esos recuentos a través de Python.

```text
Miniapp de Anuar / generador de Jere
                  |
            POST /api/events
                  |
     Validación e ID estable (API Python)
                  |
       Cola persistente local (SQLite)
                  |
           Publicador por lotes
                  |
       ClickHouse: delivery_atlas.app_events
                  |
          Vista materializada de IDs
                  |
         app_daily_rollup -> app_daily_counts
                  |
              GET /api/summary
                  |
          Dashboard de Echenique
```

SQLite es un pequeño registro de transporte y reintentos, no el almacén que consulta el dashboard. ClickHouse realiza el trabajo analítico. La API se ejecuta en un contenedor separado del nodo ClickHouse. Dos contenedores no significan dos nodos de base de datos.

## 2. Arranque reproducible sin grandes descargas

Requisitos: Docker/Compose y Python 3.10 o posterior para los comandos de pruebas y generación. Los scripts usan la biblioteca estándar. La API usa Python 3.12 en Docker y ClickHouse 25.8. Los valores `demo` son credenciales del laboratorio local.

```bash
docker compose -f compose.yaml --profile atlas up -d --build --wait
docker compose -f compose.yaml --profile atlas ps
python3 -m unittest discover -s tests -v
python3 scripts/check_atlas.py
python3 scripts/atlas.py generate --events 10000 --batch 1000 --seed 42
python3 scripts/atlas.py status
```

La API está en `http://127.0.0.1:8001`. ClickHouse recibe HTTP en `127.0.0.1:8124`. Dentro de Compose, la API usa `http://clickhouse:8123/`. La ruta antigua del laboratorio usa `python3 dashboard.py` y el puerto 8000: es otro servicio.

El arranque aplica el SQL de manera idempotente antes de admitir eventos. No requiere OTTO, REES46, Ele.me ni Glovo en el ordenador de un compañero. La imagen de Python se descarga en el primer build. Se montan dos volúmenes: el histórico `clickhouse_data` y la nueva cola `atlas_queue`.

Tras editar Python, SQL o archivos web: repetir el comando de arranque con `--build`. Para parar la API, `docker compose -f compose.yaml --profile atlas stop atlas`. El siguiente arranque recupera la cola pendiente. No usar `down -v`: borra los volúmenes.

## 3. SQL y modelo físico

| Objeto | Una fila representa | Función |
|---|---|---|
| `app_events` | Una acción o una copia física de un reintento | Detalle, `ReplacingMergeTree(ingested_at)` |
| `app_daily_rollup` | Un conjunto parcial de IDs por día/ciudad/sección/tipo/origen | Estado de agregado, `AggregatingMergeTree` |
| `app_daily_rollup_mv` | Regla que procesa los bloques insertados | Generar `uniqExactState(event_id)` |
| `app_daily_counts` | Recuento lógico por combinación de dimensiones | Vista de lectura con `uniqExactMerge` |

La fila tiene versión, `event_id`, `session_id`, hora del evento, hora de recepción, acción, sección, ciudad, referencias opcionales de usuario/restaurante/producto y procedencia. Los campos desconocidos quedan en `null`.

Las particiones agrupan meses dentro de un nodo. El orden físico empieza por procedencia, fecha, ciudad y acción; termina en hora, sesión e ID del evento. Orienta búsquedas y agrupa reintentos idénticos. **No impone una clave única.**

`ReplacingMergeTree` elimina copias durante fusiones; para leer eventos lógicos antes de esas fusiones, usar `FINAL`. La vista incremental ve las inserciones, no la eliminación posterior de duplicados. Por eso no usamos `count()` incrementado en un `SummingMergeTree` como en la propuesta inicial: guardamos conjuntos de IDs y contamos cada ID una vez por grupo. Esto consume más memoria que un contador sencillo y hay que medirlo.

La API impide modificar las dimensiones de un evento ya aceptado. Con el mismo ID y contenido diferente devuelve 409. La garantía depende de usar ese publicador y conservar su registro. Inserciones manuales con el mismo ID y dimensiones diferentes no están cubiertas.

```bash
docker exec -it bd2-clickhouse clickhouse-client --user demo --password demo
```

```sql
SELECT count() FROM delivery_atlas.app_events FINAL;
SELECT * FROM delivery_atlas.app_daily_counts ORDER BY event_date, city_id;
DESCRIBE TABLE delivery_atlas.app_events;
SHOW CREATE TABLE delivery_atlas.app_daily_rollup_mv;
```

Las consultas explicadas están también en `sql/atlas_consultas.sql`.

## 4. Contrato y endpoints para Anuar y Echenique

Enviar un objeto `{"events": [...]}`. Máximo 5000 eventos o 5 MiB por petición. Cada lote se valida completo: una entrada inválida rechaza todo el lote.

```json
{
  "events": [{
    "schema_version": 1,
    "event_id": "fc7693c4-c366-4e55-a3c3-8aba2cd0c153",
    "session_id": "4ab0d7cb-aae4-41f6-b1dc-2bfc1d7e984",
    "event_time": "2026-10-07T10:00:00.000Z",
    "event_type": "restaurant_opened",
    "section": "restaurants",
    "city_id": "madrid",
    "restaurant_id": "fictional-madrid-1",
    "source": "delivery-miniapp",
    "source_kind": "demo_live"
  }]
}
```

Es una muestra de formato, no una interacción observada. Para una acción nueva crear UUIDs con `crypto.randomUUID()` y fecha con `new Date().toISOString()`. Guardar el objeto antes de enviarlo y reutilizarlo al reintentar. `demo_live` significa acción nueva en una app ficticia, no uso real de Uber Eats.

| Ruta | Uso / respuesta |
|---|---|
| `POST /api/events` | 202: nuevos eventos guardados en cola. 200: todo era reintento conocido |
| `GET /api/status` | Aceptados, duplicados, pendientes, publicados por esta API y errores |
| `GET /api/summary` | Recuentos lógicos desde ClickHouse, no desde SQLite |
| `GET /api/recent` | Últimos 30 eventos lógicos, incluyendo ID, sesión y ambas horas |
| `GET /health` | Comprueba conexión a ClickHouse; muestra error reciente del publicador |

`/api/summary` admite `from=AAAA-MM-DD`, `to`, `city_id`, `source_kind` y `event_type`. Ejemplo: `/api/summary?city_id=madrid&source_kind=synthetic`. La lista de grupos se limita a 10000; `events` y `groups` son el total del filtro y `truncated` indica si faltan grupos en la lista.

Acciones v1: `search`, `filter_applied`, `restaurant_opened`, `product_opened`, `product_impression`, `cart_added` y `order_submitted`. Las acciones sobre restaurante necesitan `restaurant_id`; abrir producto, impresión y carrito necesitan además `product_id`. Una simulación requiere `simulation_run_id`; una fuente histórica requiere `source_record_id`.

Errores: 400 formato/contrato, 409 ID con contenido distinto, 413 tamaño, 503 cola llena o base no disponible para lecturas. Para 503 y errores de red, reintentar el objeto original con espera. No reintentar indefinidamente 400/409/413. La cola llena no acepta el lote.

Servir los futuros archivos de miniapp y dashboard desde el mismo puerto 8001 evita necesitar CORS. Las pantallas definitivas quedan a cargo de Anuar y Echenique.

## 5. Confirmación, fallos y límites

202 significa **recibido de forma duradera**, no publicado ya en ClickHouse. El publicador recoge hasta 5000 eventos. Consulta la cola cada segundo cuando está vacía y hace una pausa de 0,3 segundos entre lotes. Si falla una publicación, deja las entradas pendientes y vuelve a probar.

El registro SQLite usa WAL, confirmación duradera y transacciones. Límite: 200000 eventos pendientes, configurable por `ATLAS_MAX_PENDING`. Conserva los IDs, huellas y payloads publicados: no hay limpieza automática y su disco crece con el histórico. Esto permite reconocer reintentos antiguos, pero es una limitación de la versión de clase.

Si ClickHouse recibió el lote pero la respuesta se perdió, la cola puede volver a enviarlo. Puede haber filas físicas repetidas. La lectura `FINAL` y los conjuntos de IDs del agregado evitan inflar los eventos lógicos para contenido inmutable. No es una transacción distribuida ni una garantía universal de exactly-once.

La prueba de respuesta perdida publica una entrada desde una cola temporal y la vuelve a enviar tras abrir esa cola otra vez. Esos eventos de comprobación aparecen en `test-city`. Las métricas de cola corresponden solo al publicador principal y no a inserciones SQL u otros publicadores de prueba.

Un único proceso API/publicador y un nodo ClickHouse. No ejecutar dos APIs compartiendo la misma cola ni declarar alta disponibilidad. No hay Kafka, sharding, réplicas, backup automatizado ni permisos separados de lectura/escritura. La base y la API solo exponen puertos al host local. Un despliegue compartido exige autenticación y permisos antes de abrirlos fuera de localhost.

## 6. Generación y mediciones

```bash
python3 scripts/atlas.py generate --events 1000000 --batch 5000 --seed 42 --start 2026-10-06T10:00:00Z
python3 scripts/atlas.py status
python3 scripts/benchmark_atlas.py
```

Esperar a `pending=0` y no enviar más eventos durante el benchmark. El generador crea sesiones de cinco acciones, tres ciudades y restaurantes ficticios. Todos los recorridos completan sus cinco pasos, una simplificación intencionada; no son una estimación de demanda ni conversión real.

Guarda semilla, fecha inicial, run ID, parámetros, huella del payload y tiempo de envío en `data/atlas/<run-id>.json`. Repetir la misma configuración con el mismo ID y fecha produce la misma carga lógica. Cambiar el lote no cambia los IDs. `--rate` indica una meta de envío, no una velocidad garantizada. La velocidad de envío incluye creación de eventos y confirmación de cola, no mide por sí sola publicación ni demora del dashboard.

`benchmark_atlas.py` compara tres consultas del detalle con `FINAL` y tres del agregado, con caché SQL desactivada. Comprueba resultados iguales y guarda tiempo de pared, tiempo del servidor, filas y bytes leídos. No se importan los 27,9× de OTTO como resultado de esta base.

`scripts/check_atlas.py` registra su evidencia en `data/atlas/checks.json`. Ejecutarlo sin carga concurrente para comparar detalle y agregado. Las pruebas unitarias comprueban reintentos concurrentes, recuperación del registro, conflicto con rollback del lote, cola llena y contrato inválido.

## 7. Qué falta para cerrar el proyecto

Miniapp completa de Anuar; dashboard específico de Echenique; prueba independiente en otro ordenador; integrar el CRUD existente en la demo; carga con abandonos/horarios más realistas; medición de retraso hasta el panel y latencias bajo carga concurrente; copia y restauración documentadas; ensayo de los 30 minutos.

**Comprobado el 7 de octubre:** un millón de eventos sintéticos aceptados y verificados en ClickHouse, reintentos, conflicto de ID, igualdad entre detalle y agregado y recuperación de una entrada pendiente tras paradas ordenadas. El nuevo agregado no fue más rápido en el benchmark local (0,703 s frente a 0,498 s); estudiar su coste es una tarea pendiente. Véanse [resultados y condiciones](RESULTADOS-ATLAS.md) y [evidencia exportada](evidencia-atlas.json).

`python3 scripts/recover_atlas.py` reproduce la prueba de recuperación y para brevemente servicios locales; ejecutarlo sin otros trabajos activos. `python3 scripts/crud_demo.py` demuestra operaciones sobre `delivery.demo_events`, una tabla de ensayo separada. Los eventos Atlas son inmutables y sus vistas incrementales no recalculan automáticamente un histórico modificado.

El registro local y los agregados exactos tienen costes que habrá que medir a mayor escala. Replicación o sharding son experimentos posteriores. La compatibilidad de futuras fuentes requiere adaptar y validar sus campos: el contrato no convierte cualquier dataset en clics automáticamente.

## Referencias técnicas

- [ReplacingMergeTree](https://clickhouse.com/docs/reference/engines/table-engines/mergetree-family/replacingmergetree).
- [AggregatingMergeTree](https://clickhouse.com/docs/reference/engines/table-engines/mergetree-family/aggregatingmergetree).
- [Reintentos y límites de deduplicación](https://clickhouse.com/docs/concepts/features/operations/insert/deduplicating-inserts-on-retries). La documentación actual incluye cambios posteriores a 25.8; esta versión no depende de esos ajustes nuevos.
- Código y pruebas del repositorio; [teoría aplicada y tareas pendientes](REVISION-TEORIA.md).
