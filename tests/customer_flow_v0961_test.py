from pathlib import Path
import json
root=Path(__file__).resolve().parents[1]
app=(root/'src/app.js').read_text(encoding='utf-8')
css=(root/'src/style.css').read_text(encoding='utf-8')
main=(root/'main.js').read_text(encoding='utf-8')
backend=(root/'backend/camera_server.py').read_text(encoding='utf-8')
pkg=json.loads((root/'package.json').read_text())
assert 'const ensureCaptureCamera=async()=>{if(captureCameraReady)return;' in app
assert 'captureGridParking.appendChild(captureGrid)' in app and 'root.appendChild(captureGrid)' in app
assert app.index('const $cap=id=>captureGrid.querySelector(id)') < app.index("$cap('#flowStart').onclick") < app.index("$('#flowFrameNext').onclick")
assert 'await ensureCaptureCamera();' in app
assert "#content.photo-session-content[data-flow-step=\"1\"] .capture-grid" in css
assert "#content.photo-session-content[data-flow-step=\"2\"] .capture-grid" in css
assert 'const mirrorToggleEl=captureGrid.querySelector' in app
assert "$cap('#mirrorButton')" in app and "$cap('#flowStart')" in app
assert 'mirrorToggleEl.disabled=busy' in app and "$('#mirrorToggle').disabled" not in app
assert "start.dataset.lastError=e.message" in app
assert "id=\"flowFrameStatus\"" in app
assert 'voucher-virtual-keyboard' in app and 'data-voucher-action="backspace"' in app
assert "existing.backend_protocol===3" in main and "health.backend_protocol===3" in main
assert "KACA_BACKEND_PROTOCOL:'3'" in main
assert "'backend_protocol': int(os.environ.get('KACA_BACKEND_PROTOCOL', '3'))" in backend
assert pkg['version']=='0.9.63'
for p in [root/'src/src/app.js',root/'src_nested/app.js',root/'src_unpacked/app.js']:
    assert p.read_text(encoding='utf-8')==app
for p in [root/'src/src/style.css',root/'src_nested/style.css',root/'src_unpacked/style.css']:
    assert p.read_text(encoding='utf-8')==css
print('KACA.ID v0.9.61 transaction/capture isolation, lazy camera init, frame start guard, voucher keyboard and backend protocol: PASS')
