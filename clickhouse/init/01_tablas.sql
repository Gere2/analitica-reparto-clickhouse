-- Se ejecuta una sola vez, al arrancar ClickHouse con el volumen vacío.
-- Para repetirlo: docker compose down -v && docker compose up -d

CREATE DATABASE IF NOT EXISTS reparto;

-- ─────────────────────────────────────────────────────────────
-- 1. Tabla de hechos: un clic = una fila. Solo se añaden filas.
-- ─────────────────────────────────────────────────────────────
-- ReplacingMergeTree + event_id en la clave: si la app reintenta un INSERT
-- que ya había llegado, la fila duplicada se descarta al fusionar
-- (reintentos idempotentes). event_id y ts los genera el CLIENTE, así el
-- reintento lleva exactamente la misma clave.
CREATE TABLE IF NOT EXISTS reparto.eventos_app
(
    event_id       UUID,
    ts             DateTime64(3, 'Europe/Madrid'),
    session_id     UUID,
    user_id        UInt64,
    origen         Enum8('app_real' = 1, 'simulado' = 2),
    seccion        Enum8('inicio' = 1, 'busqueda' = 2, 'filtros' = 3, 'restaurante' = 4,
                         'menu' = 5, 'carrito' = 6, 'pago' = 7, 'pedido' = 8),
    accion         LowCardinality(String),        -- ver, clic, anadir, quitar, pagar...
    restaurante_id UInt32,
    plato_id       UInt32,
    promo_id       UInt32,
    busqueda       String,
    filtros        Array(LowCardinality(String)),
    importe        Decimal(8, 2),
    dispositivo    LowCardinality(String),
    distrito       LowCardinality(String)
)
ENGINE = ReplacingMergeTree
PARTITION BY toYYYYMM(ts)                         -- organiza DENTRO del servidor (no es sharding)
ORDER BY (origen, toDate(ts), session_id, ts, event_id);
-- Sharding (explicado, no montado): clave cityHash64(session_id), porque
-- windowFunnel agrupa por sesión y cada fragmento calcularía sus embudos solo.

-- ─────────────────────────────────────────────────────────────
-- 2. Agregados para el panel: se rellenan solos con cada INSERT
-- ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS reparto.embudo_hora
(
    hora        DateTime('Europe/Madrid'),
    origen      Enum8('app_real' = 1, 'simulado' = 2),
    seccion     Enum8('inicio' = 1, 'busqueda' = 2, 'filtros' = 3, 'restaurante' = 4,
                      'menu' = 5, 'carrito' = 6, 'pago' = 7, 'pedido' = 8),
    dispositivo LowCardinality(String),
    distrito    LowCardinality(String),
    sesiones    AggregateFunction(uniq, UUID)
)
ENGINE = AggregatingMergeTree
ORDER BY (hora, origen, seccion, dispositivo, distrito);

-- Ojo: solo ve lo insertado DESPUÉS de crearse. Por eso va en el init, antes de cargar datos.
-- uniq ignora duplicados, así que un reintento no infla el número de sesiones.
CREATE MATERIALIZED VIEW IF NOT EXISTS reparto.mv_embudo_hora TO reparto.embudo_hora AS
SELECT
    toStartOfHour(ts)      AS hora,
    origen,
    seccion,
    dispositivo,
    distrito,
    uniqState(session_id)  AS sesiones
FROM reparto.eventos_app
GROUP BY hora, origen, seccion, dispositivo, distrito;

-- ─────────────────────────────────────────────────────────────
-- 3. Dimensión: restaurantes del censo de locales de Madrid
-- ─────────────────────────────────────────────────────────────
-- Corregir un restaurante = insertar una versión mayor.
CREATE TABLE IF NOT EXISTS reparto.restaurantes
(
    restaurante_id UInt32,
    nombre         String,
    distrito       LowCardinality(String),
    tipo           LowCardinality(String),
    lat            Float64,
    lon            Float64,
    version        UInt32
)
ENGINE = ReplacingMergeTree(version)
ORDER BY restaurante_id;

-- 4. mtlift_promos (5,5 M filas reales de Meituan): se crea en
--    scripts/cargar_mtlift.sql cuando hayamos visto las columnas reales del CSV.
