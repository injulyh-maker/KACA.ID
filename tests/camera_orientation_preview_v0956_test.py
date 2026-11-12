from pathlib import Path
import ast

ROOT = Path(__file__).resolve().parents[1]
app = (ROOT / 'src' / 'app.js').read_text(encoding='utf-8')
css = (ROOT / 'src' / 'style.css').read_text(encoding='utf-8')
backend = (ROOT / 'backend' / 'camera_server.py').read_text(encoding='utf-8')
ast.parse(backend)

# Operator controls are persisted and passed into the session independently of preview controls.
for token in ('cameraRotation', 'cameraFlipHorizontal', 'cameraFlipVertical', 'saveCameraOrientation'):
    assert token in app
for token in ('livePreviewQuality', 'livePreviewBrightness', 'livePreviewFps', 'saveLivePreviewSettings'):
    assert token in app
assert 'camera_rotation:Number(settings.cameraRotation??0)' in app
assert 'camera_flip_horizontal:!!settings.cameraFlipHorizontal' in app
assert 'camera_flip_vertical:!!settings.cameraFlipVertical' in app
# Preview-only parameters are applied to MJPEG stream; brightness is a renderer CSS filter.
assert '&quality=${Number(settings.livePreviewQuality??76)}&fps=${Number(settings.livePreviewFps??15)}' in app
assert 'live.style.filter=`brightness(${Number(settings.livePreviewBrightness??100)}%)`' in app
assert "'brightness(${Number(settings.livePreviewBrightness??100)}%)'" not in backend
# Same orientation helper is used for still and Live Photo paths.
assert 'def _apply_camera_orientation(' in backend
assert 'frame = _apply_camera_orientation(frame, session.get(\'camera_rotation\'' in backend
assert 'shot_frame = _apply_camera_orientation(frame, shot_video_rotation' in backend
assert 'out=_apply_camera_orientation(frame, shot_video_rotation' in backend
# JPEG save path follows selected capture quality; preview quality never becomes a still-image setting.
assert "get('jpeg_quality',100)" in backend
assert 'PREVIEW_JPEG_QUALITY' in backend
# Filter preview must fit inside the column instead of rendering at the canvas's intrinsic dimensions.
assert 'max-width:84%!important;max-height:84%!important' in css
# Google Drive session upload uses the same local session folder; it does not independently recompress source files.
assert "google_drive.upload_session_folder(job['local_path']" in backend
print('KACA.ID v0.9.56 camera orientation, isolated preview controls, saved-image quality path, Drive source consistency and filter fit: PASS')
