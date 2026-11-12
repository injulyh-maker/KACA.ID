import os
from pathlib import Path
import json
root=Path(__file__).resolve().parents[1]
main=(root/'main.js').read_text(encoding='utf-8')
server=(root/'backend/camera_server.py').read_text(encoding='utf-8')
pkg=json.loads((root/'package.json').read_text(encoding='utf-8'))
setup=(root/'setup-runtime.bat').read_text(encoding='utf-8')
nsis=(root/'build/nsis-installer.nsh').read_text(encoding='utf-8')
assert 'requestSingleInstanceLock' in main
assert 'Found stale/incompatible KACA backend' in main and 'terminateBackendPid(existing.pid)' in main
assert 'backend_protocol===3' in main and 'health.pid!==backend.pid' in main
assert 'process.resourcesPath' in main and "'python','python.exe'" in main
assert "'app_version': os.environ.get('KACA_APP_VERSION', '0.9.63')" in server and "'backend_protocol': int(os.environ.get('KACA_BACKEND_PROTOCOL', '3'))" in server
assert 'PYVER=3.13.17' in setup and 'pip install' in setup
assert 'vc_redist.x64.exe' in setup and 'vc_redist.x64.exe' in nsis
assert any(x.get('to')=='python' for x in pkg['build']['extraResources'])
assert pkg['version']=='0.9.63'
print('KACA.ID v0.9.56 runtime packaging and backend lifecycle: PASS')
