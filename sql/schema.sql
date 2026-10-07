CREATE DATABASE IF NOT EXISTS delivery;

CREATE TABLE IF NOT EXISTS delivery.restaurants (
    restaurant_id UInt32,
    category String,
    area_id UInt32,
    score Nullable(Float32)
) ENGINE = MergeTree ORDER BY restaurant_id;

CREATE TABLE IF NOT EXISTS delivery.foods (
    food_id UInt32,
    price Nullable(Float32),
    category String
) ENGINE = MergeTree ORDER BY food_id;

CREATE TABLE IF NOT EXISTS delivery.orders (
    order_id UInt32,
    user_id UInt32,
    restaurant_id UInt32,
    area_id UInt32,
    price_band String,
    ordered_at DateTime('Asia/Shanghai'),
    period_code String,
    order_date Date
) ENGINE = MergeTree ORDER BY (order_date, order_id);

CREATE TABLE IF NOT EXISTS delivery.order_items (
    order_date Date,
    order_id UInt32,
    food_id UInt32
) ENGINE = MergeTree ORDER BY (order_date, order_id);

CREATE TABLE IF NOT EXISTS delivery.clicks (
    order_date Date,
    order_id UInt32,
    position UInt16,
    restaurant_id UInt32
) ENGINE = MergeTree ORDER BY (order_date, order_id, position);

CREATE TABLE IF NOT EXISTS delivery.click_summary (
    order_date Date,
    order_id UInt32,
    click_count UInt16,
    distinct_restaurants UInt16,
    last_clicked_restaurant_id UInt32
) ENGINE = MergeTree ORDER BY (order_date, order_id);

CREATE TABLE IF NOT EXISTS delivery.daily_clicks (
    order_date Date,
    restaurant_id UInt32,
    clicks UInt64
) ENGINE = SummingMergeTree ORDER BY (order_date, restaurant_id);

CREATE MATERIALIZED VIEW IF NOT EXISTS delivery.daily_clicks_mv
TO delivery.daily_clicks AS
SELECT order_date, restaurant_id, count() AS clicks
FROM delivery.clicks
GROUP BY order_date, restaurant_id;

CREATE TABLE IF NOT EXISTS delivery.demo_events (
    event_id UInt64,
    recorded_at DateTime DEFAULT now(),
    section String,
    action String
) ENGINE = MergeTree ORDER BY event_id;

-- Official Glovo FooDI-ML catalog. One row represents one published product sample.
CREATE TABLE IF NOT EXISTS delivery.glovo_products (
    source_row UInt32,
    country_code LowCardinality(String),
    city_code LowCardinality(String),
    store_name String,
    product_name String,
    collection_section String,
    product_description String,
    has_description UInt8,
    aux_store UInt8,
    hier UInt8
) ENGINE = MergeTree ORDER BY (country_code, city_code, store_name, source_row);

-- OTTO: real anonymized click, cart and order events. Archive and replay are separate.
CREATE TABLE IF NOT EXISTS delivery.otto_archive (
    session_id UInt32,
    article_id UInt32,
    event_time DateTime64(3, 'UTC'),
    event_type LowCardinality(String),
    event_position UInt16
) ENGINE = MergeTree
PARTITION BY toYYYYMM(event_time)
ORDER BY (event_time, session_id, event_position);

CREATE TABLE IF NOT EXISTS delivery.otto_replay (
    session_id UInt32,
    article_id UInt32,
    event_time DateTime64(3, 'UTC'),
    event_type LowCardinality(String),
    event_position UInt16,
    ingested_at DateTime64(3, 'UTC') DEFAULT now64(3)
) ENGINE = MergeTree
PARTITION BY toYYYYMMDD(ingested_at)
ORDER BY (ingested_at, session_id, event_position);

CREATE TABLE IF NOT EXISTS delivery.live_clicks (
    click_id UUID DEFAULT generateUUIDv4(),
    clicked_at DateTime64(3, 'UTC') DEFAULT now64(3),
    section LowCardinality(String),
    action LowCardinality(String)
) ENGINE = MergeTree
ORDER BY (clicked_at, click_id);

-- REES46 marketplace: real views, cart actions and purchases from seven months.
-- This is a separate source and its views are never counted as OTTO clicks.
CREATE TABLE IF NOT EXISTS delivery.rees46_events (
    event_time DateTime('UTC'),
    event_date Date MATERIALIZED toDate(event_time),
    event_type LowCardinality(String),
    product_id UInt64,
    category_id UInt64,
    category_code String,
    brand LowCardinality(String),
    price Decimal(12, 2),
    user_id UInt64,
    user_session String
) ENGINE = MergeTree
PARTITION BY toYYYYMM(event_date)
ORDER BY (event_date, event_type, category_id, product_id);

-- Clearly labelled stress-test rows derived from OTTO, not new observed users.
CREATE TABLE IF NOT EXISTS delivery.otto_scale_benchmark (
    scenario UInt8,
    session_id UInt64,
    article_id UInt32,
    event_time DateTime64(3, 'UTC'),
    event_type LowCardinality(String)
) ENGINE = MergeTree
PARTITION BY toYYYYMM(event_time)
ORDER BY (event_time, session_id, scenario);

CREATE TABLE IF NOT EXISTS delivery.otto_daily_rollup (
    event_date Date,
    event_type LowCardinality(String),
    events UInt64
) ENGINE = SummingMergeTree
ORDER BY (event_date, event_type);

CREATE MATERIALIZED VIEW IF NOT EXISTS delivery.otto_daily_rollup_mv
TO delivery.otto_daily_rollup AS
SELECT toDate(event_time) AS event_date, event_type, count() AS events
FROM delivery.otto_archive
GROUP BY event_date, event_type;
