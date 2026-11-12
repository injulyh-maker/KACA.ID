#!/usr/bin/env python3
"""Idempotent migration of the Android beta to the shared Windows design shell.
Run once from repository root (with Android source and Windows src/ present).
"""
from pathlib import Path
import xml.etree.ElementTree as ET
root=Path(__file__).resolve().parents[2]
java=root/'android-tablet/app/src/main/java/id/kaca/tablet/MainActivity.java'
if not java.is_file():raise SystemExit(f'Missing old Android beta source: {java}')
s=java.read_text(encoding='utf-8')
if 'public final class MainActivity' in s:s=s.replace('public final class MainActivity','public class MainActivity',1)
if 'Uri pendingCameraUri,frameUri,lastResultUri;' not in s:
    if 'Uri pendingCameraUri,frameUri;' not in s:raise SystemExit('MainActivity fields changed: check manually')
    s=s.replace('Uri pendingCameraUri,frameUri;','Uri pendingCameraUri,frameUri,lastResultUri;',1)
if 'lastResultUri=dest;' not in s:
    needle='if(dest==null)throw new IOException("Tidak dapat menyimpan hasil");'
    if needle not in s:raise SystemExit('Photo result output changed: inspect MainActivity')
    s=s.replace(needle,needle+'lastResultUri=dest;',1)
java.write_text(s,encoding='utf-8')

manifest=root/'android-tablet/app/src/main/AndroidManifest.xml'
ET.register_namespace('android','http://schemas.android.com/apk/res/android')
ns='{http://schemas.android.com/apk/res/android}'
tree=ET.parse(manifest);m=tree.getroot()
if not any(x.attrib.get(ns+'name')=='android.permission.CAMERA' for x in m.findall('uses-permission')):
    ET.SubElement(m,'uses-permission',{ns+'name':'android.permission.CAMERA'})
app=m.find('application')
old=next((a for a in app.findall('activity') if a.attrib.get(ns+'name')=='.MainActivity'),None)
if old is None:raise SystemExit('Manifest MainActivity not found')
old.attrib[ns+'exported']='false'
for filt in list(old.findall('intent-filter')):old.remove(filt)
new=next((a for a in app.findall('activity') if a.attrib.get(ns+'name')=='.TabletActivity'),None)
if new is None:new=ET.SubElement(app,'activity',{ns+'name':'.TabletActivity',ns+'exported':'true',ns+'screenOrientation':'unspecified'})
if not new.findall('intent-filter'):
    intent=ET.SubElement(new,'intent-filter')
    ET.SubElement(intent,'action',{ns+'name':'android.intent.action.MAIN'})
    ET.SubElement(intent,'category',{ns+'name':'android.intent.category.LAUNCHER'})
tree.write(manifest,encoding='utf-8',xml_declaration=True)

build=root/'android-tablet/app/build.gradle';b=build.read_text(encoding='utf8')
if 'androidx.webkit:webkit' not in b:
    b+='\n// Secure HTTPS-like loading of bundled Windows UI assets\ndependencies { implementation "androidx.webkit:webkit:1.12.1" }\n'
build.write_text(b,encoding='utf8')

wf=root/'.github/workflows/build-android-apk.yml';w=wf.read_text(encoding='utf8')
if 'prepare_windows_ui.py' not in w:
    anchor='      - name: Build APK for device testing\n'
    if anchor not in w:raise SystemExit('Workflow build step not found')
    w=w.replace(anchor,'      - name: Package identical Windows HTML and CSS for Android\n        run: python3 android-tablet/tools/prepare_windows_ui.py\n      - name: Verify Android UI JavaScript\n        run: node --check android-tablet/ui/android-ui.js\n'+anchor,1)
wf.write_text(w,encoding='utf8')

ignore=root/'.gitignore'
with ignore.open('a',encoding='utf8') as f:f.write('\n# Generated during Android build: Windows HTML/CSS bundled for WebView\nandroid-tablet/app/src/main/assets/www/\n')
print('Updated MainActivity, AndroidManifest, Gradle, workflow, gitignore. Ready to package shared Windows UI.')
