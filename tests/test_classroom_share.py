import json
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from unittest.mock import patch

from atlas import share


class Backend(BaseHTTPRequestHandler):
    def do_POST(self):
        body=json.loads(self.rfile.read(int(self.headers['Content-Length'])))
        self.send_response(409 if body.get('closed') else 202)
        self.send_header('Content-Type','application/json')
        self.end_headers()
        self.wfile.write(json.dumps(body).encode())

    def log_message(self, *_):
        pass


class ClassroomGatewayTest(unittest.TestCase):
    def test_bounded_write_and_methods_over_http(self):
        backend=ThreadingHTTPServer(('127.0.0.1',0),Backend)
        gateway=ThreadingHTTPServer(('127.0.0.1',0),share.Handler)
        for server in (backend,gateway):
            threading.Thread(target=server.serve_forever,daemon=True).start()
        def call(path,method,body,token=True):
            req=Request('http://127.0.0.1:'+str(gateway.server_port)+path,
                        data=json.dumps(body).encode(),method=method,
                        headers={'Authorization':'Bearer test-only' if token else '',
                                 'Content-Type':'application/json'})
            try:
                with urlopen(req,timeout=3) as r:return r.status,json.load(r)
            except HTTPError as r:
                with r:
                    return r.code,json.load(r)
        try:
            with patch.object(share,'TOKEN','test-only'),patch.object(share,'BACKEND','http://127.0.0.1:'+str(backend.server_port)):
                self.assertEqual(call('/api/classroom-order','POST',{'alias':'Alex'})[0],202)
                self.assertEqual(call('/api/classroom-order','POST',{'closed':True})[0],409)
                self.assertEqual(call('/api/classroom-order','POST',{},False)[0],401)
                self.assertEqual(call('/api/classroom-order','PUT',{})[0],405)
                self.assertEqual(call('/api/classroom-open','POST',{})[0],405)
                self.assertEqual(call('/api/classroom-order','POST',{'text':'x'*2048})[0],413)
        finally:
            for server in (gateway,backend):
                server.shutdown()
                server.server_close()
