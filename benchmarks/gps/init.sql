-- Public credentials for this loopback-only disposable lab, never the demo.
CREATE DATABASE IF NOT EXISTS gps_comparison_lab;
CREATE TABLE gps_comparison_lab.identity (identity String) ENGINE=TinyLog;
INSERT INTO gps_comparison_lab.identity VALUES ('atlas-gps-comparison-v1');
CREATE USER gps_reader IDENTIFIED BY 'gps-lab-reader-only';
GRANT SELECT ON delivery_atlas.* TO gps_reader;
GRANT SELECT ON gps_comparison_lab.identity TO gps_reader;
GRANT SELECT ON system.tables TO gps_reader;
GRANT SELECT ON system.parts TO gps_reader;
GRANT SELECT ON system.metrics TO gps_reader;
GRANT SELECT ON system.merges TO gps_reader;
GRANT SELECT ON system.disks TO gps_reader;
GRANT SELECT ON system.settings TO gps_reader;
GRANT SELECT ON system.query_log TO gps_reader;
ALTER USER gps_reader SETTINGS readonly=2;
