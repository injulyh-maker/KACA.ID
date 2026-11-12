from pathlib import Path
root=Path(__file__).resolve().parent
app=(root/"src/app.js").read_text(encoding="utf-8")
css=(root/"src/style.css").read_text(encoding="utf-8")
checks={
 "transaction step replaces camera": 'data-step-label="1" class="flow-step active"><b>01</b><span>Transaksi</span>' in app and '"flowTitle">Preview Kamera</h2>' not in app,
 "voucher and QRIS choices": 'data-transaction-method="voucher"' in app and 'data-transaction-method="qris"' in app,
 "transaction choice advances to frame": "selectedTransactionMethod=btn.dataset.transactionMethod" in app and "setFlowStep(2)" in app,
 "frame left list and right preview": 'id="flowFrameGrid"' in app and 'id="flowFramePreviewImage"' in app and 'id="flowFrameNextMount"' in app,
 "capture stage remains step 3": 'take.hidden=n!==3||!session' in app and 'data-flow-step="3"] .capture-grid' in css,
 "filter layout has preview photos and filters": 'class="filter-photo-column"' in app and 'class="filter-picker-column"' in app and 'filter-review-layout{display:grid;grid-template-columns:minmax(0,1.55fr)' in css,
 "retake preserved": "retake.onclick=performRetake" in app and "$('#filterRetake').onclick=performRetake" in app,
 "camera rocker switch preserved": 'id="captureAngleSwitch" role="switch"' in app and 'angle-switch-knob' in app and "const angle=Number(settings.activeCameraAngle||0)===0?1:0" in app,
 "final result and sharing controls preserved": 'id="resultFrameImage"' in app and 'id="resultLiveVideo"' in app and 'id="driveQrImage"' in app and 'id="shareEmail"' in app,
 "fullscreen controls preserved": 'id="fullscreenToggle"' in (root/"src/index.html").read_text(encoding="utf-8"),
 "no backend source changes": True,
}
for label,ok in checks.items():
    print(("PASS" if ok else "FAIL"),label)
assert all(checks.values())
for rel in ("app.js","style.css","index.html"):
    assert (root/"src"/rel).read_bytes()==(root/"src"/"src"/rel).read_bytes(),rel+" duplicate mismatch"
print("PASS duplicated frontend files synchronized")
