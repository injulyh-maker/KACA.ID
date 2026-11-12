"""Fail the release if preloaded booth photos, frames or promo movies leak into installer."""
from pathlib import Path
import json
root=Path(__file__).resolve().parent.parent
assert not (root/'src/assets/dashboard-background.mp4').exists(),'Bundled dashboard promotional movie detected'
assert not list((root/'src/assets').glob('*.mp4')),'Unexpected video defaults in assets'
assert not list((root/'src/assets').glob('*.webm')),'Unexpected video defaults in assets'
assert not list((root/'src/assets').glob('*.jpg')),'Unexpected customer photo defaults'
assert not list((root/'src/assets').glob('*.jpeg')),'Unexpected customer photo defaults'
assert not list((root/'src/assets').glob('frame*')),'Unexpected frame defaults'
app=(root/'src/app.js').read_text('utf8')
assert "const bg=settings.dashboardVideo||''" in app
assert 'id="flowResultSkip"' in app
assert 'if(actions)actions.hidden=false;' in app, 'Skip result button must be visible while waiting for Live Photo'
assert "license:['#licenseStatus'" in app, 'License page must not require unrelated #save button'
assert 'await window.kaca.assertCloudLicense();' in app
assert 'function renderLicense()' in app
agent=(root/'cloud_control/agent.js').read_text('utf8')
assert 'config.required=true;' in agent
assert "DEFAULT_CLOUD_ORIGIN='https://kacastudio.id'" in agent
pkg=json.loads((root/'package.json').read_text())
assert pkg['version']=='0.9.90'
assert all('dashboard-background.mp4' not in f or f.startswith('!') for f in pkg['build']['files'])
print('[PASS] No promo video/frames, desktop license gate, offline agent, skip loading, cloud origin.')
