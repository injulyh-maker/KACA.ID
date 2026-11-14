#!/usr/bin/env python3
"""Package the exact Windows operator HTML/CSS shell in the Android APK.

This does NOT port the Windows Python camera backend. The Android runtime
uses android-ui.js + its native bridge for its supported features.
"""
from pathlib import Path
import re, shutil, sys
repo=Path(__file__).resolve().parents[2]
web=repo/'src'
out=repo/'android-tablet/app/src/main/assets/www'
for rel in ('index.html','style.css'):
    if not (web/rel).is_file():raise SystemExit('Windows frontend missing: '+str(web/rel))
out.mkdir(parents=True,exist_ok=True)
html=(web/'index.html').read_text(encoding='utf-8')
html=re.sub(r'<meta http-equiv="Content-Security-Policy"[^>]*>', '',html,count=1)
html=html.replace('<body class="kaca-booting">','<body>')
html=html.replace('name="viewport" content="width=device-width,initial-scale=1"', 'name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover"')
html=html.replace('<script src="sounds.js"></script>','')
html=html.replace('<script src="app.js"></script>','<script src="android-ui.js"></script>')
if '<script src="android-ui.js"></script>' not in html:raise SystemExit('Unexpected Windows HTML: no app.js script entry')
html=html.replace('</head>','<link rel="stylesheet" href="android-ui.css"></head>',1)
# WebView only serves trusted bundled files, no remote scripts/iframes and no file URL access.
html=html.replace('<head>','<head><meta http-equiv="Content-Security-Policy" content="default-src \'self\'; script-src \'self\'; style-src \'self\' \'unsafe-inline\'; img-src \'self\' data: blob:; media-src \'self\' blob:; connect-src \'none\'; frame-src \'none\'; object-src \'none\'; base-uri \'self\';">',1)
(out/'index.html').write_text(html,encoding='utf-8')
shutil.copy2(web/'style.css',out/'style.css')
shutil.copy2(repo/'android-tablet/ui/android-ui.js',out/'android-ui.js')
shutil.copy2(repo/'android-tablet/ui/android-ui.css',out/'android-ui.css')
assets=web/'assets'; dst=out/'assets';dst.mkdir(exist_ok=True)
for f in assets.iterdir():
    if not f.is_file():continue
    # Never ship a booth operator's recordings, photo examples, or demo movie.
    if f.suffix.lower() in {'.mp4','.webm','.jpg','.jpeg','.gif'}:continue
    if f.name.startswith('dashboard-background'):continue
    if f.suffix.lower() in {'.svg','.png','.ico'}:shutil.copy2(f,dst/f.name)
print('Android UI bundled from',web)
print('HTML, CSS, sidebar/nav and branding match the Windows source.')
print('Unsupported Windows-only backend calls intentionally NOT bundled.')
