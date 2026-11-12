import os
from pathlib import Path
import json
root=Path(__file__).resolve().parents[1]
app=(root/'src/app.js').read_text(encoding='utf-8')
main=(root/'main.js').read_text(encoding='utf-8')
server=(root/'backend/camera_server.py').read_text(encoding='utf-8')
pkg=json.loads((root/'package.json').read_text(encoding='utf-8'))
nsis=(root/'build/nsis-installer.nsh').read_text(encoding='utf-8')
assert "headers={Accept:'application/json'" in app
assert "text/plain;charset=UTF-8" in app
assert "Content-Type':'application/json'" not in app
assert 'Access-Control-Allow-Origin' in server and 'Access-Control-Allow-Private-Network' in server
assert 'requestSingleInstanceLock' in main and 'backend_protocol===3' in main
assert "require('net')" in main and 'function isPortInUse()' in main and 'await isPortInUse()' in main
assert "process.platform === 'win32' && app.isPackaged" in main and 'if(!selectedPython) throw new Error' in main
assert "'app_version': os.environ.get('KACA_APP_VERSION', '0.9.63')" in server
assert pkg['version']=='0.9.63'
assert any(x.get('to')=='python' for x in pkg['build']['extraResources'])
assert any(x.get('to')=='vc_redist.x64.exe' for x in pkg['build']['extraResources'])
assert 'LogicLib.nsh' in nsis and 'vc_redist.x64.exe' in nsis and '/install /quiet /norestart' in nsis
print('KACA.ID v0.9.56 API CORS and runtime packaging: PASS')
