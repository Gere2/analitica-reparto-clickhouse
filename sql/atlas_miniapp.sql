-- Miniapp comercial (web/delivery.*). Migración aditiva: no borra ni reescribe filas.
-- Una compra manual se guarda en customer_orders con source_kind = 'demo_live'.
-- Su preparación, repartidor y GPS siguen siendo sintéticos (order_events y
-- courier_positions conservan 'synthetic'). Añadir un valor al final de un Enum8
-- es un cambio solo de metadatos en ClickHouse.
ALTER TABLE delivery_atlas.customer_orders
    MODIFY COLUMN source_kind Enum8('synthetic'=1, 'demo_live'=2);
