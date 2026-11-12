from pathlib import Path
import json
root=Path(__file__).parent
main=(root/'main.js').read_text(encoding='utf-8')
preload=(root/'preload.js').read_text(encoding='utf-8')
app=(root/'src/app.js').read_text(encoding='utf-8')
html=(root/'src/index.html').read_text(encoding='utf-8')
css=(root/'src/style.css').read_text(encoding='utf-8')
pkg=json.loads((root/'package.json').read_text(encoding='utf-8'))
assert pkg['version']=='0.9.46'
assert "window:fullscreen-toggle" in main and "win.setFullScreen(next)" in main
assert "input.key === 'F11'" in main and "input.key === 'Escape'" in main
assert "enter-full-screen" in main and "leave-full-screen" in main
assert "toggleFullscreen" in preload and "onFullscreenChange" in preload
assert 'id="fullscreenToggle"' in html
assert 'window.kaca.toggleFullscreen()' in app and 'window.kaca.isFullscreen()' in app
assert '.fullscreen-toggle' in css and 'z-index:10000' in css
for rel in ['app.js','style.css','index.html']:
 assert (root/'src'/rel).read_bytes()==(root/'src'/'src'/rel).read_bytes(), rel+' duplicate mismatch'
print('PASS: fullscreen button, F11, Escape, Electron fullscreen state, and duplicate source sync')
