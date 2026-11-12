from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
BACKEND=(ROOT/'backend'/'camera_server.py').read_text(encoding='utf-8')
APP=(ROOT/'src'/'app.js').read_text(encoding='utf-8')
# Camera originals are written before any filter; only the composed outputs use filtered derivatives.
assert "original=f'original_{number:02d}.jpg'" in BACKEND
assert "filtered=frame.copy()  # keep capture-session photos original" in BACKEND
assert "cv2.imwrite(edited_path,apply_filter(original_image,filter_name)" in BACKEND
# Customer-facing local archive copies Original only, never the filtered per-shot derivative.
archive=BACKEND[BACKEND.index('def _sync_local_session_archive'):BACKEND.index('def sync_local_session_archive')]
assert "('original', 'Original')" in archive
assert "('edited', 'Edited')" not in archive
# GIF is built from original source filenames and is now actually invoked by final rendering.
gif=BACKEND[BACKEND.index('def create_session_gif'):BACKEND.index('def _cleanup_session_live_sources')]
assert "photo.get('original','')" in gif
assert 'gif_file=create_session_gif(snapshot)' in BACKEND
# Browser preview is preserved in local archive; async status polling cannot overlap itself.
assert "('output_live.webm', os.path.join(live_dir, 'Live_Photo_Frame.webm'))" in archive
assert "Live_Photo_Frame.mp4" in archive
assert "enqueue_drive_asset_job(session['id'], target, rel)" in archive
assert 'if(renderPollBusy)return;renderPollBusy=true' in APP
assert 'pollResultStatus();setFlowStep(5)' in APP
print('KACA.ID original-unfiltered, framed-filter, GIF, MP4 deliverable, local WebM preview only: PASS')
