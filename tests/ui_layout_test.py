from pathlib import Path

root = Path(__file__).resolve().parents[1]
app = (root / "src/app.js").read_text(encoding="utf-8")
css = (root / "src/style.css").read_text(encoding="utf-8")

assert "result-download-panel" not in app[app.find("$('#finishedResult').innerHTML="):app.find("$('#printSession').onclick")]
assert 'id="driveQrImage"' in app and 'id="shareWhatsApp"' in app and 'id="shareEmail"' in app and 'id="printSession"' in app
assert 'id="driveQrEnabled"' in app and 'id="editorDriveQr"' in app and 'settings.driveQrLayouts' in app
assert 'editor-drive-qr' in css and 'drive_qr_enabled' in app and 'drive_qr_layout' in app
assert "const performRetake=async()=>" in app and "$('#filterRetake').onclick=performRetake" in app
assert "id=\"filterRetake\"" in app
assert "preview-mirror-button" in app and "id=\"mirrorButton\"" in app
assert "countdown-corner" in app and "inset: 12px auto auto 12px" in css
assert "const c=settings.uiDesignerApplied?.[screen]?.[key]" in app
assert "actions:'.photo-session-content[data-flow-step=\"5\"] .result-share-controls'" in app
assert "actions:'.photo-session-content[data-flow-step=\"4\"] #filterNextMount'" in app
assert "settings.uiDesignerApplied||settings.uiDesigner||{}" not in app
assert "data-flow-step=\"3\"] #captureGrid" in css
assert "data-flow-step=\"4\"] #flowFilterPanel" in css
assert "data-flow-step=\"5\"] .drive-qr-card" in css
print("KACA.ID customer UI layout and draft/apply isolation tests: PASS")
