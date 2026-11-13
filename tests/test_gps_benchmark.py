"""Boundary, correctness and transport checks for the standalone GPS runner."""
import gzip
import json
import sys
import tempfile
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

SCRIPTS=Path(__file__).resolve().parents[1]/'scripts'
sys.path.insert(0,str(SCRIPTS))
import gps_benchmark as gps
import gps_benchmark_lab as lab
import gps_benchmark_report as summary


def positions():
    return [{'courier_id':'ffffffff-ffff-4fff-8fff-000000000001','state':[40.4,-3.7,1,5,str(uuid4()),'2026-10-31 15:00:00.000','2026-10-31 15:00:00.001']},
            {'courier_id':'00000000-0000-4000-8000-000000000002','state':[40.5,-3.6,2,5,str(uuid4()),'2026-10-31 15:00:00.000','2026-10-31 15:00:00.001']}]


class FakeClient:
    def __init__(self, rows, error=None):
        self.rows,self.error=rows,error
        self.calls=0;self.active=0;self.peak=0;self.lock=threading.Lock()

    def query(self, sql, params=None, **kwargs):
        with self.lock:
            self.calls+=1;self.active+=1;self.peak=max(self.peak,self.active)
        try:
            time.sleep(.003)
            if self.error:
                raise self.error
            return {'data':self.rows,'statistics':{'elapsed':.001,'rows_read':100},'wall_ms':3}
        finally:
            with self.lock:self.active-=1


