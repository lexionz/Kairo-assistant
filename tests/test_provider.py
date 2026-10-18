import asyncio
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import pytest
from kairo.inference import CompatibleBrain


def test_real_http_provider_contract_and_no_key_sent_to_local(monkeypatch):
    captured = {}
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass
        def do_POST(self):
            captured['body'] = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
            captured['authorization'] = self.headers.get('Authorization')
            data = json.dumps({'choices': [{'message': {'role': 'assistant', 'content': 'HTTP contract verified'}}]}).encode()
            self.send_response(200)
            self.send_header('Content-Length', str(len(data)))
            self.end_headers()
            self.wfile.write(data)
    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    monkeypatch.setenv('KAIRO_API_KEY', 'must-not-be-sent-locally')
    try:
        result = asyncio.run(CompatibleBrain({'endpoint': f'http://127.0.0.1:{server.server_port}/chat', 'model': 'test-contract'}).complete([{'role': 'user', 'content': 'hello'}], []))
        assert result['content'] == 'HTTP contract verified'
        assert captured['body']['model'] == 'test-contract'
        assert captured['authorization'] is None
    finally:
        server.shutdown()
        server.server_close()


def test_brain_missing_configuration_is_explicit():
    with pytest.raises(ValueError, match='Configure KAIRO'):
        asyncio.run(CompatibleBrain({}).complete([], []))
