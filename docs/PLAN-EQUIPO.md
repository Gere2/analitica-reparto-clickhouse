# Delivery Atlas: plan de trabajo del equipo

Fecha: 7 de octubre de 2026. Equipo: Jere, Anuar y Echenique.

## Qué estamos construyendo

Una plataforma ficticia de comida a domicilio para demostrar cómo ClickHouse recibe y analiza muchos eventos. Una acción en la aplicación produce un registro; la API Python lo valida, lo guarda y permite consultarlo desde un dashboard. No operamos repartos ni cobros reales.

Ya existe un laboratorio con OTTO, REES46, Ele.me y el catálogo Glovo, sus paneles y mediciones. Esas fuentes conservan sus tablas y significados. La aplicación propia tendrá su base `delivery_atlas`, con acciones manuales y simuladas identificadas.

## Reparto acordado para empezar

| Persona | Responsabilidad principal | Entrega comprobable |
|---|---|---|
| **Jere, con Rayo** | ClickHouse, SQL, API de ingesta, generador y pruebas de reintentos | Una petición llega a ClickHouse, repetirla no aumenta el recuento lógico y el entorno arranca con Compose |
| **Anuar** | Miniapp y registro de acciones | Un recorrido ciudad, restaurante, producto, carrito y pedido simulado emite los eventos correctos |
| **Echenique** | Dashboard, comprobación independiente y guía de demo | El dashboard consulta la API, filtra por origen/ciudad/fecha y otra máquina reproduce la ruta pequeña |

## Jere: base e ingesta

1. Implementar `sql/atlas.sql`: eventos, agregados y consultas de lectura.
2. Implementar `atlas/`: contrato, registro duradero de recepción, publicación por lotes y endpoints.
3. Empaquetar la API en `Dockerfile.atlas` y el perfil `atlas` de `compose.yaml`.
4. Crear `scripts/atlas.py` para generar carga reproducible y `scripts/check_atlas.py` para verificar la ruta completa.
5. Guardar mediciones propias de la nueva base. Los benchmarks antiguos no describen su rendimiento.

**Base implementada y comprobada el 7 de octubre.** Ya se validan eventos, se rechazan datos incorrectos, el mismo ID con contenido distinto da conflicto y un reintento mantiene el recuento lógico. Se cargó y verificó un millón de eventos sintéticos y se probó la recuperación de cola tras reiniciar servicios. [Resultados y condiciones](RESULTADOS-ATLAS.md).

Siguientes tareas de Jere: apoyar las dos interfaces, medir retraso y uso de disco, mejorar el generador con abandonos y optimizar el agregado exacto (todavía no supera al detalle en la medición local). Después documentar backup/restauración y valorar un segundo nodo como ampliación.

## Anuar: miniapp

Trabajar en `web/delivery.html`, `web/delivery.js` y `web/delivery.css` (nuevos archivos). Coordinar con Jere el servicio de esos archivos desde la API.

1. Empezar con un catálogo ficticio pequeño y estable, sin login ni pagos.
2. Permitir seleccionar ciudad, buscar, abrir un restaurante y un producto, añadir al carrito y confirmar un pedido simulado.
3. Crear un `session_id` al iniciar la sesión y un `event_id` antes de cada envío. Un reintento reutiliza el mismo evento completo.
4. Enviar a `POST /api/events`. Usar `source=delivery-miniapp` y `source_kind=demo_live`. Son interacciones nuevas sobre un negocio ficticio.
5. Mostrar un fallo de envío sin inventar que el evento se guardó. No registrar impresiones hasta definir cuándo un producto es visible.

Terminado cuando: Echenique hace un recorrido y puede encontrar sus acciones y su sesión en la base, sin doble conteo al reintentar.

## Echenique: dashboard y reproducción

Trabajar en `web/atlas-dashboard.html`, `web/atlas-dashboard.js`, `web/atlas-dashboard.css`, `docs/DEMO-ATLAS.md` y `docs/PRUEBAS-EQUIPO.md` (nuevos archivos).

1. Consultar `GET /api/summary`, `GET /api/recent` y `GET /api/status`.
2. Mostrar eventos por día, ciudad y acción; diferenciar `synthetic` y `demo_live`.
3. Refrescar cada 2 segundos, indicar cuándo se obtuvo la última respuesta y mostrar los errores.
4. Mostrar cola pendiente y eventos publicados. No llamar conversión a una división de pedidos entre clics.
5. Seguir la instalación reducida en su ordenador, ejecutar las pruebas y registrar sistema, versión, comandos y resultados.
6. Preparar una demo de ingesta, consulta y comparación entre eventos y agregado. Dejar CRUD en una tabla de ensayo.

Terminado cuando: el dashboard representa datos de ClickHouse, una acción aparece después de la publicación y la guía permite repetirlo sin los datasets grandes.

## Orden de integración

1. Jere fija el contrato y entrega una muestra, los endpoints y la ruta reducida.
2. Anuar y Echenique trabajan en sus archivos con la API ya disponible.
3. Echenique verifica el recorrido de Anuar y el reintento de Jere.
4. Jere ejecuta una carga medida; los tres revisan sus condiciones y ensayan.

Usar ramas `codex/atlas-base`, `codex/atlas-miniapp` y `codex/atlas-dashboard`. Son nombres sugeridos; no se han creado ni enviado mensajes al equipo. Revisar cambios juntos antes de fusionar. Cada persona conserva sus archivos para evitar pisar el trabajo de otra.

## Acuerdo común

- Histórico, simulación y acciones manuales se identifican por su procedencia.
- Un catálogo no contiene clics. Las muestras de Ele.me no son una sesión completa.
- El identificador del evento permanece igual en los reintentos.
- Un nodo significa una instancia de ClickHouse. Un volumen conserva datos, pero no proporciona una réplica ni un backup.
- No descargar cientos de millones de filas en los otros ordenadores para empezar: primero la ruta reducida.
- Las cifras y garantías se presentan solo después de comprobarlas.
