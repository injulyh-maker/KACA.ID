"""v0.9.67 regression: webcam device probe failure cannot terminate the HTTP server."""
import sys,subprocess,json,os
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'backend'))
import camera_server as c
probe=(ROOT/'backend'/'camera_probe.py').read_text(encoding='utf8')
assert 'CAP_DSHOW' in probe and 'CAP_MSMF' in probe
assert 'subprocess.run(' in (ROOT/'backend'/'camera_server.py').read_text(encoding='utf8')
response='KACA_PROBE_RESULT='+json.dumps({'ok':True,'index':0,'width':640,'height':480})+'\n'
with patch.object(c.subprocess,'run',return_value=subprocess.CompletedProcess([],0,response)):
 assert c._probe_camera_isolated(0,'DirectShow')['width']==640
with patch.object(c.subprocess,'run',return_value=subprocess.CompletedProcess([],3221225477,'')):
 assert c._probe_camera_isolated(0,'DirectShow') is None
with patch.object(c.subprocess,'run',side_effect=subprocess.TimeoutExpired([],5)):
 assert c._probe_camera_isolated(0,'MSMF') is None
# Simulate several failed probes: the backend must still complete scan.
with patch.object(c,'_probe_camera_isolated',side_effect=lambda idx,back: {'ok':True,'index':idx,'width':640,'height':480} if idx==2 and back=='DirectShow' else None):
 with c.state_lock:c.state.update({'camera_open':False,'scan_running':True,'scan_done':False,'cameras':[],'selected':None})
 c.scan_worker()
 assert c.state['scan_done'] and not c.state['scan_running']
 assert any(cam['id']==2 for cam in c.state['cameras'])
print('PASS: isolated DirectShow/MSMF probe handles native crash, timeout and successful camera')
