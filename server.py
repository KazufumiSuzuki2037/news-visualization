"""NV loopback server. Only web assets and explicit JSON endpoints are served."""
import argparse
from functools import partial
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import mimetypes
from pathlib import Path
import threading
from urllib.parse import urlsplit, parse_qs

from nvcore.core import ROOT, digest
from nvcore.data import atomic_json, read_json, validate_settings, view_news

LOCK = threading.Lock()
MAX_JSON = 2_000_000


class Handler(BaseHTTPRequestHandler):
    server_version = 'NV/1'
    protocol_version = 'HTTP/1.1'

    def allowed(self, mutation=False):
        host = self.headers.get('Host','')
        authority = f'127.0.0.1:{self.server.server_port}'
        if host not in {authority, f'localhost:{self.server.server_port}'}:
            self.send_json(403, {'error':'INVALID_HOST'})
            return False
        origin = self.headers.get('Origin')
        if origin and origin != 'http://'+host:
            self.send_json(403, {'error':'INVALID_ORIGIN'})
            return False
        if self.headers.get('Sec-Fetch-Site') == 'cross-site':
            self.send_json(403, {'error':'CROSS_SITE_REQUEST'})
            return False
        if mutation and self.headers.get('Content-Type','').split(';')[0] != 'application/json':
            self.send_json(415, {'error':'JSON_REQUIRED'})
            return False
        return True

    def send_data(self,status,body,mime):
        self.send_response(status)
        self.send_header('Content-Type',mime)
        self.send_header('Content-Length',str(len(body)))
        self.send_header('Cache-Control','no-store')
        self.send_header('X-Content-Type-Options','nosniff')
        self.send_header('Content-Security-Policy',"default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' https: data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'")
        self.end_headers()
        self.wfile.write(body)

    def send_json(self,status,value):
        self.send_data(status,json.dumps(value,ensure_ascii=False,allow_nan=False).encode('utf-8'),'application/json; charset=utf-8')

    def do_GET(self):
        if not self.allowed():
            return
        path = urlsplit(self.path).path
        try:
            root = self.server.root
            if path == '/api/state':
                with LOCK:
                    settings = validate_settings(read_json(root/'config/settings.json'))
                    preferences = read_json(root/'data/preferences.json')
                    period = parse_qs(urlsplit(self.path).query).get('period',['24h'])[0]
                    if period not in ['24h','7d']:
                        raise ValueError('INVALID_PERIOD')
                    news = view_news(read_json(root/'data/news.json'),settings,period)
                    payload = {'settings':settings,'preferences':preferences,'revision':digest(settings),'news':news}
                    status_file = root/'data/research-status.json'
                    try:
                        payload['researchStatus'] = read_json(status_file) if status_file.is_file() else None
                    except (OSError,ValueError):
                        payload['researchStatus'] = None
                    payload['stateHash'] = digest(payload)
                self.send_json(200,payload)
            elif path == '/data/news.json':
                self.send_json(200,read_json(root/'data/news.json'))
            else:
                web = (root/'web').resolve()
                asset = (web/('index.html' if path=='/' else path.lstrip('/'))).resolve()
                if not asset.is_relative_to(web) or not asset.is_file() or asset.suffix not in {'.html','.js','.css','.txt'}:
                    self.send_json(404,{'error':'NOT_FOUND'})
                    return
                mime = {'.html':'text/html; charset=utf-8','.js':'text/javascript; charset=utf-8','.css':'text/css; charset=utf-8','.txt':'text/plain; charset=utf-8'}[asset.suffix]
                self.send_data(200,asset.read_bytes(),mime)
        except (OSError,ValueError,KeyError,TypeError) as error:
            self.send_json(422,{'error':str(error) if isinstance(error,ValueError) else 'LOCAL_DATA_UNAVAILABLE'})

    def do_PUT(self):
        try:
            length = int(self.headers.get('Content-Length','0'))
            if not 0 < length <= MAX_JSON:
                raise ValueError('INVALID_BODY_SIZE')
            self.connection.settimeout(5)
            raw = self.rfile.read(length)
            if len(raw) != length:
                raise ValueError('INCOMPLETE_BODY')
        except (OSError,ValueError) as error:
            self.send_json(422,{'error':'INVALID_BODY_SIZE_OR_READ'})
            return
        if not self.allowed(mutation=True):
            return
        path = urlsplit(self.path).path
        if path not in {'/api/settings','/api/preferences'}:
            self.send_json(404,{'error':'NOT_FOUND'})
            return
        try:
            payload = json.loads(raw)
            with LOCK:
                root = self.server.root
                if path == '/api/settings':
                    current = read_json(root/'config/settings.json')
                    if not isinstance(payload,dict) or set(payload) != {'revision','settings'}:
                        raise ValueError('INVALID_REQUEST')
                    if payload['revision'] != digest(current):
                        self.send_json(409,{'error':'設定が更新されています。内容を控えて再読込してください。'})
                        return
                    updated = payload['settings']
                    validate_settings(updated)
                    updated['version'] = current['version']+1
                    atomic_json(root/'config/settings.json',updated)
                    self.send_json(200,{'revision':digest(updated),'settings':updated})
                else:
                    if not isinstance(payload,dict) or set(payload) != {'knownTermIds'} or not isinstance(payload['knownTermIds'],list) or len(payload['knownTermIds'])>10000 or any(not isinstance(item,str) or not item or len(item)>200 for item in payload['knownTermIds']) or len(set(payload['knownTermIds']))!=len(payload['knownTermIds']):
                        raise ValueError('INVALID_KNOWN_TERMS')
                    atomic_json(root/'data/preferences.json',payload)
                    self.send_json(200,payload)
        except (OSError,ValueError,KeyError,TypeError) as error:
            self.send_json(422,{'error':str(error) if isinstance(error,ValueError) else 'SAVE_FAILED'})


def make_server(root=ROOT, port=8767):
    server = ThreadingHTTPServer(('127.0.0.1',port),Handler)
    server.root = Path(root)
    return server


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port',type=int,default=8767)
    parser.add_argument('--root',type=Path,default=ROOT,help=argparse.SUPPRESS)
    args = parser.parse_args()
    with make_server(args.root,args.port) as server:
        print(f'NV: http://127.0.0.1:{server.server_port}',flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
