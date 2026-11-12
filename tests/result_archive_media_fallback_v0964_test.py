from pathlib import Path
import ast
ROOT = Path(__file__).resolve().parents[1]
BACKEND = (ROOT / 'backend' / 'camera_server.py').read_text(encoding='utf-8')
APP = (ROOT / 'src' / 'app.js').read_text(encoding='utf-8')
ast.parse(BACKEND)
# The video endpoint must resolve both session-local and durable archive copies.
assert "'Live_Photos', 'Live_Photo_Frame.mp4'" in BACKEND
assert "'Live_Photos', 'Live_Photo_Frame.webm'" in BACKEND
assert "archive_dir and candidate.startswith(archive_dir + os.sep)" in BACKEND
assert "Video Live Photo belum tersedia di folder sesi maupun arsip lokal." in BACKEND
# render-status must report media found in either location, not just session preview dir.
assert 'def _live_asset_exists(name):' in BACKEND
assert 'live_master_ready=live_master in' in BACKEND
assert "_live_asset_exists(fallback_name)" in BACKEND
# QR status and endpoint both retain archive lookup, and the result UI always requests it.
assert "'Final_Results','QR_Google_Drive.png'" in BACKEND
assert "'drive_qr_archive_path'" in BACKEND
assert 'Always request the local QR endpoint' in APP
assert 'qrImage.src=`${base}/qr.png?local=${Date.now()}`' in APP
# Frontend uses logical endpoint filenames; backend maps those to archive files transparently.
assert "liveVideo.src=`${base}/${encodeURIComponent(chosenName)}?v=${Date.now()}`" in APP
print('KACA.ID v0.9.64 archive QR + Live Photo fallback source checks: PASS')
