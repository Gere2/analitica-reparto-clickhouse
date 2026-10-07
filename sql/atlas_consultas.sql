-- Recuento lógico independiente de las fusiones.
SELECT count() AS eventos FROM delivery_atlas.app_events FINAL;

-- Agregado para el dashboard. Cada clave puede tener varias filas físicas.
SELECT event_date, city_id, event_type, source_kind, sum(events) AS events
FROM delivery_atlas.app_daily_counts
GROUP BY event_date, city_id, event_type, source_kind
ORDER BY event_date, city_id, event_type, source_kind;

-- Inspección de estructura física, sin confundirla con eventos lógicos.
SELECT table, sum(rows) AS filas_fisicas,
       formatReadableSize(sum(bytes_on_disk)) AS disco
FROM system.parts WHERE database = 'delivery_atlas' AND active
GROUP BY table ORDER BY table;

-- Un único nodo no proporciona réplicas ni reparto horizontal.
SELECT version(), hostName();
