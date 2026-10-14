-- Catálogo de demo. Ubicación, importe e identidad comercial son ficticios.
CREATE TABLE IF NOT EXISTS delivery_atlas.demo_restaurants
(
    restaurant_id String,
    name String,
    city_id LowCardinality(String),
    latitude Float64,
    longitude Float64,
    location_kind Enum8('synthetic'=1),
    source_kind Enum8('synthetic'=1),
    version UInt64
)
ENGINE = ReplacingMergeTree(version) ORDER BY restaurant_id;

CREATE TABLE IF NOT EXISTS delivery_atlas.demo_products
(
    product_id String,
    restaurant_id String,
    product_name String,
    price_minor UInt32,
    currency FixedString(3),
    price_kind Enum8('synthetic'=1),
    name_kind Enum8('synthetic'=1,'public_historical'=2),
    source_table Nullable(String),
    source_row Nullable(UInt32),
    version UInt64
)
ENGINE = ReplacingMergeTree(version) ORDER BY product_id;

-- Telemetría ficticia separada de fuentes públicas y del contrato de clics v1.
CREATE TABLE IF NOT EXISTS delivery_atlas.courier_positions
(
    schema_version UInt16,
    event_id UUID,
    simulation_run_id UUID,
    event_time DateTime64(3, 'UTC'),
    ingested_at DateTime64(3, 'UTC'),
    city_id LowCardinality(String),
    courier_id UUID,
    order_id UUID,
    latitude Float64,
    longitude Float64,
    speed_kmh Float32,
    accuracy_m Float32,
    source LowCardinality(String),
    source_kind Enum8('synthetic'=1),
    CONSTRAINT gps_lat CHECK latitude BETWEEN -90 AND 90,
    CONSTRAINT gps_lon CHECK longitude BETWEEN -180 AND 180
)
ENGINE = ReplacingMergeTree(ingested_at)
PARTITION BY toYYYYMM(event_time)
ORDER BY (simulation_run_id, city_id, courier_id, event_time, event_id);

CREATE TABLE IF NOT EXISTS delivery_atlas.courier_latest_state
ENGINE = AggregatingMergeTree
ORDER BY (simulation_run_id, city_id, courier_id)
AS SELECT simulation_run_id, city_id, courier_id,
    argMaxState(tuple(latitude, longitude, speed_kmh, accuracy_m, order_id,
        event_time, ingested_at), tuple(event_time, event_id)) AS state
FROM delivery_atlas.courier_positions WHERE 0
GROUP BY simulation_run_id, city_id, courier_id;

CREATE MATERIALIZED VIEW IF NOT EXISTS delivery_atlas.courier_latest_mv
TO delivery_atlas.courier_latest_state AS
SELECT simulation_run_id, city_id, courier_id,
    argMaxState(tuple(latitude, longitude, speed_kmh, accuracy_m, order_id,
        event_time, ingested_at), tuple(event_time, event_id)) AS state
FROM delivery_atlas.courier_positions
GROUP BY simulation_run_id, city_id, courier_id;

CREATE VIEW IF NOT EXISTS delivery_atlas.courier_latest AS
SELECT simulation_run_id, city_id, courier_id, s.1 AS latitude, s.2 AS longitude,
    s.3 AS speed_kmh, s.4 AS accuracy_m, s.5 AS order_id,
    s.6 AS event_time, s.7 AS ingested_at
FROM (SELECT simulation_run_id, city_id, courier_id, argMaxMerge(state) AS s
      FROM delivery_atlas.courier_latest_state GROUP BY simulation_run_id, city_id, courier_id);

-- Cada fila es una foto completa e inmutable de un pedido en un estado.
CREATE TABLE IF NOT EXISTS delivery_atlas.order_events
(
    schema_version UInt16,
    event_id UUID,
    simulation_run_id UUID,
    event_time DateTime64(3, 'UTC'),
    ingested_at DateTime64(3, 'UTC'),
    city_id LowCardinality(String),
    order_id UUID,
    courier_id UUID,
    restaurant_id String,
    status LowCardinality(String),
    amount_minor UInt32,
    currency FixedString(3),
    pickup_lat Float64,
    pickup_lon Float64,
    dropoff_lat Float64,
    dropoff_lon Float64,
    order_created_at DateTime64(3, 'UTC'),
    promised_delivery_at DateTime64(3, 'UTC'),
    source LowCardinality(String),
    source_kind Enum8('synthetic'=1),
    CONSTRAINT status_valid CHECK status IN ('created','preparing','picked_up','en_route','delivered','cancelled'),
    CONSTRAINT currency_eur CHECK currency = 'EUR'
)
ENGINE = ReplacingMergeTree(ingested_at)
PARTITION BY toYYYYMM(event_time)
ORDER BY (simulation_run_id, city_id, order_id, event_time, event_id);

CREATE TABLE IF NOT EXISTS delivery_atlas.order_latest_state
ENGINE = AggregatingMergeTree
ORDER BY (simulation_run_id, city_id, order_id)
AS SELECT simulation_run_id, city_id, order_id,
    argMaxState(tuple(status, courier_id, restaurant_id, amount_minor, currency,
        pickup_lat, pickup_lon, dropoff_lat, dropoff_lon, order_created_at,
        promised_delivery_at, event_time, ingested_at), tuple(event_time,event_id)) AS state
FROM delivery_atlas.order_events WHERE 0
GROUP BY simulation_run_id, city_id, order_id;

CREATE MATERIALIZED VIEW IF NOT EXISTS delivery_atlas.order_latest_mv
TO delivery_atlas.order_latest_state AS
SELECT simulation_run_id, city_id, order_id,
    argMaxState(tuple(status, courier_id, restaurant_id, amount_minor, currency,
        pickup_lat, pickup_lon, dropoff_lat, dropoff_lon, order_created_at,
        promised_delivery_at, event_time, ingested_at), tuple(event_time,event_id)) AS state
FROM delivery_atlas.order_events
GROUP BY simulation_run_id, city_id, order_id;

CREATE VIEW IF NOT EXISTS delivery_atlas.order_latest AS
SELECT simulation_run_id, city_id, order_id, s.1 AS status, s.2 AS courier_id,
    s.3 AS restaurant_id, s.4 AS amount_minor, s.5 AS currency,
    s.6 AS pickup_lat, s.7 AS pickup_lon, s.8 AS dropoff_lat, s.9 AS dropoff_lon,
    s.10 AS order_created_at, s.11 AS promised_delivery_at, s.12 AS event_time, s.13 AS ingested_at
FROM (SELECT simulation_run_id, city_id, order_id, argMaxMerge(state) AS s
      FROM delivery_atlas.order_latest_state GROUP BY simulation_run_id, city_id, order_id);
