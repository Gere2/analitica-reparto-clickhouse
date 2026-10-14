# Miniapp comercial de Delivery Atlas

Responsable: Anuar. Fecha: 14/10/2026. Archivos: `web/delivery.html`, `web/delivery.js`, `web/delivery.css`.

Una persona hace un pedido en una app de reparto ficticia de Madrid. Cada acción queda registrada en ClickHouse. El pedido confirmado entra en la misma simulación de reparto que los clientes con IA: se le asigna un repartidor y se sigue por GPS hasta la entrega. Restaurantes, precios, repartidores y posiciones son ficticios. No hay login ni cobro.

## Arrancar

```bash
docker compose -f compose.yaml --profile atlas up -d --build --wait
```

1. Abrir el panel en http://127.0.0.1:8001/. En «Clientes y reparto», elegir un modo de clientes: **Política local de prueba** o **Simulador de tráfico** (no necesitan Ollama), o **IA + tráfico masivo**. Después, pulsar «Iniciar clientes y reparto».
2. Abrir la miniapp en http://127.0.0.1:8001/delivery.html.
3. Buscar, filtrar, abrir un restaurante, añadir platos y pulsar **Confirmar pedido**.

Si no hay ninguna simulación de clientes activa, el checkout responde 409 y no crea nada. La miniapp lo explica y enlaza al panel. La navegación se registra igualmente.

## Qué se registra

Todo lleva `source = delivery-miniapp` y `source_kind = demo_live`: son acciones nuevas que hace una persona en un negocio ficticio.

| Acción en la app | `event_type` | `section` | Campos extra |
|---|---|---|---|
| Buscar | `search` | `search` | — |
| Activar un filtro (desactivarlo no cuenta) | `filter_applied` | `search` | — |
| Abrir restaurante | `restaurant_opened` | `restaurants` | `restaurant_id` |
| Abrir plato | `product_opened` | `menu` | `restaurant_id`, `product_id` |
| Añadir / quitar del carrito | `cart_added` / `cart_removed` | `cart` | `restaurant_id`, `product_id` |
| Vaciar el carrito o cerrar la pestaña con productos | `session_abandoned` | `session` | — |
| Confirmar pedido | `order_submitted` | `checkout` | `restaurant_id`, `order_id` |

- **Identificadores:** `session_id` es nuevo en cada visita y después de cada pedido. `user_id` es un UUID que se guarda en el navegador (`localStorage`); si el navegador lo bloquea, la app sigue funcionando y se genera uno nuevo cada vez.
- **Impresiones:** no se registran (`product_impression`), siguiendo el plan del equipo: falta definir cuándo un producto es visible.
- **Envío de eventos:** cada evento se envía a `POST /api/events` en cuanto ocurre. La columna derecha («Eventos de esta sesión») enseña la respuesta real de la API:
  - 202: en cola.
  - 200: ya estaba registrado.
  - 400/409: no guardado, y se muestra el motivo.
  - Error de red o 503: se reintenta con espera exponencial, hasta 6 intentos.

## Reintentos sin doble conteo

Un evento se construye una sola vez. Al reintentar se reenvía el mismo objeto, con el mismo `event_id` y la misma hora, así que la cola lo reconoce como duplicado y responde 200.

El checkout funciona igual: `order_id`, `checkout_event_id` y la hora se fijan al primer intento. Si se cae la red y se pulsa otra vez, se reenvía el mismo pedido y la API responde 200 sin crear otro. Si cambia la cesta, el pedido es otro.

## Checkout: `POST /api/checkout`

```json
{
  "order_id": "…uuid…", "customer_id": "…uuid…", "session_id": "…uuid…",
  "checkout_event_id": "…uuid…", "event_time": "2026-10-14T15:44:23.120Z",
  "restaurant_id": "fictional-madrid-12",
  "items": [{"product_id": "fictional-madrid-12-product-1", "quantity": 1}]
}
```

