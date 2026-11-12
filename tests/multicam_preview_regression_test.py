from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
backend = (ROOT / "backend" / "camera_server.py").read_text(encoding="utf-8")
app = (ROOT / "src" / "app.js").read_text(encoding="utf-8")
css = (ROOT / "src" / "style.css").read_text(encoding="utf-8")

assert "OpenCV (reuse)" in backend, "secondary OpenCV camera reuse guard missing"
assert "'reused': True" in backend, "secondary camera idempotency response missing"
assert "requested_angle == 1" in backend, "session start does not validate selected camera angle"
assert "filterPreviewLive" not in app, "Filter slide should not initialize Live Photo decoding"
assert '<video id="resultLiveVideo" autoplay muted loop playsinline' in app, "Result Live Photo autoplay missing"
assert '<video id="resultLiveVideo" controls' not in app, "Result Live Photo native controls must remain hidden"
assert ".result-slide>video{pointer-events:none!important" in css, "Result video must ignore touch/click controls"
assert "bottom:12px" in css and "preview-angle-switch" in css, "angle switch bottom placement missing"
assert "max-height:248px" in css, "photo slot picker height extension missing"
print("MultiCam reuse, angle validation, Live Photo autoplay and layout regression checks: PASS")
