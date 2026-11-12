from pathlib import Path
import os, sys, tempfile
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
APP = (ROOT / 'src' / 'app.js').read_text(encoding='utf-8')
SERVER = (ROOT / 'backend' / 'camera_server.py').read_text(encoding='utf-8')

# Settings screen must not wait for a fixed camera scan delay.
assert "await new Promise(r=>setTimeout(r,1800))" not in APP
assert 'Promise.all([' in APP and "api('/api/google-drive/status')" in APP and "api('/api/cameras')" in APP
assert 'let navigationGeneration=0;' in APP
assert 'if(pageGeneration!==navigationGeneration)return;' in APP

# Filter preview should use parallel low-resolution thumbnails, not original-resolution files.
assert 'Promise.all(list.map(photo=>loadImage' in APP
assert '/preview/${encodeURIComponent(photo.original)}' in APP
assert '/original/${photo.original}' not in APP[APP.index('const drawFilterReview=async()=>{'):APP.index('const renderFilterChoices=')]
assert 'filterPreviewRevision' in APP
assert "api('/api/session/prepare'" in APP and 'waitForPreparedPreview' in APP
assert "'/preview/' in path" in SERVER and 'PREVIEW_CACHE_DIR' in SERVER

# Exercise the thumbnail cache against a temporary full-resolution original.
sys.path.insert(0, str(ROOT / 'backend'))
import camera_server
with tempfile.TemporaryDirectory(prefix='kaca-v0955-thumb-') as temp:
    old_sessions, old_cache = camera_server.SESSIONS_DIR, camera_server.PREVIEW_CACHE_DIR
    try:
        camera_server.SESSIONS_DIR = os.path.join(temp, 'sessions')
        camera_server.PREVIEW_CACHE_DIR = os.path.join(temp, 'cache')
        os.makedirs(os.path.join(camera_server.SESSIONS_DIR, 'session-test'))
        os.makedirs(camera_server.PREVIEW_CACHE_DIR)
        source = os.path.join(camera_server.SESSIONS_DIR, 'session-test', 'original_01.jpg')
        Image.new('RGB', (2400, 1600), (80, 120, 160)).save(source, 'JPEG', quality=95)
        original_bytes = open(source, 'rb').read()
        thumb = camera_server._session_preview_thumbnail('session-test', 'original_01.jpg')
        assert thumb and os.path.isfile(thumb)
        with Image.open(thumb) as im:
            assert im.width <= 640 and im.height <= 480
        assert open(source, 'rb').read() == original_bytes, 'original photo must remain byte-identical'
        assert camera_server._session_preview_thumbnail('../bad', 'original_01.jpg') is None
    finally:
        camera_server.SESSIONS_DIR, camera_server.PREVIEW_CACHE_DIR = old_sessions, old_cache
print('KACA.ID v0.9.55 regression baseline, parallel thumbnail preview, original preservation and filter pre-render: PASS')
