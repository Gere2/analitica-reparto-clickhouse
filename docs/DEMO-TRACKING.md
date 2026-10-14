# Demo de seguimiento: ruta principal

La implementación la continúa Rayo con Jere. No requiere descargar históricos públicos en el ordenador de otro compañero.

## Preparar

```bash
docker compose -f compose.yaml --profile atlas up -d --build --wait
python3 -m unittest discover -s tests -v
python3 scripts/check_operations.py
```

Abrir http://127.0.0.1:8001/. Comprobar los dos servicios healthy y que el panel no muestra errores. En un ordenador nuevo el catálogo Glovo público puede estar vacío; habrá doce restaurantes y treinta y seis productos de demo. El histórico masivo se puede enseñar desde el ordenador de Jere y los informes guardados.

## Recorrido de clase

1. **Explicar la etiqueta:** Madrid y flota ficticia. GPS y estados son eventos nuevos del simulador, no un servicio conectado a Uber Eats.
2. **Iniciar 12 repartidores.** Seleccionar uno en la lista. Mostrar ID de pedido, latitud/longitud y hora del evento; esperar a que cambien en una actualización.
3. **Consultar SQL** con `sql/atlas_tracking_consultas.sql`. Mostrar `courier_positions` y `courier_latest_mv`: una conserva histórico, la otra calcula estado reciente.
4. **Mostrar un cambio de estado.** Created, preparing, picked_up, en_route, delivered o cancelled. Los ciclos están escalonados; habrá pedidos en fases distintas. No prometer un estado concreto en una fecha de reloj exacta.
5. **Registrar búsqueda manual.** Pulsar el botón y cambiar Procedencia a Acciones manuales. 202 confirma la cola; el recuento aparece tras publicación y consulta. El agregado de navegación refresca cada diez segundos.
6. **Parar.** Los puntos quedan visibles y envejecen. El histórico no se borra. Iniciar otra vez crea otro run y otra flota.
7. **Mostrar integridad.** Leer `docs/evidencia-tracking.json`: reintento reconocido; dato antiguo no reemplaza uno nuevo; fallo entre INSERTs se recupera. El test es una comprobación realizada, no algo que esté fallando en el momento.
8. **Reflexión:** observar antigüedad y cola. Consultar más a menudo no elimina un atraso de publicación. No hay transacción entre tablas ni réplica del nodo.

## Operaciones SQL del enunciado

El script `python3 scripts/crud_demo.py` ya demuestra inserción, consulta, actualización y borrado en `delivery.demo_events`. Coordinar su ejecución con la generación, y explicar por qué no se modifica un histórico Atlas cuyos agregados incrementales no recalculan automáticamente borrados. Para una demo tranquila, parar la simulación antes del CRUD y reanudarla después.

## Carga y evidencia

- Un millón de eventos de navegación del primer generador: `docs/RESULTADOS-ATLAS.md`.
- 100000 posiciones históricas sintéticas y 5965 estados, verificados: `docs/evidencia-carga-gps.json`.
- Nueve pruebas unitarias y prueba HTTP/SQL de telemetría. El test HTTP usa su propio run; no cambia el run que ve el panel.
- El ritmo configurado es dos segundos, sujeto al coste de recepción/publicación. El panel muestra antigüedad y errores; los datos pueden atrasarse bajo carga. No se ha fijado un SLA.

## Si algo falla

- API no responde: `docker compose -f compose.yaml --profile atlas ps`, luego `docker compose -f compose.yaml --profile atlas logs --tail 40 atlas`.
- Cola aumenta: leer `/api/status`, incluyendo `publisher_phase`, `publisher_phase_seconds`, `last_batch` y `last_publish_seconds`. Diferenciar lectura de cola, INSERT y confirmación en cola.
- Simulación parada por error: el mensaje se muestra en el panel. Resolverlo antes de iniciar otro run; no ocultar el error ni borrarlo con `down -v`.
- Catálogo no cargado: la flota funciona con su catálogo ficticio. No inventar que se cargó Glovo.
- Reiniciar la API conserva la cola y la última ejecución, pero la generación no se reactiva automáticamente.

La cola del servicio usa una conexión SQLite persistente protegida por un lock entre hilos, mantiene `synchronous=FULL` y limita la caché a 32 MiB. Esto evita abrir/cerrar el registro en cada tick y conserva las transacciones. No se comparten escrituras entre varias APIs. Véase la explicación de [WAL y checkpoints](https://sqlite.org/wal.html).
