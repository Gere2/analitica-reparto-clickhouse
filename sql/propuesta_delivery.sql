-- DISEÑO PROPUESTO. No aplicado al servidor ni conectado a la API actual.
-- Base separada para que un eventual ensayo no cambie las tablas históricas.
-- La API debe resolver reintentos duplicados ANTES de publicar eventos y agregados.
CREATE DATABASE IF NOT EXISTS delivery_proposal;

CREATE TABLE IF NOT EXISTS delivery_proposal.app_events
(
    schema_version UInt16,
    event_id UUID,
    event_time DateTime64(3, 'UTC'),
    event_date Date MATERIALIZED toDate(event_time),
    ingested_at DateTime64(3, 'UTC') DEFAULT now64(3),
    event_type LowCardinality(String),
    section LowCardinality(String),
    session_id UUID,
    user_id Nullable(String),
    city_id LowCardinality(String),
    restaurant_id Nullable(String),
    product_id Nullable(String),
    source LowCardinality(String),
    source_kind Enum8('synthetic' = 1, 'demo_live' = 2,
                     'public_historical' = 3, 'historical_replay' = 4),
    source_record_id Nullable(String),
    simulation_run_id Nullable(UUID),
    CONSTRAINT version_positive CHECK schema_version > 0,
    CONSTRAINT action_valid CHECK event_type IN
        ('search', 'filter_applied', 'restaurant_opened', 'product_opened',
         'product_impression', 'cart_added', 'order_submitted')
)
ENGINE = MergeTree
PARTITION BY toYYYYMM(event_date)
ORDER BY (source_kind, event_date, city_id, event_type, event_time, session_id);

-- Solo recuentos por día, ciudad, sección, tipo y procedencia.
-- Las sesiones únicas y los embudos requieren otras consultas/modelos.
CREATE TABLE IF NOT EXISTS delivery_proposal.app_daily_rollup
(
    source_kind Enum8('synthetic' = 1, 'demo_live' = 2,
                     'public_historical' = 3, 'historical_replay' = 4),
    event_date Date,
    city_id LowCardinality(String),
    section LowCardinality(String),
    event_type LowCardinality(String),
    events UInt64
)
ENGINE = SummingMergeTree(events)
PARTITION BY toYYYYMM(event_date)
ORDER BY (source_kind, event_date, city_id, section, event_type);

-- Activar únicamente después de probar el protocolo de reintentos del publicador.
-- La vista procesa cada bloque nuevo. No elimina duplicados por event_id.
CREATE MATERIALIZED VIEW IF NOT EXISTS delivery_proposal.app_daily_rollup_mv
TO delivery_proposal.app_daily_rollup AS
SELECT source_kind, event_date, city_id, section, event_type, count() AS events
FROM delivery_proposal.app_events
GROUP BY source_kind, event_date, city_id, section, event_type;