class RunnerTests(unittest.TestCase):
    def test_production_gateway_and_credential_urls_are_rejected(self):
        for url in ('http://127.0.0.1:8124/','https://demo.vercel.app/',
                    'http://localhost:18124/','http://user:secret@127.0.0.1:18124/',
                    'http://127.0.0.1:18124/?readonly=0','http://127.0.0.1:18124/other'):
            with self.subTest(url=url),self.assertRaises(ValueError):gps.Client(url)

    def test_duplicate_couriers_and_changed_positions_fail_but_uuid_order_is_normalized(self):
        rows=positions()
        self.assertEqual(gps.canonical(rows,2),gps.canonical(rows[::-1],2))
        with self.assertRaises(gps.BenchmarkError):gps.canonical([rows[0],rows[0]],2)
        changed=json.loads(json.dumps(rows));changed[0]['state'][0]+=1
        self.assertNotEqual(gps.canonical(rows,2),gps.canonical(changed,2))

    def test_fixed_concurrency_is_bounded_and_every_request_is_accounted(self):
        rows=positions();client=FakeClient(rows)
        result=gps.measure_phase(client,'SELECT 1',{},design='history',concurrency=4,requests=24,
            expected_digest=gps.canonical(rows,2),expected_couriers=2,deadline=time.monotonic()+3,prefix='unit',slo_ms=1000)
        self.assertEqual(client.calls,24);self.assertEqual(client.peak,4)
        self.assertEqual(result['summary']['slo_status'],'pass')
        self.assertEqual(len({s['query_id'] for s in result['samples']}),24)

    def test_memory_error_stops_new_work_and_is_not_retried_or_called_a_latency_pass(self):
        client=FakeClient(positions(),gps.QueryError('Code: 241. Memory limit exceeded'))
        result=gps.measure_phase(client,'SELECT 1',{},design='history',concurrency=2,requests=30,
            expected_digest='unused',expected_couriers=2,deadline=time.monotonic()+2,prefix='unit',slo_ms=1000)
        self.assertLessEqual(client.calls,2)
        self.assertEqual(result['summary']['slo_status'],'incomplete')
        self.assertEqual(result['summary']['reason'],'query_error')
        self.assertTrue(all(s['error_code']==241 for s in result['samples']))

    def test_changed_answer_and_time_budget_are_not_capacity_boundaries(self):
        rows=positions()
        result=gps.measure_phase(FakeClient(rows),'SELECT 1',{},design='prepared',concurrency=1,requests=5,
            expected_digest='different',expected_couriers=2,deadline=time.monotonic()+2,prefix='unit',slo_ms=1000)
        self.assertEqual(result['summary']['reason'],'correctness')
        expired=gps.measure_phase(FakeClient(rows),'SELECT 1',{},design='history',concurrency=1,requests=5,
            expected_digest=gps.canonical(rows,2),expected_couriers=2,deadline=time.monotonic()-1,prefix='unit',slo_ms=1000)
        self.assertEqual(expired['summary']['attempted'],0)
        self.assertEqual(expired['summary']['reason'],'time_budget')

    def test_failed_requests_are_separate_from_success_only_percentiles(self):
        result=gps.summarize([{'ok':True,'wall_ms':10},{'ok':False,'wall_ms':9000}],2,1,1000,'complete')
        self.assertEqual(result['p95_client_ms'],10)
        self.assertEqual(result['errors'],1)
        self.assertEqual(result['slo_status'],'fail')

    def test_frozen_corpus_changes_and_disk_reserve_abort(self):
        args=gps.parse_args(['--run-id',str(uuid4()),'--expected-rows','10','--expected-couriers','2','--label','test'])
        original={'corpus':{'rows':'10','couriers':'2','fingerprint':'a'},'disks':[{'free_space':10*gps.GIB}]}
        gps.validate_snapshot(original,None,args)
        changed={**original,'corpus':{**original['corpus'],'fingerprint':'b'}}
        with self.assertRaises(gps.BenchmarkError):gps.validate_snapshot(changed,original,args)
        with self.assertRaises(gps.BenchmarkError):gps.validate_snapshot({**original,'disks':[{'free_space':1}]},None,args)

    def test_missing_query_logs_remain_missing_not_zero_memory(self):
        report={'phases':[{'design':'history','concurrency':1,'repetition':1,
            'summary':gps.summarize([{'ok':True,'wall_ms':10}],1,1,1000,'complete'),
            'samples':[{'query_id':'one','ok':True,'wall_ms':10}]}]}
        gps.attach_logs(report,[])
        self.assertFalse(report['query_log_coverage']['complete'])
        self.assertIsNone(summary.phase_rows(report)[0]['peak_query_memory_mib'])

    def test_wrong_marker_blocks_even_a_read_benchmark(self):
        client=type('Wrong',(),{'query':lambda *args,**kw:{'data':[{'identity':'other'}]}})()
        with self.assertRaises(gps.BenchmarkError):gps.marker(client)

    def test_smoke_is_labelled_and_invalid_budgets_rejected(self):
        base=['--run-id',str(uuid4()),'--expected-rows','12','--label','test']
        args=gps.parse_args(base+['--smoke'])
        self.assertEqual((args.concurrency,args.requests,args.repetitions),([1],3,1))
        with self.assertRaises(SystemExit),patch('sys.stderr'):
            gps.parse_args(base+['--concurrency','8','--requests','2'])


class TransportTests(unittest.TestCase):
    def test_http_errors_and_redirects_do_not_retry_or_leak_credentials(self):
        state={'mode':'error','requests':0,'sink':0}
        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                state['requests']+=1
                self.rfile.read(int(self.headers.get('Content-Length','0')))
                if state['mode']=='redirect':
                    self.send_response(302);self.send_header('Location',f'http://127.0.0.1:{self.server.server_port}/sink');self.end_headers()
                else:
                    self.send_response(500);self.end_headers();self.wfile.write(b'Code: 241. Memory limit exceeded')
            def do_GET(self):
                state['sink']+=1;self.send_response(200);self.end_headers()
            def log_message(self,*args):pass
        server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        try:
            client=gps.Client()
            # The test-only URL substitution never exists in the CLI.
            client.url=f'http://127.0.0.1:{server.server_port}/'
            with self.assertRaises(gps.QueryError) as error:client.query('SELECT 1')
            self.assertEqual(error.exception.code,241);self.assertEqual(state['requests'],1)
            state['mode']='redirect'
            with self.assertRaises(gps.QueryError):client.query('SELECT 1')
            self.assertEqual(state['requests'],2);self.assertEqual(state['sink'],0)
        finally:
            server.shutdown();server.server_close();thread.join(2)


