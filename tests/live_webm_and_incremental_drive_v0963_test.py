from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
BACKEND=(ROOT/'backend'/'camera_server.py').read_text(encoding='utf-8')
DRIVE=(ROOT/'backend'/'google_drive.py').read_text(encoding='utf-8')
APP=(ROOT/'src'/'app.js').read_text(encoding='utf-8')
archive=BACKEND[BACKEND.index('def _sync_local_session_archive'):BACKEND.index('def sync_local_session_archive')]
assert "('output_live.webm', os.path.join(live_dir, 'Live_Photo_Frame.webm'))" in archive
assert "enqueue_drive_asset_job(session['id'], target, rel)" in archive
assert "enqueue_drive_asset_job(session['id'], dst, 'Photos/' + os.path.basename(dst))" in archive
assert "def upload_session_asset(self, local_file, folder_id, relative_path):" in DRIVE
assert "if filename.lower().endswith('.webm')" in DRIVE
assert "drive_upload_manifest_complete" in BACKEND
assert "latest_manifest = read_manifest(session_id) or {}" in BACKEND
cleanup=BACKEND[BACKEND.index("if path.startswith('/api/session/') and path.endswith('/cleanup-previews')"):BACKEND.index("if path == '/api/session/finish'")]
assert "manifest.get('live_output_preview')" not in cleanup
assert "webm_persisted':True" in cleanup
assert "output_live.webm" in APP
assert "qr.png?local=" in APP and 'Always request the local QR endpoint' in APP
print('KACA.ID local WebM persistence, no Drive WebM, incremental per-file Drive uploads, QR URL polling: PASS')
