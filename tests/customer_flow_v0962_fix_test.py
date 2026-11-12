from pathlib import Path
import json
ROOT=Path(__file__).resolve().parents[1]
APP=(ROOT/'src/app.js').read_text(encoding='utf-8')
CSS=(ROOT/'src/style.css').read_text(encoding='utf-8')
PKG=json.loads((ROOT/'package.json').read_text(encoding='utf-8'))
assert PKG['version']=='0.9.63'
assert 'const finished=await finish.onclick();if(finished!==true)' in APP
flow=APP[APP.index("$('#flowFilterNext').onclick=async()=>"):APP.index("$cap('#flowCaptureStart').hidden=true")]
assert 'await waitForPreparedPreview()' not in flow
assert 'if(finalizedSessionId)' in APP and 'setFlowStep(5);return true;' in APP
assert 'frameNextButton.disabled=!chosenFrameId||!activeFrameList.length' in APP
assert 'frameNextButton.disabled=!chosenFrameId||!activeFrameList.length||!!session' in APP
assert 'transform:translateY(clamp(22px,5vh,64px))!important' in CSS
for rel in ['src/src/app.js','src_nested/app.js','src_unpacked/app.js']:
 assert (ROOT/rel).read_text(encoding='utf-8')==APP
for rel in ['src/src/style.css','src_nested/style.css','src_unpacked/style.css']:
 assert (ROOT/rel).read_text(encoding='utf-8')==CSS
print('KACA.ID v0.9.63 non-blocking result flow, error propagation, frame button state and transaction positioning: PASS')
