"""HTTP-level tests for standalone video capture from both MultiCam angles."""
import importlib.util
import http.client
import json
import os
import tempfile
import threading
import time
import numpy as np

spec = importlib.util.spec_from_file_location('kaca_v0926_backend_test', os.path.join(os.path.dirname(__file__), '..', 'backend', 'camera_server.py'))
backend = importlib.util.module_from_spec(spec)
spec.loader.exec_module(backend)

with tempfile.TemporaryDirectory(prefix='kaca_v0926_test_') as temp:
    backend.DATA_DIR = os.path.join(temp, 'data')
    backend.LOCAL_ARCHIVE_ROOT = os.path.join(temp, 'archive')
    os.makedirs(backend.DATA_DIR, exist_ok=True)
    backend.latest_frame = np.zeros((240, 320, 3), dtype=np.uint8)
    backend.latest_secondary_frame = np.zeros((240, 320, 3), dtype=np.uint8)
    server = backend.ThreadingHTTPServer(('127.0.0.1', 0), backend.Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        for angle, route in ((0, '/api/video/start'), (1, '/api/booth/video/start')):
            conn = http.client.HTTPConnection('127.0.0.1', server.server_port, timeout=10)
            conn.request('POST', route, body=json.dumps({'angle': angle}), headers={'Content-Type': 'application/json'})
            response = conn.getresponse()
            started = json.loads(response.read())
            assert response.status == 200 and started.get('ok') and started.get('id'), started
            for i in range(32):
                frame = np.full((240, 320, 3), (i * 7) % 255, dtype=np.uint8)
                if angle == 0:
                    backend.latest_frame = frame
                else:
                    backend.latest_secondary_frame = frame
                backend.write_booth_video_frame(frame, angle)
                time.sleep(0.055)
            conn.request('POST', '/api/video/stop', body='{}', headers={'Content-Type': 'application/json'})
            response = conn.getresponse()
            stopped = json.loads(response.read())
            assert response.status == 200 and stopped.get('ok') and stopped.get('frames', 0) >= 2, stopped
            mp4 = os.path.join(backend.DATA_DIR, 'video_sessions', started['id'] + '.mp4')
            assert os.path.isfile(mp4) and os.path.getsize(mp4) > 1024
            print(f'Angle {angle + 1}: PASS ({stopped["frames"]} frames, {stopped["size_bytes"]} bytes)')
            conn.close()
    finally:
        server.shutdown()
        server.server_close()

app = open(os.path.join(os.path.dirname(__file__), '..', 'src', 'app.js'), encoding='utf-8').read()
for token in ('enablePhotoMode', 'enableVideoMode', 'data-ui-screen="dashboard"', 'data-ui-screen="preview"', 'data-ui-screen="frame"', 'data-ui-screen="filter"', 'data-ui-screen="result"', 'showMultiPreview1', 'showMultiPreview2'):
    assert token in app, f'Missing UI feature: {token}'
print('KACA.ID v0.9.26 video and UI regression checks: PASS')
