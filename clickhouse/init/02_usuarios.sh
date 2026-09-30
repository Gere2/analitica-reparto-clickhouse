#!/bin/bash
# Usuarios con permisos mínimos (autorización):
#   app_writer     → solo INSERT en eventos_app (y leer restaurantes para pintarlos)
#   grafana_reader → solo SELECT (readonly = 2: puede ajustar settings, no escribir)
# Las contraseñas llegan por variables de entorno desde .env: nada queda en git.
set -e

clickhouse client --user "$CLICKHOUSE_USER" --password "$CLICKHOUSE_PASSWORD" --multiquery <<EOSQL
CREATE USER IF NOT EXISTS app_writer IDENTIFIED WITH sha256_password BY '${APP_WRITER_PASSWORD}';
GRANT INSERT ON reparto.eventos_app TO app_writer;
GRANT SELECT ON reparto.restaurantes TO app_writer;

CREATE USER IF NOT EXISTS grafana_reader IDENTIFIED WITH sha256_password BY '${GRAFANA_READER_PASSWORD}'
    SETTINGS readonly = 2;
GRANT SELECT ON reparto.* TO grafana_reader;
GRANT SELECT ON system.query_log TO grafana_reader;   -- para mostrar la latencia de las consultas
EOSQL
