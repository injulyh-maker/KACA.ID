import os, sys, tempfile, importlib.util, json, threading, urllib.request, time, types
from pathlib import Path
from http.server import ThreadingHTTPServer
import cv2, numpy as np
ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("kaca_smoke_backend", ROOT / "backend" / "camera_server.py")
mod = importlib.util.module_from_spec(spec); sys.modules[spec.name] = mod; spec.loader.exec_module(mod)
tmp = Path(tempfile.mkdtemp(prefix="kaca-id-smoke-"))
mod.SESSIONS_DIR = str(tmp / "sessions"); mod.FRAMES_DIR = str(tmp / "frames")
Path(mod.SESSIONS_DIR).mkdir(); Path(mod.FRAMES_DIR).mkdir()
sid = "smoke1234567890"; folder = Path(mod.SESSIONS_DIR) / sid; folder.mkdir()
cv2.imwrite(str(folder / "p1.jpg"), np.full((100, 100, 3), (0, 0, 220), np.uint8))
cv2.imwrite(str(folder / "p2.jpg"), np.full((100, 100, 3), (220, 0, 0), np.uint8))
layout = [dict(x=0,y=0,w=.3,h=1,photo_index=0), dict(x=.3,y=0,w=.3,h=1,photo_index=0), dict(x=.6,y=0,w=.4,h=1,photo_index=1)]
session = dict(id=sid, photos=[dict(number=1,edited="p1.jpg"),dict(number=2,edited="p2.jpg")], layout_slots=layout, frame_id=None, paper_size="4R", settings=dict(orientation="landscape",jpegQuality=95,print_dpi=300))
resolved = mod._layout_slots(session, 3, 1800, 1200)
assert [slot[4] for slot in resolved] == [0,0,1], resolved
out = mod.compose_output(session, mark_finished=False); image = cv2.imread(out)
assert image is not None and image.shape[:2] == (1200,1800)
assert np.array_equal(image[600,270], image[600,810]) and not np.array_equal(image[600,270], image[600,1440])
# Verify the runtime local-storage folder API and session metadata output.
server = ThreadingHTTPServer(("127.0.0.1", 0), mod.Handler)
threading.Thread(target=server.serve_forever, daemon=True).start()
selected_root = tmp / "selected-output"
request = urllib.request.Request(f"http://127.0.0.1:{server.server_address[1]}/api/storage/location", data=json.dumps({"path": str(selected_root)}).encode(), headers={"Content-Type": "application/json"}, method="POST")
with urllib.request.urlopen(request, timeout=5) as response: storage_result = json.loads(response.read())
assert storage_result["ok"] and Path(storage_result["path"]) == selected_root
server.shutdown(); server.server_close()
session["created_at"] = "2026-11-06T10:00:00"
archive = Path(mod.create_local_session_archive(session)); mod._sync_local_session_archive(session, final=True)
assert (archive / "Photos").is_dir() and (archive / "Live_Photos").is_dir() and (archive / "Final_Results").is_dir()
assert (archive / "Session_Info.json").is_file() and (archive / "KACA-ID-Hasil-Sesi.zip").is_file()
# Exercise the same duplicate-source mapping through the framed Live Photo renderer.
for number, color in ((1, (0, 0, 220)), (2, (220, 0, 0))):
    writer = cv2.VideoWriter(str(folder / f"live{number}.mp4"), cv2.VideoWriter_fourcc(*"mp4v"), 8.0, (160, 120))
    assert writer.isOpened(), "MP4 VideoWriter unavailable in this environment"
    for _ in range(40): writer.write(np.full((120, 160, 3), color, np.uint8))
    writer.release()
session["photos"][0]["live_photo"] = "live1.mp4"; session["photos"][1]["live_photo"] = "live2.mp4"
session["live_photo_enabled"] = True; session["live_photo_duration_seconds"] = 5; session["filter"] = "original"
session["settings"]["video_quality"] = "compact"
assert mod.compose_live_output(session, session["photos"]) == "output_live.mp4"
live_path = folder / "output_live.mp4"
assert live_path.is_file() and live_path.stat().st_size > 1000
cap = cv2.VideoCapture(str(live_path)); ok, frame = cap.read(); cap.release()
assert ok and frame is not None
# Exercise standalone VIDEO mode recorder and local Video_Results archive.
mod.DATA_DIR = str(tmp / "data")
mod.LOCAL_ARCHIVE_ROOT = str(selected_root)
Path(mod.DATA_DIR).mkdir(parents=True, exist_ok=True)
video_start = mod.start_booth_video(np.zeros((120, 160, 3), np.uint8))
assert video_start["ok"]
for i in range(24):
    mod.publish_frame(np.full((120, 160, 3), i * 8, np.uint8))
    time.sleep(0.055)
video_result = mod.stop_booth_video()
assert video_result["ok"] and video_result["frames"] >= 20
assert Path(video_result["local_path"]).is_file()
# Exercise MultiCam Canon Angle 2 lifecycle with a fake EDSDK controller.
class FakeCanonController:
    def __init__(self, on_frame, camera_index=0): self.on_frame=on_frame; self.active=True
    def start(self):
        ok, jpg = cv2.imencode('.jpg', np.full((60, 80, 3), 120, np.uint8)); self.on_frame(jpg.tobytes())
        return {"ok":True,"name":"Fake Canon","width":80,"height":60}
    def take_picture(self): return {"ok":True,"captured":True}
    def stop(self): self.active=False; return True
    def status(self): return {"active":self.active}
fake_module=types.ModuleType("canon_edsdk_live"); fake_module.CanonLiveView=FakeCanonController
old_module=sys.modules.get("canon_edsdk_live"); sys.modules["canon_edsdk_live"]=fake_module
mod.state.update({"backend":"OpenCV","camera_open":True,"selected":1})
secondary=mod.open_secondary_canon_camera("canon_edsdk_0")
assert secondary.get("ok") and mod.latest_secondary_frame is not None
assert mod.canon_secondary_controller.take_picture().get("captured")
assert mod.close_secondary_camera() is True and mod.latest_secondary_frame is None
if old_module is None: sys.modules.pop("canon_edsdk_live",None)
else: sys.modules["canon_edsdk_live"]=old_module
print("KACA.ID smoke test: PASS — duplicate slots, local archive, standalone MP4 recording, and MultiCam Canon worker lifecycle (mock)")
