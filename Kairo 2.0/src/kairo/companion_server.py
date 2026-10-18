import asyncio
import json
import ssl
import threading
from pathlib import Path
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from kairo.companion import lan_address


def start_companion(companion, loop, address, port, certfile, keyfile):
    address = lan_address(address)
    if type(port) is not int or not 1024 <= port <= 65535:
        raise ValueError('Companion port must be 1024–65535')
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    context.load_cert_chain(certfile, keyfile)
    origin = f'https://{address}:{port}'
    class Handler(BaseHTTPRequestHandler):
        def setup(self):
            super().setup()
            self.connection.settimeout(10)

        def log_message(self, *_):
            pass

        def do_GET(self):
            if self.path != '/' or self.headers.get('Host') != f'{address}:{port}':
                return self.send(404, {'error': 'Not found'})
            try:
                lan_address(self.client_address[0])
            except ValueError:
                return self.send(403, {'error': 'LAN clients only'})
            body = Path(__file__).with_name('companion.html').read_bytes()
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.send_header('Content-Length', str(len(body)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('Referrer-Policy', 'no-referrer')
            self.send_header('Content-Security-Policy', "default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; connect-src 'self'; img-src data:; frame-ancestors 'none'; base-uri 'none'; form-action 'none'")
            self.end_headers()
            self.wfile.write(body)

        def send(self, status, data):
            body = json.dumps(data).encode()
            self.send_response(status)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(body)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.end_headers()
            self.wfile.write(body)

        def do_POST(self):
            if self.headers.get('Host') != f'{address}:{port}' or self.headers.get('Origin') not in {None, origin}:
                return self.send(403, {'error': 'Invalid host or origin'})
            try:
                lan_address(self.client_address[0])
                size = int(self.headers.get('Content-Length', '0'))
                if not 0 < size <= 4096 or self.headers.get('Content-Type') != 'application/json':
                    raise ValueError('Expected bounded JSON')
                data = json.loads(self.rfile.read(size))
                if not isinstance(data, dict):
                    raise ValueError('Expected object')
                async def dispatch():
                    if self.path == '/pair':
                        return companion.pair(data.get('code'))
                    if self.path in {'/control', '/frame', '/disconnect'}:
                        auth = self.headers.get('Authorization', '')
                        if not auth.startswith('Bearer '):
                            raise PermissionError('Session required')
                        if self.path == '/disconnect':
                            return companion.disconnect(auth[7:])
                        if self.path == '/frame':
                            return await companion.frame(auth[7:])
                        return await companion.control(auth[7:], data.get('sequence'), data.get('action'), data.get('args'))
                    raise ValueError('Unknown endpoint')
                future = asyncio.run_coroutine_threadsafe(dispatch(), loop)
                try:
                    result = future.result(timeout=190)
                except TimeoutError:
                    future.cancel()
                    raise ValueError('Control timed out; do not replay')
                self.send(200, result)
            except PermissionError as exc:
                self.send(403, {'error': str(exc)})
            except (ValueError, TypeError) as exc:
                self.send(400, {'error': str(exc)[:150]})
            except Exception:
                self.send(503, {'error': 'Control unavailable; no automatic retry'})

    server = ThreadingHTTPServer((address, port), Handler)
    server.daemon_threads = True
    try:
        server.socket = context.wrap_socket(server.socket, server_side=True)
    except BaseException:
        server.server_close()
        raise
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    return server
