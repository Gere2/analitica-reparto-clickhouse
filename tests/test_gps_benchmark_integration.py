"""Opt-in SQL validation against the dedicated marked GPS benchmark lab."""
import csv
import gzip
import os
import sys
import tempfile
import unittest
from pathlib import Path
from uuid import uuid4
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import gps_benchmark as gps
import gps_benchmark_lab as lab
import export_run as exporter


@unittest.skipUnless(os.environ.get('GPS_BENCHMARK_TEST_URL'), 'Requires the separate GPS benchmark lab')
class GPSIntegrationTests(unittest.TestCase):
    def test_real_gzip_run_export_counts_all_tables_and_verifies_an_existing_archive(self):
        gps.lab_url(os.environ['GPS_BENCHMARK_TEST_URL'])
        run=str(uuid4());lab.load(lab.admin_client(),run)
        with tempfile.TemporaryDirectory() as temporary, patch.object(exporter,'CLICKHOUSE',gps.LAB_URL.rstrip('/')):
            target=Path(temporary)/'verified-run'
            first=exporter.export(run,target)
            self.assertEqual(first['tables']['courier_positions']['rows'],12)
            self.assertEqual(set(first['tables']),set(exporter.TABLES))
            self.assertEqual(exporter.export(run,target),first)

    def test_gzip_csv_stream_import_preserves_quoted_records_and_refuses_a_second_load(self):
        gps.lab_url(os.environ['GPS_BENCHMARK_TEST_URL'])
        run_id=str(uuid4())
        rows=lab.fixture_rows(run_id)
        rows[0]['source']='Quoted, multiline\nvalidation fixture'
        with tempfile.TemporaryDirectory() as temporary:
            source=Path(temporary)/'courier_positions.csv.gz'
            with gzip.open(source,'wt',encoding='utf-8',newline='') as stream:
                writer=csv.DictWriter(stream,fieldnames=list(rows[0]))
                writer.writeheader();writer.writerows(rows)
            loaded=lab.load(lab.admin_client(),run_id,source,12)
            self.assertEqual((loaded['rows'],loaded['couriers']),(12,3))
            with self.assertRaises(ValueError):lab.load(lab.admin_client(),run_id,source,12)
            client=gps.Client();params={'param_run':run_id,'param_city':'madrid'}
            self.assertEqual(gps.canonical(client.query(gps.QUERIES['history'],params)['data'],3),
                             gps.canonical(client.query(gps.QUERIES['prepared'],params)['data'],3))

    def test_out_of_order_history_and_materialized_state_match_through_real_http(self):
        gps.lab_url(os.environ['GPS_BENCHMARK_TEST_URL'])
        run_id=str(uuid4())
        loaded=lab.load(lab.admin_client(),run_id)
        self.assertEqual((loaded['rows'],loaded['couriers']),(12,3))
        client=gps.Client()
        gps.marker(client)
        params={'param_run':run_id,'param_city':'madrid'}
        a=client.query(gps.QUERIES['history'],params)['data']
        b=client.query(gps.QUERIES['prepared'],params)['data']
        self.assertEqual(gps.canonical(a,3),gps.canonical(b,3))
        self.assertTrue(all(abs(row['state'][0]-40.403)<.000001 for row in a))
        with tempfile.TemporaryDirectory() as temporary:
            output=Path(temporary)/'report'
            args=gps.parse_args(['--run-id',run_id,'--expected-rows','12','--expected-couriers','3',
                '--label','Integration fixture, not capacity','--smoke','--output',str(output)])
            report,_=gps.run(args,client)
            self.assertEqual(report['status'],'complete',report.get('stop_reason'))
            self.assertTrue(report['valid_comparison'])
            self.assertTrue(report['query_log_coverage']['complete'])
            self.assertEqual(report['purpose'],'smoke')
            self.assertEqual(len(report['phases']),2)


if __name__=='__main__':
    unittest.main()
