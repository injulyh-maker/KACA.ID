from pathlib import Path
import re
ROOT = Path(__file__).resolve().parents[1]
backend = (ROOT / 'backend' / 'camera_server.py').read_text(encoding='utf-8')
app = (ROOT / 'src' / 'app.js').read_text(encoding='utf-8')
# Capture finalization must dispatch WebM conversion asynchronously, not wait for it.
stop = backend.split('def stop_shot_live_photo', 1)[1].split('def compose_live_output', 1)[0]
assert 'threading.Thread(target=_make_preview_async' in stop
assert 'preview_pending' in stop
assert 'preview_name = create_full_quality_browser_preview(path)' not in stop
# The filter page is intentionally static-only to reduce CPU and decoder load.
assert 'filterPreviewCanvas' in app
assert 'filterPreviewLive' not in app
assert 'filterPreviewLiveVideo' not in app
assert 'startFilterLiveCanvas' not in app
# The result-page Live Photo has autoplay/loop but no native play/pause controls.
assert '<video id="resultLiveVideo" autoplay muted loop playsinline' in app
assert '<video id="resultLiveVideo" controls' not in app
css = (ROOT / 'src' / 'style.css').read_text(encoding='utf-8')
assert '.result-slide>video{pointer-events:none!important' in css
print('PASS: background Live Photo preview conversion; filter slide static-only; result Live Photo autoplay without controls')
