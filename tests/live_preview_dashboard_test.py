from pathlib import Path
import ast, importlib.util, sys, tempfile
import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
backend_path = ROOT / 'backend' / 'camera_server.py'
source = backend_path.read_text(encoding='utf-8')
ast.parse(source)
app = (ROOT / 'src' / 'app.js').read_text(encoding='utf-8')
assert "'live_output_preview':live_preview if live_preview_ready else None" in source
assert 'threading.Thread(target=_make_preview_async' in source
assert 'preview_pending' in source
assert 'const previewName=String(st.live_output_preview||' in app
assert 'liveVideo.src=`${base}/${encodeURIComponent(chosenName)}?v=${Date.now()}`' in app
assert 'resultDeadline=Date.now()' in app
assert 'resultTimer=setInterval(updateResultCountdown,250)' in app
assert 'Always request the local QR endpoint' in app
assert "'drive_qr_error':manifest.get('drive_qr_error')" in source
assert "const returnToDashboard=()=>" in app
assert 'if(left<=0)returnToDashboard();' in app
assert "go('dashboard')" in app
assert 'startFilterLiveCanvas' not in app
assert 'filterPreviewLive' not in app

# Verify this OpenCV build can create and read the browser-preview companion.
spec = importlib.util.spec_from_file_location('kaca_live_preview_test_backend', backend_path)
mod = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = mod
spec.loader.exec_module(mod)
tmp = Path(tempfile.mkdtemp(prefix='kaca-live-preview-'))
mp4 = tmp / 'sample.mp4'
writer = cv2.VideoWriter(str(mp4), cv2.VideoWriter_fourcc(*'mp4v'), 10.0, (320, 240))
assert writer.isOpened(), 'MP4 writer unavailable'
for i in range(30):
    writer.write(np.full((240, 320, 3), (i * 5 % 255, 90, 170), dtype=np.uint8))
writer.release()
preview = mod.create_full_quality_browser_preview(str(mp4))
assert preview == 'sample.webm', preview
preview_path = tmp / preview
assert preview_path.is_file() and preview_path.stat().st_size > 1000
cap = cv2.VideoCapture(str(preview_path))
ok, frame = cap.read()
count = cap.get(cv2.CAP_PROP_FRAME_COUNT)
cap.release()
assert ok and frame is not None and count >= 2, (ok, count)
print('Live Photo WebM preview generation, render-status exposure, and dashboard return: PASS')
