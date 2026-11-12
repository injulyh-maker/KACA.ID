"""Static CI preflight, usable from Linux and Windows without downloading tools."""
from pathlib import Path
from PIL import Image
import json
import re
import subprocess

ROOT = Path(__file__).resolve().parent.parent
pkg = json.loads((ROOT/'package.json').read_text(encoding='utf-8'))
assert pkg['version'] == '0.9.90'
assert pkg['main'] == 'main.js'
assert pkg['build']['asar'] is False
assert pkg['build']['nsis']['perMachine'] is True
assert pkg['build']['nsis']['oneClick'] is False
assert pkg['build']['win']['target'][0]['arch'] == ['x64']
resource_by_target = {x['to']: x['from'] for x in pkg['build']['extraResources']}
assert resource_by_target['python'] == 'runtime/python'
assert resource_by_target['vc_redist.x64.exe'] == 'runtime/vc_redist.x64.exe'
assert resource_by_target['runtime-build-complete.json'] == 'runtime/runtime-build-complete.json'
assert (ROOT/'backend/edsdk/SDK_Package/EDSDK/api.cp312-win_amd64.pyd').exists()
assert (ROOT/'backend/edsdk/EDSDK.dll').exists()
assert (ROOT/'build/icon.ico').exists()
with Image.open(ROOT/'build/icon.ico') as im:
    assert im.size in ((256,256),(128,128)), im.size
nsis = (ROOT/'build/nsis-installer.nsh').read_text(encoding='utf-8')
assert '$INSTDIR\\resources\\vc_redist.x64.exe' in nsis
assert '$INSTDIR\\resources\\python\\python.exe' in nsis
assert 'ExecWait' in nsis and '3010' in nsis and '1638' in nsis
assert 'Abort' in nsis
ps = (ROOT/'build/prepare-windows-runtime.ps1').read_text(encoding='utf-8')
assert '3.12.10' in ps
assert 'python312._pth' in ps
assert 'Get-AuthenticodeSignature' in ps
assert 'cloud_control\\requirements.txt' in ps
assert 'requirements.txt' in ps
workflow=(ROOT/'.github/workflows/build-windows-installer.yml').read_text(encoding='utf-8')
assert 'runs-on: windows-2022' in workflow
assert 'actions/upload-artifact@v4' in workflow
assert 'prepare-windows-runtime.ps1' in workflow
main=(ROOT/'main.js').read_text(encoding='utf-8')
assert "path.join(process.resourcesPath || root,'python','python.exe')" in main
assert "if (process.platform === 'win32' && app.isPackaged) return null;" in main
for file in ('main.js', 'preload.js', 'src/app.js'):
    subprocess.run(['node','--check',str(ROOT/file)],check=True)
print('[PASS] electron-builder Windows x64 NSIS config, bundled CPython/VC++, Canon cp312, branded icon, Electron launcher, build workflow')