class LoaderTests(unittest.TestCase):
    def test_import_blocks_stay_bounded_under_the_existing_memory_budget(self):
        import io
        from types import SimpleNamespace
        from urllib.parse import parse_qs, urlsplit
        from unittest.mock import Mock
        opener=Mock();opener.open.return_value=io.BytesIO(b'')
        with patch.object(lab,'build_opener',return_value=opener):
            lab.insert(SimpleNamespace(user='gps_lab_admin',password='gps-lab-admin-only'),b'fixture','JSONEachRow')
        request=opener.open.call_args.args[0]
        settings=parse_qs(urlsplit(request.full_url).query)
        self.assertEqual(settings['max_insert_block_size'],['262144'])
        self.assertEqual(settings['min_insert_block_size_rows'],['262144'])
        self.assertEqual(settings['input_format_parallel_parsing'],['0'])
        self.assertEqual(settings['max_memory_usage'],['536870912'])

    def test_csv_parser_counts_records_with_embedded_newlines_and_rejects_wrong_run_before_insert(self):
        import csv
        run=str(uuid4());rows=lab.fixture_rows(run)
        rows[0]['source']='label\nwith newline'
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'positions.csv.gz'
            with gzip.open(path,'wt',encoding='utf8',newline='') as f:
                writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
            actual=lab.inspect_csv(path,run,12)
            self.assertEqual((actual['rows'],actual['couriers']),(12,3))
            with self.assertRaises(ValueError):lab.inspect_csv(path,str(uuid4()),12)
            with self.assertRaises(ValueError):lab.inspect_csv(path,run,11)

    def test_existing_run_is_not_reinserted(self):
        with patch.object(lab,'marker'),patch.object(lab,'count_run',return_value=12),patch.object(lab,'insert') as insert:
            with self.assertRaises(ValueError):lab.load(object(),str(uuid4()))
            insert.assert_not_called()


class EndToEndControlTests(unittest.TestCase):
    def test_smoke_artifacts_join_query_ids_and_do_not_claim_capacity(self):
        rows=positions()
        class ProtocolClient:
            deadline=None
            def __init__(self):self.logs=[]
            def query(self,sql,params=None,**kwargs):
                if sql==gps.QUERIES['history'] or sql==gps.QUERIES['prepared']:
                    if kwargs.get('query_id'):
                        self.logs.append(dict(query_id=kwargs['query_id'],type='QueryFinish',query_duration_ms=1,
                            read_rows=100 if sql==gps.QUERIES['history'] else 2,read_bytes=1000,
                            memory_usage=4096,exception_code=0,user_cpu_us=500,system_cpu_us=20))
                    return {'data':rows,'wall_ms':2,'statistics':{'elapsed':.001}}
                if 'gps_comparison_lab.identity' in sql:return {'data':[{'identity':gps.LAB_MARKER}]}
                if 'system.query_log' in sql:return {'data':self.logs}
                if 'SELECT version()' in sql:return {'data':[{'version':'protocol-test-fixture'}]}
                return {'data':[]}
        state={'corpus':{'rows':'10','couriers':'2','fingerprint':'fixed'},'disks':[{'free_space':10*gps.GIB}]}
        with tempfile.TemporaryDirectory() as tmp:
            args=gps.parse_args(['--run-id',str(uuid4()),'--expected-rows','10','--expected-couriers','2',
                '--label','Protocol fixture, not capacity','--smoke','--output',str(Path(tmp)/'output')])
            with patch.object(gps,'snapshot',return_value=state),patch('builtins.print'):
                report,folder=gps.run(args,ProtocolClient())
            self.assertTrue(report['valid_comparison']);self.assertEqual(report['status'],'complete')
            self.assertEqual(report['query_log_coverage']['terminal_records_found'],6)
            self.assertEqual(len(list(folder.glob('*.csv'))),2)
            target=summary.render(folder/'report.json')
            self.assertIn('not a capacity measurement',target.read_text())
            self.assertIn('history',(folder/'samples.csv').read_text())

    def test_stopped_report_cannot_advertise_a_boundary(self):
        report={'status':'stopped','valid_comparison':False,'purpose':'boundary_confirmation'}
        self.assertIn('No capacity conclusion',summary.conclusion(report,[]))


if __name__=='__main__':
    unittest.main()
