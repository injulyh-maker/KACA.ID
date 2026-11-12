import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
server = (ROOT / 'backend' / 'camera_server.py').read_text(encoding='utf-8')
main = (ROOT / 'main.js').read_text(encoding='utf-8')

assert "'pid': os.getpid()" in server, 'health endpoint must expose backend process PID'
assert "'opencv': None" in server and "}, 503)" in server, 'health must fail when OpenCV is unavailable'
assert 'Found stale/incompatible KACA backend' in main and 'terminateBackendPid(existing.pid)' in main, 'Electron must replace an old backend instead of silently attaching to stale routes'
assert "'app_version': os.environ.get('KACA_APP_VERSION', '0.9.63')" in server and "'backend_protocol': int(os.environ.get('KACA_BACKEND_PROTOCOL', '3'))" in server, 'health must identify the exact backend build'
assert 'CAP_MSMF' in (ROOT / 'backend' / 'camera_probe.py').read_text(encoding='utf-8') and \
    "('DirectShow','MSMF')" in server, 'isolated camera scan must include Media Foundation fallback'
assert '[BACKEND_DIAGNOSTIC]' in server, 'backend must log active Python/OpenCV versions'
assert 'SCAN_ABORT' in server, 'camera scan must fail clearly if OpenCV cannot load'
print('camera backend health v0.9.48: PASS')
