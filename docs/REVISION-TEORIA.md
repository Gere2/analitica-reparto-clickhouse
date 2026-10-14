# Revisión del proyecto frente a la teoría del profesor

Fecha: 5 de octubre de 2026. Esta revisión compara los materiales de `recursos/` con `compose.yaml`, `dashboard.py`, los DDL de `sql/` y las mediciones guardadas. La guía docente describe la asignatura. Los apuntes explican conceptos y ejemplos, y no convierten cada componente del ejemplo en un requisito de nuestro proyecto.

## Conclusión

**El proyecto encaja como infraestructura de analítica de eventos para una plataforma ficticia de comida a domicilio.** La guía incluye almacenamiento por columnas, modelado, ingesta, data warehouses y streaming. El trabajo actual demuestra almacenamiento y consultas masivas. El siguiente paso debe completar el contrato y la ingesta de la aplicación ficticia, y medir sus garantías. Ya hay volumen suficiente.

ClickHouse es un sistema analítico por columnas con SQL y esquema tipado. Conviene presentarlo como OLAP y justificar esa elección por sus patrones de lectura y agregación. Almacenamiento columnar de ClickHouse y modelo wide-column de Cassandra son conceptos distintos. Los recursos entregados no incluyen la sección **Personas** que asigna las tecnologías, así que esta revisión no confirma la elegibilidad administrativa de ClickHouse para la entrega.

## Contraste con los apuntes

| Concepto y referencia | Evidencia del proyecto | Valoración y ajuste |
|---|---|---|
| Modelar según los accesos. Guía, páginas 1–2 y 4 | Una fila OTTO es un evento. Ele.me conserva muestras. Glovo conserva catálogo | Encaja. Documentar el grano de cada tabla y conservar fuentes separadas |
| Frontend, API y backend. `01_1_Components.md` | Navegador, API HTTP Python y ClickHouse | Encaja. La API actual es pequeña y monolítica, sin gateway ni balanceador |
| Escalera de escalado. `01_1_Components.md` | Claves físicas y agregado diario antes de añadir nodos | Encaja. El benchmark acredita una optimización local, no escalado horizontal |
| Docker, persistencia y salud. `01_3_Docker.md` | Imagen 25.8, volumen y healthcheck | Parcial. La API de la ruta actual corre en el host. Falta empaquetar toda esa ruta para reproducirla con una orden |
| Disponibilidad. `01_2_Concepts.md` | Un nodo y un volumen Docker | Falta redundancia. Persistencia no implica alta disponibilidad ni sustituye una copia de seguridad |
| Consistencia, CAP y PACELC. `01_2_Concepts.md` | Sin réplicas en el despliegue actual | Explicar qué ocurre al insertar y al leer. No asignar una etiqueta CP/AP al producto sin indicar topología y configuración |
| Sharding y replicación. `01_4_Cross_cutting_concerns.md` | Particiones locales por mes o archivo | Precisar que son particiones de tablas dentro de un nodo. Sharding reparte datos entre nodos y replicación conserva copias |
| Warehouse y lake. `01_4_Cross_cutting_concerns.md` | Archivos fuente y tablas tipadas con agregados | Capa analítica similar a un warehouse. Archivos locales de entrada por sí solos no demuestran un data lake ni un lakehouse |
| Streaming. `01_4_Cross_cutting_concerns.md` | Replay Python por lotes y botones con acciones nuevas | Ingesta incremental. El replay es histórico y el refresco del dashboard usa consultas periódicas. Falta un log duradero con offsets para demostrar las garantías de un stream |
| Idempotencia. `01_1_Components.md` | `/api/live-click` inserta un UUID generado en servidor. El DDL futuro propone ID estable | Falta resolver reintentos. Repetir el POST puede producir dos filas. `event_id` y `ORDER BY` no imponen unicidad |
| Resiliencia. `01_4_Cross_cutting_concerns.md` | Timeouts de HTTP y validación básica | Parcial. Falta definir confirmación, reanudación, límites de lotes/cola y respuesta ante saturación |
| Percentiles y observabilidad. `01_1_Components.md`, `01_4_Cross_cutting_concerns.md` | Mediana de tres consultas y metadatos de lecturas | Sirve como comparación local. No acredita p95/p99, capacidad de API ni latencia completa del evento hasta el dashboard |
| Seguridad de Docker. `01_3_Docker.md` | Puertos de demo limitados a localhost, configuración con valores `demo` y variables opcionales en Python | Configuración de laboratorio. Para un despliegue compartido, externalizar credenciales y separar permisos de ingesta y lectura |
| Reflexión crítica y comparación. Enunciado de la entrega | Histórico frente a agregado, misma respuesta | Comparación dentro de ClickHouse. Todavía no hay un benchmark contra PostgreSQL ni otro motor |

