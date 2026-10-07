-- Delivery Atlas v1. Base independiente del laboratorio histórico `delivery`.
CREATE DATABASE IF NOT EXISTS delivery_atlas;

-- Una acción lógica. Reintentos pueden producir filas físicas antes de fusionar.
-- La API fija la identidad y el contenido; ORDER BY no impone unicidad.
CREATE TABLE IF NOT EXISTS delivery_atlas.app_events
(
    schema_version UInt16,
    event_id UUID,
    session_id UUID,
    event_time DateTime64(3, 'UTC'),
    event_date Date MATERIALIZED toDate(event_time),
    ingested_at DateTime64(3, 'UTC'),
    event_type LowCardinality(String),
    section LowCardinality(String),
    city_id LowCardinality(String),
    user_id Nullable(String),
    restaurant_id Nullable(String),
    product_id Nullable(String),
    source LowCardinality(String),
    source_kind Enum8('synthetic'=1, 'demo_live'=2, 'public_historical'=3, 'historical_replay'=4),
    source_record_id Nullable(String),
    simulation_run_id Nullable(UUID),
    CONSTRAINT version_v1 CHECK schema_version = 1,
    CONSTRAINT action_valid CHECK event_type IN
        ('search','filter_applied','restaurant_opened','product_opened',
         'product_impression','cart_added','order_submitted')
)
ENGINE = ReplacingMergeTree(ingested_at)
PARTITION BY toYYYYMM(event_date)
ORDER BY (source_kind, event_date, city_id, event_type, event_time, session_id, event_id);

-- Guardar conjuntos de IDs, no sumar filas físicas. Los reintentos no suman dos veces.
CREATE TABLE IF NOT EXISTS delivery_atlas.app_daily_rollup
(
    source_kind Enum8('synthetic'=1, 'demo_live'=2, 'public_historical'=3, 'historical_replay'=4),
    event_date Date,
    city_id LowCardinality(String),
    section LowCardinality(String),
    event_type LowCardinality(String),
    event_ids AggregateFunction(uniqExact, UUID)
)
ENGINE = AggregatingMergeTree
PARTITION BY toYYYYMM(event_date)
ORDER BY (source_kind, event_date, city_id, section, event_type);

CREATE MATERIALIZED VIEW IF NOT EXISTS delivery_atlas.app_daily_rollup_mv
TO delivery_atlas.app_daily_rollup AS
SELECT source_kind, event_date, city_id, section, event_type,
       uniqExactState(event_id) AS event_ids
FROM delivery_atlas.app_events
GROUP BY source_kind, event_date, city_id, section, event_type;

CREATE VIEW IF NOT EXISTS delivery_atlas.app_daily_counts AS
SELECT source_kind, event_date, city_id, section, event_type,
       uniqExactMerge(event_ids) AS events
FROM delivery_atlas.app_daily_rollup
GROUP BY source_kind, event_date, city_id, section, event_type;
