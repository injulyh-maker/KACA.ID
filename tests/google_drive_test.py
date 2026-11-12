import os, sys, tempfile, urllib.parse, json, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))
from google_drive import GoogleDriveManager

with tempfile.TemporaryDirectory(prefix='kaca-drive-test-') as temp:
    drive=GoogleDriveManager(temp)
    st=drive.configure('desktop-client-id.apps.googleusercontent.com','desktop-client-secret')
    assert st['configured'] and not st['connected']
    drive.configure('desktop-client-id.apps.googleusercontent.com','')
    assert drive._read().get('client_secret')=='desktop-client-secret'
    url=drive.auth_url(); parsed=urllib.parse.urlparse(url); q=urllib.parse.parse_qs(parsed.query)
    assert parsed.hostname=='accounts.google.com'
    assert q['redirect_uri'][0]=='http://127.0.0.1:8765/api/google-drive/callback'
    assert q['access_type'][0]=='offline' and 'drive.file' in q['scope'][0]
    cfg=drive._read(); state=cfg['oauth_state']
    def fake_url_json(url, body=None, headers=None, method=None):
        if url.startswith('https://oauth2.googleapis.com/token'):
            return {'access_token':'test-access-token','refresh_token':'test-refresh-token','expires_in':3600,'token_type':'Bearer'}
        if '/about?' in url:
            return {'user':{'emailAddress':'booth@example.com'}}
        return {}
    drive._url_json=fake_url_json
    drive.callback({'state':state,'code':'test-authorization-code'})
    st=drive.status()
    assert st['connected'] and st['account_email']=='booth@example.com'
    drive.disconnect()
    assert not drive.status()['connected'] and drive.status()['configured']
print('Google Drive OAuth configuration and state-flow tests: PASS (network OAuth not performed)')

# Exercise folder creation and resumable upload without network access.
from unittest.mock import patch
class FakeResponse:
    def __init__(self, headers=None, body=b'{}'):
        self.headers=headers or {}; self._body=body
    def __enter__(self): return self
    def __exit__(self,*args): return False
    def read(self): return self._body
    def readable(self): return True

with tempfile.TemporaryDirectory(prefix='kaca-drive-upload-test-') as temp:
    drive=GoogleDriveManager(temp)
    drive.configure('client.apps.googleusercontent.com','secret')
    cfg=drive._read();cfg.update({'access_token':'access','expires_at':time.time()+3600});drive._write(cfg)
    created=[]
    def fake_api(method,path,payload=None,params=None):
        if method=='GET' and path=='/files': return {'files':[]}
        if method=='POST' and path=='/files':
            item={'id':'folder-'+str(len(created)+1),'name':(payload or {}).get('name')};created.append(item);return item
        if method=='POST' and path.endswith('/permissions'): return {'id':'permission'}
        if method=='GET' and path.startswith('/files/'): return {'id':path.rsplit('/',1)[-1],'name':'KACA STUDIO'}
        return {}
    calls=[]
    def fake_urlopen(req,timeout=90):
        calls.append(req)
        if req.method in ('POST','PATCH'):
            return FakeResponse({'Location':'https://upload.example/session/1'})
        if req.method=='PUT':
            return FakeResponse({},json.dumps({'id':'uploaded-file','name':'asset.jpg'}).encode())
        raise AssertionError(req.method)
    drive._api=fake_api
    root=tempfile.mkdtemp(prefix='kaca-drive-session-')
    os.makedirs(os.path.join(root,'Photos'));os.makedirs(os.path.join(root,'Final_Results'))
    with open(os.path.join(root,'Photos','asset.jpg'),'wb') as f:f.write(b'photo-bytes')
    with open(os.path.join(root,'Session_Info.json'),'w') as f:f.write('{}')
    with open(os.path.join(root,'KACA-ID-Hasil-Sesi.zip'),'wb') as f:f.write(b'zip-local-only')
    uploaded_names=[]; original_upload=drive._upload_resumable
    def tracked_upload(path,parent_id):
        uploaded_names.append(os.path.basename(path)); return original_upload(path,parent_id)
    drive._upload_resumable=tracked_upload
    with patch('urllib.request.urlopen',fake_urlopen):
        result=drive.upload_session_folder(root,'Sesi_20261107_001')
    assert result['url'].startswith('https://drive.google.com/drive/folders/')
    assert any(c.method=='PUT' for c in calls) and len([c for c in calls if c.method=='POST'])>=1
    assert 'asset.jpg' in uploaded_names and 'Session_Info.json' not in uploaded_names and 'KACA-ID-Hasil-Sesi.zip' not in uploaded_names, uploaded_names
    print('Google Drive folder hierarchy and resumable upload tests: PASS (mock HTTP)')
