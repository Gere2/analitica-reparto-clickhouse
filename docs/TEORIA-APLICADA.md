# Teoría del curso aplicada al proyecto

Cada decisión técnica y el concepto del temario que la justifica.

| Concepto | Decisión | Dónde está |
|---|---|---|
| **Monolito o microservicios** | Una sola app Flask. Separar un servicio de eventos solo añadiría latencia de red | `app/app.py` |
| **ACID frente a BASE** | ClickHouse no tiene transacciones entre filas ni tablas. El carrito y el pago **no** se guardan aquí (serían trabajo de PostgreSQL); solo registramos que *ocurrieron* | Diseño general |
| **CAP / PACELC** | Un nodo = «CA» (sin partición posible, pero sin alta disponibilidad). Con réplicas (`ReplicatedMergeTree`) sería **PA/EL**: un embudo con segundos de retraso no rompe nada. `insert_quorum` lo acercaría a PC/EC a cambio de latencia | Defensa oral |
| **Sharding** | Clave `cityHash64(session_id)`: reparte bien (no hay sesión «caliente») y `windowFunnel` calcula cada embudo en un solo fragmento. Contrapartida: «eventos del restaurante X» pregunta a todos los fragmentos. Se explica, no se monta | `01_tablas.sql` (comentario) |
| **Particionado ≠ sharding** | `PARTITION BY toYYYYMM(ts)` organiza dentro de un servidor | `01_tablas.sql` |
| **Replicación** | Siguiente paso: `ReplicatedMergeTree` + ClickHouse Keeper | Defensa oral |
| **Colas o flujos** | Los clics interesan a varios sistemas → son un **flujo** (Kafka), no una cola. En la demo: INSERT directo con `async_insert`. Kafka es la evolución | `app/app.py` |
| **Tolerancia a fallos** | Timeouts, reintentos con backoff exponencial y jitter, reintentos **idempotentes** (`event_id` y `ts` del cliente + `ReplacingMergeTree`), búfer si ClickHouse no responde | `app/app.py`, `01_tablas.sql` |
| **Observabilidad** | Grafana: embudo (producto) y latencia de consultas desde `system.query_log` (sistema) | `grafana/`, consulta 7 |
| **Seguridad** | Usuarios con permisos mínimos (`app_writer` solo inserta, `grafana_reader` solo lee), secretos en `.env`, contenedor sin root, imagen `slim` | `02_usuarios.sh`, `Dockerfile` |
| **Almacenamiento** | ClickHouse = *data warehouse* (esquema al escribir). Los CSV en bruto de `datos/` = pequeño *data lake* | `datos/` |
| **Docker Compose** | Healthchecks con `service_healthy`, volúmenes nombrados, límites de recursos, sin clave `version:` | `docker-compose.yml` |

## Ventajas y desventajas de ClickHouse aquí

**Ventajas:** almacenamiento por columnas (un embudo lee 3 o 4 columnas de 15), `windowFunnel` y
`uniq` nativos, tabla en la que solo se añaden filas, vista materializada incremental para el panel
y tabla ancha sin JOIN.

**Desventajas:** UPDATE y DELETE son mutaciones caras; sin transacciones; los INSERT pequeños
penalizan (se mitiga con `async_insert` y lotes); la desduplicación es eventual (`FINAL` si hace
falta exactitud); la vista materializada no ve los datos anteriores a su creación; MT-LIFT y
nuestra app no se pueden cruzar por usuario.
