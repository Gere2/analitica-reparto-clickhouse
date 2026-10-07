-- Leer mientras el simulador está activo. Ejecutar en clickhouse-client.
SHOW CREATE TABLE delivery_atlas.courier_positions;
SHOW CREATE TABLE delivery_atlas.courier_latest_mv;

-- Elegir una ejecución; no combinar flotas de runs anteriores.
SELECT simulation_run_id, max(event_time) AS last_event, uniqExact(courier_id) AS couriers
FROM delivery_atlas.courier_positions
GROUP BY simulation_run_id ORDER BY last_event DESC;

-- Última posición calculada desde estados incrementales.
SELECT simulation_run_id, courier_id, order_id, latitude, longitude, event_time,
       dateDiff('second',event_time,now()) AS age_seconds
FROM delivery_atlas.courier_latest
ORDER BY event_time DESC LIMIT 12;

-- Por defecto agrupa por ejecución para no mezclar cantidades de flotas distintas.
SELECT simulation_run_id,status,count() AS orders,
       sum(amount_minor)/100 AS fictional_amount_eur
FROM delivery_atlas.order_latest
GROUP BY simulation_run_id,status ORDER BY simulation_run_id,status;

-- Comparar filas físicas e IDs lógicos: puede haber reintentos.
SELECT simulation_run_id,count() AS physical_rows,uniqExact(event_id) AS logical_positions
FROM delivery_atlas.courier_positions
GROUP BY simulation_run_id;

-- Enriquecimiento ficticio del catálogo con procedencia por campo.
SELECT product_id,product_name,price_minor,price_kind,name_kind,source_table,source_row
FROM delivery_atlas.demo_products FINAL LIMIT 8;
