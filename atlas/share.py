"""Authenticated read-only gateway for the temporary classroom demo."""
import hmac
import json
import os
import threading
import time
from collections import OrderedDict
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlencode, urlsplit
from urllib.request import urlopen
from uuid import UUID

ROUTES = {'simulation', 'operations', 'status', 'track', 'summary', 'inventory', 'catalog'}
CACHE = OrderedDict()
LOCK = threading.Lock()
READ_LOCKS = {endpoint: threading.Lock() for endpoint in ROUTES}
TOKEN = os.environ.get('ATLAS_SHARE_TOKEN', '')
BACKEND = os.environ.get('ATLAS_SHARE_BACKEND', 'http://atlas:8001').rstrip('/')


def canonical_path(raw):
    url = urlsplit(raw)
    endpoint = url.path.removeprefix('/api/')
    if not url.path.startswith('/api/') or endpoint not in ROUTES:
        raise ValueError('Ruta no disponible')
    query = parse_qs(url.query, keep_blank_values=True, max_num_fields=4)
    allowed = {'track': {'run_id', 'courier_id'}, 'summary': {'city_id', 'source_kind'}}.get(endpoint, set())
    if set(query) - allowed or any(len(v) != 1 for v in query.values()):
        raise ValueError('Parámetros no disponibles')
    if endpoint == 'track':
        if set(query) != allowed:
            raise ValueError('Falta el identificador del recorrido')
        query = {k: [str(UUID(v[0]))] for k, v in query.items()}
    if endpoint == 'summary':
        if query.get('city_id', ['madrid'])[0] != 'madrid' or query.get('source_kind', ['synthetic'])[0] not in {'synthetic', 'demo_live'}:
            raise ValueError('Solo está disponible la demo de Madrid')
        query.setdefault('city_id', ['madrid'])
        query.setdefault('source_kind', ['synthetic'])
    suffix = urlencode(sorted((k, v[0]) for k, v in query.items()))
    return endpoint, '/api/' + endpoint + ('?' + suffix if suffix else '')


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass  # Do not log request headers or the shared credential.

    def send_json(self, code, body):
        payload = json.dumps(body, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Cache-Control', 'no-store')
        self.send_header('Content-Length', str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def do_POST(self):
        self.send_json(405, {'error': 'La demo compartida es de solo lectura'})

    do_PUT = do_PATCH = do_DELETE = do_POST

    def do_GET(self):
        if not hmac.compare_digest(self.headers.get('Authorization', ''), 'Bearer ' + TOKEN):
            return self.send_json(401, {'error': 'Acceso no autorizado'})
        try:
            endpoint, path = canonical_path(self.path)
        except (ValueError, TypeError):
            return self.send_json(400, {'error': 'Consulta no disponible'})
        try:
            # Coalesce concurrent viewers into one local query per cache window.
            with READ_LOCKS[endpoint]:
                ttl = 60 if endpoint in {'inventory', 'catalog'} else 10 if endpoint == 'summary' else 1.5
                with LOCK:
                    cached = CACHE.get(path)
                if cached and time.monotonic() - cached[0] < ttl:
                    body = cached[1]
                    with LOCK:
                        if path in CACHE:
                            CACHE.move_to_end(path)
                else:
                    with urlopen(BACKEND + path, timeout=10) as response:
                        payload = response.read(2 * 1024 * 1024 + 1)
                    if len(payload) > 2 * 1024 * 1024:
                        raise ValueError('Response too large')
                    body = json.loads(payload)
                    if endpoint == 'status':
                        body = {k: body[k] for k in ('pending', 'published', 'publisher_phase') if k in body}
                    if endpoint == 'simulation':
                        body = {k: body[k] for k in ('running', 'fleet', 'interval_seconds', 'run_id') if k in body}
                    with LOCK:
                        CACHE[path] = (time.monotonic(), body)
                        while len(CACHE) > 128:
                            CACHE.popitem(last=False)
            self.send_json(200, body)
        except Exception:
            self.send_json(503, {'error': 'El ordenador de Jere no responde. Se reintentará.'})


if __name__ == '__main__':
    if len(TOKEN) < 32:
        raise SystemExit('ATLAS_SHARE_TOKEN must contain at least 32 characters')
    print('Read-only share gateway listening on 8080', flush=True)
    ThreadingHTTPServer(('0.0.0.0', 8080), Handler).serve_forever()
