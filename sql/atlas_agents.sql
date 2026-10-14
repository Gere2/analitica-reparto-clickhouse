-- Backwards-compatible nullable link. Existing rows remain historical/unlinked.
ALTER TABLE delivery_atlas.app_events ADD COLUMN IF NOT EXISTS order_id Nullable(UUID);
ALTER TABLE delivery_atlas.app_events DROP CONSTRAINT IF EXISTS action_valid;
ALTER TABLE delivery_atlas.app_events ADD CONSTRAINT action_valid CHECK event_type IN
 ('search','filter_applied','restaurant_opened','product_opened','product_impression',
  'cart_added','cart_removed','session_abandoned','order_submitted');

CREATE TABLE IF NOT EXISTS delivery_atlas.customer_activity
(
 schema_version UInt16, event_id UUID, simulation_run_id UUID,
 customer_id UUID, session_id UUID, event_time DateTime64(3,'UTC'),
 ingested_at DateTime64(3,'UTC'), customer_label String, objective String,
 budget_minor UInt32, action LowCardinality(String), stage LowCardinality(String),
 reason String, restaurant_id Nullable(String), product_id Nullable(String),
 order_id Nullable(UUID), cart_total_minor UInt32,
 decision_mode LowCardinality(String), model Nullable(String),
 source_kind Enum8('synthetic'=1)
)
ENGINE = ReplacingMergeTree(ingested_at)
PARTITION BY toYYYYMM(event_time)
ORDER BY (simulation_run_id,customer_id,event_time,event_id);

CREATE TABLE IF NOT EXISTS delivery_atlas.customer_latest_state
ENGINE = AggregatingMergeTree ORDER BY (simulation_run_id,customer_id)
AS SELECT simulation_run_id,customer_id,
 argMaxState(tuple(session_id,event_time,customer_label,objective,budget_minor,
  action,stage,reason,restaurant_id,product_id,order_id,cart_total_minor,decision_mode,model),
  tuple(event_time,event_id)) AS state
FROM delivery_atlas.customer_activity WHERE 0
GROUP BY simulation_run_id,customer_id;

CREATE MATERIALIZED VIEW IF NOT EXISTS delivery_atlas.customer_latest_mv
TO delivery_atlas.customer_latest_state AS
SELECT simulation_run_id,customer_id,
 argMaxState(tuple(session_id,event_time,customer_label,objective,budget_minor,
  action,stage,reason,restaurant_id,product_id,order_id,cart_total_minor,decision_mode,model),
  tuple(event_time,event_id)) AS state
FROM delivery_atlas.customer_activity GROUP BY simulation_run_id,customer_id;

CREATE VIEW IF NOT EXISTS delivery_atlas.customer_latest AS
SELECT simulation_run_id,customer_id,s.1 AS session_id,s.2 AS event_time,
 s.3 AS customer_label,s.4 AS objective,s.5 AS budget_minor,s.6 AS action,
 s.7 AS stage,s.8 AS reason,s.9 AS restaurant_id,s.10 AS product_id,
 s.11 AS order_id,s.12 AS cart_total_minor,s.13 AS decision_mode,s.14 AS model
FROM (SELECT simulation_run_id,customer_id,argMaxMerge(state) AS s
 FROM delivery_atlas.customer_latest_state GROUP BY simulation_run_id,customer_id);

CREATE TABLE IF NOT EXISTS delivery_atlas.customer_orders
(
 schema_version UInt16, event_id UUID, simulation_run_id UUID,
 order_id UUID, customer_id UUID, session_id UUID, checkout_event_id UUID,
 event_time DateTime64(3,'UTC'), ingested_at DateTime64(3,'UTC'),
 restaurant_id String, items Array(Tuple(product_id String,quantity UInt16,unit_price_minor UInt32)),
 amount_minor UInt32, currency FixedString(3), decision_mode LowCardinality(String),
 source_kind Enum8('synthetic'=1)
)
ENGINE = ReplacingMergeTree(ingested_at)
PARTITION BY toYYYYMM(event_time)
ORDER BY (simulation_run_id,order_id,event_id);
