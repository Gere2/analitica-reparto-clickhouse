CREATE DATABASE IF NOT EXISTS delivery;

CREATE TABLE IF NOT EXISTS delivery.eleme_samples
(
    source_id FixedString(64),
    source_file String,
    source_row UInt64,
    sample_day UInt8,
    clicked UInt8,
    user_id String,
    shop_id String,
    item_id String,
    city_id LowCardinality(String),
    district_id LowCardinality(String),
    category_id LowCardinality(String),
    request_hour UInt8,
    weekday LowCardinality(String),
    meal_period LowCardinality(String),
    request_time_raw String,
    raw_features String,
    loaded_at DateTime DEFAULT now(),
    CONSTRAINT click_binary CHECK clicked IN (0, 1),
    CONSTRAINT hour_valid CHECK request_hour < 24,
    CONSTRAINT day_valid CHECK sample_day BETWEEN 1 AND 8
)
ENGINE = MergeTree
PARTITION BY source_id
ORDER BY (sample_day, city_id, request_hour, category_id, shop_id, source_row)
SETTINGS merge_max_block_size = 512,
         max_bytes_to_merge_at_max_space_in_pool = 268435456,
         parts_to_delay_insert = 1000,
         parts_to_throw_insert = 1500;

-- Matching layout allows atomic MOVE PARTITION after a whole file validates.
CREATE TABLE IF NOT EXISTS delivery.eleme_staging AS delivery.eleme_samples;
