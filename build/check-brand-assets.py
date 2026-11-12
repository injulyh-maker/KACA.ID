# Branding smoke test; requires only Python standard library on GitHub Actions.
from pathlib import Path
import json,struct
R=Path(__file__).resolve().parent.parent
x=json.loads((R/'package.json').read_text('utf8'))
assert x['version']=='0.9.90'
assert x['build']['win']['icon']=='build/icon.ico'
assert x['build']['nsis']['installerIcon']=='build/icon.ico'
assert x['build']['nsis']['uninstallerIcon']=='build/icon.ico'
assert x['build']['nsis']['installerHeaderIcon']=='build/icon.ico'
ico=(R/'build/icon.ico').read_bytes()
reserved,kind,count=struct.unpack_from('<HHH',ico,0)
assert (reserved,kind)==(0,1) and count>=7,(reserved,kind,count)
sizes=set()
for i in range(count):
    w,h,colors,rsv,planes,bpp,amount,offset=struct.unpack_from('<BBBBHHII',ico,6+16*i)
    side=256 if w==0 else w
    assert side==(256 if h==0 else h)
    assert amount>40 and offset+amount<=len(ico)
    sizes.add(side)
assert {16,24,32,48,64,128,256}<=sizes,sizes
for p in ['build/icon.png','src/assets/kaca-loading-brand.png','cloud_control/web/favicon.ico',
          'cloud_control/web/favicon-32.png','cloud_control/web/logo-kaca-192.png',
          'cloud_control/web/apple-touch-icon.png']:
    assert (R/p).is_file(),p
main=(R/'main.js').read_text('utf8')
assert "icon:KACA_APP_ICON" in main
html=(R/'cloud_control/web/index.html').read_text('utf8')
assert html.count('src="/static/logo-kaca-192.png"')==2
assert '/static/favicon.ico' in html
print('BRANDING CHECK PASSED: Windows ICO 7 sizes, NSIS, Electron, Cloud favicon/login/sidebar, splash')
