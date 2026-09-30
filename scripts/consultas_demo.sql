-- Consultas de la demo, en el orden en que se presentan.
-- Abrir un cliente:  docker compose exec clickhouse clickhouse client --user admin --password
-- (pide la contraseña; así no queda en el historial)

-- 1. Volumen real de Meituan (cuando esté cargado, ver docs/DATOS.md)
-- SELECT count() FROM reparto.mtlift_promos;

-- 2. Cuántos eventos tenemos, separando reales y simulados
SELECT origen, count() AS eventos, uniq(session_id) AS sesiones
FROM reparto.eventos_app
GROUP BY origen;

-- 3. Embudo por sesión: hasta qué paso llega cada una (ventana de 30 min)
SELECT nivel, count() AS sesiones
FROM
(
    SELECT
        session_id,
        windowFunnel(1800)(toDateTime(ts),
            seccion = 'busqueda', seccion = 'restaurante',
            seccion = 'carrito',  seccion = 'pago', seccion = 'pedido') AS nivel
    FROM reparto.eventos_app
    WHERE origen = 'simulado'          -- cambiar a 'app_real' para nuestros clics
    GROUP BY session_id
)
GROUP BY nivel
ORDER BY nivel;

-- 4. Qué búsquedas terminan en pedido
SELECT
    busqueda,
    count() AS sesiones_que_buscan,
    countIf(pidio) AS acaban_en_pedido,
    round(100 * acaban_en_pedido / sesiones_que_buscan, 1) AS conversion_pct
FROM
(
    SELECT session_id,
           anyIf(busqueda, seccion = 'busqueda') AS busqueda,
           max(seccion = 'pedido') AS pidio
    FROM reparto.eventos_app
    GROUP BY session_id
    HAVING busqueda != ''
)
GROUP BY busqueda
ORDER BY conversion_pct DESC;

-- 5. Panel rápido: sesiones por sección y hora, desde los agregados de la vista materializada
SELECT hora, seccion, uniqMerge(sesiones) AS sesiones
FROM reparto.embudo_hora
WHERE hora >= now() - INTERVAL 1 DAY
GROUP BY hora, seccion
ORDER BY hora, seccion;

-- 6. CRUD sobre un evento de prueba
INSERT INTO reparto.eventos_app (event_id, ts, session_id, origen, seccion, accion, importe)
VALUES ('00000000-0000-0000-0000-000000000001', now64(3), generateUUIDv4(), 'app_real', 'carrito', 'anadir', 9.90);

SELECT * FROM reparto.eventos_app WHERE event_id = '00000000-0000-0000-0000-000000000001';

-- Corregir: es una MUTACIÓN asíncrona (reescribe partes enteras), no un UPDATE de fila.
-- No se pueden modificar columnas de la clave (origen, ts, session_id, event_id).
ALTER TABLE reparto.eventos_app UPDATE importe = 12.50
WHERE event_id = '00000000-0000-0000-0000-000000000001';

-- Borrar: borrado ligero (marca la fila; se elimina físicamente al fusionar)
DELETE FROM reparto.eventos_app WHERE event_id = '00000000-0000-0000-0000-000000000001';

-- 7. Rendimiento: cuánto tardaron las últimas consultas (observabilidad)
SELECT event_time, query_duration_ms, read_rows, substring(query, 1, 80) AS consulta
FROM system.query_log
WHERE type = 'QueryFinish' AND query ILIKE '%eventos_app%'
ORDER BY event_time DESC
LIMIT 10;
