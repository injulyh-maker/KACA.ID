from pathlib import Path
root=Path(__file__).resolve().parents[1]
app=(root/'src/app.js').read_text()
css=(root/'src/style.css').read_text()
main=(root/'main.js').read_text()
backend=(root/'backend/camera_server.py').read_text()
assert 'Tanpa frame PNG</b>' not in app
assert 'data-frame-id=""' not in app
assert 'aria-label="Pilih frame"' in app
assert 'flowFramePreviewName' not in app and 'flowFrameAutoInfo' not in app and 'flowFrameNotice' not in app
assert 'if(!chosenFrameId)' in app
assert 'state.still_ready||state.render_status===\'ready\'' in app
assert 'Live Photo dan upload Google Drive dilanjutkan di latar belakang.' in app
assert 'drive_qr_available' in backend and 'still_ready' in backend
assert 'Reusing matching KACA backend' in main
assert 'Found stale/incompatible KACA backend' in main and 'backend_protocol===3' in main
assert 'flow-frame-preview-name' in css and 'object-fit:contain!important' in css
for p in [root/'src/src/app.js',root/'src_nested/app.js']:
    assert p.read_text()==app
for p in [root/'src/src/style.css',root/'src_nested/style.css']:
    assert p.read_text()==css
print('KACA.ID v0.9.49 frame picker, contained result preview, early still render, QR and backend reuse: PASS')