## Cambios que aplicamos al alcance y a la presentación

1. Usar **Delivery Atlas** para el caso ficticio y marcar las tablas de su contrato como propuestas. El laboratorio público ya funciona, pero no demuestra aún el rendimiento del modelo futuro.
2. Centrar el avance de **5 minutos** en arquitectura, grano del evento, diseño físico y una mejora de consulta medida. OTTO demuestra escala. Ele.me y Glovo aportan contexto del sector. REES46 y el estrés quedan como material complementario.
3. Describir los tres tiempos con precisión: hora histórica del evento, momento de ingesta y momento de refresco del panel. Solo los botones registran acciones nuevas de la demo actual.
4. Mostrar las limitaciones operativas: nodo único, sin sharding ni réplica y sin protocolo general de idempotencia demostrado.
5. Mantener el DDL futuro fuera del servidor hasta implementar y probar su publicación. La vista incremental debe recibir eventos sin duplicados de reintento.

## Siguiente implementación, por prioridad

### P1. Una ruta completa para el nuevo contrato

Miniapp mínima, publicador por lotes y `app_events`. Definir acciones y campos por tipo de evento, tamaño máximo, validación y trazabilidad. Usar un identificador estable creado antes del envío. Ensayar un reintento después de perder una respuesta y demostrar un único evento lógico y un único incremento en el agregado.

Elegir y documentar la garantía de entrega. Si se pretende recuperar después de una caída, el publicador necesita estado duradero y un mecanismo de deduplicación coherente con el almacenamiento y la vista. Una caché en memoria con IDs no acredita esa garantía. No presentar una entrega exactly-once hasta verificar el recorrido completo.

### P2. Medir la infraestructura

Registrar eventos aceptados por segundo, filas y bytes por lote, rechazos, errores, memoria y retraso desde `event_time`/`ingested_at` hasta el panel. Medir latencia de solicitudes con una carga suficiente para calcular percentiles. Diferenciar caché de API, caché SQL y agregado persistente.

### P3. Reproducibilidad y fallos

Empaquetar API y ClickHouse de la ruta actual en Compose con healthcheck, red por nombre de servicio, versiones y límites declarados. Reproducir desde un equipo limpio con un conjunto reducido. Ensayar caída y recuperación, comparar recuentos y documentar copia/restauración. Un volumen conserva datos tras recrear un contenedor, pero no cubre la pérdida del disco.

### P4. Experimento distribuido opcional

Si queda tiempo, probar réplicas mediante `ReplicatedMergeTree` y ClickHouse Keeper, o sharding mediante tablas locales y `Distributed`. Cada experimento debe responder a un requisito medido. Replicar mejora redundancia y puede introducir retraso entre copias. Distribuir datos aumenta capacidad y exige elegir una clave y coordinar consultas. El diseño actual no ha ejecutado ninguno de esos experimentos.

## Preparación académica

La guía, página 5, pide justificar y citar la ayuda de IA y verificar sus resultados. Este trabajo ha usado Codex para revisión del código, documentación y creación de diapositivas. La portada es una ilustración generada con IA. Las medidas proceden de los informes del proyecto y las decisiones requieren defensa del grupo. El identificador exacto de modelo de cada ejecución anterior no queda registrado en estos archivos, y no se atribuye una versión inventada.

## Fuentes

- [Guía docente](../recursos/guia_bbdda.pdf), páginas 1–5.
- [Componentes](../recursos/01_1_Components.md).
- [Conceptos](../recursos/01_2_Concepts.md).
- [Docker](../recursos/01_3_Docker.md) y [ejemplos](../recursos/01_3_docker/INSTRUCTIONS.md).
- [Aspectos transversales](../recursos/01_4_Cross_cutting_concerns.md).
- [Estructura actual y propuesta](ESTRUCTURA-BD.md), [resultados](RESULTADOS.md) y código del repositorio.
- [Replicación en ClickHouse](https://clickhouse.com/docs/reference/engines/table-engines/mergetree-family/replication).
- [Arquitectura analítica de ClickHouse](https://clickhouse.com/docs/get-started/about/why-clickhouse-is-so-fast).
