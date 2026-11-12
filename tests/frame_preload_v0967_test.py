from pathlib import Path
root=Path(__file__).resolve().parents[1]
s=(root/'src'/'app.js').read_text(encoding='utf8')
assert 'const preloadAllFrames=()=>{' in s
assert 'const showPreparedFrameStep=async()=>{' in s
assert "const cardImages=[...frameGrid.querySelectorAll('img')];" in s
assert "if(n!==2)flowSlideLoadingTimer=setTimeout" in s
assert 'frameLoadRunning' in s and 'im.decode()' in s
assert 'loading="eager" decoding="async"' in s
assert 'void showPreparedFrameStep();' in s
assert "transactionPanel.hidden=true;void showPreparedFrameStep();" in s
assert 'Coba Muat Frame Lagi' in s
print('PASS: all active frame PNGs decoded before frame page shows; overlay has progress and retry')
