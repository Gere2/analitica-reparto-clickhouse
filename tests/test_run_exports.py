"""An interrupted or malformed export must never become a saved run."""
import csv
import gzip
import hashlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import export_run as exporter
import runs_report


class RunExportTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.target = Path(self.tmp.name) / '2026-11-13_run'
        self.run = str(uuid4())
        self.stats = {'rows': 2, 'first': '2026-11-13 10:00:00', 'last': '2026-11-13 10:00:01'}

    def write_csv(self, run, table, path):
        with gzip.open(path, 'wt', encoding='utf-8', newline='') as stream:
            writer = csv.writer(stream)
            writer.writerow(['simulation_run_id', 'event_time', 'value'])
            writer.writerow([run, self.stats['first'], 'quoted, value\nsecond line'])
            writer.writerow([run, self.stats['last'], 'other'])
        payload = path.read_bytes()
        return len(payload), hashlib.sha256(payload).hexdigest()

    def metadata(self, run, sql):
        if 'AS customers' in sql: return [{'customers': 2, 'ai_customers': 0, 'ai_decisions': 0}]
        if 'AS couriers' in sql: return [{'couriers': 2}]
        return []

    def create(self, stream=None, stats=None):
        with patch.object(exporter, 'stream_table', side_effect=stream or self.write_csv), \
             patch.object(exporter, 'table_stats', side_effect=stats or (lambda *a: dict(self.stats))), \
             patch.object(exporter, 'rows', side_effect=self.metadata):
            return exporter.export(self.run, self.target)

    def test_verified_archive_is_reused_but_corrupted_archive_is_not_accepted(self):
        summary = self.create()
        self.assertEqual(len(summary['tables']), 5)
        with patch.object(exporter, 'stream_table', side_effect=AssertionError('must not overwrite')):
            self.assertEqual(exporter.export(self.run, self.target), summary)
        (self.target / 'app_events.csv.gz').write_bytes(b'not a gzip archive')
        with self.assertRaises((ValueError, OSError)):
            exporter.export(self.run, self.target)
        self.assertFalse(self.target.with_name(self.target.name + '.export-lock').exists())

    def test_failed_attempt_is_never_promoted_and_retry_uses_a_new_staging_directory(self):
        with self.assertRaises(OSError): self.create(stream=lambda *a: (_ for _ in ()).throw(OSError('connection lost')))
        self.assertFalse(self.target.exists())
        first = list(self.target.parent.glob('*.partial-*'))
        self.assertEqual(len(first), 1)
        self.create()
        self.assertTrue(self.target.is_dir())
        self.assertTrue(first[0].is_dir())
        self.assertEqual(exporter.inspect_csv(self.target / 'app_events.csv.gz', self.run), 2)

    def test_changed_source_count_blocks_promotion(self):
        checks = iter([self.stats, dict(self.stats, rows=3)])
        with self.assertRaises(ValueError): self.create(stats=lambda *a: next(checks))
        self.assertFalse(self.target.exists())

    def test_wrong_run_and_truncated_gzip_are_rejected(self):
        path = self.target.parent / 'example.gz'
        self.write_csv(self.run, 'app_events', path)
        with self.assertRaises(ValueError): exporter.inspect_csv(path, str(uuid4()))
        path.write_bytes(path.read_bytes()[:-6])
        with self.assertRaises((EOFError, OSError)): exporter.inspect_csv(path, self.run)

    def test_streaming_never_requests_the_entire_large_http_body(self):
        path = self.target.parent / 'transport.gz'
        class Response(io.BytesIO):
            headers = {'Content-Encoding': 'gzip'}
            def read(self, size=-1):
                if not 0 < size <= 1024 * 1024: raise AssertionError('unbounded body read')
                return super().read(size)
        payload = gzip.compress(b'a,b\n1,2\n')
        with patch.object(exporter, 'urlopen', return_value=Response(payload)):
            count, digest = exporter.stream_table(self.run, 'app_events', path)
        self.assertEqual((count, digest), (len(payload), hashlib.sha256(payload).hexdigest()))

    def test_report_ignores_a_partial_directory_even_if_a_manifest_was_written(self):
        summary = self.create()
        partial = self.target.parent / 'unfinished.partial-1234'
        partial.mkdir(); (partial / 'summary.json').write_text(json.dumps(summary))
        report = self.target.parent / 'report.md'
        with patch.object(runs_report, 'RUNS', self.target.parent), patch.object(runs_report, 'TARGET', report), \
             patch.object(runs_report, 'ROOT', self.target.parent), patch('builtins.print'):
            runs_report.main()
        self.assertIn('**1 runs,', report.read_text())
        self.assertIn('Event span', report.read_text())
        self.assertNotIn('unfinished.partial', report.read_text())


if __name__ == '__main__': unittest.main()
