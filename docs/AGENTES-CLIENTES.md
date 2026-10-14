# Clientes con IA, compras y reparto conectado

Ampliación del 14/10/2026. La IA elige acciones sobre un catálogo ficticio; Python valida y ejecuta esas acciones, crea pedidos y genera su GPS. Son compras simuladas, sin pagos. Las acciones representan clics lógicos en nuestra aplicación, no automatización de una web comercial externa.

## Arranque

```bash
docker compose -f compose.yaml --profile atlas --profile ai up -d --build --wait
docker compose -f compose.yaml --profile ai exec -T ollama ollama pull qwen3:0.6b
```

Abrir http://127.0.0.1:8001/. Elegir **IA local · Ollama**, tres clientes y los repartidores deseados; pulsar **Iniciar clientes y reparto**. La primera decisión puede tardar mientras el modelo se carga. El GPS tiene un hilo independiente.

El perfil `ai` incorpora Ollama y un volumen persistente para los modelos. No publica un puerto del modelo en el host. Ollama se limita a 2 CPU y 2 GiB; la inferencia usa dos hilos y un contexto de 2048 tokens. [Qwen3:0.6b](https://ollama.com/library/qwen3:0.6b) tiene una descarga publicada de unos 523 MB; la imagen de Ollama se descarga aparte. Se usan recursos del ordenador, sin API de pago.

La imagen Ollama está fijada por digest (versión comprobada `0.40.4`); la evidencia registra su digest y el del modelo. No garantiza resultados idénticos entre versiones. El proveedor recibe solo objetivos ficticios, carrito y opciones del catálogo local. [API de chat](https://docs.ollama.com/api/chat) y [salidas estructuradas](https://docs.ollama.com/capabilities/structured-outputs).

## Modos diferenciados

- **IA local (ollama):** Qwen propone `action`, índice `choice` y una explicación breve. La aplicación valida la decisión; no se ejecuta código ni SQL producido por el modelo. No hay sustitución automática por una política si la IA falla.
- **Política local (policy):** baseline reproducible, explícitamente etiquetado sin modelo de IA. Útil para pruebas o un ordenador sin Ollama.
- **Solo flota anterior (legacy):** conserva el escenario anterior y los generadores históricos. Sus sesiones y pedidos independientes no se reinterpretan como compras enlazadas.

La API `POST /api/simulation/start` admite `mode=customers`, `agent_mode=ollama|policy|hybrid|traffic`, `customers` (1-24 para IA/política; 1-500 para modos masivos), `fleet` (1-150), `interval` (1-10 s) y `seed`. Los clientes tienen una sesión, presupuesto y objetivo. Pueden buscar, comparar, abrir productos, añadir/quitar del carrito, comprar y abandonar. Un pedido espera a que haya un repartidor disponible.

## Identidad del recorrido

```text
customer_id + session_id
   -> app_events (clics lógicos)
   -> checkout_event_id + order_id + cesta
   -> customer_orders (compra inmutable)
   -> order_events (estados del mismo pedido)
   -> courier_positions (GPS de ese mismo order_id)
```

Un checkout válido suma `cantidad * precio_unitario` de los productos del carrito. Solo admite productos del negocio seleccionado y una cesta dentro del presupuesto. Los precios son ficticios y se congelan en la compra. No se inventa otro pedido separado después del clic.

`customer_activity` guarda decisiones, explicación breve, fase y procedencia (`ollama`, `policy`, `system`). `customer_latest_state` y su materializada guardan `argMaxState`; `customer_latest` finaliza el último estado. `customer_orders` enlaza la sesión con el clic de checkout y conserva las líneas de cesta.

Los eventos de navegación mantienen el contrato v1 y añaden `order_id` opcional. Los reintentos de clientes antiguos sin ese campo conservan su payload normalizado: no se añade automáticamente un nuevo `null` al digest anterior. La migración añade acciones de quitar del carrito y abandono, sin borrar filas históricas.

Un pedido creado sin repartidor usa el UUID cero hasta la asignación. Un repartidor disponible también tiene UUID cero como pedido; el panel lo presenta como disponible. Los estados creados avanzan a preparación, recogida, reparto y entrega en unos 95 s desde la asignación; su plazo ficticio es creación + 120 s. No son tiempos de reparto reales. Al terminar, el repartidor parte desde la posición final hacia la próxima recogida.

## Aceptación, concurrencia y errores

`CustomerRuntime` prepara una copia del estado de negocio y envía todos los registros de una acción en una única transacción de la cola SQLite. Solo cambia el estado en memoria si la cola los acepta. Así un error/capacidad llena no crea una compra fantasma en memoria.

El publicador hace INSERTs por tabla. No hay una transacción entre ClickHouse y SQLite ni entre esos INSERTs; las relaciones pueden aparecer en momentos ligeramente distintos. Las tablas de detalle usan reemplazo/FINAL y las vistas de último estado usan `argMax`. Se conservan las protecciones frente a reintentos y eventos tardíos.

La decisión se valida contra la revisión vigente del cliente: una respuesta antigua no compra sobre otra sesión. Parar impide aceptar respuestas del modelo que todavía estén en vuelo; la inferencia ya enviada puede terminar después. Reiniciar no reconstruye los carritos ni reanuda automáticamente la ejecución anterior; los hechos aceptados y pendientes sí permanecen en la cola/base.

Máximo 14 pasos por sesión, cinco unidades en el carrito, `max(100, clientes*2)` pedidos activos y 120 llamadas de modelo por run. Tras tres decisiones fallidas consecutivas se detienen nuevas decisiones y el panel lo indica; los pedidos ya creados siguen avanzando. El límite de llamadas también pausa las decisiones. Parar e iniciar crea otra ejecución. Son límites operativos de una demo local.

## Qué consultar en el dashboard

- Clientes: presupuesto, acción, explicación, producto/negocio, carrito y pedido.
- **Ver reparto:** selecciona el repartidor que actualmente lleva ese pedido. Cuando ya no lo lleva, no atribuye su nueva posición a una entrega pasada.
- Detalle del mapa: cliente, sesión y clic de compra del pedido seleccionado.
- Pedidos: cliente/sesión y estado de entrega. La lista sigue limitada a 200.
- Actividad: últimas 30 acciones, diferenciando decisiones de modelo, política y sistema.
- Contadores de clientes: solo el run seleccionado, calculados desde el registro lógico de actividad. El panel de navegación inferior conserva todo el histórico Atlas, identificado aparte.

Todas las filas de clientes, compras y rutas son sintéticas y se leen desde ClickHouse. El frontend no mueve una flota por separado ni rellena cifras con datos aleatorios. Los controles y la cola reflejan estado del proceso; los contadores analíticos reflejan publicaciones en la base.

## Archivos

| Parte | Código |
|---|---|
| Decisiones y proveedor local | `atlas/customer_agent.py` |
| Carrito, checkout, asignación y entrega | `atlas/commerce.py` |
| Hilos y aceptación antes de cambiar estado | `atlas/customer_runtime.py` |
| Arranque compatible | `atlas/simulation.py`, `atlas/server.py` |
| SQL aditivo y estados agregados | `sql/atlas_agents.sql` |
| Lecturas y enlace del panel | `atlas/clickhouse.py`, `web/atlas-dashboard.*` |
| Pruebas de compra/cola/entrega | `tests/test_commerce.py` |

Las guías de 17 y cuatro páginas describen la etapa previa. Esta ampliación incorpora la relación checkout-pedido que figuraba pendiente; la miniapp comercial manual y su checkout siguen siendo una futura interfaz sobre este backend.

## Compartición

La lectura usa las rutas públicas existentes: `/api/operations` incorpora clientes, decisiones y compras; `/api/simulation` expone modo/modelo y contadores seguros. Se conserva el acceso de solo lectura y el token del gateway. Hay que reconstruir el gateway y publicar la web nueva para ver la ampliación desde Vercel; actualizar la URL temporal si el túnel ha cambiado. No se expone la API de Ollama ni sus controles.

## Verificación

```bash
python3 -m unittest discover -s tests -v
```

Las pruebas comprueban el vínculo real entre clic, cesta y pedido; rechazo de checkout vacío o repetido; presupuesto/opciones inventadas; rollback por cola llena; compatibilidad de reintentos antiguos; identidad del GPS y continuidad del repartidor entre pedidos. La prueba con IA real debe registrar run/modelo, una compra, la relación en ClickHouse y su entrega; la política de prueba no sustituye esa evidencia.

### Prueba comprobada en el equipo

`docs/evidencia-clientes.json` conserva una compra decidida por el modelo local, su cesta comprobada contra el importe, el clic/sesión enlazados y las posiciones del mismo pedido hasta la entrega. Ejecutar `python3 scripts/check_customer_agent.py --mode ollama` para repetirlo (sin otra ejecución activa), o añadir `--existing` para comprobar la actual. La carga inicial del modelo y las decisiones tardan varios segundos; no se producen millones de llamadas de IA. El volumen masivo sigue aportándolo el laboratorio histórico/generadores, mientras la IA alimenta el recorrido conectado en directo.

Se observaron rechazos transitorios de lecturas por el límite global de memoria de ClickHouse durante fusiones en segundo plano. El cliente reintenta solo lecturas con el código 241, hasta dos veces; un fallo persistente se muestra en el panel. Las escrituras siguen usando la cola y su publicador. Esta demo no implica un SLA de latencia ni mide conducta comercial real.

### Publicación y revisión visual

- Código desplegado: `36ea395`, proyecto Vercel `delivery-atlas-demo`, equipo `contrerasgeremi-gmailcoms-projects`, entorno producción, estado Ready.
- Enlace: https://delivery-atlas-demo.vercel.app/. El portátil, Ollama, Atlas, ClickHouse y el túnel deben permanecer encendidos. Los controles están en http://127.0.0.1:8001/.
- Comprobado: tres clientes del run local visibles a través del proxy; HTML sin controles de inicio; POST público rechazado con 405; sin errores de JavaScript registrados durante la visita.
- Revisado escritorio y móvil de 390 px: sin desbordamiento horizontal de la página. Las tablas conservan desplazamiento horizontal dentro de su contenedor.
- Captura de la versión publicada: `docs/capturas/clientes-ia-publico.png`; el clic «Ver reparto» mostró el mismo cliente, sesión, checkout y pedido en el detalle del mapa.
- Las capturas de escritorio/móvil anteriores registran la revisión previa a convertir los importes enviados al modelo a euros. La captura pública corresponde a la versión final. Las explicaciones de un modelo pequeño pueden ser imprecisas; la validación y el importe de la compra dependen del catálogo y del carrito, no de ese texto.

## Tráfico concurrente — ampliación del 14/10

El modo **IA + tráfico masivo (hybrid)** combina los tres primeros clientes con Ollama y el resto con un simulador de tráfico explícitamente etiquetado. Escenario activado: **200 clientes y 80 repartidores**. El modo **Simulador de tráfico (traffic)** no usa un modelo. IA y política anteriores conservan su funcionamiento y se limitan a 24 clientes; los modos masivos admiten hasta 500 clientes y 150 repartidores.

El simulador elige productos dentro del presupuesto, permite ampliar o modificar carritos y también abandonar. Uno de cada cinco perfiles de tráfico explora y abandona siempre: vuelve a visitar la aplicación y mantiene clics continuos mientras otros esperan la entrega. Los demás también pueden abandonar una visita con una probabilidad configurada del 12 %. Son parámetros de demo, no tasas observadas. Pausas de 1,2–3,8 s por acción y arranques escalonados de hasta ocho segundos distribuyen la actividad. Un hilo procesa por lotes todos los clientes elegibles cada medio segundo: una sola copia del estado y transacción de cola por lote, sin cientos de hilos ni llamadas de IA. Un segundo hilo decide para los tres clientes de IA; el hilo GPS continúa independiente. La semilla reproduce elecciones y pausas, pero la ejecución real depende del reloj y de la inferencia.

Todas las compras siguen usando el mismo checkout y la misma cesta, asignación y GPS. El límite de pedidos activos pasa a `max(100, clientes*2)` para permitir compras que esperan un repartidor. Llegar a 120 llamadas o a tres errores de Ollama pausa solo la IA; el tráfico continúa. Si la cola está llena, el lote de tráfico se descarta en memoria y se reintenta posteriormente; un fallo del hilo GPS todavía detiene la ejecución completa.

El dashboard muestra doce clientes en el resumen (los tres de IA y actividad reciente), con un botón para verlos todos. Los contadores incluyen el conjunto completo. Los marcadores de flotas grandes son más pequeños y solo el seleccionado lleva número; todos se pueden elegir en la lista. Sus coordenadas proceden de ClickHouse. Las posiciones iniciales se distribuyen alrededor de las zonas del catálogo para evitar que ochenta repartidores comiencen en doce puntos superpuestos.

```bash
# Tras arrancar los perfiles atlas y ai y descargar el modelo:
curl -X POST http://127.0.0.1:8001/api/simulation/start \
  -H 'Content-Type: application/json' \
  -d '{"mode":"customers","agent_mode":"hybrid","customers":200,"fleet":80,"interval":2,"seed":42}'
python3 scripts/check_traffic.py
```

Parar la ejecución anterior con el control local antes de iniciar otra. `docs/evidencia-trafico.json` recoge clientes, pico de repartidores asignados simultáneamente, movimientos observados, decisiones publicadas, entregas y cola. No representa usuarios de Uber Eats ni un benchmark de máxima capacidad.

El listado de 200 pedidos prioriza los activos y asignados. El servidor resuelve sus enlaces de compra por order_id, incluso si su checkout ya está fuera de las últimas 200 compras, para conservar cliente y sesión en el mapa. Los contadores de pedidos siguen incluyendo todo el run.

### Reloj y compras concurrentes

La carga detectó una carrera: el hilo GPS capturaba `now` antes de entrar en el bloqueo del estado. Una compra podía confirmarse durante esa espera y aparecer creada después del timestamp del GPS. La validación rechazaba la asignación y detenía la ingesta. El reloj se captura ahora dentro del bloqueo y después de copiar el estado. La nueva prueba retiene el GPS mientras confirma un checkout: falla con la implementación anterior y pasa con la corregida. Las 20 pruebas pasan. No se relajan las restricciones temporales del pedido.

Las cifras de `evidencia-trafico.json` son acumuladas por run; su ventana mide únicamente la observación de movimiento. `evidencia-enlaces-trafico.json` registra, en una ejecución anterior, tres enlaces resueltos fuera de las últimas 200 compras. El intervalo GPS solicitado sigue siendo dos segundos y el panel muestra el retraso efectivo.
