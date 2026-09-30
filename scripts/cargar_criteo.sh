#!/bin/bash
# Carga datos/criteo-uplift-v2.1.csv en reparto.criteo_uplift (unos minutos).
# Uso, desde la raíz del proyecto:  bash scripts/cargar_criteo.sh
set -euo pipefail
set -a; . ./.env; set +a
CH() { docker compose exec -T clickhouse clickhouse client \
         --user "$CLICKHOUSE_ADMIN_USER" --password "$CLICKHOUSE_ADMIN_PASSWORD" "$@"; }

# Por si el volumen se creó antes de existir 03_criteo.sql
CH --multiquery < clickhouse/init/03_criteo.sql
# </dev/null: con -q y sin terminal, el cliente se queda esperando datos por stdin
CH -q "TRUNCATE TABLE reparto.criteo_uplift" </dev/null
# FROM INFILE lo lee el cliente dentro del contenedor, que ve ./datos como /datos
CH -q "INSERT INTO reparto.criteo_uplift FROM INFILE '/datos/criteo-uplift-v2.1.csv' FORMAT CSVWithNames" </dev/null
CH -q "SELECT count() AS filas FROM reparto.criteo_uplift" </dev/null
