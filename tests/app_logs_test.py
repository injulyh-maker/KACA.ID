import os
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
main = (ROOT / 'main.js').read_text(encoding='utf-8')
preload = (ROOT / 'preload.js').read_text(encoding='utf-8')
app = (ROOT / 'src' / 'app.js').read_text(encoding='utf-8')
css = (ROOT / 'src' / 'style.css').read_text(encoding='utf-8')
backend = (ROOT / 'backend' / 'camera_server.py').read_text(encoding='utf-8')

assert 'app:logs-read' in main and 'app:logs-open' in main and 'app:logs-clear' in main
assert 'render-process-gone' in main and 'unresponsive' in main
assert 'reportRendererError' in preload and 'app:renderer-log' in preload
assert 'App Logs' in app and 'refreshAppLogs' in app and 'appLogsViewer' in app
assert 'unhandledrejection' in app and "addEventListener('error'" in app
assert '.app-logs-viewer' in css
assert 'def stream_file(' in backend and 'length=256 * 1024' in backend
assert "self.stream_file(zip_path, 'application/zip'" in backend
assert "open(zip_path, 'rb').read()" not in backend
print('App Logs UI, Electron crash capture, renderer error capture, and bounded media streaming: PASS')

# Exercise the actual backend streaming helper with a file larger than one chunk.
import importlib.util
spec = importlib.util.spec_from_file_location('kaca_camera_server_for_log_test', ROOT / 'backend' / 'camera_server.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
class FakeWriter:
    def __init__(self): self.bytes = 0; self.calls = 0
    def write(self, data): self.bytes += len(data); self.calls += 1
class FakeHandler:
    stream_file = module.Handler.stream_file
    def __init__(self): self.wfile=FakeWriter(); self.headers=[]; self.status=None
    def send_response(self, code): self.status=code
    def send_header(self, key, value): self.headers.append((key,value))
    def end_headers(self): pass
with tempfile.NamedTemporaryFile(delete=False) as f:
    f.write(os.urandom(700_000)); test_path=f.name
try:
    handler=FakeHandler(); handler.stream_file(test_path, 'application/octet-stream', 'large.bin')
    assert handler.status == 200 and handler.wfile.bytes == 700_000
    assert handler.wfile.calls >= 3, handler.wfile.calls
    assert ('Content-Length','700000') in handler.headers
finally:
    os.unlink(test_path)
print('Backend media stream helper chunked transfer: PASS')
