from pathlib import Path
root=Path(__file__).resolve().parents[1]
css=(root/'src/style.css').read_text(encoding='utf-8')
checks={
 'full-screen navy session canvas':'body.photo-session-mode #content.photo-session-content' in css and '#080548' in css,
 'customer headers hidden':'body.photo-session-mode .photo-flow-head,body.photo-session-mode .photo-flow-steps' in css,
 'transaction slide centered':'#flowTransactionPanel .transaction-method-options' in css,
 'frame gallery left and preview right':'#flowFramePanel .flow-frame-layout' in css,
 'camera slide large preview':'#content[data-flow-step="3"] .capture-preview' in css,
 'shutter round red button':'#content[data-flow-step="3"] #takePhoto' in css,
 'camera switch bottom left':'#content[data-flow-step="3"] .preview-angle-switch' in css,
 'mirror bottom right':'#content[data-flow-step="3"] .preview-icon-button.preview-mirror-button' in css,
 'retake on photo tray right':'#content[data-flow-step="3"] #retakePhoto' in css,
 'filter three-column layout':'#flowFilterPanel .filter-review-layout' in css,
 'result QR panel':'#content[data-flow-step="5"] .drive-qr-card' in css,
 'result share and print controls':'#content[data-flow-step="5"] .result-share-controls .actions' in css,
}
for name,ok in checks.items(): print(('PASS' if ok else 'FAIL'),name)
assert all(checks.values())
for rel in ('app.js','style.css','index.html'):
 a=(root/'src'/rel).read_bytes(); b=(root/'src'/'src'/rel).read_bytes()
 assert a==b, f'nested src duplicate mismatch: {rel}'
 if rel!='index.html':
  c=(root/'src_nested'/rel).read_bytes(); assert a==c, f'src_nested mismatch: {rel}'
print('PASS synchronized UI copies')
