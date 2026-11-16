"""Authenticated demo gateway with a bounded classroom checkout route."""
import hmac
import json
import os
import threading
import time
from collections import OrderedDict
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlencode, urlsplit
from urllib.request import urlopen, Request
from urllib.error import HTTPError
from uuid import UUID
from atlas.analytics import ROUTES as ANALYTICS_ROUTES, validate_filters

ROUTES = {'simulation', 'operations', 'status', 'track', 'summary', 'inventory', 'catalog', 'datasets', 'classroom'} | ANALYTICS_ROUTES
CACHE = OrderedDict()
LOCK = threading.Lock()
READ_LOCKS = {endpoint: threading.Lock() for endpoint in ROUTES}
TOKEN = os.environ.get('ATLAS_SHARE_TOKEN', '')
BACKEND = os.environ.get('ATLAS_SHARE_BACKEND', 'http://atlas:8001').rstrip('/')


def canonical_path(raw):
    url = urlsplit(raw)
    endpoint = url.path.removeprefix('/api/')
    if not url.path.startswith('/api/') or endpoint not in ROUTES:
        raise ValueError('Route not available')
    query = parse_qs(url.query, keep_blank_values=True, max_num_fields=8)
    if endpoint in ANALYTICS_ROUTES:
        filters = validate_filters(endpoint, query)
        suffix = urlencode(sorted(filters.items()))
        return endpoint, '/api/' + endpoint + ('?' + suffix if suffix else '')
    allowed = {'classroom': {'room_id'}, 'track': {'run_id', 'courier_id'}, 'summary': {'city_id', 'source_kind'}}.get(endpoint, set())
    if set(query) - allowed or any(len(v) != 1 for v in query.values()):
        raise ValueError('Parameters not available')
    if endpoint in {'track','classroom'}:
        if endpoint == 'track' and set(query) != allowed:
            raise ValueError('Missing track identifier')
        query = {k: [str(UUID(v[0]))] for k, v in query.items()}
    if endpoint == 'summary':
        if query.get('city_id', ['madrid'])[0] != 'madrid' or query.get('source_kind', ['synthetic'])[0] not in {'synthetic', 'demo_live'}:
            raise ValueError('Only the Madrid demo is available')
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
        if self.path != '/api/classroom-order':
            return self.send_json(405, {'error': 'Write route unavailable'})
        if not hmac.compare_digest(self.headers.get('Authorization', ''), 'Bearer ' + TOKEN):
            return self.send_json(401, {'error': 'Unauthorized access'})
        self.connection.settimeout(15)
        try:
            size = int(self.headers.get('Content-Length', '0'))
            if not 0 < size <= 2048:
                return self.send_json(413, {'error': 'Order is too large'})
            payload = self.rfile.read(size)
            body = json.loads(payload)
            if not isinstance(body, dict):
                raise ValueError('Send an order object')
            req = Request(BACKEND + '/api/classroom-order', data=payload,
                          headers={'Content-Type': 'application/json'}, method='POST')
            with urlopen(req, timeout=12) as response:
                self.send_json(response.status, json.load(response))
        except HTTPError as error:
            with error:
                self.send_json(error.code, json.loads(error.read()))
        except (ValueError, TypeError):
            self.send_json(400, {'error': 'Invalid classroom order'})
        except Exception:
            self.send_json(503, {'error': 'Connection interrupted. Retry the same order.'})

    def do_PUT(self):
        self.send_json(405, {'error': 'Method unavailable'})

    do_PATCH = do_DELETE = do_PUT

    def do_GET(self):
        if not hmac.compare_digest(self.headers.get('Authorization', ''), 'Bearer ' + TOKEN):
            return self.send_json(401, {'error': 'Unauthorized access'})
        try:
            endpoint, path = canonical_path(self.path)
        except (ValueError, TypeError):
            return self.send_json(400, {'error': 'Query not available'})
        try:
            # Coalesce concurrent viewers into one local query per cache window.
            with READ_LOCKS[endpoint]:
                ttl = 60 if endpoint in {'inventory', 'catalog', 'datasets', 'historical', 'benchmark'} else 10 if endpoint in {'summary', 'performance'} else 5 if endpoint == 'journey' else 1.5
                with LOCK:
                    cached = CACHE.get(path)
                if cached and time.monotonic() - cached[0] < ttl:
                    body = cached[1]
                    with LOCK:
                        if path in CACHE:
                            CACHE.move_to_end(path)
                else:
                    with urlopen(BACKEND + path, timeout=24 if endpoint in ANALYTICS_ROUTES else 10) as response:
                        payload = response.read(2 * 1024 * 1024 + 1)
                    if len(payload) > 2 * 1024 * 1024:
                        raise ValueError('Response too large')
                    body = json.loads(payload)
                    if endpoint == 'status':
                        body = {k: body[k] for k in ('pending', 'published', 'publisher_phase') if k in body}
                    if endpoint == 'simulation':
                        body = {k: body[k] for k in ('running', 'fleet', 'interval_seconds', 'run_id','mode','customers',
                            'agent_mode','model','agent_state','decisions','model_calls','max_model_calls',
                            'ai_customers','traffic_customers','traffic_decisions','traffic_state') if k in body}
                    with LOCK:
                        CACHE[path] = (time.monotonic(), body)
                        while len(CACHE) > 128:
                            CACHE.popitem(last=False)
            self.send_json(200, body)
        except HTTPError as error:
            with error:
                self.send_json(error.code, json.loads(error.read()))
        except Exception:
            self.send_json(503, {'error': 'The demo server is not responding. It will be retried.'})


if __name__ == '__main__':
    if len(TOKEN) < 32:
        raise SystemExit('ATLAS_SHARE_TOKEN must contain at least 32 characters')
    print('Atlas share gateway listening on 8080', flush=True)
    ThreadingHTTPServer(('0.0.0.0', 8080), Handler).serve_forever()
