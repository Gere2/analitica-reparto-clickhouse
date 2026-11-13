"""Read-only, bounded GPS history vs prepared-state comparison (standard library).

Only the marked loopback lab on port 18124 is accepted. Never imports atlas,
starts a simulation, modifies ClickHouse, or calls the demo/gateway.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import platform
import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlparse
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener
from uuid import UUID, uuid4

ROOT = Path(__file__).resolve().parents[1]
LAB_URL = 'http://127.0.0.1:18124/'
LAB_MARKER = 'atlas-gps-comparison-v1'
GIB = 1024 ** 3
FILTER = 'simulation_run_id={run:UUID} AND city_id={city:String}'
QUERIES = {
    'history': '''SELECT courier_id,
        argMax(tuple(latitude,longitude,speed_kmh,accuracy_m,order_id,event_time,ingested_at),
               tuple(event_time,event_id)) AS state
        FROM delivery_atlas.courier_positions WHERE ''' + FILTER + '''
        GROUP BY courier_id ORDER BY courier_id''',
    'prepared': '''SELECT courier_id,
        tuple(latitude,longitude,speed_kmh,accuracy_m,order_id,event_time,ingested_at) AS state
        FROM delivery_atlas.courier_latest WHERE ''' + FILTER + ' ORDER BY courier_id',
}
CORPUS_SQL = '''SELECT count() AS rows,uniqExact(courier_id) AS couriers,
    groupBitXor(cityHash64(toString(tuple(event_id,event_time,ingested_at,latitude,
        longitude,speed_kmh,accuracy_m,order_id)))) AS fingerprint,
    toString(min(event_time)) AS first_event,toString(max(event_time)) AS last_event
    FROM delivery_atlas.courier_positions WHERE ''' + FILTER


class BenchmarkError(Exception):
    pass


class QueryError(BenchmarkError):
    def __init__(self, message, code=None):
        super().__init__(message)
        found = re.search(r'Code:\s*(\d+)', message)
        self.code = code if code is not None else int(found[1]) if found else None


class BudgetExpired(BenchmarkError):
    pass


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def lab_url(value):
    p = urlparse(value)
    if (p.scheme != 'http' or p.hostname != '127.0.0.1' or p.port != 18124
            or p.path not in ('', '/') or p.query or p.fragment or p.username or p.password):
        raise ValueError('Only the separate lab at http://127.0.0.1:18124/ is supported.')
    return LAB_URL


class Client:
    def __init__(self, url=LAB_URL, *, user=None, password=None, query_seconds=8,
                 memory_bytes=268435456, threads=2):
        self.url = lab_url(url)
        self.user = user or os.environ.get('GPS_BENCHMARK_USER', 'gps_reader')
        self.password = password if password is not None else os.environ.get(
            'GPS_BENCHMARK_PASSWORD', 'gps-lab-reader-only')
        self.query_seconds, self.memory_bytes, self.threads = query_seconds, memory_bytes, threads
        self.deadline = None

    def query(self, sql, params=None, *, query_id=None, remaining=None):
        if not sql.lstrip().startswith('SELECT ') or ';' in sql:
            raise ValueError('The benchmark client only accepts single SELECT statements.')
        seconds = self.query_seconds
        if self.deadline is not None:
            global_remaining = self.deadline-time.monotonic()
            remaining = min(remaining,global_remaining) if remaining is not None else global_remaining
        if remaining is not None:
            if remaining <= .05:
                raise BudgetExpired('No query budget remains.')
            seconds = min(seconds, remaining)
        settings = {'readonly': 2, 'default_format': 'JSON', 'wait_end_of_query': 1,
                    'max_execution_time': seconds, 'max_memory_usage': self.memory_bytes,
                    'max_threads': self.threads, 'use_query_cache': 0,
                    'log_queries': 1, 'log_queries_probability': 1,
                    'max_result_rows': 20000, 'result_overflow_mode': 'throw',
                    'query_id': query_id or 'gps_control_' + uuid4().hex, **(params or {})}
        request = Request(self.url + '?' + urlencode(settings), data=sql.encode(),
                          headers={'X-ClickHouse-User': self.user, 'X-ClickHouse-Key': self.password})
        started = time.monotonic()
        try:
            # Fresh opener per worker request; no environment proxy or redirect with credentials.
            with build_opener(ProxyHandler({}), NoRedirect()).open(request, timeout=seconds + 2) as response:
                payload = response.read(16 * 1024 * 1024 + 1)
            if len(payload) > 16 * 1024 * 1024:
                raise QueryError('Response exceeded the 16 MiB client bound.')
            try:
                body = json.loads(payload)
            except (ValueError, UnicodeError) as exc:
                # ClickHouse can append an exception after HTTP headers were sent.
                raise QueryError(payload.decode(errors='replace')[:2000]) from exc
            if not isinstance(body, dict) or not isinstance(body.get('data'), list):
                raise QueryError('Missing JSON data array.')
            return {'query_id': settings['query_id'], 'wall_ms': (time.monotonic()-started)*1000,
                    'data': body['data'], 'statistics': body.get('statistics', {})}
        except HTTPError as exc:
            try:
                message = exc.read(2000).decode(errors='replace')
            finally:
                exc.close()
            code = re.search(r'Code:\s*(\d+)', message)
            raise QueryError(message, int(code[1]) if code else None) from exc
        except (URLError, TimeoutError, OSError) as exc:
            raise QueryError(type(exc).__name__ + ': ' + str(exc)) from exc


def marker(client):
    rows = client.query('SELECT identity FROM gps_comparison_lab.identity')['data']
    if rows != [{'identity': LAB_MARKER}]:
        raise BenchmarkError('Lab identity missing or different; refusing the benchmark.')


def canonical(rows, expected_couriers):
    if len(rows) != expected_couriers:
        raise BenchmarkError(f'Expected {expected_couriers} courier rows, received {len(rows)}.')
    ids = []
    for row in rows:
        if set(row) != {'courier_id', 'state'} or not isinstance(row['state'], list) or len(row['state']) != 7:
            raise BenchmarkError('Unexpected position result schema.')
        ids.append(str(UUID(row['courier_id'])))
    if len(set(ids)) != len(ids):
        raise BenchmarkError('Courier output must be unique.')
    # ClickHouse UUID ordering is not Python's string ordering. Normalize both answers.
    ordered = sorted(rows, key=lambda row: row['courier_id'])
    return hashlib.sha256(json.dumps(ordered, sort_keys=True, separators=(',', ':'),
                                     allow_nan=False).encode()).hexdigest()


def percentile(values, fraction):
    return sorted(values)[max(0, math.ceil(fraction*len(values))-1)] if values else None


def summarize(samples, requested, duration, slo_ms, reason):
    ok = [s for s in samples if s['ok']]
    times = [s['wall_ms'] for s in ok]
    p95 = percentile(times, .95)
    complete = reason == 'complete' and len(samples) == requested
    status = ('pass' if len(ok) == requested and p95 <= slo_ms else 'fail') if complete else 'incomplete'
    return {'requested': requested, 'attempted': len(samples), 'successful': len(ok),
            'errors': len(samples)-len(ok), 'complete': complete, 'reason': reason,
            'p50_client_ms': percentile(times, .5), 'p95_client_ms': p95,
            'max_client_ms': max(times, default=None), 'phase_seconds': duration,
            'successful_qps': len(ok)/duration if duration else None, 'slo_status': status,
            'latency_population': 'Successful requests only; all attempted failures counted separately.'}


def measure_phase(client, sql, params, *, design, concurrency, requests, expected_digest,
                  expected_couriers, deadline, prefix, slo_ms):
    started = time.monotonic()
    lock, stop = threading.Lock(), threading.Event()
    issued, samples, failures = 0, [], []
    gate = threading.Barrier(concurrency)

    def worker():
        nonlocal issued
        gate.wait()
        while not stop.is_set() and time.monotonic() < deadline:
            with lock:
                if issued >= requests:
                    return
                index = issued
                issued += 1
            qid = prefix + '_m_' + design + '_' + uuid4().hex
            begin = time.monotonic()
            sample = {'query_id': qid, 'request': index, 'ok': False}
            try:
                reply = client.query(sql, params, query_id=qid, remaining=deadline-begin)
                sample.update(wall_ms=reply['wall_ms'], statistics=reply['statistics'])
                actual = canonical(reply['data'], expected_couriers)
                if actual != expected_digest:
                    raise BenchmarkError('Position results changed or designs disagree.')
                sample.update(ok=True, result_sha256=actual)
            except (BenchmarkError, ValueError) as exc:
                sample.update(error=str(exc), error_code=getattr(exc, 'code', None),
                              wall_ms=sample.get('wall_ms', (time.monotonic()-begin)*1000))
                sample['error_type'] = ('budget' if isinstance(exc, BudgetExpired) else
                                        'query' if isinstance(exc, QueryError) else 'correctness')
                failures.append(sample['error_type'])
                stop.set()  # No automatic retries or repeated failing requests.
            sample['started_offset_seconds'] = begin-started
            with lock:
                samples.append(sample)

    with ThreadPoolExecutor(max_workers=concurrency) as pool:
        jobs = [pool.submit(worker) for _ in range(concurrency)]
        for job in jobs:
            job.result()
    reason = ('correctness' if 'correctness' in failures else 'query_error' if 'query' in failures
              else 'time_budget' if 'budget' in failures or len(samples) < requests else 'complete')
    return {'design': design, 'concurrency': concurrency,
            'summary': summarize(samples, requests, time.monotonic()-started, slo_ms, reason),
            'samples': sorted(samples, key=lambda s: s['request'])}


def snapshot(client, params):
    corpus = client.query(CORPUS_SQL, params)['data'][0]
    return {'corpus': corpus, 'at_utc': datetime.now(timezone.utc).isoformat(),
        'parts': client.query("SELECT table,sum(rows) AS physical_rows,count() AS active_parts,"
            "sum(bytes_on_disk) AS disk_bytes FROM system.parts WHERE active AND database='delivery_atlas' "
            "AND table IN ('courier_positions','courier_latest_state') GROUP BY table ORDER BY table")['data'],
        'memory': client.query("SELECT metric,value FROM system.metrics WHERE metric IN "
            "('MemoryTracking','BackgroundMergesAndMutationsPoolTask')")['data'],
        'merges': client.query("SELECT table,elapsed,progress,memory_usage FROM system.merges "
            "WHERE database='delivery_atlas'")['data'],
        'disks': client.query('SELECT name,free_space,total_space FROM system.disks')['data']}


def validate_snapshot(state, initial, args):
    corpus = state['corpus']
    if int(corpus['rows']) != args.expected_rows or int(corpus['couriers']) != args.expected_couriers:
        raise BenchmarkError('Corpus count differs from the expected frozen input.')
    if initial is not None and corpus != initial['corpus']:
        raise BenchmarkError('Corpus fingerprint changed. Ingestion/mutations invalidate this comparison.')
    if not state['disks'] or min(int(d['free_space']) for d in state['disks']) < args.min_free_gib*GIB:
        raise BenchmarkError('Disk reserve reached; do not increase load.')


def collect_logs(client, prefix, query_ids, wait_seconds=5):
    end = time.monotonic()+wait_seconds
    while True:
        rows = client.query("SELECT query_id,toString(type) AS type,query_duration_ms,read_rows,read_bytes,"
            "memory_usage,exception_code,ProfileEvents['UserTimeMicroseconds'] AS user_cpu_us,"
            "ProfileEvents['SystemTimeMicroseconds'] AS system_cpu_us FROM system.query_log "
            "WHERE startsWith(query_id,{prefix:String}) AND type!='QueryStart' "
            'ORDER BY event_time_microseconds LIMIT 20000', {'param_prefix': prefix+'_m_'})['data']
        rows = [r for r in rows if r['query_id'] in query_ids]
        if query_ids <= {r['query_id'] for r in rows} or time.monotonic() >= end:
            return rows
        time.sleep(min(.5, max(0, end-time.monotonic())))


def attach_logs(report, logs):
    by_id = {r['query_id']: r for r in logs}
    measured = [s for p in report['phases'] for s in p['samples']]
    for sample in measured:
        sample['server'] = by_id.get(sample['query_id'])
    report['query_log_coverage'] = {'measured_requests': len(measured),
        'terminal_records_found': sum(s['server'] is not None for s in measured),
        'complete': all(s['server'] is not None for s in measured)}


def save_report(folder, report):
    temporary = folder/'report.json.tmp'
    temporary.write_text(json.dumps(report, indent=2, allow_nan=False)+'\n', encoding='utf-8')
    temporary.replace(folder/'report.json')
    columns = ['design','concurrency','repetition','requested','attempted','successful','errors',
               'complete','reason','p50_client_ms','p95_client_ms','successful_qps','slo_status']
    with (folder/'phases.csv').open('w', newline='', encoding='utf-8') as stream:
        writer = csv.DictWriter(stream, fieldnames=columns, extrasaction='ignore')
        writer.writeheader()
        for phase in report['phases']:
            writer.writerow({**phase, **phase['summary']})
    columns = ['query_id','design','concurrency','repetition','ok','wall_ms','error_type','error_code',
               'query_duration_ms','read_rows','read_bytes','memory_usage','exception_code','user_cpu_us','system_cpu_us']
    with (folder/'samples.csv').open('w', newline='', encoding='utf-8') as stream:
        writer = csv.DictWriter(stream, fieldnames=columns, extrasaction='ignore')
        writer.writeheader()
        for phase in report['phases']:
            for sample in phase['samples']:
                writer.writerow({**phase, **sample, **(sample.get('server') or {})})


def run(args, client=None):
    client = client or Client(args.url, query_seconds=args.query_seconds,
                             memory_bytes=args.memory_mib*1024**2, threads=args.threads)
    folder = args.output or ROOT/'data/gps-benchmark'/('gps_'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'_'+uuid4().hex[:8])
    folder.mkdir(parents=True, exist_ok=False)
    prefix = 'gpsbench_'+uuid4().hex
    started, deadline = time.monotonic(), time.monotonic()+args.max_seconds
    client.deadline = deadline
    report = {'schema_version': 1, 'experiment_id': prefix, 'status': 'running',
        'started_at_utc': datetime.now(timezone.utc).isoformat(), 'label': args.label,
        'client_platform': platform.platform(), 'scope': 'Frozen-run, database-only, read-only lab comparison.',
        'valid_comparison': False,
        'purpose': 'smoke' if args.smoke else 'exploration' if args.requests < 200 or args.repetitions < 3 else 'boundary_confirmation',
        'parameters': {k:str(v) if isinstance(v, Path) else v for k,v in vars(args).items()},
        'sql': QUERIES, 'corpus_sql': CORPUS_SQL, 'phases': [], 'snapshots': [],
        'cache_policy': 'Query-result cache disabled. Warmups excluded. OS cache uncontrolled; warm comparison.',
        'method': 'Fixed closed-loop concurrency, no retries. Client time includes local HTTP and Python overhead. Not an open-loop arrival-rate test or a production SLA.',
        'script_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    params = {'param_run': args.run_id, 'param_city': args.city}
    try:
        marker(client)
        report['server'] = client.query('SELECT version() AS version,hostName() AS hostname,uptime() AS uptime_seconds')['data'][0]
        report['settings'] = client.query("SELECT name,value FROM system.settings WHERE name IN "
            "('max_threads','max_memory_usage','max_execution_time','readonly','use_query_cache') ORDER BY name")['data']
        report['table_definitions'] = client.query("SELECT name,engine,create_table_query FROM system.tables "
            "WHERE database='delivery_atlas' AND name IN ('courier_positions','courier_latest_state','courier_latest_mv','courier_latest') ORDER BY name")['data']
        initial = snapshot(client, params)
        validate_snapshot(initial, None, args)
        report['snapshots'].append(initial)
        reference = client.query(QUERIES['history'], params)['data']
        expected = canonical(reference, args.expected_couriers)
        if canonical(client.query(QUERIES['prepared'], params)['data'], args.expected_couriers) != expected:
            raise BenchmarkError('The two designs do not return identical positions.')
        report['correctness'] = {'same_result': True, 'couriers': len(reference), 'result_sha256': expected}
        (folder/'reference-output.json').write_text(json.dumps(reference, indent=2)+'\n', encoding='utf-8')
        print(f'Equal answers verified: {args.expected_couriers} couriers, {args.expected_rows:,} GPS rows.', flush=True)
        for c in args.concurrency:
            for design in ('history','prepared'):
                for _ in range(args.warmups):
                    reply = client.query(QUERIES[design], params, remaining=deadline-time.monotonic())
                    if canonical(reply['data'], args.expected_couriers) != expected:
                        raise BenchmarkError('Output changed during warmup.')
            level = []
            for rep in range(args.repetitions):
                order = ('history','prepared') if rep % 2 == 0 else ('prepared','history')
                for design in order:
                    if time.monotonic() >= deadline:
                        raise BudgetExpired('Overall time budget exhausted; no capacity conclusion.')
                    phase = measure_phase(client, QUERIES[design], params, design=design,
                        concurrency=c, requests=args.requests, expected_digest=expected,
                        expected_couriers=args.expected_couriers,
                        deadline=min(deadline, time.monotonic()+args.phase_seconds), prefix=prefix, slo_ms=args.slo_ms)
                    phase['repetition'] = rep+1
                    report['phases'].append(phase)
                    level.append(phase)
                    save_report(folder, report)
                    print(json.dumps({'design':design,'concurrency':c,'repetition':rep+1,**phase['summary']}), flush=True)
                    if not phase['summary']['complete']:
                        raise BenchmarkError('Phase stopped: '+phase['summary']['reason']+'. Inspect errors; incomplete samples are not a measured capacity boundary.')
                    current = snapshot(client, params)
                    report['snapshots'].append(current)
                    validate_snapshot(current, initial, args)
            if any(p['summary']['slo_status'] == 'fail' for p in level):
                report['stop_reason'] = 'At least one phase crossed the experimental SLO; higher concurrency was not attempted.'
                break
        report['status'] = 'complete'
        report['valid_comparison'] = True
    except (BenchmarkError, ValueError, KeyboardInterrupt) as exc:
        report['status'] = 'stopped'
        report['stop_reason'] = str(exc) or 'Interrupted'
    finally:
        client.deadline = None  # Bounded log collection after the workload budget.
        ids = {s['query_id'] for p in report['phases'] for s in p['samples']}
        try:
            attach_logs(report, collect_logs(client, prefix, ids) if ids else [])
        except (BenchmarkError, ValueError) as exc:
            report['query_log_error'] = str(exc)
            attach_logs(report, [])
        report['finished_at_utc'] = datetime.now(timezone.utc).isoformat()
        report['elapsed_seconds'] = time.monotonic()-started
        save_report(folder, report)
    print(str(folder.resolve()), flush=True)
    return report, folder


def parse_args(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--url', default=LAB_URL)
    p.add_argument('--run-id', required=True, type=lambda s:str(UUID(s)))
    p.add_argument('--city', default='madrid')
    p.add_argument('--expected-rows', type=int, required=True)
    p.add_argument('--expected-couriers', type=int, default=150)
    p.add_argument('--label', required=True, help='Machine, allocated resources and competing workloads.')
    p.add_argument('--concurrency', default='1,2,4,8')
    p.add_argument('--requests', type=int, default=30)
    p.add_argument('--repetitions', type=int, default=1)
    p.add_argument('--warmups', type=int, default=5)
    p.add_argument('--slo-ms', type=float, default=1000)
    p.add_argument('--query-seconds', type=float, default=8)
    p.add_argument('--phase-seconds', type=int, default=180)
    p.add_argument('--max-seconds', type=int, default=1800)
    p.add_argument('--memory-mib', type=int, default=256)
    p.add_argument('--threads', type=int, default=2)
    p.add_argument('--min-free-gib', type=float, default=5)
    p.add_argument('--output', type=Path)
    p.add_argument('--smoke', action='store_true', help='One reader, three requests, one warmup; no capacity claim.')
    args = p.parse_args(argv)
    try:
        lab_url(args.url)
        args.concurrency = [int(x) for x in args.concurrency.split(',')]
    except ValueError as exc:
        p.error(str(exc))
    if args.smoke:
        args.concurrency,args.requests,args.repetitions,args.warmups=[1],3,1,1
        args.max_seconds=min(args.max_seconds,120)
    if (not args.concurrency or args.concurrency != sorted(set(args.concurrency))
            or min(args.concurrency)<1 or max(args.concurrency)>16 or args.requests<max(args.concurrency)
            or args.requests>2000 or not 1<=args.repetitions<=5 or not 0<=args.warmups<=10
            or args.requests*args.repetitions*2*len(args.concurrency)>16000
            or not 0<args.expected_rows<=1000000000 or not 1<=args.expected_couriers<=5000
            or not 0<args.slo_ms<=60000 or not .1<=args.query_seconds<=30
            or not 1<=args.phase_seconds<=600 or not 1<=args.max_seconds<=7200
            or not 32<=args.memory_mib<=512 or not 1<=args.threads<=4
            or not 1<=args.min_free_gib<=100 or not re.fullmatch('[a-z][a-z0-9_-]{0,31}',args.city)):
        p.error('Invalid input or bounded experiment budget exceeded.')
    return args


if __name__ == '__main__':
    result,_ = run(parse_args())
    raise SystemExit(0 if result['status']=='complete' and result['query_log_coverage']['complete'] else 1)
