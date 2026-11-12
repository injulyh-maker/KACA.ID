from pathlib import Path
import ast

ROOT = Path(__file__).resolve().parents[1]
source = (ROOT / 'backend' / 'camera_server.py').read_text(encoding='utf-8')
ast.parse(source)
assert 'PREVIEW_MAIN_MAX_FPS = 15.0' in source
assert 'PREVIEW_SECONDARY_MAX_FPS = 10.0' in source
assert 'PREVIEW_JPEG_QUALITY = 76' in source
assert 'def _get_preview_jpeg(secondary=False, quality=PREVIEW_JPEG_QUALITY):' in source
assert 'def _encode_preview_jpeg(frame, quality=PREVIEW_JPEG_QUALITY):' in source
assert 'Lazily encode the newest frame from a stream client, never on the capture thread.' in source
assert 'def _get_preview_jpeg(secondary=False, quality=PREVIEW_JPEG_QUALITY):' in source
# Preview HTTP handlers consume the shared JPEG cache; they must not encode once per client.
main_handler = source.split("if path == '/api/stream.mjpg':", 1)[1].split("if path.startswith('/api/session/')", 1)[0]
assert '_get_preview_jpeg(secondary=False, quality=stream_quality)' in main_handler
assert 'cv2.imencode' not in main_handler
secondary_handler = source.split("if path == '/api/stream-secondary.mjpg':", 1)[1].split("if path == '/api/stream.mjpg':", 1)[0]
assert '_get_preview_jpeg(secondary=True, quality=stream_quality)' in secondary_handler
assert 'cv2.imencode' not in secondary_handler
# Capture path continues to publish full-resolution source frames; resize is isolated to preview encoder.
assert 'latest_frame = frame.copy()' in source
assert 'cv2.resize(frame, (max(1,int(w*scale)), max(1,int(h*scale)))' in source
assert '_encode_preview_jpeg(frame, q)' in source
assert 'stream_fps = max(5.0, min(30.0' in source
assert 'stream_quality = max(40, min(95' in source
print('Low-memory preview cache, FPS caps, and full-resolution capture separation: PASS')
