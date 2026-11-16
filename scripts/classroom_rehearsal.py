"""Temporary public classroom frontend. All host controls stay on the local API."""
import mimetypes
import secrets
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

from atlas import share

ROOT = Path(__file__).resolve().parents[1] / 'shared-public'


class RehearsalHandler(share.Handler):
    def do_GET(self):
        path = urlsplit(self.path).path
        if path.startswith('/api/'):
            self.headers['Authorization'] = 'Bearer ' + share.TOKEN
            return super().do_GET()
        target = (ROOT / ('index.html' if path == '/' else path.lstrip('/'))).resolve()
        if not target.is_relative_to(ROOT) or not target.is_file():
            return self.send_json(404, {'error': 'Page unavailable'})
        raw = target.read_bytes()
        self.send_response(200)
        self.send_header('Content-Type', mimetypes.guess_type(target)[0] or 'application/octet-stream')
        self.send_header('Content-Length', str(len(raw)))
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        self.wfile.write(raw)

    def do_POST(self):
        self.headers['Authorization'] = 'Bearer ' + share.TOKEN
        return super().do_POST()


if __name__ == '__main__':
    share.TOKEN = secrets.token_hex(32)
    share.BACKEND = 'http://127.0.0.1:18701'
    ThreadingHTTPServer(('127.0.0.1', 18702), RehearsalHandler).serve_forever()
