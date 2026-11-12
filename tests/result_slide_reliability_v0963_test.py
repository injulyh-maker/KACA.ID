from pathlib import Path
import ast
ROOT=Path(__file__).resolve().parents[1]
APP=(ROOT/'src'/'app.js').read_text(encoding='utf-8')
CSS=(ROOT/'src'/'style.css').read_text(encoding='utf-8')
BACKEND=(ROOT/'backend'/'camera_server.py').read_text(encoding='utf-8')
ast.parse(BACKEND)
# Countdown starts on entry to the result slide and does not wait for local render, Live Photo, QR, or Drive upload.
html=APP.index("id=\"resultReturnCountdown\"")
timer=APP.index('resultTimer=setInterval(updateResultCountdown,250)')
share=APP.index("$('#printSession').onclick=async()=>", html)
assert html < timer < share
assert 'resultCountdownStarted=true;resultDeadline=Date.now()+resultCountdownSeconds*1000' in APP
assert "Countdown slide akhir mulai tepat ketika slide dibuka" in APP
assert "renderPoll=setInterval(pollResultStatus,1500);pollResultStatus();setFlowStep(5);maybeStartResultCountdown();return true;" in APP
assert "'live_photo_enabled':bool(manifest.get('live_photo_enabled'))" in BACKEND
assert 'Math.ceil((resultDeadline-Date.now())/1000)' in APP
# QR image is requested whenever Drive URL exists; backend can lazily generate the QR.
assert 'Always request the local QR endpoint' in APP and 'drive_qr_archive_path' in BACKEND
assert 'v0.9.44-compatible QR serving' in BACKEND and 'drive_qr_archive_path' in BACKEND
assert 'st.live_output_available||st.live_output||st.live_output_preview_available' in APP
assert "Persist the session's Google Drive QR locally" in BACKEND
# Live Photo preview uses WebM when present and MP4 master as fallback.
assert 'const previewName=String(st.live_output_preview||' in APP
assert 'liveVideo.onloadeddata=' in APP and 'liveVideo.onerror=' in APP
assert "'drive_qr_error':manifest.get('drive_qr_error')" in BACKEND
assert 'finishNowButton.onclick=(ev)=>' in APP
assert 'let resultLeaving=false' in APP
assert "Promise.resolve(go('dashboard')).catch" in APP
# Hidden video must remain hidden until a live clip is ready, even under kiosk CSS overrides.
assert '.result-slide>video[hidden]{display:none!important' in CSS
print('KACA.ID result slide countdown, QR fallback, and Live Photo playback guards: PASS')
