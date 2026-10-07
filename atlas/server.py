"""Single API process with a durable queue and one batch publisher."""
import json
import os
import signal
import threading
import time
from datetime import date
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from atlas.clickhouse import ClickHouse
from atlas.contract import validate, KINDS, ACTIONS
from atlas.store import Store, Conflict, Full

MAX_BATCH = 5000
MAX_BODY = 5 * 1024 * 1024
ROOT = Path(__file__).resolve().parents[1]

class Publisher:
    def __init__(self, store, ch):
        self.store, self.ch = store, ch
        self.stop = threading.Event()
        self.error = None
        self.thread = threading.Thread(target=self.run, daemon=True)

    def once(self):
        rows = self.store.pending(MAX_BATCH)
        if not rows:
            return False
        self.ch.publish([payload for _, payload in rows])
        self.store.published([seq for seq, _ in rows])
        self.error = None
        return True

    def run(self):
        while not self.stop.is_set():
            try:
                worked = self.once()
                self.stop.wait(0.3 if worked else 1)
            except Exception as error:
                self.error = str(error)[:300]
                self.store.count('publication_errors')
                self.stop.wait(2)

def make_handler(store, ch, publisher):
    class Handler(BaseHTTPRequestHandler):
        def send_json(self, data, status=200):
            raw = json.dumps(data, ensure_ascii=False).encode()
            self.send_response(status)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Content-Length', str(len(raw)))
            self.send_header('Cache-Control', 'no-store')
            if status == 503:
                self.send_header('Retry-After', '2')
            self.end_headers()
            self.wfile.write(raw)

        def do_POST(self):
            if urlparse(self.path).path != '/api/events':
                return self.send_json({'error':'Ruta desconocida'}, 404)
            self.connection.settimeout(15)
            try:
                size = int(self.headers.get('Content-Length', '0'))
                if not 0 < size <= MAX_BODY:
                    return self.send_json({'error':'Cuerpo requerido, máximo 5 MiB'}, 413)
                raw = self.rfile.read(size)
                if len(raw) != size:
                    raise ValueError('Cuerpo incompleto')
                data = json.loads(raw)
                if not isinstance(data, dict) or set(data) != {'events'} or not isinstance(data['events'], list) or not 1 <= len(data['events']) <= MAX_BATCH:
                    raise ValueError('Enviar {events: [...]} con 1 a 5000 eventos.')
                events = [validate(e) for e in data['events']]
                result = store.accept(events)
                self.send_json(result, 202 if result['accepted'] else 200)
            except Conflict as error:
                store.count('conflicts')
                self.send_json({'error':str(error)}, 409)
            except Full as error:
                store.count('backpressure')
                self.send_json({'error':str(error)}, 503)
            except (ValueError, TypeError, OSError) as error:
                store.count('rejected_requests')
                self.send_json({'error':str(error)}, 400)

        def do_GET(self):
            parsed = urlparse(self.path)
            try:
                if parsed.path == '/health':
                    ch.query('SELECT 1')
                    return self.send_json({'ok': True, 'publisher_error':publisher.error})
                if parsed.path == '/api/status':
                    return self.send_json(dict(store.status(), publisher_error=publisher.error))
                if parsed.path == '/api/summary':
                    multi = parse_qs(parsed.query, keep_blank_values=True)
                    if set(multi)-{'from','to','city_id','source_kind','event_type'} or any(len(v)!=1 for v in multi.values()):
                        raise ValueError('Filtro desconocido o repetido.')
                    filters = {k:v[0] for k,v in multi.items()}
                    if any(not 0<len(v)<=160 for v in filters.values()):
                        raise ValueError('Filtro vacío o demasiado largo.')
                    for k in ('from','to'):
                        if k in filters:
                            date.fromisoformat(filters[k])
                    if 'from' in filters and 'to' in filters and filters['from']>filters['to']:
                        raise ValueError('Intervalo invertido.')
                    if 'source_kind' in filters and filters['source_kind'] not in KINDS or 'event_type' in filters and filters['event_type'] not in ACTIONS:
                        raise ValueError('Tipo u origen inválido.')
                    return self.send_json(ch.summary(filters))
                if parsed.path == '/api/recent':
                    return self.send_json({'rows':ch.query('SELECT toString(event_id) AS event_id, '
                        'toString(session_id) AS session_id,toString(event_time) AS event_time, '
                        'toString(ingested_at) AS ingested_at,event_type,city_id,source,source_kind '
                        'FROM delivery_atlas.app_events FINAL ORDER BY ingested_at DESC LIMIT 30')})
                if parsed.path == '/':
                    return self.send_json({'project':'Delivery Atlas', 'state':'Infraestructura v1',
                        'routes':['/health','/api/status','/api/summary','/api/recent','POST /api/events'],
                        'guide':'docs/INFRAESTRUCTURA-ATLAS.md',
                        'team':{'Jere':'Base e ingesta','Anuar':'Miniapp','Echenique':'Dashboard y reproducción'}})
                target = (ROOT/'web'/parsed.path.lstrip('/')).resolve()
                if not target.is_relative_to(ROOT/'web') or not target.is_file():
                    return self.send_json({'error':'Ruta desconocida'}, 404)
                content = target.read_bytes()
                mime = {'.html':'text/html; charset=utf-8','.js':'text/javascript; charset=utf-8',
                        '.css':'text/css; charset=utf-8','.svg':'image/svg+xml','.png':'image/png'}.get(target.suffix, 'application/octet-stream')
                self.send_response(200)
                self.send_header('Content-Type', mime)
                self.send_header('Content-Length', str(len(content)))
                self.end_headers()
                self.wfile.write(content)
            except (ValueError, TypeError) as error:
                self.send_json({'error':str(error)}, 400)
            except OSError:
                self.send_json({'error':'ClickHouse no disponible. La cola aceptada se conserva.'}, 503)

        def log_message(self, *_):
            pass
    return Handler

def main():
    ch = ClickHouse()
    ch.init()
    store = Store(os.environ.get('ATLAS_QUEUE_PATH', str(ROOT/'data/atlas/outbox.sqlite')),
                  int(os.environ.get('ATLAS_MAX_PENDING', '200000')))
    publisher = Publisher(store, ch)
    server = ThreadingHTTPServer((os.environ.get('HOST','127.0.0.1'), int(os.environ.get('PORT','8001'))), make_handler(store,ch,publisher))
    publisher.thread.start()
    signal.signal(signal.SIGTERM, lambda *_: threading.Thread(target=server.shutdown, daemon=True).start())
    print('Delivery Atlas: API y publicador listos', flush=True)
    try:
        server.serve_forever()
    finally:
        publisher.stop.set()
        publisher.thread.join(5)
        server.server_close()

if __name__ == '__main__':
    main()
