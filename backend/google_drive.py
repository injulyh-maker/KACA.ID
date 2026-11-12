"""Google Drive OAuth and resumable upload helper for KACA.ID.
Uses only Python standard library so the camera backend does not need extra packages.
"""
import json, os, time, secrets, urllib.parse, urllib.request, urllib.error, mimetypes, re

AUTH_ENDPOINT = 'https://accounts.google.com/o/oauth2/v2/auth'
TOKEN_ENDPOINT = 'https://oauth2.googleapis.com/token'
API_ROOT = 'https://www.googleapis.com/drive/v3'
UPLOAD_ROOT = 'https://www.googleapis.com/upload/drive/v3'
REDIRECT_URI = 'http://127.0.0.1:8765/api/google-drive/callback'
SCOPES = 'https://www.googleapis.com/auth/drive.file'
FOLDER_MIME = 'application/vnd.google-apps.folder'

class GoogleDriveManager:
    def __init__(self, data_dir):
        self.data_dir = data_dir
        self.config_path = os.path.join(data_dir, 'google-drive-config.json')
        self._state = None
        os.makedirs(data_dir, exist_ok=True)

    def _read(self):
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f: return json.load(f)
        except Exception: return {}

    def _write(self, value):
        tmp = self.config_path + '.tmp'
        with open(tmp, 'w', encoding='utf-8') as f: json.dump(value, f, ensure_ascii=False, indent=2)
        os.replace(tmp, self.config_path)

    def configure(self, client_id, client_secret):
        client_id = str(client_id or '').strip()
        client_secret = str(client_secret or '').strip()
        cfg = self._read()
        if not client_secret and client_id == cfg.get('client_id'):
            client_secret = str(cfg.get('client_secret') or '')
        if not client_id or not client_secret:
            raise ValueError('Client ID dan Client Secret Google OAuth wajib diisi. Client Secret dapat dikosongkan jika sebelumnya sudah tersimpan untuk Client ID yang sama.')
        if cfg.get('client_id') != client_id or cfg.get('client_secret') != client_secret:
            for key in ('access_token','refresh_token','expires_at','account_email','root_folder_id'):
                cfg.pop(key, None)
        cfg.update({'client_id': client_id, 'client_secret': client_secret})
        self._write(cfg)
        return self.status()

    def status(self):
        cfg = self._read()
        connected = bool(cfg.get('refresh_token') or (cfg.get('access_token') and float(cfg.get('expires_at', 0)) > time.time()+60))
        return {'configured': bool(cfg.get('client_id') and cfg.get('client_secret')), 'connected': connected,
                'client_id': cfg.get('client_id'), 'account_email': cfg.get('account_email'), 'root_folder_id': cfg.get('root_folder_id')}

    def auth_url(self):
        cfg = self._read()
        if not cfg.get('client_id') or not cfg.get('client_secret'):
            raise ValueError('Simpan Client ID dan Client Secret terlebih dahulu.')
        state = secrets.token_urlsafe(24)
        cfg['oauth_state'] = state
        self._write(cfg)
        query = urllib.parse.urlencode({'client_id': cfg['client_id'], 'redirect_uri': REDIRECT_URI,
            'response_type': 'code', 'scope': SCOPES, 'access_type': 'offline', 'prompt': 'consent',
            'include_granted_scopes': 'true', 'state': state})
        return AUTH_ENDPOINT + '?' + query

    def callback(self, query):
        cfg = self._read()
        if query.get('error'):
            raise RuntimeError('Google menolak otorisasi: ' + str(query.get('error')))
        if not query.get('state') or not secrets.compare_digest(str(query.get('state')), str(cfg.get('oauth_state') or '')):
            raise RuntimeError('State OAuth tidak cocok. Ulangi proses hubungkan Google Drive.')
        code = query.get('code')
        if not code: raise RuntimeError('Google tidak mengirim authorization code.')
        body = urllib.parse.urlencode({'code': code, 'client_id': cfg['client_id'], 'client_secret': cfg['client_secret'],
            'redirect_uri': REDIRECT_URI, 'grant_type': 'authorization_code'}).encode()
        data = self._url_json(TOKEN_ENDPOINT, body=body, headers={'Content-Type':'application/x-www-form-urlencoded'})
        cfg.update({'access_token': data.get('access_token'), 'refresh_token': data.get('refresh_token') or cfg.get('refresh_token'),
                    'expires_at': time.time()+int(data.get('expires_in', 3600)), 'token_type': data.get('token_type','Bearer'), 'oauth_state': None})
        self._write(cfg)
        try:
            about=self._api('GET','/about',params={'fields':'user(emailAddress)'})
            cfg['account_email']=about.get('user',{}).get('emailAddress');self._write(cfg)
        except Exception: pass
        return True

    def disconnect(self):
        cfg = self._read()
        for key in ('access_token','refresh_token','expires_at','account_email','oauth_state'):
            cfg.pop(key, None)
        self._write(cfg)
        return self.status()

    def _url_json(self, url, body=None, headers=None, method=None):
        req = urllib.request.Request(url, data=body, headers=headers or {}, method=method)
        try:
            with urllib.request.urlopen(req, timeout=90) as res:
                raw = res.read()
                return json.loads(raw.decode('utf-8')) if raw else {}
        except urllib.error.HTTPError as exc:
            raw = exc.read().decode('utf-8', 'replace')
            try: detail = json.loads(raw).get('error', {}).get('message', raw)
            except Exception: detail = raw
            raise RuntimeError(f'Google Drive API HTTP {exc.code}: {detail}')

    def _token(self):
        cfg = self._read()
        if not cfg.get('client_id') or not cfg.get('client_secret'):
            raise RuntimeError('Google Drive belum dikonfigurasi. Isi OAuth Client ID dan Client Secret.')
        if cfg.get('access_token') and float(cfg.get('expires_at',0)) > time.time()+90:
            return cfg['access_token']
        if not cfg.get('refresh_token'):
            raise RuntimeError('Google Drive belum terhubung. Hubungkan akun Google terlebih dahulu.')
        body = urllib.parse.urlencode({'client_id':cfg['client_id'],'client_secret':cfg['client_secret'],
            'refresh_token':cfg['refresh_token'],'grant_type':'refresh_token'}).encode()
        data = self._url_json(TOKEN_ENDPOINT, body=body, headers={'Content-Type':'application/x-www-form-urlencoded'})
        cfg['access_token'] = data['access_token']; cfg['expires_at'] = time.time()+int(data.get('expires_in',3600)); self._write(cfg)
        return cfg['access_token']

    def _api(self, method, path, payload=None, params=None):
        token = self._token()
        url = API_ROOT + path
        if params: url += '?' + urllib.parse.urlencode(params)
        body = json.dumps(payload).encode() if payload is not None else None
        headers = {'Authorization':'Bearer '+token}
        if body is not None: headers['Content-Type']='application/json; charset=UTF-8'
        return self._url_json(url, body=body, headers=headers, method=method)

    def _find_folder(self, name, parent_id=None):
        q = "mimeType='%s' and name='%s' and trashed=false" % (FOLDER_MIME, name.replace("'", "\\'"))
        if parent_id: q += " and '%s' in parents" % parent_id
        result = self._api('GET','/files',params={'q':q,'pageSize':100,'fields':'files(id,name,webViewLink)'})
        return result.get('files',[{}])[0] if result.get('files') else None

    def ensure_folder(self, name, parent_id=None):
        found = self._find_folder(name,parent_id)
        if found: return found['id']
        meta = {'name':name,'mimeType':FOLDER_MIME}
        if parent_id: meta['parents']=[parent_id]
        return self._api('POST','/files',payload=meta,params={'fields':'id,name,webViewLink'})['id']

    def ensure_root(self):
        cfg = self._read()
        root_id = cfg.get('root_folder_id')
        if root_id:
            try:
                self._api('GET','/files/'+root_id,params={'fields':'id,name,trashed'})
                return root_id
            except Exception: pass
        root_id = self.ensure_folder('KACA STUDIO')
        cfg['root_folder_id'] = root_id; self._write(cfg)
        return root_id

    def _upload_resumable(self, path, parent_id):
        token = self._token(); name = os.path.basename(path); size = os.path.getsize(path)
        mime = mimetypes.guess_type(name)[0] or 'application/octet-stream'
        existing=self._api('GET','/files',params={'q':"name='%s' and '%s' in parents and trashed=false"%(name.replace("'","\\'"),parent_id),'pageSize':10,'fields':'files(id,name)'})
        existing_id=(existing.get('files') or [{}])[0].get('id')
        metadata = json.dumps({'name':name, **({'parents':[parent_id]} if not existing_id else {})}).encode()
        if existing_id:
            upload_endpoint=UPLOAD_ROOT+'/files/'+existing_id+'?uploadType=resumable&fields=id,name,webViewLink,size'
            upload_method='PATCH'
        else:
            upload_endpoint=UPLOAD_ROOT+'/files?uploadType=resumable&fields=id,name,webViewLink,size'
            upload_method='POST'
        req = urllib.request.Request(upload_endpoint, data=metadata,
            headers={'Authorization':'Bearer '+token,'Content-Type':'application/json; charset=UTF-8','X-Upload-Content-Type':mime,'X-Upload-Content-Length':str(size)}, method=upload_method)
        try:
            with urllib.request.urlopen(req, timeout=90) as res: upload_url = res.headers.get('Location')
        except urllib.error.HTTPError as exc: raise RuntimeError('Gagal memulai upload Google Drive: '+exc.read().decode('utf-8','replace'))
        if not upload_url: raise RuntimeError('Google Drive tidak memberikan URL upload resumable.')
        chunk_size = 8*1024*1024
        with open(path,'rb') as f:
            offset=0
            while offset<size:
                chunk=f.read(min(chunk_size,size-offset)); end=offset+len(chunk)-1
                put=urllib.request.Request(upload_url,data=chunk,headers={'Content-Type':mime,'Content-Length':str(len(chunk)),'Content-Range':f'bytes {offset}-{end}/{size}'},method='PUT')
                try:
                    with urllib.request.urlopen(put,timeout=180) as res:
                        result=json.loads(res.read().decode('utf-8')) if res.readable() else {}
                        if result.get('id'): return result
                except urllib.error.HTTPError as exc:
                    if exc.code==308:
                        rng=exc.headers.get('Range','')
                        offset=int(rng.split('-')[-1])+1 if rng else end+1
                        f.seek(offset)
                        continue
                    raise RuntimeError(f'Upload Google Drive gagal HTTP {exc.code}: '+exc.read().decode('utf-8','replace'))
                offset=end+1
        return self._api('GET','/files',params={'q':"name='%s' and '%s' in parents and trashed=false"%(name.replace("'","\\'"),parent_id),'pageSize':10,'fields':'files(id,name,webViewLink,size)'}).get('files',[{}])[0]

    def event_parent_folder(self, event_id):
        """Events have their own stable Drive namespace. The user QR points to a
        single session folder, never to the entire event with other guests.
        """
        root = self.ensure_root()
        event_id = str(event_id or '').strip().lower()
        if not event_id:
            return root
        if not re.fullmatch(r'[a-f0-9]{16}', event_id):
            raise ValueError('ID event Google Drive tidak valid.')
        events = self.ensure_folder('Events', root)
        return self.ensure_folder('Event_' + event_id, events)

    def create_session_folder(self, folder_name, event_id=None):
        """Provision an isolated customer folder and the standard child folders."""
        root = self.event_parent_folder(event_id)
        session_id = self.ensure_folder(folder_name, root)
        subfolders = {}
        for sub in ('Photos', 'Live_Photos', 'Final_Results', 'Video_Results'):
            subfolders[sub] = self.ensure_folder(sub, session_id)
        share_warning = None
        try:
            permissions = self._api('GET', f'/files/{session_id}/permissions',
                                    params={'fields': 'permissions(id,type,role)'})
            already_public = any(p.get('type') == 'anyone' and p.get('role') == 'reader'
                                 for p in permissions.get('permissions', []))
            if not already_public:
                self._api('POST', f'/files/{session_id}/permissions',
                          payload={'type': 'anyone', 'role': 'reader'})
        except Exception as exc:
            share_warning = str(exc)
            print('[GOOGLE_DRIVE_SHARE_WARNING]', repr(exc), flush=True)
        return {'folder_id': session_id,
                'url': f'https://drive.google.com/drive/folders/{session_id}',
                'subfolders': subfolders, 'share_warning': share_warning}

    def trash_session_folder(self, folder_id, event_id=None):
        """Move only a KACA session folder to Drive Trash (recoverable).

        Both its parent and MIME type are verified before any mutation. The KACA
        root, Events root, and Event roots can never pass this check.
        """
        import re
        folder_id = str(folder_id or '')
        if not re.fullmatch(r'[A-Za-z0-9_-]{8,200}', folder_id):
            raise ValueError('ID folder Drive tidak valid.')
        expected_parent = self.event_parent_folder(event_id)
        if folder_id == expected_parent:
            raise ValueError('Tidak boleh menghapus folder utama KACA/Event.')
        entry = self._api('GET', '/files/' + folder_id,
                          params={'fields': 'id,name,mimeType,parents,trashed'})
        if entry.get('trashed'):
            return {'trashed': True, 'already_trashed': True}
        if entry.get('mimeType') != FOLDER_MIME or expected_parent not in (entry.get('parents') or []):
            raise ValueError('Folder bukan sesi yang berada langsung di bawah KACA/Event.')
        updated = self._api('PATCH', '/files/' + folder_id, payload={'trashed': True},
                            params={'fields': 'id,trashed'})
        if updated.get('trashed') is not True:
            raise RuntimeError('Google Drive belum mengonfirmasi folder masuk Sampah.')
        return {'trashed': True}

    def upload_session_asset(self, local_file, folder_id, relative_path):
        """Upload one completed local session asset immediately, preserving its folder."""
        if not os.path.isfile(local_file):
            raise RuntimeError('File lokal belum tersedia: ' + str(local_file))
        rel = os.path.normpath(str(relative_path)).replace('\\', '/')
        parts = [part for part in rel.split('/') if part and part not in ('.', '..')]
        if not parts:
            raise RuntimeError('Lokasi file sesi tidak valid.')
        filename = parts[-1]
        # Browser-only WebM previews stay on this PC; only the MP4 master is uploaded.
        if filename.lower().endswith('.webm'):
            return {'skipped': True, 'reason': 'local_preview_only'}
        parent_id = folder_id
        for folder_name in parts[:-1]:
            parent_id = self.ensure_folder(folder_name, parent_id)
        result = self._upload_resumable(local_file, parent_id)
        return {'file_id': result.get('id'), 'name': filename, 'relative_path': rel}

    def upload_session_folder(self, local_folder, folder_name, folder_id=None):
        if not os.path.isdir(local_folder):
            raise RuntimeError('Folder arsip lokal tidak ditemukan: ' + str(local_folder))
        prepared = self.create_session_folder(folder_name) if not folder_id else None
        session_id = folder_id or prepared['folder_id']
        subfolders = {}
        for sub in ('Photos', 'Live_Photos', 'Final_Results', 'Video_Results'):
            local_sub = os.path.join(local_folder, sub)
            if os.path.isdir(local_sub):
                subfolders[sub] = self.ensure_folder(sub, session_id)
        share_warning = prepared.get('share_warning') if prepared else None
        for base, dirs, files in os.walk(local_folder):
            dirs[:] = [d for d in dirs if d not in ('.tmp',)]
            rel = os.path.relpath(base, local_folder)
            parent = session_id if rel == '.' else subfolders.get(rel.split(os.sep)[0], session_id)
            for filename in files:
                lower_name = filename.lower()
                # ZIP bundles and internal session metadata stay local; never publish them to Drive.
                if lower_name.endswith(('.tmp', '.zip')) or lower_name == 'session_info.json':
                    continue
                self._upload_resumable(os.path.join(base, filename), parent)
        return {'folder_id': session_id,
                'url': f'https://drive.google.com/drive/folders/{session_id}',
                'share_warning': share_warning}

    def create_video_folder(self, folder_name, event_id=None):
        root=self.event_parent_folder(event_id)
        folder=self.ensure_folder(folder_name,root)
        self.ensure_folder('Video_Results',folder)
        share_warning=None
        try:self._api('POST',f'/files/{folder}/permissions',payload={'type':'anyone','role':'reader'})
        except Exception as exc:
            share_warning=str(exc);print('[GOOGLE_DRIVE_SHARE_WARNING]',repr(exc),flush=True)
        return {'folder_id':folder,'url':f'https://drive.google.com/drive/folders/{folder}',
                'share_warning':share_warning}

    def upload_video(self, local_file, folder_name, event_id=None, folder_id=None):
        if not os.path.isfile(local_file): raise RuntimeError('File video lokal tidak ditemukan.')
        prepared=self.create_video_folder(folder_name,event_id) if not folder_id else None
        folder=folder_id or prepared['folder_id']
        video_folder=self.ensure_folder('Video_Results',folder)
        share_warning=prepared.get('share_warning') if prepared else None
        result=self._upload_resumable(local_file, video_folder)
        sidecar=os.path.splitext(local_file)[0]+'.json'
        if os.path.isfile(sidecar): self._upload_resumable(sidecar,video_folder)
        return {'folder_id':folder,'url':f'https://drive.google.com/drive/folders/{folder}','file_id':result.get('id'),'share_warning':share_warning}
