"""HTTP print test with an intentionally mocked Windows print spooler."""
import base64, json, os, sys, tempfile, threading, urllib.request, urllib.error
from pathlib import Path
import numpy as np, cv2
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'backend'))
import camera_server as cs
from http.server import ThreadingHTTPServer

with tempfile.TemporaryDirectory(prefix='kaca-print-http-') as td:
 original_sessions=cs.SESSIONS_DIR
 cs.SESSIONS_DIR=td
 sid='1234abcdefaa'
 folder=Path(td)/sid;folder.mkdir()
 img=np.full((1100,800,3),(240,225,225),dtype=np.uint8)
 cv2.imwrite(str(folder/'output.jpg'),img)
 session={'id':sid,'created_at':'2026-11-10T08:00:00','status':'finished','drive_qr_enabled':True,'drive_qr_layout':{'x':.72,'y':.7,'w':.22,'h':.22}}
 cs.write_manifest(session)
 server=ThreadingHTTPServer(('127.0.0.1',0),cs.Handler)
 threading.Thread(target=server.serve_forever,daemon=True).start()
 url='http://127.0.0.1:'+str(server.server_port)+'/api/session/'+sid+'/print'
 def post():
  body=json.dumps({'printer_name':'Virtual Printer','paper_size':'4R','copies':3,'auto_print':True}).encode()
  req=urllib.request.Request(url,data=body,method='POST',headers={'Content-Type':'text/plain'})
  try:
   with urllib.request.urlopen(req,timeout=10) as reply:return reply.status,json.load(reply)
  except urllib.error.HTTPError as ex:return ex.code,json.load(ex)
 try:
  code,response=post()
  assert code==409 and 'QR' in response['error'],(code,response)
  session['drive_url']='https://drive.google.com/drive/folders/qr-test-2026'
  cs.write_manifest(session)
  import subprocess
  old_platform=sys.platform
  old_check=subprocess.check_output
  received=[]
  def fake_check(argv,**kwargs):
   payload=json.loads(base64.b64decode(kwargs['env']['KACA_PRINT_PAYLOAD']))
   received.append(payload)
   assert payload['image'].endswith('output_print_qr.jpg'),payload
   assert payload['copies']==3
   assert os.path.isfile(payload['image'])
   return 'PRINT_OK|Virtual Printer|4x6|3'
  subprocess.check_output=fake_check
  ps=Path(td)/'System32'/'WindowsPowerShell'/'v1.0'/'powershell.exe';ps.parent.mkdir(parents=True,exist_ok=True);ps.write_text('fake powershell')
  old_windir=os.environ.get('WINDIR');os.environ['WINDIR']=td
  sys.platform='win32'
  try:
   code,response=post()
   assert code==200 and response['ok'] and response['copies']==3,(code,response)
   code,response=post()
   assert code==200 and response.get('already_printed'),(code,response)
   assert len(received)==1,received
   assert cs.read_manifest(sid)['auto_print_completed'] is True
   print('PASS HTTP: QR required, printable JPG selected, 3 copies sent, auto print idempotent')
  finally:
   sys.platform=old_platform
   subprocess.check_output=old_check
   if old_windir is None: os.environ.pop('WINDIR',None)
   else: os.environ['WINDIR']=old_windir
 finally:
  server.shutdown();server.server_close();cs.SESSIONS_DIR=original_sessions