El navegador envía solo identificadores y cantidades. **El precio y el importe los calcula la API** con el catálogo de la ejecución: un cliente no puede fijar el precio ni mezclar restaurantes. Límites: de 1 a 10 unidades por plato y 20 por pedido.

| Respuesta | Significado |
|---|---|
| 202 | Pedido aceptado en la cola. Devuelve `run_id`, `order_id` y `amount_minor` |
| 200 | Reintento de un pedido ya aceptado |
| 400 | Cesta o identificadores no válidos para el catálogo |
| 409 `no_customer_run` | No hay simulación de clientes activa; no se ha creado nada |

Una compra genera tres registros, en el mismo commit de la cola:

1. `app_events`: el clic `order_submitted` (`demo_live`), con `order_id`.
2. `customer_orders`: la cesta con precios del catálogo, `decision_mode = 'manual'` y `source_kind = 'demo_live'`. Para guardar ese valor, `sql/atlas_miniapp.sql` añade `demo_live` al Enum. Es un cambio aditivo que no reescribe filas.
3. `order_events`: el estado `created`. Después, el simulador asigna repartidor y publica `preparing` → `picked_up` → `en_route` → `delivered` y las posiciones GPS. Todo ello sigue marcado como `synthetic`.

La pantalla de seguimiento consulta `GET /api/operations?run_id=…` cada 2 s y pinta el estado que lee de ClickHouse, no uno inventado en el navegador. En el panel, el pedido aparece en «Pedidos de esta ejecución» como «Miniapp (manual)».

## Comprobar en ClickHouse

```sql
-- Acciones de la miniapp (recuento lógico)
SELECT event_type, uniqExact(event_id) FROM delivery_atlas.app_events
WHERE source = 'delivery-miniapp' GROUP BY event_type;

-- Clic de compra → cesta → estados del mismo pedido
SELECT o.order_id, o.amount_minor, o.items, e.event_type
FROM delivery_atlas.customer_orders AS o FINAL
JOIN delivery_atlas.app_events AS e FINAL ON e.event_id = o.checkout_event_id
WHERE o.decision_mode = 'manual';

SELECT status, courier_id, event_time FROM delivery_atlas.order_events FINAL
WHERE order_id = '<order_id>' ORDER BY event_time;
```

## Verificación del 14/10

Tests: `python3 -m unittest discover -s tests -v`. Los 26 pasan, incluidos los 8 de `tests/test_miniapp.py`.

Prueba de punta a punta en Chromium, con ClickHouse 25.8 y la API Atlas, usando la simulación con la política local y 8 repartidores:
- **Recorrido:** búsqueda, 2 filtros, restaurante, 3 platos abiertos, 3 añadidos, 1 quitado y checkout. Son 12 eventos `demo_live` en `app_events` y coinciden con el agregado `app_daily_counts`.
- **Compra:** el clic `order_submitted` enlaza con la compra (`checkout_event_id`) y con su `order_id`. El importe de 22,67 € lo calculó la API.
- **Entrega:** el pedido pasó por 6 estados hasta `delivered` en unos 97 s, con 49 posiciones GPS de su repartidor.
- **Pantalla:** el seguimiento mostró los cinco pasos leídos de ClickHouse.

Se repitió sobre el commit de tráfico concurrente de Gere2, en modo «Simulador de tráfico» con 200 clientes y 80 repartidores. El pedido manual se entregó entre 239 pedidos simulados y conservó su procedencia (`manual` / `demo_live` frente a `traffic` / `synthetic`). En la ejecución se aceptaron unos 14.000 eventos, sin duplicados ni errores de publicación.

## Límites

- **Catálogo:** es el de demo (12 restaurantes y 36 platos). Sin el catálogo de Glovo cargado, todos los restaurantes comparten los mismos tres nombres de plato, así que la búsqueda por plato encuentra casi todos.
- **Ciudades:** solo Madrid. El selector de ciudad se rellena con las ciudades del catálogo.
- **Seguimiento:** es esquemático (sin red viaria), como el resto del tracking simulado.
