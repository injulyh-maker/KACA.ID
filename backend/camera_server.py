import json, threading, time, sys, traceback, os, uuid, datetime, re, base64, zipfile, copy, shutil, queue, subprocess, hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, unquote, parse_qs
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from google_drive import GoogleDriveManager
from session_retention import SessionRetention
from whatsapp_cloud import WhatsAppCloudManager, normalize_whatsapp_number
from doku_qris import DokuQris
from whatsapp_gateway import FonnteGateway

try:
    import cv2
except Exception as exc:
    print('CAMERA_BACKEND_IMPORT_ERROR:', repr(exc), flush=True)
    cv2 = None

HOST, PORT = '127.0.0.1', 8765
state_lock = threading.RLock()
capture_lock = threading.RLock()
state = {
    'scan_running': False, 'scan_done': False, 'cameras': [], 'selected': None,
    'camera_open': False, 'error': None, 'backend': 'OpenCV',
    'frames_read': 0, 'read_failures': 0, 'frame_width': 0, 'frame_height': 0,
    'last_frame_time': None, 'reader_alive': False, 'last_read_error': None,
    'frame_mean': None, 'frame_min': None, 'frame_max': None,
    'scan_stage': 'idle', 'scan_started_at': None, 'scan_duration_ms': 0
}
cap = None
canon_controller = None
canon_lifecycle_lock = threading.RLock()
canon_secondary_controller = None
canon_secondary_lock = threading.RLock()
latest_frame = None
secondary_cap = None
secondary_selected_index = None
latest_secondary_frame = None
secondary_thread = None
stop_secondary_reader = threading.Event()
secondary_lock = threading.RLock()
active_camera_angle = 0
shot_video_source = 0
frame_id = 0
frame_condition = threading.Condition()
# Shared bounded JPEG cache: encode each preview frame once and fan it out to all clients.
preview_cache_lock = threading.RLock()
preview_jpeg_main = None
preview_jpeg_main_id = 0
preview_jpeg_secondary = None
preview_jpeg_secondary_id = 0
preview_encoded_main_source_id = -1
preview_encoded_secondary_source_id = -1
secondary_frame_id = 0
PREVIEW_MAIN_MAX_FPS = 15.0
PREVIEW_SECONDARY_MAX_FPS = 10.0
PREVIEW_JPEG_QUALITY = 76
preview_encoded_main_quality = PREVIEW_JPEG_QUALITY
preview_encoded_secondary_quality = PREVIEW_JPEG_QUALITY
reader_thread = None
stop_reader = threading.Event()
video_lock = threading.RLock()
session_video_writer = None
session_video_path = None
session_video_id = None
session_video_last_write = 0.0
booth_video_writer = None
booth_video_id = None
booth_video_path = None
booth_video_last_write = 0.0
booth_video_frames = 0
booth_video_started_at = None
booth_video_event_id = None
booth_video_event_name = None
booth_video_frame_id = None
booth_video_frame_overlay = None
booth_video_mirror = False
booth_video_rotation = 0
booth_video_flip_horizontal = False
booth_video_flip_vertical = False
video_preview_errors = {}
booth_video_source = 0
shot_video_writer = None  # retained for backward-compatible shutdown paths
shot_video_path = None
shot_video_session_id = None
shot_video_number = None
shot_video_started_at = None
shot_video_last_write = 0.0
shot_video_frame_count = 0
shot_video_codec = None
shot_video_last_result = {'frames': 0, 'duration': 0.0, 'codec': None, 'size_bytes': 0}
shot_video_frames = []  # sampled, resized frames collected only during the selected countdown
shot_video_sampled_at = 0.0
shot_video_target_seconds = 5
shot_video_mirror = False
shot_video_rotation = 0
shot_video_flip_horizontal = False
shot_video_flip_vertical = False
shot_video_fps = 30.0
shot_video_width = 0
shot_video_height = 0
video_test_writer = None
video_test_path = None
video_test_started = None
video_test_frames = 0
video_test_fps = 30.0
video_test_width = 0
video_test_height = 0
video_test_passed = False
render_jobs = {}
render_jobs_lock = threading.RLock()


# Local photobooth session storage. Electron supplies a writable per-user data directory.
DATA_DIR = os.environ.get('KACA_DATA_DIR', os.path.join(os.path.dirname(__file__), '..', 'data'))
SESSIONS_DIR = os.path.join(DATA_DIR, 'sessions')
FRAMES_DIR = os.path.join(DATA_DIR, 'frames')
PREVIEW_CACHE_DIR = os.path.join(DATA_DIR, 'preview-cache')
os.makedirs(SESSIONS_DIR, exist_ok=True)
os.makedirs(FRAMES_DIR, exist_ok=True)
os.makedirs(PREVIEW_CACHE_DIR, exist_ok=True)


def _session_preview_thumbnail(session_id, filename):
    # Return a cached low-resolution preview without modifying the original photo.
    if not session_id.replace('-', '').isalnum() or not re.fullmatch(r'original_\d+\.jpg', filename):
        return None
    source = os.path.join(SESSIONS_DIR, session_id, filename)
    if not os.path.isfile(source):
        return None
    try:
        stat = os.stat(source)
        cache_name = f'{session_id}_{filename}_{stat.st_size}_{stat.st_mtime_ns}.jpg'
        target = os.path.join(PREVIEW_CACHE_DIR, cache_name)
        if not os.path.isfile(target):
            from PIL import Image
            with Image.open(source) as image:
                image.thumbnail((640, 480), Image.Resampling.LANCZOS)
                temp = target + '.tmp'
                image.convert('RGB').save(temp, 'JPEG', quality=72, optimize=True)
                os.replace(temp, target)
        return target if os.path.isfile(target) else None
    except Exception as exc:
        print('[PREVIEW_THUMBNAIL_ERROR]', repr(exc), flush=True)
        return None

active_session = None
session_lock = threading.RLock()

def session_manifest(session_id):
    folder = os.path.join(SESSIONS_DIR, session_id)
    return folder, os.path.join(folder, 'session.json')

def read_manifest(session_id):
    folder, manifest_path = session_manifest(session_id)
    if not os.path.isfile(manifest_path):
        return None
    with open(manifest_path, 'r', encoding='utf-8') as f:
        raw = f.read()
    try:
        value = json.loads(raw)
        return value if isinstance(value, dict) else None
    except json.JSONDecodeError as original_error:
        # Some older/retried writes left consecutive JSON objects in session.json.
        # Recover the newest fields instead of making all session endpoints fail.
        decoder = json.JSONDecoder()
        objects = []
        offset = 0
        while offset < len(raw):
            while offset < len(raw) and raw[offset].isspace():
                offset += 1
            if offset >= len(raw):
                break
            try:
                item, end = decoder.raw_decode(raw, offset)
            except json.JSONDecodeError:
                break
            if isinstance(item, dict):
                objects.append(item)
            offset = end
        if not objects:
            print('[GOOGLE_DRIVE_MANIFEST_RECOVERY_FAILED]', session_id, repr(original_error), flush=True)
            raise original_error
        # Keep earlier fields and allow later JSON objects to override them.
        recovered = {}
        for item in objects:
            recovered.update(item)
        try:
            backup_path = manifest_path + '.corrupt-backup'
            if not os.path.exists(backup_path):
                with open(backup_path, 'w', encoding='utf-8') as backup:
                    backup.write(raw)
            temp = manifest_path + '.recovered.tmp'
            with open(temp, 'w', encoding='utf-8') as output:
                json.dump(recovered, output, ensure_ascii=False, indent=2)
            os.replace(temp, manifest_path)
            print('[GOOGLE_DRIVE_MANIFEST_RECOVERED]', session_id, 'objects='+str(len(objects)), flush=True)
        except OSError as recovery_write_error:
            print('[GOOGLE_DRIVE_MANIFEST_RECOVERY_WRITE_WARNING]', session_id, repr(recovery_write_error), flush=True)
        return recovered

def write_manifest(session):
    folder, manifest_path = session_manifest(session['id'])
    os.makedirs(folder, exist_ok=True)
    temp = manifest_path + '.tmp'
    with open(temp, 'w', encoding='utf-8') as f:
        json.dump(session, f, ensure_ascii=False, indent=2)
    os.replace(temp, manifest_path)

DEFAULT_LOCAL_ARCHIVE_ROOT = os.path.abspath(os.environ.get('KACA_DEFAULT_ARCHIVE_DIR') or os.path.join(os.path.expanduser('~'), 'Pictures', 'KACA STUDIO'))
LOCAL_ARCHIVE_ROOT = os.path.abspath(os.environ.get('KACA_LOCAL_ARCHIVE_DIR') or DEFAULT_LOCAL_ARCHIVE_ROOT)
try:
    os.makedirs(LOCAL_ARCHIVE_ROOT, exist_ok=True)
except OSError as archive_root_error:
    fallback_archive_root = DEFAULT_LOCAL_ARCHIVE_ROOT
    print('[LOCAL_ARCHIVE_ROOT_WARNING]', repr(archive_root_error), 'Falling back to', fallback_archive_root, flush=True)
    LOCAL_ARCHIVE_ROOT = fallback_archive_root
    os.makedirs(LOCAL_ARCHIVE_ROOT, exist_ok=True)
local_archive_queue = queue.Queue()
local_archive_lock = threading.RLock()

google_drive = GoogleDriveManager(DATA_DIR)
session_retention = SessionRetention(DATA_DIR)
whatsapp_cloud = WhatsAppCloudManager(DATA_DIR)
doku_qris = DokuQris(DATA_DIR)
fonnte_gateway = FonnteGateway(DATA_DIR)
DRIVE_JOBS_PATH = os.path.join(DATA_DIR, 'google-drive-jobs.json')
WHATSAPP_JOBS_PATH = os.path.join(DATA_DIR, 'whatsapp-jobs.json')
VOUCHERS_PATH = os.path.join(DATA_DIR, 'vouchers.json')
QRIS_IMAGE_PATH = os.path.join(DATA_DIR, 'qris-static.png')
voucher_lock = threading.RLock()
try:
    with open(VOUCHERS_PATH, 'r', encoding='utf-8') as _vf: vouchers_store = json.load(_vf)
    if not isinstance(vouchers_store, list): vouchers_store = []
except Exception: vouchers_store = []
qris_config_path = os.path.join(DATA_DIR, 'qris-config.json')
try:
    with open(qris_config_path, 'r', encoding='utf-8') as _qf: qris_config = json.load(_qf)
    if not isinstance(qris_config, dict): qris_config = {}
except Exception: qris_config = {}

def _save_vouchers():
    tmp = VOUCHERS_PATH + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f: json.dump(vouchers_store, f, ensure_ascii=False, indent=2)
    os.replace(tmp, VOUCHERS_PATH)

def _voucher_public(v):
    return {k:v.get(k) for k in ('code','created_at','expires_at','max_uses','used_count','active','custom')}

def _voucher_is_expired(v, now=None):
    now = now or datetime.datetime.now()
    raw = str(v.get('expires_at') or '').strip()
    if not raw: return False
    try:
        expiry = datetime.datetime.fromisoformat(raw.replace('Z', '+00:00'))
        if expiry.tzinfo is not None:
            expiry = expiry.astimezone().replace(tzinfo=None)
        return now >= expiry
    except Exception:
        # An unreadable expiry must never remain redeemable; classify it as expired.
        return True

def _voucher_status(v, now=None):
    now = now or datetime.datetime.now()
    expired = _voucher_is_expired(v, now)
    if not v.get('active', True): return 'nonaktif'
    if expired: return 'kedaluwarsa'
    if int(v.get('used_count',0)) >= int(v.get('max_uses',1)): return 'habis'
    return 'aktif'
drive_jobs_lock = threading.RLock()
drive_jobs_queue = queue.Queue()
try:
    with open(DRIVE_JOBS_PATH, 'r', encoding='utf-8') as _f: drive_jobs = json.load(_f)
    if not isinstance(drive_jobs, dict): drive_jobs = {}
except Exception: drive_jobs = {}
whatsapp_jobs_lock = threading.RLock()
whatsapp_jobs_queue = queue.Queue()
try:
    with open(WHATSAPP_JOBS_PATH, 'r', encoding='utf-8') as _f: whatsapp_jobs = json.load(_f)
    if not isinstance(whatsapp_jobs, dict): whatsapp_jobs = {}
except Exception: whatsapp_jobs = {}

def _save_whatsapp_jobs():
    with whatsapp_jobs_lock:
        tmp = WHATSAPP_JOBS_PATH + '.tmp'
        with open(tmp, 'w', encoding='utf-8') as _f: json.dump(whatsapp_jobs, _f, ensure_ascii=False, indent=2)
        os.replace(tmp, WHATSAPP_JOBS_PATH)

def enqueue_whatsapp_job(reference_id, phone, kind='session'):
    if not re.fullmatch(r'[A-Za-z0-9_-]{1,80}', str(reference_id or '')): raise ValueError('ID sesi/video tidak valid.')
    if kind not in ('session','video'): raise ValueError('Jenis hasil WhatsApp tidak dikenal.')
    recipient = normalize_whatsapp_number(phone)
    if kind == 'session':
        manifest = read_manifest(reference_id)
        if not manifest: raise ValueError('Sesi tidak ditemukan.')
        if not manifest.get('local_archive_path'): raise ValueError('Arsip lokal sesi belum tersedia.')
    else:
        with drive_jobs_lock: video_drive_job = dict(drive_jobs.get(reference_id) or {})
        if video_drive_job.get('kind') != 'video': raise ValueError('Arsip video tidak ditemukan atau belum masuk antrean Google Drive.')
    if not whatsapp_cloud.status().get('configured'): raise ValueError('WhatsApp Cloud API belum dikonfigurasi di Pengaturan Umum.')
    job_id = str(uuid.uuid4())
    with whatsapp_jobs_lock:
        for old in whatsapp_jobs.values():
            if old.get('reference_id') == reference_id and old.get('kind','session') == kind and old.get('recipient') == recipient and old.get('status') in ('waiting_drive','pending','sending','sent'):
                return dict(old), True
        now = datetime.datetime.now().isoformat(timespec='seconds')
        job = {'id':job_id,'reference_id':reference_id,'session_id':reference_id,'kind':kind,'recipient':recipient,'status':'waiting_drive',
               'created_at':now,'updated_at':now,'consent':True,'consent_at':now,'attempts':0,'error':None,'message_id':None,'drive_url':None}
        whatsapp_jobs[job_id] = job
        _save_whatsapp_jobs()
    whatsapp_jobs_queue.put(job_id)
    return dict(job), False

def _whatsapp_worker():
    while True:
        job_id = whatsapp_jobs_queue.get()
        try:
            with whatsapp_jobs_lock: job = dict(whatsapp_jobs.get(job_id) or {})
            if not job or job.get('status') in ('sent','cancelled'): continue
            if not whatsapp_cloud.status().get('configured'):
                job.update({'status':'error','error':'WhatsApp Cloud API belum dikonfigurasi.'})
            else:
                with drive_jobs_lock: drive_job = dict(drive_jobs.get(job.get('reference_id') or job.get('session_id')) or {})
                if drive_job.get('status') != 'ready' or not drive_job.get('url'):
                    job.update({'status':'waiting_drive','error':None})
                    with whatsapp_jobs_lock: whatsapp_jobs[job_id]=job; _save_whatsapp_jobs()
                    time.sleep(5)
                    whatsapp_jobs_queue.put(job_id)
                    continue
                if drive_job.get('share_warning'):
                    job.update({'status':'error','error':'Google Drive belum mengizinkan akses berbagi publik: '+str(drive_job.get('share_warning'))})
                else:
                    job.update({'status':'sending','drive_url':drive_job['url'],'error':None})
                    with whatsapp_jobs_lock: whatsapp_jobs[job_id]=job; _save_whatsapp_jobs()
                    try:
                        sent = whatsapp_cloud.send_result_template(job['recipient'], drive_job['url'], job['session_id'])
                        job.update({'status':'sent','message_id':sent['message_id'],'sent_at':datetime.datetime.now().isoformat(timespec='seconds'),'error':None})
                    except Exception as send_exc:
                        job.update({'status':'error','attempts':int(job.get('attempts',0))+1,'error':str(send_exc)})
            job['updated_at']=datetime.datetime.now().isoformat(timespec='seconds')
            with whatsapp_jobs_lock: whatsapp_jobs[job_id]=job; _save_whatsapp_jobs()
            print('[WHATSAPP_JOB]', job_id, job.get('status'), job.get('error') or '', flush=True)
        except Exception as exc:
            print('[WHATSAPP_QUEUE_ERROR]', job_id, repr(exc), flush=True)
        finally:
            whatsapp_jobs_queue.task_done()

for _wid, _wjob in list(whatsapp_jobs.items()):
    if _wjob.get('status') == 'sending':
        # Avoid a duplicate if the process stopped after Meta accepted a message
        # but before the returned wamid was persisted.
        _wjob['status']='error'
        _wjob['error']='Aplikasi berhenti saat pengiriman. Status ke Meta belum dapat dipastikan; periksa WhatsApp penerima sebelum mencoba ulang.'
        _wjob['updated_at']=datetime.datetime.now().isoformat(timespec='seconds')
    elif _wjob.get('status') in ('waiting_drive','pending'):
        _wjob['status']='waiting_drive'; whatsapp_jobs_queue.put(_wid)
if whatsapp_jobs:
    _save_whatsapp_jobs()

def _save_drive_jobs():
    with drive_jobs_lock:
        tmp = DRIVE_JOBS_PATH + '.tmp'
        with open(tmp, 'w', encoding='utf-8') as _f: json.dump(drive_jobs, _f, ensure_ascii=False, indent=2)
        os.replace(tmp, DRIVE_JOBS_PATH)

def _set_drive_manifest(job, status, url=None, error=None):
    sid = job.get('session_id')
    if not sid: return
    try:
        manifest = read_manifest(sid)
        if manifest:
            manifest['drive_status'] = status
            if url: manifest['drive_url'] = url
            if error: manifest['drive_error'] = error
            elif status == 'ready': manifest['drive_error'] = None
            manifest['drive_share_warning'] = job.get('share_warning')
            if job.get('folder_id'):
                manifest['drive_folder_id'] = job.get('folder_id')
                manifest['drive_folder_status'] = 'ready'
                if manifest.get('drive_url'):
                    _write_session_qr(manifest)
                elif url:
                    manifest['drive_url'] = url
                    _write_session_qr(manifest)
            manifest['drive_updated_at'] = datetime.datetime.now().isoformat(timespec='seconds')
            write_manifest(manifest)
            folder = manifest.get('local_archive_path')
            if folder and os.path.isdir(folder): _write_local_session_info(manifest)
            refreshed = _refresh_drive_qr_output(manifest) if manifest.get('drive_url') else False
            if refreshed and status == 'ready' and manifest.get('drive_folder_id'):
                try:
                    final_dir = os.path.join(folder, 'Final_Results')
                    target = os.path.join(final_dir, 'Hasil_Frame.jpg')
                    if os.path.isfile(target):
                        final_id = google_drive.ensure_folder('Final_Results', manifest['drive_folder_id'])
                        google_drive._upload_resumable(target, final_id)
                except Exception as upload_exc:
                    print('[GOOGLE_DRIVE_FRAME_QR_REUPLOAD_ERROR]', repr(upload_exc), flush=True)
    except Exception as exc: print('[GOOGLE_DRIVE_MANIFEST_WARNING]', repr(exc), flush=True)

def enqueue_drive_job(kind, local_path, folder_name, reference_id, session_id=None, event_id=None):
    job_id = str(reference_id)
    with drive_jobs_lock:
        old = drive_jobs.get(job_id, {})
        manifest = read_manifest(session_id) if session_id else None
        job = {'id':job_id,'kind':kind,'local_path':os.path.abspath(local_path),'folder_name':folder_name,
               'created_at':old.get('created_at') or datetime.datetime.now().isoformat(timespec='seconds'),
               'session_id':session_id,'event_id':_event_storage_key(event_id),
               'status':'pending' if google_drive.status().get('connected') else 'waiting_auth',
               'attempts':int(old.get('attempts',0) or 0),'url':(manifest or {}).get('drive_url') or old.get('url'),
               'folder_id':(manifest or {}).get('drive_folder_id') or old.get('folder_id'),
               'share_warning':(manifest or {}).get('drive_share_warning') or old.get('share_warning'), 'error':None,
               'updated_at':datetime.datetime.now().isoformat(timespec='seconds')}
        drive_jobs[job_id] = job
        _save_drive_jobs()
    _set_drive_manifest(job, job['status'])
    if job['status'] == 'pending': drive_jobs_queue.put(job_id)
    return dict(job)

def enqueue_drive_asset_job(session_id, local_path, relative_path):
    """Queue each local asset as soon as it exists; never wait for session completion."""
    # Upload WebM as a regular session asset as soon as the local render exists.
    # The result-slide preview remains local and does not wait for this upload.
    job_id = str(session_id) + ':' + str(relative_path).replace('\\', '/')
    with drive_jobs_lock:
        old = drive_jobs.get(job_id, {})
        if old.get('status') in ('ready', 'uploading', 'pending'):
            return dict(old)
        job = {'id':job_id,'kind':'asset','local_path':os.path.abspath(local_path),
               'relative_path':str(relative_path).replace('\\','/'),
               'folder_name':'','session_id':session_id,'status':'pending',
               'attempts':int(old.get('attempts',0) or 0),'updated_at':datetime.datetime.now().isoformat(timespec='seconds')}
        drive_jobs[job_id] = job
        _save_drive_jobs()
    if google_drive.status().get('connected'):
        drive_jobs_queue.put(job_id)
    else:
        with drive_jobs_lock:
            drive_jobs[job_id]['status'] = 'waiting_auth'
            _save_drive_jobs()
    return dict(job)

def _write_video_drive_qr(job):
    if not job.get('url') or not job.get('local_path') or job.get('share_warning'): return job
    qr_bytes=_session_qr_png_bytes({'drive_url':job['url']})
    if not qr_bytes:return job
    qr_path=os.path.join(os.path.dirname(job['local_path']),str(job['id'])+'_QR_Google_Drive.png')
    tmp=qr_path+'.tmp'
    with open(tmp,'wb') as f:f.write(qr_bytes)
    os.replace(tmp,qr_path)
    job['qr_path']=qr_path
    return job

def _google_drive_worker():
    while True:
        job_id = drive_jobs_queue.get()
        try:
            with drive_jobs_lock: job = dict(drive_jobs.get(job_id) or {})
            if not job or job.get('status') in ('ready', 'expired'): continue
            sid = job.get('session_id')
            if sid and (read_manifest(sid) or {}).get('drive_deleted_at'):
                with drive_jobs_lock:
                    job['status'] = 'expired'
                    drive_jobs[job_id] = job
                    _save_drive_jobs()
                continue
            if not google_drive.status().get('connected'):
                job['status']='waiting_auth'; job['error']='Hubungkan akun Google Drive untuk melanjutkan unggahan.'
                with drive_jobs_lock: drive_jobs[job_id]=job; _save_drive_jobs()
                _set_drive_manifest(job,'waiting_auth',error=job['error']); continue
            job['status']='uploading'; job['error']=None
            with drive_jobs_lock: drive_jobs[job_id]=job; _save_drive_jobs()
            _set_drive_manifest(job,'uploading')
            if job.get('kind') == 'asset':
                sid = job.get('session_id')
                folder_id = None
                for _ in range(600):
                    current_manifest = read_manifest(sid) if sid else None
                    folder_id = (current_manifest or {}).get('drive_folder_id')
                    if folder_id:
                        break
                    if not google_drive.status().get('connected'):
                        break
                    time.sleep(1)
                if not folder_id and google_drive.status().get('connected'):
                    prepared = _provision_drive_session_folder(read_manifest(sid), job.get('folder_name') or os.path.basename((read_manifest(sid) or {}).get('local_archive_path','Sesi')))
                    folder_id = prepared.get('folder_id')
                    manifest = read_manifest(sid) or {}
                    manifest.update({'drive_folder_id':folder_id,'drive_url':prepared.get('url'),
                                     'drive_folder_status':'ready','drive_status':'uploading',
                                     'drive_share_warning':prepared.get('share_warning')})
                    _write_session_qr(manifest); write_manifest(manifest)
                if not folder_id:
                    raise RuntimeError('Folder Google Drive sesi belum tersedia.')
                result = google_drive.upload_session_asset(job['local_path'], folder_id, job['relative_path'])
                job.update({'status':'ready','result':result,'updated_at':datetime.datetime.now().isoformat(timespec='seconds'),'error':None})
                with drive_jobs_lock:
                    drive_jobs[job_id] = job; _save_drive_jobs()
                    session_jobs = [j for j in drive_jobs.values() if j.get('session_id') == sid and j.get('kind') == 'asset']
                    all_uploaded = all(j.get('status') == 'ready' for j in session_jobs)
                manifest = read_manifest(sid) or {}
                uploaded = set(manifest.get('drive_uploaded_assets') or [])
                uploaded.add(job.get('relative_path'))
                manifest['drive_uploaded_assets'] = sorted(uploaded)
                if manifest.get('drive_upload_manifest_complete') and all_uploaded:
                    manifest['drive_status'] = 'ready'; manifest['drive_error'] = None
                else:
                    manifest['drive_status'] = 'uploading'
                write_manifest(manifest)
                print('[GOOGLE_DRIVE_ASSET_UPLOADED]', sid, job.get('relative_path'), flush=True)
            elif job.get('kind') == 'session':
                # Legacy whole-folder jobs are retained for recovery of older sessions.
                for _ in range(600):
                    current_manifest = read_manifest(job.get('session_id')) if job.get('session_id') else None
                    if not current_manifest or current_manifest.get('drive_folder_status') != 'creating':
                        break
                    time.sleep(1)
                current_manifest = read_manifest(job.get('session_id')) if job.get('session_id') else None
                if current_manifest:
                    job['folder_id'] = current_manifest.get('drive_folder_id') or job.get('folder_id')
                    job['url'] = current_manifest.get('drive_url') or job.get('url')
                    job['share_warning'] = current_manifest.get('drive_share_warning') or job.get('share_warning')
                # If Drive was connected only after the session began, provision the empty folder
                # now, publish its QR/link, and only then start transferring the session assets.
                if not job.get('folder_id'):
                    prepared = _provision_drive_session_folder(current_manifest, job['folder_name'])
                    job.update({'folder_id':prepared.get('folder_id'),'url':prepared.get('url'),
                                'share_warning':prepared.get('share_warning')})
                    with drive_jobs_lock:
                        drive_jobs[job_id] = dict(job); _save_drive_jobs()
                    _set_drive_manifest(job,'uploading',url=job.get('url'))
                result=google_drive.upload_session_folder(job['local_path'],job['folder_name'],job.get('folder_id'))
            else:
                # Provision a public per-video folder and create its QR first.
                # Uploading the potentially large MP4 continues asynchronously.
                if not job.get('folder_id'):
                    prepared=google_drive.create_video_folder(job['folder_name'],event_id=job.get('event_id'))
                    job.update({'folder_id':prepared['folder_id'],'url':prepared['url'],
                                'share_warning':prepared.get('share_warning')})
                    _write_video_drive_qr(job)
                    with drive_jobs_lock:drive_jobs[job_id]=dict(job);_save_drive_jobs()
                result=google_drive.upload_video(job['local_path'],job['folder_name'],event_id=job.get('event_id'),folder_id=job['folder_id'])
            job.update({'status':'ready','url':result.get('url'),'folder_id':result.get('folder_id'),'share_warning':result.get('share_warning'),
                        'updated_at':datetime.datetime.now().isoformat(timespec='seconds'),'error':None})
            if job.get('kind') == 'video' and job.get('url'):
                try:_write_video_drive_qr(job)
                except Exception as qr_exc:print('[EVENT_VIDEO_QR_WARNING]',repr(qr_exc),flush=True)
            with drive_jobs_lock: drive_jobs[job_id]=job; _save_drive_jobs()
            _set_drive_manifest(job,'ready',url=job['url'])
            # Session_Info.json is internal/local-only metadata and is intentionally not uploaded.
            print('[GOOGLE_DRIVE_UPLOAD_READY]', job_id, job['url'], flush=True)
        except Exception as exc:
            print('[GOOGLE_DRIVE_UPLOAD_ERROR]', job_id, repr(exc), flush=True)
            try:
                with drive_jobs_lock:
                    job=dict(drive_jobs.get(job_id) or {})
                    job['attempts']=int(job.get('attempts',0))+1
                    job['error']=str(exc)
                    job['status']='pending' if job['attempts'] < 20 else 'error'
                    job['updated_at']=datetime.datetime.now().isoformat(timespec='seconds')
                    drive_jobs[job_id]=job; _save_drive_jobs()
                _set_drive_manifest(job,job['status'],error=job['error'])
                if job['status']=='pending':
                    time.sleep(min(300, max(30, job['attempts']*30)))
                    drive_jobs_queue.put(job_id)
            except Exception as nested: print('[GOOGLE_DRIVE_QUEUE_ERROR]',repr(nested),flush=True)
        finally:
            drive_jobs_queue.task_done()

for _job_id, _job in list(drive_jobs.items()):
    if _job.get('status') in ('pending','uploading') and os.path.exists(_job.get('local_path','')):
        _job['status']='pending'; drive_jobs_queue.put(_job_id)
    elif _job.get('status') == 'waiting_auth' and google_drive.status().get('connected') and os.path.exists(_job.get('local_path','')):
        _job['status']='pending'; drive_jobs_queue.put(_job_id)

def _event_storage_key(event_id):
    """Stable and safe folder ID. Event renames never move old customers' results."""
    value = str(event_id or '').strip().lower()
    return value if re.fullmatch(r'[a-f0-9]{16}', value) else None


def _event_archive_root(session):
    event_key = _event_storage_key(session.get('event_id'))
    if not event_key:
        return LOCAL_ARCHIVE_ROOT
    event_root = os.path.join(LOCAL_ARCHIVE_ROOT, 'Events', 'Event_' + event_key)
    os.makedirs(event_root, exist_ok=True)
    # Kept at the event level (not inside customer folders) for identification.
    metadata = os.path.join(event_root, 'Event_Info.json')
    event_name = str(session.get('event_name') or '').strip()[:100]
    if event_name:
        data = {'event_id': event_key, 'event_name': event_name,
                'updated_at': datetime.datetime.now().isoformat(timespec='seconds')}
        tmp = metadata + '.tmp'
        with open(tmp, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp, metadata)
    return event_root


def _provision_drive_session_folder(manifest, folder_name):
    """Use the ordinary QR-enabled folder workflow, scoped per event when active."""
    event_key = _event_storage_key((manifest or {}).get('event_id'))
    if event_key:
        return google_drive.create_session_folder(folder_name, event_id=event_key)
    return google_drive.create_session_folder(folder_name)


def _session_archive_date(session):
    raw = str(session.get('created_at') or datetime.datetime.now().isoformat())
    try:
        return datetime.datetime.fromisoformat(raw.replace('Z', '+00:00')).strftime('%Y%m%d')
    except Exception:
        return datetime.datetime.now().strftime('%Y%m%d')

def create_local_session_archive(session):
    global LOCAL_ARCHIVE_ROOT
    # Create the customer-facing folder immediately when a session starts.
    existing = session.get('local_archive_path')
    if existing and os.path.isdir(existing):
        folder = existing
    else:
        try:
            os.makedirs(LOCAL_ARCHIVE_ROOT, exist_ok=True)
        except OSError as archive_root_error:
            fallback_archive_root = DEFAULT_LOCAL_ARCHIVE_ROOT
            print('[LOCAL_ARCHIVE_ROOT_WARNING]', repr(archive_root_error), 'Falling back to', fallback_archive_root, flush=True)
            LOCAL_ARCHIVE_ROOT = fallback_archive_root
            os.makedirs(LOCAL_ARCHIVE_ROOT, exist_ok=True)
        archive_parent = _event_archive_root(session)
        prefix = f"Sesi_{_session_archive_date(session)}_"
        numbers = []
        try:
            for name in os.listdir(archive_parent):
                if name.startswith(prefix):
                    try: numbers.append(int(name[len(prefix):]))
                    except ValueError: pass
        except OSError:
            pass
        sequence = max(numbers or [0]) + 1
        folder = os.path.join(archive_parent, f'{prefix}{sequence:03d}')
        while os.path.exists(folder):
            sequence += 1
            folder = os.path.join(archive_parent, f'{prefix}{sequence:03d}')
    for name in ('Photos', 'Live_Photos', 'Final_Results', 'Video_Results'):
        os.makedirs(os.path.join(folder, name), exist_ok=True)
    session['local_archive_path'] = folder
    session['local_archive_status'] = 'saving'
    _write_local_session_info(session)
    return folder

def _write_local_session_info(session):
    folder = session.get('local_archive_path')
    if not folder: return
    os.makedirs(folder, exist_ok=True)
    info = dict(session)
    info['local_archive_path'] = os.path.basename(folder)
    temp = os.path.join(folder, 'Session_Info.json.tmp')
    with open(temp, 'w', encoding='utf-8') as f:
        json.dump(info, f, ensure_ascii=False, indent=2)
    os.replace(temp, os.path.join(folder, 'Session_Info.json'))

def _qr_matrix_to_png(matrix, target, scale=8, quiet_zone=4):
    """Write a QR matrix as a grayscale PNG using only the Python standard library."""
    import struct
    import zlib

    modules = len(matrix)
    if not modules or any(len(row) != modules for row in matrix):
        raise ValueError('Invalid QR matrix')
    width = (modules + quiet_zone * 2) * scale
    height = width
    rows = []
    white = bytes([255]) * width
    for y in range(height):
        module_y = y // scale - quiet_zone
        scanline = bytearray(white)
        if 0 <= module_y < modules:
            row = matrix[module_y]
            for module_x, dark in enumerate(row):
                if dark:
                    left = (module_x + quiet_zone) * scale
                    scanline[left:left + scale] = bytes([0]) * scale
        rows.append(b'\x00' + bytes(scanline))  # PNG filter: None

    def chunk(kind, data):
        payload = kind + data
        return struct.pack('!I', len(data)) + payload + struct.pack('!I', zlib.crc32(payload) & 0xffffffff)

    png = (b'\x89PNG\r\n\x1a\n'
           + chunk(b'IHDR', struct.pack('!IIBBBBB', width, height, 8, 0, 0, 0, 0))
           + chunk(b'IDAT', zlib.compress(b''.join(rows), 9))
           + chunk(b'IEND', b''))
    with open(target, 'wb') as output:
        output.write(png)
    return width


def _session_qr_png_bytes(session):
    """Build PNG bytes for the session QR. The caller persists the PNG locally only."""
    drive_url = str(session.get('drive_url') or '').strip()
    if not drive_url:
        return None
    try:
        import struct, zlib
        import qrcode
        qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=1, border=4)
        qr.add_data(drive_url)
        qr.make(fit=True)
        matrix = qr.get_matrix()
        modules = len(matrix); scale = 8; quiet_zone = 4
        width = (modules + quiet_zone * 2) * scale
        rows = []
        white = bytes([255]) * width
        for y in range(width):
            module_y = y // scale - quiet_zone
            scanline = bytearray(white)
            if 0 <= module_y < modules:
                for module_x, dark in enumerate(matrix[module_y]):
                    if dark:
                        left = (module_x + quiet_zone) * scale
                        scanline[left:left + scale] = bytes([0]) * scale
            rows.append(b'\x00' + bytes(scanline))
        def chunk(kind, data):
            payload = kind + data
            return struct.pack('!I', len(data)) + payload + struct.pack('!I', zlib.crc32(payload) & 0xffffffff)
        return (b'\x89PNG\r\n\x1a\n'
                + chunk(b'IHDR', struct.pack('!IIBBBBB', width, width, 8, 0, 0, 0, 0))
                + chunk(b'IDAT', zlib.compress(b''.join(rows), 9))
                + chunk(b'IEND', b''))
    except Exception as exc:
        session['drive_qr_error'] = str(exc)
        print('[GOOGLE_DRIVE_QR_ERROR]', repr(exc), flush=True)
        return None


def _write_session_qr(session):
    """Persist the session's Google Drive QR locally; never enqueue or upload it to Drive."""
    drive_url = str(session.get('drive_url') or '').strip()
    sid = str(session.get('id') or session.get('session_id') or '').strip()
    if not drive_url or not sid or not re.fullmatch(r'[A-Za-z0-9_-]{1,80}', sid):
        session['drive_qr_available'] = False
        return None
    try:
        qr_bytes = _session_qr_png_bytes(session)
        if not qr_bytes:
            session['drive_qr_available'] = False
            return None
        session_dir = os.path.join(SESSIONS_DIR, sid)
        os.makedirs(session_dir, exist_ok=True)
        qr_path = os.path.join(session_dir, 'google_drive_qr.png')
        temp_path = qr_path + '.tmp'
        with open(temp_path, 'wb') as output:
            output.write(qr_bytes)
        os.replace(temp_path, qr_path)
        session['drive_qr_available'] = True
        session['drive_qr_path'] = qr_path
        session.pop('drive_qr_error', None)
        # Keep a customer/operator-visible copy in the configured local archive.
        # This copy is deliberately NOT passed to enqueue_drive_asset_job.
        archive = session.get('local_archive_path')
        if archive:
            final_dir = os.path.join(archive, 'Final_Results')
            os.makedirs(final_dir, exist_ok=True)
            archive_qr = os.path.join(final_dir, 'QR_Google_Drive.png')
            archive_tmp = archive_qr + '.tmp'
            with open(archive_tmp, 'wb') as output:
                output.write(qr_bytes)
            os.replace(archive_tmp, archive_qr)
            session['drive_qr_archive_path'] = archive_qr
        print('[GOOGLE_DRIVE_QR_SAVED_LOCAL]', sid, qr_path, flush=True)
        return qr_path
    except Exception as exc:
        session['drive_qr_available'] = False
        session['drive_qr_error'] = str(exc)
        print('[GOOGLE_DRIVE_QR_SAVE_ERROR]', sid, repr(exc), flush=True)
        return None


def _prepare_session_drive_folder(session_id):
    """Create the cloud folder asynchronously, independently of file uploads."""
    session = read_manifest(session_id)
    if not session or session.get('drive_deleted_at'):
        return
    if not google_drive.status().get('connected'):
        session['drive_folder_status'] = 'waiting_auth'
        session['drive_status'] = 'waiting_auth'
        session['drive_error'] = 'Hubungkan Google Drive untuk membuat tautan dan QR sesi.'
        write_manifest(session)
        return
    session['drive_folder_status'] = 'creating'
    session['drive_status'] = 'provisioning'
    session['drive_error'] = None
    write_manifest(session)
    folder_error = None
    for attempt in range(1, 6):
        try:
            result = _provision_drive_session_folder(session, os.path.basename(session['local_archive_path']))
            session.update({'drive_folder_id':result.get('folder_id'), 'drive_url':result.get('url'),
                            'drive_folder_status':'ready', 'drive_status':'folder_ready',
                            'drive_share_warning':result.get('share_warning'), 'drive_error':None})
            _write_session_qr(session)
            folder_error = None
            print('[GOOGLE_DRIVE_FOLDER_READY]', session_id, 'attempt='+str(attempt), flush=True)
            break
        except Exception as exc:
            folder_error = exc
            print('[GOOGLE_DRIVE_FOLDER_CREATE_RETRY]', session_id, 'attempt='+str(attempt), repr(exc), flush=True)
            if attempt < 5:
                time.sleep(min(20, 2 ** attempt))
    if folder_error is not None:
        session['drive_folder_status'] = 'error'
        session['drive_status'] = 'waiting_auth' if not google_drive.status().get('connected') else 'error'
        session['drive_error'] = str(folder_error)
        print('[GOOGLE_DRIVE_FOLDER_CREATE_ERROR]', repr(folder_error), flush=True)
    # Merge only Drive fields into the latest manifest so a fast-finishing session is never reverted.
    latest = read_manifest(session_id) or session
    for key in ('drive_folder_id','drive_url','drive_folder_status','drive_share_warning','drive_error','drive_qr_path','drive_qr_error'):
        if key in session: latest[key] = session[key]
    if latest.get('status') == 'active' or latest.get('drive_status') not in ('pending','uploading','ready'):
        latest['drive_status'] = session.get('drive_status', latest.get('drive_status'))
    if latest.get('drive_url'):
        _write_session_qr(latest)
        _refresh_drive_qr_output(latest)
    write_manifest(latest)
    _write_local_session_info(latest)
    with session_lock:
        if active_session and active_session.get('id') == session_id:
            active_session.update({k:latest[k] for k in latest if k.startswith('drive_')})


def _start_session_drive_folder_provision(session_id):
    threading.Thread(target=_prepare_session_drive_folder, args=(session_id,),
                     name='KACA-Drive-Folder-'+str(session_id), daemon=True).start()


# Recover an interrupted early folder-creation attempt after an application restart.
if google_drive.status().get('connected'):
    try:
        for _sid in os.listdir(SESSIONS_DIR):
            _manifest = read_manifest(_sid)
            if (_manifest and not _manifest.get('drive_folder_id') and
                    _manifest.get('drive_folder_status') in ('creating', 'error')):
                _start_session_drive_folder_provision(_sid)
    except Exception as _recover_exc:
        print('[GOOGLE_DRIVE_FOLDER_RECOVERY_WARNING]', repr(_recover_exc), flush=True)


# v0.9.73: exported original JPEGs for customers are Full HD 1920x1080.
# Internal/session originals are deliberately left untouched for accurate photo
# composition and non-destructive retake/filter workflows.
ORIGINAL_EXPORT_WIDTH = 1920
ORIGINAL_EXPORT_HEIGHT = 1080
ORIGINAL_EXPORT_JPEG_QUALITY = 98


def _export_original_full_hd(source_path, export_path):
    """Write an atomic 1920x1080 customer-original from the raw session JPEG.

    Preserve all image content and the original aspect ratio; letterbox if the
    camera delivers portrait / 4:3 frames. Upsampling cannot recover missing
    sensor detail, but the exported file meets the requested pixel resolution.
    """
    if not os.path.isfile(source_path):
        raise FileNotFoundError(source_path)
    if os.path.isfile(export_path) and os.path.getmtime(export_path) >= os.path.getmtime(source_path):
        # Subsequent archive passes must not replace a file while Drive uploads it.
        # The source file for a retaken photo gets a newer mtime and is reexported.
        return export_path
    image = cv2.imread(source_path, cv2.IMREAD_COLOR)
    if image is None or image.size == 0:
        raise ValueError('Foto original tidak dapat dibaca: ' + source_path)
    source_h, source_w = image.shape[:2]
    if source_w < 1 or source_h < 1:
        raise ValueError('Dimensi foto original tidak valid.')
    scale = min(ORIGINAL_EXPORT_WIDTH / source_w, ORIGINAL_EXPORT_HEIGHT / source_h)
    resized_w = max(1, min(ORIGINAL_EXPORT_WIDTH, round(source_w * scale)))
    resized_h = max(1, min(ORIGINAL_EXPORT_HEIGHT, round(source_h * scale)))
    interpolation = cv2.INTER_AREA if scale < 1 else cv2.INTER_LANCZOS4
    resized = cv2.resize(image, (resized_w, resized_h), interpolation=interpolation)
    canvas = cv2.copyMakeBorder(
        resized,
        (ORIGINAL_EXPORT_HEIGHT - resized_h) // 2,
        ORIGINAL_EXPORT_HEIGHT - resized_h - (ORIGINAL_EXPORT_HEIGHT - resized_h) // 2,
        (ORIGINAL_EXPORT_WIDTH - resized_w) // 2,
        ORIGINAL_EXPORT_WIDTH - resized_w - (ORIGINAL_EXPORT_WIDTH - resized_w) // 2,
        cv2.BORDER_CONSTANT,
        value=(0, 0, 0),
    )
    params = [int(cv2.IMWRITE_JPEG_QUALITY), ORIGINAL_EXPORT_JPEG_QUALITY]
    if hasattr(cv2, 'IMWRITE_JPEG_OPTIMIZE'):
        params.extend((int(cv2.IMWRITE_JPEG_OPTIMIZE), 1))
    temp_path = export_path + '.tmp.jpg'
    try:
        if not cv2.imwrite(temp_path, canvas, params):
            raise OSError('Gagal mengekspor original Full HD: ' + export_path)
        os.replace(temp_path, export_path)
    finally:
        if os.path.exists(temp_path):
            try: os.unlink(temp_path)
            except OSError: pass
    return export_path


def _sync_local_session_archive(session, final=False):
    # Copy assets into the organized local folder on the archive worker.
    folder = session.get('local_archive_path') or create_local_session_archive(session)
    photos_dir = os.path.join(folder, 'Photos')
    live_dir = os.path.join(folder, 'Live_Photos')
    final_dir = os.path.join(folder, 'Final_Results')
    os.makedirs(photos_dir, exist_ok=True); os.makedirs(live_dir, exist_ok=True); os.makedirs(final_dir, exist_ok=True)
    source_dir = os.path.join(SESSIONS_DIR, session['id'])
    copy_errors = []
    for photo in session.get('photos', []):
        number = int(photo.get('number', 0) or 0)
        for key, suffix in (('original', 'Original'),):
            filename = photo.get(key)
            if filename and re.match(r'^[A-Za-z0-9_.-]+$', str(filename)):
                src = os.path.join(source_dir, filename)
                dst = os.path.join(photos_dir, f'Foto_{number:02d}_{suffix}.jpg')
                if os.path.isfile(src):
                    try:
                        # Export once, then upload this same Full HD JPEG to Drive.
                        _export_original_full_hd(src, dst)
                        enqueue_drive_asset_job(session['id'], dst, 'Photos/' + os.path.basename(dst))
                    except (OSError, ValueError, cv2.error) as exc:
                        copy_errors.append(str(exc))
                        print('[LOCAL_ARCHIVE_HD_EXPORT_ERROR]', repr(exc), flush=True)
    # Persist every deliverable as soon as the renderer creates it. This runs for
    # both final=False (result slide) and final=True (customer leaves the slide).
    # Never delete the QR here: it is a durable local deliverable, not a transient.
    qr_source = session.get('drive_qr_archive_path') or os.path.join(source_dir, 'google_drive_qr.png')
    qr_target = os.path.join(final_dir, 'QR_Google_Drive.png')
    if qr_source and os.path.isfile(qr_source) and os.path.abspath(qr_source) != os.path.abspath(qr_target):
        try: shutil.copy2(qr_source, qr_target)
        except OSError as exc: copy_errors.append(str(exc))
    if session.get('drive_qr_enabled') and session.get('drive_url'):
        _refresh_drive_qr_output(session)
    for filename, target in (('output.jpg', os.path.join(final_dir, 'Hasil_Frame.jpg')),
                             ('output_print_qr.jpg', os.path.join(final_dir, 'Hasil_Frame_Dengan_QR.jpg')),
                             ('output_live.mp4', os.path.join(live_dir, 'Live_Photo_Frame.mp4')),
                             ('output_live.webm', os.path.join(live_dir, 'Live_Photo_Frame.webm')),
                             ('originals.gif', os.path.join(final_dir, 'GIF_Originals.gif'))):
        src = os.path.join(source_dir, filename)
        if os.path.isfile(src):
            try:
                shutil.copy2(src, target)
                # Queue each completed deliverable immediately; WebM upload is independent
                # from local slide playback. QR is intentionally never uploaded to Drive.
                rel = os.path.relpath(target, folder).replace('\\','/')
                enqueue_drive_asset_job(session['id'], target, rel)
            except OSError as exc:
                copy_errors.append(str(exc))
                print('[LOCAL_ARCHIVE_COPY_ERROR]', repr(exc), flush=True)
    if final:
        if copy_errors:
            raise OSError('Gagal menyalin sebagian file ke arsip lokal: ' + '; '.join(copy_errors[:3]))
        if not os.path.isfile(os.path.join(final_dir, 'Hasil_Frame.jpg')):
            raise OSError('Hasil_Frame.jpg belum tersedia untuk arsip lokal.')
        session['local_archive_status'] = 'ready'
        _write_local_session_info(session)
        package = os.path.join(folder, 'KACA-ID-Hasil-Sesi.zip')
        temp_package = package + '.tmp'
        with zipfile.ZipFile(temp_package, 'w', compression=zipfile.ZIP_STORED) as bundle:
            for root_dir, _dirs, files in os.walk(folder):
                for filename in files:
                    full = os.path.join(root_dir, filename)
                    if full in (package, temp_package): continue
                    arcname = os.path.relpath(full, folder)
                    bundle.write(full, arcname)
        os.replace(temp_package, package)
        # Preserve a folder that may have been provisioned asynchronously at session start.
        latest_drive = read_manifest(session.get('id')) or {}
        for key in ('drive_folder_id','drive_url','drive_folder_status','drive_share_warning','drive_qr_path','drive_qr_error'):
            if key in latest_drive:
                session[key] = latest_drive[key]
        if session.get('drive_url'):
            _write_session_qr(session)
            _refresh_drive_qr_output(session)
        session['drive_status'] = 'pending' if google_drive.status().get('connected') else 'waiting_auth'
        session['drive_error'] = None
        if not session.get('drive_folder_id') and not session.get('drive_url'):
            session['drive_url'] = None
    else:
        session['local_archive_status'] = 'saving'
    _write_local_session_info(session)
    if final:
        # All locally available deliverables have now been queued individually.
        session['drive_upload_manifest_complete'] = True
        session['drive_status'] = 'uploading' if google_drive.status().get('connected') else 'waiting_auth'
        write_manifest(session)
        if google_drive.status().get('connected'):
            with drive_jobs_lock:
                remaining = [j for j in drive_jobs.values() if j.get('session_id') == session['id'] and j.get('kind') == 'asset' and j.get('status') != 'ready']
            if not remaining:
                session['drive_status'] = 'ready'
                write_manifest(session)
    return folder

def sync_local_session_archive(session, final=False):
    with local_archive_lock:
        return _sync_local_session_archive(session, final)

def _local_archive_worker():
    while True:
        session, final = local_archive_queue.get()
        try:
            sync_local_session_archive(session, final)
        except Exception as exc:
            print('[LOCAL_ARCHIVE_ERROR]', repr(exc), flush=True)
            try:
                session['local_archive_status'] = 'error'
                _write_local_session_info(session)
                write_manifest(session)
            except Exception: pass
        finally:
            local_archive_queue.task_done()

def enqueue_local_session_archive(session, final=False):
    local_archive_queue.put((copy.deepcopy(session), bool(final)))

def _retention_on_expire(sid, storage):
    # Mark pending uploads closed, so expired folders cannot be recreated.
    with drive_jobs_lock:
        for job in drive_jobs.values():
            if job.get('session_id') == sid and (storage == 'drive' or storage == 'local'):
                if job.get('status') not in ('ready', 'expired'):
                    job['status'] = 'expired'
                    job['error'] = 'Sesi melewati masa penyimpanan.'
        _save_drive_jobs()


def _retention_sweep_once(now=None):
    with session_lock:
        current_id = active_session.get('id') if active_session else None
    def upload_pending(sid):
        with drive_jobs_lock:
            return any(j.get('session_id') == sid and j.get('kind') in ('asset','session') and
                       j.get('status') in ('pending','uploading','waiting_auth','error')
                       for j in drive_jobs.values())
    summary = session_retention.sweep(SESSIONS_DIR, LOCAL_ARCHIVE_ROOT,
                                      read_manifest, write_manifest, google_drive,
                                      active_id=current_id, on_expire=_retention_on_expire,
                                      upload_pending=upload_pending, now=now)
    with video_lock:
        active_video = booth_video_id
    with drive_jobs_lock:
        video_result = session_retention.sweep_videos(drive_jobs,
                         os.path.join(DATA_DIR,'video_sessions'),LOCAL_ARCHIVE_ROOT,
                         google_drive,_save_drive_jobs,active_id=active_video,now=now)
    return {**summary, **video_result}


def _retention_worker():
    # Check soon after startup (so expired data from an offline booth is handled),
    # then every 15 minutes without blocking camera or the customer UI.
    time.sleep(20)
    while True:
        try:
            _retention_sweep_once()
        except Exception as exc:
            print('[KACA_RETENTION_SWEEP_ERROR]',repr(exc),flush=True)
        time.sleep(15 * 60)

threading.Thread(target=_retention_worker,name='KACA-Retention',daemon=True).start()

threading.Thread(target=_local_archive_worker, name='KACA-Local-Archive', daemon=True).start()
threading.Thread(target=_google_drive_worker,name='KACA-Google-Drive',daemon=True).start()
threading.Thread(target=_whatsapp_worker,name='KACA-WhatsApp-Cloud',daemon=True).start()

def apply_filter(frame, filter_name):
    """Apply CSS-style color matrices for the five customer-facing filter presets."""
    import numpy as np
    name = str(filter_name or 'sepia').strip().lower().replace('_', '-')
    identity = np.eye(3, dtype=np.float32)
    sepia_matrix = np.array([[.393, .769, .189], [.349, .686, .168], [.272, .534, .131]], dtype=np.float32)
    def matrix(image, mat):
        rgb = image[:, :, ::-1].astype(np.float32)
        out = np.einsum('...c,dc->...d', rgb, mat, optimize=True)
        return np.clip(out, 0, 255).astype(np.uint8)[:, :, ::-1].copy()
    def contrast(image, factor):
        return np.clip((image.astype(np.float32) - 127.5) * factor + 127.5, 0, 255).astype(np.uint8)
    def sepia(image, amount):
        return matrix(image, identity * (1.0 - amount) + sepia_matrix * amount)
    def saturate(image, amount):
        mat = np.array([
            [.213 + .787*amount, .715 - .715*amount, .072 - .072*amount],
            [.213 - .213*amount, .715 + .285*amount, .072 - .072*amount],
            [.213 - .213*amount, .715 - .715*amount, .072 + .928*amount]
        ], dtype=np.float32)
        return matrix(image, mat)
    def hue_rotate(image, degrees):
        angle = np.deg2rad(degrees); c, si = np.cos(angle), np.sin(angle)
        mat = np.array([
            [.213+.787*c-.213*si, .715-.715*c-.715*si, .072-.072*c+.928*si],
            [.213-.213*c+.143*si, .715+.285*c+.140*si, .072-.072*c-.283*si],
            [.213-.213*c-.787*si, .715-.715*c+.715*si, .072+.928*c+.072*si]
        ], dtype=np.float32)
        return matrix(image, mat)
    # v0.9.69: faithfully adapted from the supplied OpenCV filter formulas.
    # The camera is already managed by KACA.ID: never call VideoCapture here.
    if name in ('pencil', 'sketch', 'pencil-sketch', 'sketsa-pensil'):
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        inv_gray = 255 - gray
        blur = cv2.GaussianBlur(inv_gray, (21, 21), 0)
        sketch = cv2.divide(gray, 255 - blur, scale=256)
        return cv2.cvtColor(sketch, cv2.COLOR_GRAY2BGR)
    if name in ('cartoon', 'kartun', 'ilustrasi'):
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        color = cv2.bilateralFilter(frame, 9, 300, 300)
        gray_blur = cv2.medianBlur(gray, 7)
        edge = cv2.adaptiveThreshold(gray_blur, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY, 9, 2)
        edge_colored = cv2.cvtColor(edge, cv2.COLOR_GRAY2BGR)
        return cv2.bitwise_and(color, edge_colored)
    if name in ('mono', 'bw', 'black & white', 'hitam putih', 'monochrome'):
        gray = matrix(frame, np.array([[.2126,.7152,.0722]]*3, dtype=np.float32))
        return contrast(gray, 1.20)
    if name == 'sepia':
        return sepia(frame, 1.0)
    if name in ('chrome', 'vivid'):
        return contrast(saturate(frame, 1.60), 1.20)
    if name in ('vintage', 'warm', 'hangat'):
        result = sepia(frame, .40)
        result = saturate(result, 1.20)
        result = contrast(result, .90)
        return hue_rotate(result, -10)
    if name in ('cool', 'cinematic', 'dingin'):
        result = hue_rotate(frame, 15)
        result = saturate(result, .85)
        return contrast(result, 1.05)
    return frame.copy()

def _layout_slots(session, count, W, H):
    """Resolve photo slots without silently discarding a saved manual layout.

    Manual slots are authoritative and remain in their saved order. If a legacy or
    externally-created session asks for more photos than it has manual slots, only
    the missing tail is filled with automatic slots; the existing manual positions
    are never replaced wholesale.
    """
    count = max(0, int(count))
    configured = session.get('layout_slots') or session.get('settings', {}).get('layout_slots') or []
    slots = []
    if isinstance(configured, list):
        for value in configured[:count]:
            if not isinstance(value, dict):
                continue
            try:
                x = max(0.0, min(.99, float(value.get('x', 0))))
                y = max(0.0, min(.99, float(value.get('y', 0))))
                w = max(.01, min(1.0, float(value.get('w', 1))))
                h = max(.01, min(1.0, float(value.get('h', 1))))
                source_index = int(value.get('photo_index', len(slots)))
                source_index = max(0, min(7, source_index))
                slots.append((x, y, min(w, 1.0-x), min(h, 1.0-y), source_index))
            except (TypeError, ValueError, OverflowError):
                continue
    if len(slots) < count:
        missing = count - len(slots)
        start_index = len(slots)
        cols = 1 if '2r' in str(session.get('paper_size','')).lower() else (2 if count > 1 else 1)
        rows = (missing + cols - 1)//cols
        slots.extend((((i % cols)/cols, (i // cols)/rows, 1/cols, 1/rows, start_index+i) for i in range(missing)))
    # Layout percentages are defined against the PNG frame. If its aspect ratio differs
    # from the paper canvas, map slot coordinates into the exact same centered fit box.
    frame_id = session.get('frame_id') or session.get('settings', {}).get('frame_id')
    if frame_id and re.match(r'^[a-f0-9]{12,32}$', str(frame_id)):
        overlay = cv2.imread(os.path.join(FRAMES_DIR, str(frame_id) + '.png'), cv2.IMREAD_UNCHANGED)
        if overlay is not None and overlay.shape[1] > 0 and overlay.shape[0] > 0:
            fh, fw = overlay.shape[:2]
            scale = min(W / float(fw), H / float(fh))
            fit_w, fit_h = fw * scale, fh * scale
            off_x, off_y = (W - fit_w) / 2.0, (H - fit_h) / 2.0
            slots = [((off_x + x * fit_w) / W, (off_y + y * fit_h) / H,
                      (w * fit_w) / W, (h * fit_h) / H, source_index) for x,y,w,h,source_index in slots]
    return slots


def _blend_drive_qr(canvas, session):
    """Burn the current session's Drive-folder QR into the printable frame."""
    if not session.get('drive_qr_enabled') or not session.get('drive_url'):
        return canvas
    layout = session.get('drive_qr_layout') or {}
    try:
        x = max(0.0, min(.99, float(layout.get('x', .78))))
        y = max(0.0, min(.99, float(layout.get('y', .78))))
        w = max(.04, min(.5, float(layout.get('w', .16))))
        h = max(.04, min(.5, float(layout.get('h', w))))
        frame_id = session.get('frame_id') or (session.get('settings') or {}).get('frame_id')
        ch, cw = canvas.shape[:2]
        fit_x = fit_y = 0.0; fit_w = float(cw); fit_h = float(ch)
        if frame_id and re.match(r'^[a-f0-9]{12,32}$', str(frame_id)):
            frame = cv2.imread(os.path.join(FRAMES_DIR, str(frame_id)+'.png'), cv2.IMREAD_UNCHANGED)
            if frame is not None and frame.shape[1] and frame.shape[0]:
                fh, fw = frame.shape[:2]
                scale = min(cw / float(fw), ch / float(fh))
                fit_w, fit_h = fw * scale, fh * scale
                fit_x, fit_y = (cw-fit_w)/2.0, (ch-fit_h)/2.0
        size = max(200, int(round(min(w*fit_w, h*fit_h))))
        left = int(round(fit_x + x*fit_w)); top = int(round(fit_y + y*fit_h))
        left = max(0, min(cw-size, left)); top = max(0, min(ch-size, top)); size = min(size, cw-left, ch-top)
        import qrcode
        qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=1, border=4)
        qr.add_data(str(session['drive_url'])); qr.make(fit=True)
        matrix = __import__('numpy').asarray(qr.get_matrix(), dtype='uint8')
        qr_img = cv2.resize((255 - matrix*255), (size, size), interpolation=cv2.INTER_NEAREST)
        canvas[top:top+size, left:left+size] = cv2.cvtColor(qr_img, cv2.COLOR_GRAY2BGR)
        session['drive_qr_embedded'] = True
        session.pop('drive_qr_embed_error', None)
    except Exception as exc:
        session['drive_qr_embedded'] = False
        session['drive_qr_embed_error'] = str(exc)
        print('[GOOGLE_DRIVE_FRAME_QR_ERROR]', repr(exc), flush=True)
    return canvas


def _refresh_drive_qr_output(session):
    """Prepare a separate printable JPG with QR, never overwrite digital output.jpg.

    Called both when Drive folder/QR becomes available and after photo rendering,
    so either completion order can produce a printable QR without operator action.
    """
    if not (session or {}).get('drive_qr_enabled'):
        return False
    if not str(session.get('drive_url') or '').startswith('https://drive.google.com/'):
        return False
    sid = str(session.get('id') or '')
    if not re.fullmatch(r'[A-Za-z0-9_-]{6,64}', sid):
        return False
    folder = os.path.join(SESSIONS_DIR, sid)
    src = os.path.join(folder, 'output.jpg')
    dst = os.path.join(folder, 'output_print_qr.jpg')
    if not os.path.isfile(src):
        return False
    try:
        # The result may be rerendered when the customer changes filters.
        revision = str(session['drive_url']) + '|' + json.dumps(session.get('drive_qr_layout') or {},sort_keys=True)
        stamp = os.path.join(folder, 'output_print_qr.meta.json')
        fingerprint = hashlib.sha256(revision.encode('utf-8')).hexdigest()
        try:
            with open(stamp,encoding='utf-8') as fp: old = json.load(fp)
        except (OSError,ValueError):old={}
        if os.path.isfile(dst) and os.stat(dst).st_mtime_ns >= os.stat(src).st_mtime_ns and old.get('hash')==fingerprint:
            session['print_qr_ready']=True
            return True
        image = cv2.imread(src,cv2.IMREAD_COLOR)
        if image is None: return False
        session['drive_qr_embedded']=False
        _blend_drive_qr(image,session)
        if not session.get('drive_qr_embedded'):
            return False
        temp=dst+'.tmp.jpg'
        try:
            if not cv2.imwrite(temp,image,[int(cv2.IMWRITE_JPEG_QUALITY),98]):
                raise OSError('File cetak QR gagal ditulis.')
            os.replace(temp,dst)
            with open(stamp+'.tmp','w',encoding='utf-8') as fp:
                json.dump({'hash':fingerprint},fp)
            os.replace(stamp+'.tmp',stamp)
        finally:
            if os.path.isfile(temp):os.unlink(temp)
        session['print_qr_ready']=True
        session.pop('print_qr_error',None)
        return True
    except Exception as exc:
        session['print_qr_ready']=False
        session['print_qr_error']=str(exc)
        print('[KACA_PRINT_QR_PREPARE_ERROR]',repr(exc),flush=True)
        return False


def _blend_frame_png(canvas, session):
    frame_id = session.get('frame_id') or session.get('settings', {}).get('frame_id')
    if not frame_id: return canvas
    if not re.match(r'^[a-f0-9]{12,32}$', str(frame_id)): return canvas
    overlay = cv2.imread(os.path.join(FRAMES_DIR, frame_id + '.png'), cv2.IMREAD_UNCHANGED)
    if overlay is None: return canvas
    if overlay.shape[2] == 3: overlay = cv2.cvtColor(overlay, cv2.COLOR_BGR2BGRA)
    # Never stretch a frame PNG: fit it inside the print canvas and retain its native ratio.
    ch, cw = canvas.shape[:2]
    fh, fw = overlay.shape[:2]
    scale = min(cw / float(fw), ch / float(fh))
    nw, nh = max(1, int(round(fw * scale))), max(1, int(round(fh * scale)))
    interpolation = cv2.INTER_AREA if scale < 1 else cv2.INTER_CUBIC
    fitted = cv2.resize(overlay, (nw, nh), interpolation=interpolation)
    x, y = (cw - nw) // 2, (ch - nh) // 2
    region = canvas[y:y+nh, x:x+nw]
    alpha = fitted[:, :, 3:4].astype('float32') / 255.0
    canvas[y:y+nh, x:x+nw] = (fitted[:, :, :3].astype('float32') * alpha + region.astype('float32') * (1-alpha)).clip(0,255).astype('uint8')
    return canvas

def _output_dimensions(session, default_width, default_height, dpi_override=None):
    """Calculate pixel dimensions from physical paper size and selected print DPI."""
    settings = session.get('settings', {}) or {}
    dpi = int(dpi_override) if dpi_override else (600 if int(settings.get('print_dpi', settings.get('printDpi', 300)) or 300) >= 600 else 300)
    paper = str(session.get('paper_size', '4R')).strip().lower()
    if '2r' in paper:
        return 2*dpi, 6*dpi  # 2 x 6 inches
    if 'custom' in paper:
        try:
            width_in = max(1.0, min(20.0, float(settings.get('custom_width_inches', settings.get('customWidth', 4)))))
            height_in = max(1.0, min(20.0, float(settings.get('custom_height_inches', settings.get('customHeight', 6)))))
            return int(round(width_in * dpi)), int(round(height_in * dpi))
        except (TypeError, ValueError):
            pass
    frame_id = session.get('frame_id') or settings.get('frame_id')
    if frame_id and re.match(r'^[a-f0-9]{12,32}$', str(frame_id)):
        overlay = cv2.imread(os.path.join(FRAMES_DIR, str(frame_id) + '.png'), cv2.IMREAD_UNCHANGED)
        if overlay is not None and overlay.shape[1] > 0 and overlay.shape[0] > 0:
            # A frame PNG may choose 4R orientation, but the physical size stays 4 x 6 in.
            return (4*dpi, 6*dpi) if overlay.shape[0] > overlay.shape[1] else (6*dpi, 4*dpi)
    orientation = str(settings.get('orientation', 'landscape')).lower()
    return (4*dpi, 6*dpi) if orientation == 'portrait' else (6*dpi, 4*dpi)



def compose_output(session, selected_numbers=None, mark_finished=True):
    photos = session.get('photos', [])
    if selected_numbers is not None:
        by_number = {int(p.get('number', 0)): p for p in photos}
        photos = [by_number[int(n)] for n in selected_numbers if int(n) in by_number]
    if not photos: raise ValueError('Pilih minimal satu foto untuk dimasukkan ke frame.')
    session['selected_photo_numbers'] = [int(p.get('number', i+1)) for i, p in enumerate(photos)]
    paper = str(session.get('paper_size', '4R')).lower()
    orientation = str(session.get('settings', {}).get('orientation', 'landscape')).lower()
    if '2r' in paper: W,H=600,1800
    elif orientation == 'portrait': W,H=1200,1800
    else: W,H=1800,1200
    W,H = _output_dimensions(session, W, H)
    canvas = __import__('numpy').full((H,W,3),(24,23,22),dtype='uint8')
    visual_count = max(len(session.get('layout_slots') or []), len(photos))
    slots = _layout_slots(session,visual_count,W,H)
    for nx,ny,nw,nh,source_index in slots:
        if not photos: continue
        photo = photos[min(max(0,source_index),len(photos)-1)]
        image=cv2.imread(os.path.join(SESSIONS_DIR,session['id'],photo['edited']))
        if image is None: continue
        x,y,cw,ch=int(nx*W),int(ny*H),max(1,int(nw*W)),max(1,int(nh*H))
        # Fill each manually positioned slot; crop excess to preserve its exact shape.
        scale=max(cw/image.shape[1],ch/image.shape[0]); rw,rh=max(cw,int(image.shape[1]*scale)),max(ch,int(image.shape[0]*scale))
        resized=cv2.resize(image,(rw,rh),interpolation=cv2.INTER_AREA)
        ox=max(0,(rw-cw)//2); oy=max(0,(rh-ch)//2)
        canvas[y:min(H,y+ch),x:min(W,x+cw)] = resized[oy:oy+min(ch,H-y),ox:ox+min(cw,W-x)]
    _blend_frame_png(canvas,session)
    # Session QR is rendered only in the result UI; never burn it into customer photo files.
    out=os.path.join(SESSIONS_DIR,session['id'],'output.jpg')
    if not cv2.imwrite(out,canvas,[int(cv2.IMWRITE_JPEG_QUALITY),int((session.get('settings',{}) or {}).get('jpegQuality',100))]): raise RuntimeError('Gagal menyimpan hasil komposisi.')
    try:
        from PIL import Image
        im=Image.open(out); im.save(out,format='JPEG',quality=int((session.get('settings',{}) or {}).get('jpegQuality',100)),dpi=(int((session.get('settings',{}) or {}).get('print_dpi',300)),int((session.get('settings',{}) or {}).get('print_dpi',300))))
    except Exception as dpi_exc: print('[JPEG_DPI_METADATA]',repr(dpi_exc),flush=True)
    session['output']='output.jpg'
    if mark_finished:
        session['status']='finished'; session['finished_at']=datetime.datetime.now().isoformat(timespec='seconds')
    write_manifest(session); return out


def start_session_video(session_id, frame):
    """Start one continuous MP4 recording for the complete customer session."""
    global session_video_writer, session_video_path, session_video_id, session_video_last_write
    stop_session_video()
    h, w = frame.shape[:2]
    path = os.path.join(SESSIONS_DIR, session_id, 'session_live.mp4')
    try:
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        writer = cv2.VideoWriter(path, fourcc, 20.0, (w, h))
        if not writer.isOpened():
            writer.release()
            print('[VIDEO] MP4 VideoWriter unavailable; continuous recording disabled', flush=True)
            return False
        with video_lock:
            session_video_writer = writer
            session_video_path = path
            session_video_id = session_id
            session_video_last_write = 0.0
        print(f'[VIDEO] session recording started: {path} {w}x{h}', flush=True)
        return True
    except Exception as exc:
        print('[VIDEO_START_ERROR]', repr(exc), flush=True)
        return False


def stop_session_video():
    global session_video_writer, session_video_path, session_video_id
    with video_lock:
        writer = session_video_writer
        path = session_video_path
        session_video_writer = None
        session_video_path = None
        session_video_id = None
    if writer is not None:
        try:
            writer.release()
            print(f'[VIDEO] session recording stopped: {path}', flush=True)
        except Exception as exc:
            print('[VIDEO_STOP_ERROR]', repr(exc), flush=True)


def event_frame_owner_error(frame_id, event_id):
    """Prevent a booth event from accidentally using frames belonging to another profile."""
    fid=str(frame_id or '').strip()
    if not fid: return None
    if not re.fullmatch(r'[a-f0-9]{12,32}',fid): return 'ID frame tidak valid.'
    filename=os.path.join(FRAMES_DIR,fid+'.png')
    if not os.path.isfile(filename): return 'Frame yang dipilih tidak ditemukan.'
    try:
        with open(os.path.join(FRAMES_DIR,fid+'.json'),'r',encoding='utf-8') as f:
            meta=json.load(f)
    except (OSError,ValueError): meta={}
    if str(meta.get('event_id') or '') != str(event_id or ''):
        return 'Frame berasal dari event lain. Pilih frame khusus event yang aktif.'
    return None


def start_booth_video(frame, source=0, event_id=None, event_name=None, frame_id=None, mirror=False, rotation=0, flip_horizontal=False, flip_vertical=False):
    global booth_video_writer, booth_video_id, booth_video_path, booth_video_last_write, booth_video_frames, booth_video_started_at, booth_video_source, booth_video_event_id, booth_video_event_name, booth_video_frame_id, booth_video_frame_overlay, booth_video_mirror, booth_video_rotation, booth_video_flip_horizontal, booth_video_flip_vertical
    with video_lock:
        if booth_video_writer is not None:
            raise RuntimeError('Perekaman video sedang berlangsung.')
        if frame is None or getattr(frame, 'size', 0) == 0:
            raise RuntimeError('Frame kamera kosong; preview belum siap.')
        prepared = _apply_camera_orientation(frame,rotation,flip_horizontal,flip_vertical,mirror)
        h, w = prepared.shape[:2]
        video_id = uuid.uuid4().hex[:12]
        folder = os.path.join(DATA_DIR, 'video_sessions')
        os.makedirs(folder, exist_ok=True)
        path = os.path.join(folder, video_id + '.mp4')
        writer = cv2.VideoWriter(path, cv2.VideoWriter_fourcc(*'mp4v'), 20.0, (w, h))
        if not writer.isOpened():
            writer.release()
            raise RuntimeError('Encoder MP4 tidak tersedia pada perangkat ini.')
        booth_video_writer = writer
        booth_video_id = video_id
        booth_video_path = path
        booth_video_last_write = 0.0
        booth_video_frames = 0
        booth_video_started_at = time.time()
        booth_video_source = 1 if int(source or 0) == 1 else 0
        booth_video_event_id = str(event_id or '') or None
        booth_video_event_name = str(event_name or '')[:100]
        booth_video_frame_id = str(frame_id or '') or None
        booth_video_mirror = bool(mirror)
        booth_video_rotation = int(rotation or 0)%360
        booth_video_flip_horizontal = bool(flip_horizontal)
        booth_video_flip_vertical = bool(flip_vertical)
        booth_video_frame_overlay = None
        if booth_video_frame_id:
            rgba = cv2.imread(os.path.join(FRAMES_DIR, booth_video_frame_id+'.png'), cv2.IMREAD_UNCHANGED)
            if rgba is not None:
                if rgba.ndim == 2: rgba = cv2.cvtColor(rgba,cv2.COLOR_GRAY2BGRA)
                if rgba.shape[2] == 3: rgba = cv2.cvtColor(rgba,cv2.COLOR_BGR2BGRA)
                fh,fw=rgba.shape[:2];scale=min(w/float(fw),h/float(fh))
                nw,nh=max(1,int(round(fw*scale))),max(1,int(round(fh*scale)))
                fitted=cv2.resize(rgba,(nw,nh),interpolation=cv2.INTER_AREA if scale<1 else cv2.INTER_LINEAR)
                mask=__import__('numpy').zeros((h,w,4),dtype='uint8')
                ox,oy=(w-nw)//2,(h-nh)//2
                mask[oy:oy+nh,ox:ox+nw]=fitted
                booth_video_frame_overlay=mask
        return {'ok': True, 'id': video_id, 'width': w, 'height': h, 'fps': 20, 'source': booth_video_source, 'frame_id':booth_video_frame_id}


def write_booth_video_frame(frame, source=0):
    """Write frames from either the primary or secondary camera into the active booth recording."""
    global booth_video_last_write, booth_video_frames
    if frame is None or getattr(frame, 'size', 0) == 0:
        return
    with video_lock:
        writer = booth_video_writer
        if writer is None or booth_video_source != (1 if int(source or 0) == 1 else 0):
            return
        now_mono = time.monotonic()
        if now_mono - booth_video_last_write < 0.05:
            return
        try:
            h, w = frame.shape[:2]
            target_w = int(writer.get(cv2.CAP_PROP_FRAME_WIDTH) or w)
            target_h = int(writer.get(cv2.CAP_PROP_FRAME_HEIGHT) or h)
            oriented=_apply_camera_orientation(frame,booth_video_rotation,booth_video_flip_horizontal,booth_video_flip_vertical,booth_video_mirror)
            oh,ow=oriented.shape[:2]
            out = oriented if (ow == target_w and oh == target_h) else cv2.resize(oriented, (target_w, target_h), interpolation=cv2.INTER_AREA)
            # Blend the same selected PNG frame into recorded video frames.
            if booth_video_frame_overlay is not None:
                mask=booth_video_frame_overlay
                import numpy as np
                a=mask[:,:,3:4].astype('float32')/255.0
                out=(out.astype('float32')*(1-a)+mask[:,:,:3].astype('float32')*a).clip(0,255).astype('uint8')
            writer.write(__import__('numpy').ascontiguousarray(out))
            booth_video_last_write = now_mono
            booth_video_frames += 1
        except Exception as exc:
            print('[BOOTH_VIDEO_WRITE_ERROR]', repr(exc), flush=True)


def build_booth_video_webm_preview(video_id, source_path):
    """Encode a VP8/VP9 WebM preview that Chromium/Electron can play reliably.

    The archive MP4 remains the authoritative original, and uploads are queued
    separately. The browser never needs to decode OpenCV's MPEG-4 Part 2 MP4.
    """
    target=os.path.join(DATA_DIR,'video_sessions',video_id+'.webm')
    temp=target+'.tmp.webm'
    try:
        video=cv2.VideoCapture(source_path)
        if not video.isOpened():raise RuntimeError('MP4 sumber tidak dapat dibuka oleh encoder.')
        fps=float(video.get(cv2.CAP_PROP_FPS) or 20)
        fps=max(5.0,min(30.0,fps))
        width=int(video.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
        height=int(video.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
        if width<1 or height<1:raise RuntimeError('Resolusi sumber video kosong.')
        writer=None
        for codec in ('VP80','VP90'):
            trial=cv2.VideoWriter(temp,cv2.VideoWriter_fourcc(*codec),fps,(width,height))
            if trial.isOpened():writer=trial;break
            trial.release()
        if writer is None:raise RuntimeError('Encoder VP8/VP9 WebM tidak tersedia pada komputer.')
        frames=0
        try:
            while True:
                ok,frame=video.read()
                if not ok:break
                writer.write(__import__('numpy').ascontiguousarray(frame))
                frames+=1
        finally:
            writer.release()
            video.release()
        if frames<2 or not os.path.isfile(temp) or os.path.getsize(temp)<1000:
            raise RuntimeError('File WebM belum berisi video valid.')
        os.replace(temp,target)
        video_preview_errors.pop(video_id,None)
        print('[BOOTH_VIDEO_PREVIEW_READY]',video_id,'frames',frames,flush=True)
    except Exception as exc:
        video_preview_errors[video_id]=str(exc)
        print('[BOOTH_VIDEO_PREVIEW_ERROR]',video_id,repr(exc),flush=True)
        try:
            if os.path.exists(temp):os.unlink(temp)
        except OSError:pass


def stop_booth_video():
    global booth_video_writer, booth_video_id, booth_video_path, booth_video_last_write, booth_video_frames, booth_video_started_at, booth_video_source, booth_video_event_id, booth_video_event_name, booth_video_frame_id, booth_video_frame_overlay, booth_video_mirror, booth_video_rotation, booth_video_flip_horizontal, booth_video_flip_vertical
    with video_lock:
        writer, video_id, path = booth_video_writer, booth_video_id, booth_video_path
        frames, started = booth_video_frames, booth_video_started_at
        event_id, event_name = booth_video_event_id, booth_video_event_name
        frame_id = booth_video_frame_id
        booth_video_writer = None
        booth_video_id = None
        booth_video_path = None
        booth_video_last_write = 0.0
        booth_video_frames = 0
        booth_video_started_at = None
        booth_video_source = 0
        booth_video_event_id = None
        booth_video_event_name = None
        booth_video_frame_id = None
        booth_video_frame_overlay = None
        booth_video_mirror = False
        booth_video_rotation = 0
        booth_video_flip_horizontal = False
        booth_video_flip_vertical = False
    if writer is None or not path:
        return {'ok': False, 'error': 'Tidak ada perekaman video yang aktif.'}
    writer.release()
    duration = max(0.0, time.time() - (started or time.time()))
    if frames < 2 or not os.path.isfile(path) or os.path.getsize(path) < 1024:
        try: os.remove(path)
        except OSError: pass
        raise RuntimeError(f'Rekaman belum menerima frame yang cukup ({frames} frame). Periksa preview kamera dan coba lagi.')
    local_path = None
    try:
        folder = os.path.join(_event_archive_root({'event_id':event_id, 'event_name':event_name}), 'Video_Results')
        os.makedirs(folder, exist_ok=True)
        local_path = os.path.join(folder, video_id + '.mp4')
        shutil.copy2(path, local_path)
        # Persist a local video poster, allowing the common result template to
        # preview the video even if Drive has not yet finished uploading.
        cap=cv2.VideoCapture(path)
        try:
            grabbed, first=cap.read()
            if grabbed and first is not None:
                cv2.imwrite(os.path.join(folder,video_id+'_Poster.jpg'),first,[int(cv2.IMWRITE_JPEG_QUALITY),94])
        finally: cap.release()
        with open(os.path.join(folder, video_id + '.json'), 'w', encoding='utf-8') as fp:
            json.dump({'id': video_id, 'created_at': datetime.datetime.now().isoformat(timespec='seconds'), 'duration_seconds': round(duration, 2), 'frames': frames, 'file': os.path.basename(local_path), 'event_id':event_id, 'event_name':event_name,'frame_id':frame_id}, fp, ensure_ascii=False, indent=2)
    except Exception as exc:
        print('[VIDEO_ARCHIVE_ERROR]', repr(exc), flush=True)
    # Generate browser-playable VP8/VP9 preview in the background. Local MP4 is
    # already durable and its Google Drive upload is not blocked by encoding.
    threading.Thread(target=build_booth_video_webm_preview,args=(video_id,path),daemon=True).start()
    drive_job = enqueue_drive_job('video', local_path, 'Video_'+video_id, video_id, event_id=event_id) if local_path else None
    return {'ok': True, 'id': video_id, 'duration_seconds': round(duration, 2), 'frames': frames, 'size_bytes': os.path.getsize(path), 'url': f'http://127.0.0.1:{PORT}/api/video/{video_id}.mp4', 'local_path': local_path, 'drive_job_id': video_id if drive_job else None, 'frame_id': frame_id, 'drive_status': drive_job.get('status') if drive_job else 'local_only', 'archive_warning': None if local_path else 'Video tersimpan pada data aplikasi, tetapi gagal disalin ke folder arsip lokal.'}


def _session_camera_orientation(session, source=None):
    """Orientation fields belong to the camera angle used for this shot."""
    angle=int(session.get('camera_angle',0) if source is None else source)
    secondary=angle==1
    return (int(session.get('camera_rotation2',0) if secondary else session.get('camera_rotation',0))%360,
            bool(session.get('camera_flip_horizontal2',False) if secondary else session.get('camera_flip_horizontal',False)),
            bool(session.get('camera_flip_vertical2',False) if secondary else session.get('camera_flip_vertical',False)))


def _apply_camera_orientation(frame, rotation=0, flip_horizontal=False, flip_vertical=False, mirror=False):
    """Apply session orientation to a copy; never mutate the camera reader buffer."""
    if frame is None or not getattr(frame, 'size', 0):
        return frame
    out = frame
    try:
        angle = int(rotation or 0) % 360
    except Exception:
        angle = 0
    if angle == 90:
        out = cv2.rotate(out, cv2.ROTATE_90_CLOCKWISE)
    elif angle == 180:
        out = cv2.rotate(out, cv2.ROTATE_180)
    elif angle == 270:
        out = cv2.rotate(out, cv2.ROTATE_90_COUNTERCLOCKWISE)
    horizontal = bool(flip_horizontal) ^ bool(mirror)
    vertical = bool(flip_vertical)
    if horizontal and vertical:
        out = cv2.flip(out, -1)
    elif horizontal:
        out = cv2.flip(out, 1)
    elif vertical:
        out = cv2.flip(out, 0)
    return out


def start_shot_live_photo(session_id, photo_number, frame, duration_seconds=5, mirror=False, source=0, quality='high', rotation=0, flip_horizontal=False, flip_vertical=False):
    """Start full-resolution camera recording directly to MP4; keep only small preview samples in RAM."""
    global shot_video_writer, shot_video_path, shot_video_session_id, shot_video_number
    global shot_video_started_at, shot_video_last_write, shot_video_frame_count, shot_video_codec, shot_video_last_result
    global shot_video_frames, shot_video_sampled_at, shot_video_target_seconds, shot_video_mirror, shot_video_rotation, shot_video_flip_horizontal, shot_video_flip_vertical, shot_video_fps, shot_video_width, shot_video_height, shot_video_source
    stop_shot_live_photo(discard=True)
    if frame is None or getattr(frame, 'size', 0) == 0:
        print('[LIVE_PHOTO] cannot start: first camera frame is empty', flush=True)
        return False
    path = os.path.join(SESSIONS_DIR, session_id, f'live_{photo_number:02d}.mp4')
    os.makedirs(os.path.dirname(path), exist_ok=True)
    try:
        if os.path.exists(path): os.remove(path)
    except OSError:
        pass
    frame = _apply_camera_orientation(frame, rotation, flip_horizontal, flip_vertical, mirror)
    h, w = frame.shape[:2]
    source_h, source_w = h, w
    scale = min(1.0, 960.0 / max(w, h))
    w = max(2, int(w * scale) // 2 * 2)
    h = max(2, int(h * scale) // 2 * 2)
    fps = 10.0
    try:
        with capture_lock:
            if cap is not None and cap.isOpened():
                reported = float(cap.get(cv2.CAP_PROP_FPS) or 0)
                if 5.0 <= reported <= 60.0: fps = min(10.0, reported)
    except Exception:
        pass
    writer = None
    chosen = None
    for candidate in ('mp4v', 'avc1', 'H264', 'MP4V'):
        trial = cv2.VideoWriter(path, cv2.VideoWriter_fourcc(*candidate), fps, (w, h))
        if trial is not None and trial.isOpened():
            try:
                if hasattr(cv2,'VIDEOWRITER_PROP_QUALITY'): trial.set(cv2.VIDEOWRITER_PROP_QUALITY, {'high':70,'balanced':55,'compact':40}.get(str(quality),55))
            except Exception: pass
            writer, chosen = trial, candidate
            break
        if trial is not None: trial.release()
    if writer is None:
        print('[LIVE_PHOTO] failed to open full-resolution video writer', flush=True)
        return False
    started = time.monotonic()
    with video_lock:
        shot_video_writer = writer
        shot_video_path = path
        shot_video_session_id = session_id
        shot_video_number = photo_number
        shot_video_started_at = started
        shot_video_last_write = started
        shot_video_frame_count = 0
        shot_video_codec = chosen
        shot_video_fps = fps
        shot_video_width = w
        shot_video_height = h
        shot_video_target_seconds = max(5, min(30, int(duration_seconds or 5)))
        shot_video_mirror = bool(mirror)
        shot_video_rotation = int(rotation or 0) % 360
        shot_video_flip_horizontal = bool(flip_horizontal)
        shot_video_flip_vertical = bool(flip_vertical)
        shot_video_source = int(source or 0)
        shot_video_frames = []
        shot_video_sampled_at = started
        shot_video_last_result = {'frames': 0, 'duration': 0.0, 'fps': fps, 'width': w, 'height': h, 'codec': chosen, 'size_bytes': 0}
    print(f'[LIVE_PHOTO] lightweight recording started: {w}x{h} @ {fps:.2f}fps (camera source {source_w}x{source_h}) codec={chosen}', flush=True)
    return True

def create_browser_preview_webm(mp4_path, frames, fps):
    """Create a Chromium-friendly VP8/VP9 WebM companion for in-app preview.

    Keep the MP4 as the customer download/original deliverable; Chromium builds
    may not include MPEG-4 Part 2 (mp4v) decoding, even when Windows Media Player does.
    """
    base = os.path.splitext(mp4_path)[0]
    preview_path = base + '.webm'
    if not frames:
        return None
    h, w = frames[0].shape[:2]
    for codec in ('VP80', 'VP90'):
        writer = None
        try:
            writer = cv2.VideoWriter(preview_path, cv2.VideoWriter_fourcc(*codec), float(fps), (w, h))
            if not writer.isOpened():
                writer.release(); writer = None
                continue
            for frame in frames:
                if frame.shape[1] != w or frame.shape[0] != h:
                    frame = cv2.resize(frame, (w, h))
                writer.write(__import__('numpy').ascontiguousarray(frame))
            writer.release(); writer = None
            if os.path.isfile(preview_path) and os.path.getsize(preview_path) > 1000:
                check = cv2.VideoCapture(preview_path)
                ok, _ = check.read()
                count = check.get(cv2.CAP_PROP_FRAME_COUNT)
                check.release()
                if ok and count >= 2:
                    print(f'[LIVE_PHOTO_PREVIEW] saved: codec={codec} frames={int(count)} size={os.path.getsize(preview_path)}', flush=True)
                    return os.path.basename(preview_path)
        except Exception as exc:
            print('[LIVE_PHOTO_PREVIEW_ERROR]', repr(exc), flush=True)
        finally:
            if writer is not None:
                try: writer.release()
                except Exception: pass
    try:
        if os.path.exists(preview_path): os.remove(preview_path)
    except OSError: pass
    return None


def create_full_quality_browser_preview(mp4_path):
    """Transcode the finished MP4 to a Chromium-friendly WebM without reducing dimensions or FPS."""
    preview_path = os.path.splitext(mp4_path)[0] + '.webm'
    source = cv2.VideoCapture(mp4_path)
    if not source.isOpened():
        source.release()
        return None
    fps = float(source.get(cv2.CAP_PROP_FPS) or 30.0)
    if not 5.0 <= fps <= 60.0: fps = 30.0
    width = int(source.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
    height = int(source.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
    if width < 2 or height < 2:
        source.release(); return None
    for codec in ('VP90', 'VP80'):
        writer = None
        try:
            writer = cv2.VideoWriter(preview_path, cv2.VideoWriter_fourcc(*codec), fps, (width, height))
            if not writer.isOpened():
                writer.release(); writer = None
                continue
            try:
                if hasattr(cv2, 'VIDEOWRITER_PROP_QUALITY'):
                    writer.set(cv2.VIDEOWRITER_PROP_QUALITY, 95)
            except Exception:
                pass
            written = 0
            source.set(cv2.CAP_PROP_POS_FRAMES, 0)
            while True:
                ok, frame = source.read()
                if not ok: break
                if frame.shape[1] != width or frame.shape[0] != height:
                    frame = cv2.resize(frame, (width, height), interpolation=cv2.INTER_AREA)
                writer.write(__import__('numpy').ascontiguousarray(frame))
                written += 1
            writer.release(); writer = None
            if written >= 2 and os.path.isfile(preview_path) and os.path.getsize(preview_path) > 1000:
                check = cv2.VideoCapture(preview_path)
                ok, _ = check.read()
                out_w = int(check.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
                out_h = int(check.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
                out_fps = float(check.get(cv2.CAP_PROP_FPS) or 0)
                check.release()
                if ok and (out_w, out_h) == (width, height) and out_fps >= 5:
                    print(f'[LIVE_PHOTO_PREVIEW] full quality: {out_w}x{out_h} @ {out_fps:.2f}fps frames={written} codec={codec}', flush=True)
                    source.release()
                    return os.path.basename(preview_path)
        except Exception as exc:
            print('[LIVE_PHOTO_PREVIEW_ERROR]', repr(exc), flush=True)
        finally:
            if writer is not None:
                try: writer.release()
                except Exception: pass
    source.release()
    try:
        if os.path.exists(preview_path): os.remove(preview_path)
    except OSError: pass
    return None

def _normalize_live_photo_duration(path, target_seconds, output_fps):
    """Re-time a shot using held frames to match the actual countdown length.

    A camera under heavy load may supply only e.g. 30 frames during a 5s
    countdown. Encoding those 30 frames at 10fps makes the clip play in 3s.
    We remap recorded frames across the selected duration without inventing
    nonexistent camera detail or requiring a memory-sized full-frame buffer.
    """
    target_seconds = max(5, min(30, int(target_seconds or 5)))
    fps = max(5.0, min(30.0, float(output_fps or 10.0)))
    source = cv2.VideoCapture(path)
    if not source.isOpened():
        source.release()
        raise RuntimeError('Live Photo tidak dapat dibuka untuk pemeriksaan durasi.')
    try:
        count = int(source.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        width = int(source.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
        height = int(source.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
        required = max(2, round(target_seconds * fps))
        if count < 2 or width < 2 or height < 2:
            raise RuntimeError('Live Photo tidak memiliki frame yang cukup.')
        if count == required:
            return required, round(required / fps, 2)
        tmp = path + '.duration-fixed.mp4'
        writer = cv2.VideoWriter(tmp, cv2.VideoWriter_fourcc(*'mp4v'), fps, (width, height))
        if not writer.isOpened():
            writer.release()
            raise RuntimeError('Encoder durasi Live Photo tidak tersedia.')
        current_index = -1
        last_frame = None
        try:
            for i in range(required):
                wanted = min(count - 1, int(round(i * (count-1) / max(1,required-1))))
                while current_index < wanted:
                    success, frame = source.read()
                    if not success: break
                    current_index += 1
                    last_frame = frame
                if last_frame is None:
                    raise RuntimeError('Video sumber Live Photo tidak dapat dibaca.')
                writer.write(last_frame)
        finally:
            writer.release()
        check = cv2.VideoCapture(tmp)
        output_frames = int(check.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        output_fps_actual = float(check.get(cv2.CAP_PROP_FPS) or 0)
        check.release()
        duration = output_frames / output_fps_actual if output_fps_actual else 0
        if output_frames < required-1 or abs(duration-target_seconds) > 0.25:
            raise RuntimeError(f'Durasi hasil Live Photo tidak sesuai ({duration:.2f}s != {target_seconds}s).')
        os.replace(tmp, path)
        print(f'[LIVE_DURATION_FIXED] {count} -> {output_frames} frames, {target_seconds}s',flush=True)
        return output_frames, round(duration,2)
    finally:
        source.release()
        temporary = path + '.duration-fixed.mp4'
        if os.path.exists(temporary):
            try: os.remove(temporary)
            except OSError: pass


def stop_shot_live_photo(discard=False):
    """Finalize full-resolution MP4 and a same-resolution, same-FPS Chromium preview."""
    global shot_video_writer, shot_video_path, shot_video_session_id, shot_video_number
    global shot_video_started_at, shot_video_frame_count, shot_video_codec, shot_video_last_result
    global shot_video_frames, shot_video_target_seconds, shot_video_sampled_at, shot_video_mirror, shot_video_fps
    with video_lock:
        path = shot_video_path
        writer = shot_video_writer
        started = shot_video_started_at
        codec = shot_video_codec
        count = int(shot_video_frame_count)
        fps = float(shot_video_fps or 30.0)
        full_w, full_h = int(shot_video_width or 0), int(shot_video_height or 0)
        target_seconds = shot_video_target_seconds
        shot_video_writer = None
        shot_video_path = None
        shot_video_session_id = None
        shot_video_number = None
        shot_video_started_at = None
        shot_video_frame_count = 0
        shot_video_codec = None
        shot_video_frames = []
        shot_video_sampled_at = 0.0
        shot_video_mirror = False
    elapsed = max(0.0, time.monotonic() - started) if started else 0.0
    if writer is not None:
        try: writer.release()
        except Exception: pass
    if discard or not path or count < 2:
        if path:
            try:
                if os.path.exists(path): os.remove(path)
            except OSError: pass
        shot_video_last_result = {'frames': count, 'duration': 0.0, 'fps': fps, 'codec': codec, 'size_bytes': 0, 'target_seconds': target_seconds}
        print(f'[LIVE_PHOTO] discarded: frames={count} elapsed={elapsed:.2f}s discard={discard}', flush=True)
        return None
    try:
        size = os.path.getsize(path) if os.path.isfile(path) else 0
        duration = round(count / fps, 2)
        if count < 8 or size < 1000 or duration < 0.8:
            raise RuntimeError(f'Video terlalu pendek/kosong: frames={count}, size={size}, duration={duration}s')
        # Normalize before the asynchronous WebM conversion reads this MP4.
        # Keep the captured master if the local encoder fails; the framed
        # result renderer still guarantees the selected output duration.
        duration_warning = None
        try:
            count, duration = _normalize_live_photo_duration(path, target_seconds, fps)
        except Exception as exc:
            duration_warning = str(exc)
            print('[LIVE_DURATION_NORMALIZE_WARNING]', repr(exc), flush=True)
        size = os.path.getsize(path)
        # Keep MP4 as the archival master. Build the Chromium WebM companion in
        # the background so conversion never delays the next capture.
        preview_name = os.path.splitext(os.path.basename(path))[0] + '.webm'
        def _make_preview_async(source_path, expected_name):
            result = create_full_quality_browser_preview(source_path)
            if result:
                print(f'[LIVE_PHOTO_PREVIEW] ready: {result}', flush=True)
            else:
                print(f'[LIVE_PHOTO_PREVIEW] unavailable: {expected_name}', flush=True)
        threading.Thread(target=_make_preview_async, args=(path, preview_name), daemon=True, name='LivePhotoPreview').start()
        shot_video_last_result = {'frames': count, 'duration': duration, 'fps': fps, 'width': full_w, 'height': full_h, 'codec': codec, 'size_bytes': size, 'preview': preview_name, 'preview_codec': 'VP8/VP9 (background)', 'preview_pending': True, 'target_seconds': target_seconds, 'recorded_seconds': round(elapsed, 2), 'duration_warning':duration_warning}
        print(f'[LIVE_PHOTO] saved full-resolution: frames={count} duration={duration}s fps={fps:.2f} size={size} codec={codec} preview=background:{preview_name}', flush=True)
        return os.path.basename(path)
    except Exception as exc:
        print('[LIVE_PHOTO_FINALIZE_ERROR]', repr(exc), flush=True)
        try:
            if os.path.exists(path): os.remove(path)
        except OSError: pass
        shot_video_last_result = {'frames': count, 'duration': 0.0, 'fps': fps, 'codec': codec, 'size_bytes': 0, 'target_seconds': target_seconds, 'error': str(exc)}
        return None

# v0.9.66: on-demand animated GIF is a browser-decoder-independent backup for
# Live Photo in the result slide. It is not uploaded to Drive or substituted for MP4.
_live_animation_tasks=set()
_live_animation_failed={}
_live_animation_guard=threading.RLock()

def _start_live_animation_generation(sid, manifest):
    session_dir=os.path.join(SESSIONS_DIR,sid)
    archive_dir=str(manifest.get('local_archive_path') or '')
    destination=os.path.join(session_dir,'output_live.gif')
    if os.path.isfile(destination) and os.path.getsize(destination)>1024:
        return 'ready'
    candidates=[os.path.join(session_dir,'output_live.mp4'),
                os.path.join(archive_dir,'Live_Photos','Live_Photo_Frame.mp4') if archive_dir else '',
                os.path.join(session_dir,'output_live.webm'),
                os.path.join(archive_dir,'Live_Photos','Live_Photo_Frame.webm') if archive_dir else '']
    source=next((c for c in candidates if c and os.path.isfile(c) and os.path.getsize(c)>1024),None)
    if not source or cv2 is None:return 'unavailable'
    with _live_animation_guard:
        if sid in _live_animation_tasks:return 'processing'
        if time.time()-_live_animation_failed.get(sid,0)<45:return 'unavailable'
        _live_animation_tasks.add(sid)
    def worker():
        # OpenCV VideoCapture/FFmpeg can terminate the entire Python process on
        # some Windows driver/codec combinations. Run GIF decoding out-of-process.
        try:
            helper=os.path.join(os.path.dirname(os.path.abspath(__file__)),'live_gif_worker.py')
            args=[sys.executable,'-u',helper,source,destination,archive_dir]
            flags=getattr(subprocess,'CREATE_NO_WINDOW',0) if os.name=='nt' else 0
            completed=subprocess.run(args,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,
                                     timeout=65,creationflags=flags,check=False,text=True,errors='replace')
            if completed.returncode!=0:
                raise RuntimeError(f'Proses GIF berhenti dengan kode {completed.returncode}: '+completed.stdout[-1500:])
            if not (os.path.isfile(destination) and os.path.getsize(destination)>1024):
                raise RuntimeError('Pekerja GIF selesai tanpa file animasi yang valid: '+completed.stdout[-1000:])
            with _live_animation_guard:_live_animation_failed.pop(sid,None)
            print('[LIVE_GIF_FALLBACK_READY]',sid,os.path.getsize(destination),flush=True)
        except Exception as exc:
            with _live_animation_guard:_live_animation_failed[sid]=time.time()
            print('[LIVE_GIF_FALLBACK_ERROR]',sid,repr(exc),flush=True)
        finally:
            with _live_animation_guard:_live_animation_tasks.discard(sid)
    threading.Thread(target=worker,name='LiveGifFallback-'+sid,daemon=True).start()
    print('[LIVE_GIF_FALLBACK_STARTED]',sid,flush=True)
    return 'processing'

def compose_live_output(session, selected_photos):
    """Create a framed MP4 where every selected slot plays its matching Live Photo."""
    clips = {}
    for photo in {int(p.get('number', 0)): p for p in selected_photos}.values():
        number = int(photo.get('number', 0))
        name = photo.get('live_photo')
        cap_video = None
        if name:
            candidate = cv2.VideoCapture(os.path.join(SESSIONS_DIR, session['id'], name))
            if candidate.isOpened():
                cap_video = candidate
            else:
                candidate.release()
        still = cv2.imread(os.path.join(SESSIONS_DIR, session['id'], photo.get('edited', '')))
        clips[number] = {'cap': cap_video, 'last': still, 'still': still}
    # At least one real Live Photo clip is required; missing clips use their still photo
    # rather than preventing the entire framed Live Photo file from being delivered.
    if not any(item['cap'] is not None for item in clips.values()):
        return None
    paper = str(session.get('paper_size', '4R')).lower()
    orientation = str(session.get('settings', {}).get('orientation', 'landscape')).lower()
    if '2r' in paper: W,H=480,1440
    elif orientation == 'portrait': W,H=720,1080
    else: W,H=1080,720
    W,H = _output_dimensions(session, W, H, dpi_override=150)
    # Live Photo is a lightweight motion preview; the still JPG remains full quality.
    scale=min(1.0, 960.0/max(W,H))
    W=max(2,int(W*scale)//2*2); H=max(2,int(H*scale)//2*2)
    visual_count=max(len(session.get('layout_slots') or []),len(selected_photos))
    live_slots=_layout_slots(session,visual_count,W,H)
    target_seconds=max(5,min(30,int(session.get('live_photo_duration_seconds',5) or 5)))
    first_cap=next((item['cap'] for item in clips.values() if item['cap'] is not None), None)
    if first_cap is None: return None
    output_fps=max(5.0,min(10.0,float(first_cap.get(cv2.CAP_PROP_FPS) or 8.0)))
    total_frames=max(1,int(round(target_seconds*output_fps)))
    out_path=os.path.join(SESSIONS_DIR,session['id'],'output_live.mp4')
    webm_path=os.path.join(SESSIONS_DIR,session['id'],'output_live.webm')
    writer=None
    webm_writer=None
    try:
        writer=cv2.VideoWriter(out_path,cv2.VideoWriter_fourcc(*'mp4v'),output_fps,(W,H))
        # Encode the Chromium/Electron preview from the same composed frames,
        # rather than transcoding the MP4 afterward (which can fail on mp4v decoders).
        for webm_codec in ('VP90','VP80'):
            candidate=cv2.VideoWriter(webm_path,cv2.VideoWriter_fourcc(*webm_codec),output_fps,(W,H))
            if candidate.isOpened():
                webm_writer=candidate
                print('[LIVE_OUTPUT_WEBM_ENCODER]', webm_codec, W, H, output_fps, flush=True)
                break
            candidate.release()
        try:
            if hasattr(cv2,'VIDEOWRITER_PROP_QUALITY'): writer.set(cv2.VIDEOWRITER_PROP_QUALITY, {'high':75,'balanced':60,'compact':45}.get(str((session.get('settings',{}) or {}).get('video_quality','compact')),45))
        except Exception: pass
        if not writer.isOpened(): raise RuntimeError('Encoder untuk frame Live Photo tidak tersedia.')
        for frame_index in range(total_frames):
            canvas=__import__('numpy').full((H,W,3),(24,23,22),dtype='uint8')
            current_frames={}
            for number,item in clips.items():
                if item['cap'] is not None:
                    ok, fr=item['cap'].read()
                    if ok: item['last']=fr
                current_frames[number]=item['last']
            for nx,ny,nw,nh,source_index in live_slots:
                if not selected_photos: continue
                photo=selected_photos[min(max(0,source_index),len(selected_photos)-1)]
                x,y,cw,ch=int(nx*W),int(ny*H),max(1,int(nw*W)),max(1,int(nh*H))
                item=clips[int(photo.get('number',0))]
                frame=current_frames.get(int(photo.get('number',0)),item['last'])
                if frame is None:
                    frame=cv2.imread(os.path.join(SESSIONS_DIR,session['id'],photo['edited']))
                elif item['cap'] is not None:
                    frame=apply_filter(frame, session.get('filter', 'sepia'))
                if frame is not None:
                    scale=max(cw/frame.shape[1],ch/frame.shape[0]); rw,rh=max(cw,int(frame.shape[1]*scale)),max(ch,int(frame.shape[0]*scale))
                    resized=cv2.resize(frame,(rw,rh),interpolation=cv2.INTER_AREA); ox=max(0,(rw-cw)//2); oy=max(0,(rh-ch)//2)
                    canvas[y:min(H,y+ch),x:min(W,x+cw)]=resized[oy:oy+min(ch,H-y),ox:ox+min(cw,W-x)]
            _blend_frame_png(canvas,session)
            writer.write(canvas)
            if webm_writer is not None:
                webm_writer.write(canvas)
        writer.release(); writer=None
        if webm_writer is not None:
            webm_writer.release(); webm_writer=None
        for item in clips.values():
            if item['cap'] is not None: item['cap'].release()
        if os.path.isfile(out_path) and os.path.getsize(out_path)>1000:
            # Keep MP4 as the downloadable master, and create a WebM companion for Chromium.
            # The renderer uses WebM because OpenCV's mp4v (MPEG-4 Part 2) is not
            # consistently decodable by Chromium/Electron even when Windows can play it.
            check_master=cv2.VideoCapture(out_path)
            final_frames=float(check_master.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
            final_fps=float(check_master.get(cv2.CAP_PROP_FPS) or 0)
            check_master.release()
            if final_fps < 1 or abs((final_frames / final_fps) - target_seconds) > .3:
                raise RuntimeError('Durasi final Live Photo tidak sesuai pengaturan. Harap ulangi render.')
            preview_name = 'output_live.webm' if os.path.isfile(webm_path) and os.path.getsize(webm_path)>1000 else create_full_quality_browser_preview(out_path)
            if preview_name == 'output_live.webm':
                check=cv2.VideoCapture(webm_path)
                preview_ok, _frame=check.read()
                check.release()
                if not preview_ok:
                    try: os.remove(webm_path)
                    except OSError: pass
                    preview_name=create_full_quality_browser_preview(out_path)
            session['live_output_preview'] = preview_name
            if not preview_name:
                print('[LIVE_OUTPUT_PREVIEW_WARNING] MP4 master saved but Chromium WebM preview could not be encoded.', flush=True)
            else:
                print('[LIVE_OUTPUT_PREVIEW_READY]', session['id'], preview_name, flush=True)
            return 'output_live.mp4'
        raise RuntimeError('Output Live Photo tidak berisi frame.')
    except Exception as exc:
        print('[LIVE_OUTPUT_ERROR]',repr(exc),flush=True)
        if writer is not None: writer.release()
        if webm_writer is not None: webm_writer.release()
        for item in clips.values():
            if item['cap'] is not None: item['cap'].release()
        try:
            if os.path.exists(out_path): os.remove(out_path)
        except OSError: pass
        return None
    finally:
        for item in clips.values():
            try: item['cap'].release()
            except Exception: pass

def create_session_gif(session):
    """Create an animated GIF from all original still photographs in this session."""
    try:
        from PIL import Image
        frames=[]
        for photo in session.get('photos',[]):
            path=os.path.join(SESSIONS_DIR,session['id'],photo.get('original',''))
            if not os.path.isfile(path): continue
            im=Image.open(path).convert('RGB')
            im.thumbnail((640,480))
            frames.append(im.copy())
        if not frames: return None
        out=os.path.join(SESSIONS_DIR,session['id'],'originals.gif')
        frames[0].save(out,save_all=True,append_images=frames[1:],duration=700,loop=0,optimize=True)
        return 'originals.gif' if os.path.isfile(out) and os.path.getsize(out)>100 else None
    except Exception as exc:
        print('[GIF_CREATE_ERROR]',repr(exc),flush=True)
        return None

def _cleanup_session_live_sources(snapshot):
    """Remove per-shot Live Photo inputs only after the final render is committed."""
    session_dir=os.path.join(SESSIONS_DIR, snapshot.get('id',''))
    for shot in snapshot.get('photos', []):
        clip=shot.get('live_photo')
        preview_clip=shot.get('live_photo_preview')
        for temporary_clip in (clip, preview_clip):
            if temporary_clip:
                try: os.remove(os.path.join(session_dir, temporary_clip))
                except OSError: pass
        if clip or preview_clip:
            shot['live_photo']=None
            shot['live_photo_preview']=None
            shot['live_photo_url']=None
            shot['live_photo_preview_url']=None


def _render_session_worker(session_id):
    """Render still/frame and framed Live Photo; keep source clips during filter review."""
    while True:
        with render_jobs_lock:
            job=render_jobs.get(session_id)
            if not job: return
            snapshot=copy.deepcopy(job['session'])
            selected=list(job.get('selected_numbers') or [])
            version=job['version']
            finish_requested=bool(job.get('finish_requested'))
        try:
            filter_name=snapshot.get('filter')
            if filter_name:
                for photo in snapshot.get('photos',[]):
                    original_path=os.path.join(SESSIONS_DIR,session_id,photo.get('original',''))
                    edited_path=os.path.join(SESSIONS_DIR,session_id,photo.get('edited',''))
                    original_image=cv2.imread(original_path)
                    if original_image is not None:
                        cv2.imwrite(edited_path,apply_filter(original_image,filter_name),[int(cv2.IMWRITE_JPEG_QUALITY),max(60,min(100,int((snapshot.get('settings',{}) or {}).get('jpeg_quality',100) or 100)))])
            compose_output(snapshot,selected or None,mark_finished=False)
            by_number={int(p.get('number',0)):p for p in snapshot.get('photos',[])}
            selected_photos=[by_number[int(n)] for n in selected if int(n) in by_number] if selected else list(snapshot.get('photos',[]))
            live_output=compose_live_output(snapshot,selected_photos) if snapshot.get('live_photo_enabled') else None
            live_preview=snapshot.get('live_output_preview') if live_output else None
            gif_file=create_session_gif(snapshot)
            # Keep per-shot source clips while the customer is still on the filter
            # slide: changing the filter or selected photos must be renderable again.
            snapshot['live_output']=live_output
            snapshot['live_output_preview']=live_preview
            snapshot['gif_output']=gif_file
            snapshot['render_status']='ready'
            snapshot['render_error']=None
            with render_jobs_lock:
                job=render_jobs.get(session_id)
                if not job: return
                if job['version'] != version:
                    continue
                finish_requested=bool(job.get('finish_requested'))
                if finish_requested:
                    _cleanup_session_live_sources(snapshot)
                snapshot['status']='finished' if finish_requested else 'processing'
                if finish_requested:
                    snapshot['finished_at']=datetime.datetime.now().isoformat(timespec='seconds')
                # Render artifacts are copied immediately on result-slide entry;
                # final=True only packages the archive when the customer exits.
                enqueue_local_session_archive(snapshot, final=finish_requested)
                # Folder provisioning runs independently and may finish after this render snapshot
                # was taken. Never overwrite its Drive URL/ID with stale render state.
                latest_manifest = read_manifest(session_id) or {}
                for drive_key in ('drive_folder_id','drive_url','drive_folder_status','drive_status',
                                  'drive_share_warning','drive_error','drive_uploaded_assets',
                                  'drive_upload_manifest_complete'):
                    if drive_key in latest_manifest:
                        snapshot[drive_key] = latest_manifest[drive_key]
                if snapshot.get('drive_qr_enabled') and snapshot.get('drive_url'):
                    _refresh_drive_qr_output(snapshot)
                write_manifest(snapshot)
                job['session']=snapshot
                job['ready']=True
                job['running']=False
                if finish_requested:
                    render_jobs.pop(session_id,None)
                print(f"[SESSION_RENDER] {session_id} ready finish={finish_requested} live={bool(live_output)}",flush=True)
                return
        except Exception as exc:
            print('[SESSION_RENDER_ERROR]',session_id,repr(exc),flush=True)
            snapshot['render_status']='error'; snapshot['render_error']=str(exc)
            with render_jobs_lock:
                job=render_jobs.get(session_id)
                if not job: return
                if job['version'] != version:
                    # A newer filter/photo selection arrived while this render failed.
                    # Continue the worker loop with the newest request instead of
                    # leaving its job marked as running with no worker behind it.
                    continue
                snapshot['status']='finished' if job.get('finish_requested') else 'processing'
                if job.get('finish_requested'): snapshot['finished_at']=datetime.datetime.now().isoformat(timespec='seconds')
                write_manifest(snapshot); job['session']=snapshot; job['running']=False; job['ready']=False
                if job.get('finish_requested'): render_jobs.pop(session_id,None)
            return


def queue_session_render(session, selected_numbers, filter_name, finish_requested=False, frame_id=None, layout_slots=None, frame_slots=None):
    snapshot=copy.deepcopy(session)
    if filter_name: snapshot['filter']=filter_name
    if frame_id is not None: snapshot['frame_id']=frame_id
    if layout_slots: snapshot['layout_slots']=layout_slots
    if frame_slots is not None: snapshot['frame_slots']=max(1,min(8,int(frame_slots)))
    snapshot['render_status']='processing'
    with render_jobs_lock:
        job=render_jobs.get(snapshot['id'])
        if job:
            current=job.get('session',{})
            same_request=(job.get('selected_numbers')==list(selected_numbers or []) and current.get('filter')==snapshot.get('filter') and current.get('frame_id')==snapshot.get('frame_id') and current.get('layout_slots')==snapshot.get('layout_slots') and current.get('frame_slots')==snapshot.get('frame_slots') and current.get('drive_qr_enabled')==snapshot.get('drive_qr_enabled') and current.get('drive_qr_layout')==snapshot.get('drive_qr_layout'))
            if same_request and job.get('ready'):
                snapshot=job['session']
                if finish_requested:
                    _cleanup_session_live_sources(snapshot)
                    snapshot['status']='finished'; snapshot['finished_at']=datetime.datetime.now().isoformat(timespec='seconds'); snapshot['render_status']='ready'
                    enqueue_local_session_archive(snapshot, final=True)
                    write_manifest(snapshot)
                    render_jobs.pop(snapshot['id'],None)
                return snapshot
            if same_request and job.get('running'):
                if finish_requested: job['finish_requested']=True
                return job['session']
            job['session']=snapshot
            job['selected_numbers']=list(selected_numbers or [])
            job['version']+=1
            job['finish_requested']=bool(job.get('finish_requested') or finish_requested)
            job['ready']=False
            if not job.get('running'):
                job['running']=True
                threading.Thread(target=_render_session_worker,args=(snapshot['id'],),daemon=True).start()
        else:
            render_jobs[snapshot['id']]={'session':snapshot,'selected_numbers':list(selected_numbers or []),'version':1,'finish_requested':bool(finish_requested),'running':True,'ready':False}
            threading.Thread(target=_render_session_worker,args=(snapshot['id'],),daemon=True).start()
    return snapshot


def camera_backends():
    if sys.platform == 'win32':
        return [('DirectShow', cv2.CAP_DSHOW), ('Media Foundation', cv2.CAP_MSMF)]
    if sys.platform == 'darwin':
        return [('AVFoundation', cv2.CAP_AVFOUNDATION)]
    return [('V4L2', cv2.CAP_V4L2), ('Default', cv2.CAP_ANY)]


def frame_luminance(frame):
    # Sample grayscale pixels to identify genuinely black frames without expensive full-frame analysis.
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    sample = gray[::8, ::8]
    return round(float(sample.mean()), 2), int(sample.min()), int(sample.max())


def _encode_preview_jpeg(frame, quality=PREVIEW_JPEG_QUALITY):
    """Encode a bounded preview; retain the original frame for full-quality capture."""
    if frame is None or not getattr(frame, 'size', 0): return None
    try:
        h, w = frame.shape[:2]
        scale = min(1.0, 1280.0 / max(1, w), 720.0 / max(1, h))
        preview = cv2.resize(frame, (max(1,int(w*scale)), max(1,int(h*scale))), interpolation=cv2.INTER_AREA) if scale < 1.0 else frame
        ok, encoded = cv2.imencode('.jpg', preview, [int(cv2.IMWRITE_JPEG_QUALITY), max(40, min(95, int(quality or PREVIEW_JPEG_QUALITY)))])
        return encoded.tobytes() if ok else None
    except Exception as exc:
        print('[PREVIEW_ENCODE_ERROR]', repr(exc), flush=True); return None


def _get_preview_jpeg(secondary=False, quality=PREVIEW_JPEG_QUALITY):
    """Lazily encode the newest frame from a stream client, never on the capture thread."""
    global preview_jpeg_main, preview_jpeg_main_id, preview_jpeg_secondary, preview_jpeg_secondary_id
    global preview_encoded_main_source_id, preview_encoded_secondary_source_id, preview_encoded_main_quality, preview_encoded_secondary_quality
    with preview_cache_lock:
        if secondary:
            with secondary_lock:
                frame = None if latest_secondary_frame is None else latest_secondary_frame.copy()
                source_id = secondary_frame_id
            if frame is None: return None, preview_jpeg_secondary_id
            q = max(40, min(95, int(quality or PREVIEW_JPEG_QUALITY)))
            if source_id != preview_encoded_secondary_source_id or q != preview_encoded_secondary_quality:
                payload = _encode_preview_jpeg(frame, q)
                if payload is not None:
                    preview_jpeg_secondary = payload
                    preview_jpeg_secondary_id += 1
                    preview_encoded_secondary_source_id = source_id
                    preview_encoded_secondary_quality = q
            return preview_jpeg_secondary, preview_jpeg_secondary_id
        with frame_condition:
            frame = None if latest_frame is None else latest_frame.copy()
            source_id = frame_id
        if frame is None: return None, preview_jpeg_main_id
        q = max(40, min(95, int(quality or PREVIEW_JPEG_QUALITY)))
        if source_id != preview_encoded_main_source_id or q != preview_encoded_main_quality:
            payload = _encode_preview_jpeg(frame, q)
            if payload is not None:
                preview_jpeg_main = payload
                preview_jpeg_main_id += 1
                preview_encoded_main_source_id = source_id
                preview_encoded_main_quality = q
        return preview_jpeg_main, preview_jpeg_main_id


def publish_frame(frame):
    global latest_frame, frame_id, session_video_last_write, shot_video_last_write, shot_video_frame_count, shot_video_sampled_at, shot_video_frames, shot_video_width, shot_video_height, video_test_frames
    h, w = frame.shape[:2]
    with frame_condition:
        latest_frame = frame.copy()
        frame_id += 1
        frame_condition.notify_all()
    with video_lock:
        now_mono = time.monotonic()
        # Write every camera frame at native resolution and native cadence; no frame sampling or resizing.
        if shot_video_path and shot_video_writer is not None and shot_video_source == 0:
            try:
                if now_mono - shot_video_last_write >= (1.0 / max(1.0, shot_video_fps)):
                    shot_frame = _apply_camera_orientation(frame, shot_video_rotation, shot_video_flip_horizontal, shot_video_flip_vertical, shot_video_mirror)
                    if shot_frame.shape[1] != shot_video_width or shot_frame.shape[0] != shot_video_height:
                        shot_frame = cv2.resize(shot_frame, (shot_video_width, shot_video_height), interpolation=cv2.INTER_AREA)
                    shot_video_writer.write(__import__('numpy').ascontiguousarray(shot_frame))
                    shot_video_frame_count += 1
                    shot_video_last_write = now_mono
            except Exception as exc:
                print('[LIVE_PHOTO_WRITE_ERROR]', repr(exc), flush=True)
        if video_test_writer is not None:
            try:
                test_frame = cv2.flip(frame, 1) if False else frame
                video_test_writer.write(__import__('numpy').ascontiguousarray(test_frame))
                video_test_frames += 1
            except Exception as exc:
                print('[VIDEO_TEST_WRITE_ERROR]', repr(exc), flush=True)
        write_booth_video_frame(frame, 0)
        writer = session_video_writer
        if writer is not None and (now_mono - session_video_last_write) >= 0.05:
            try:
                writer.write(frame)
                session_video_last_write = now_mono
            except Exception as exc:
                print('[VIDEO_WRITE_ERROR]', repr(exc), flush=True)
    with state_lock:
        state['frames_read'] += 1
        count = state['frames_read']
        state['frame_width'] = int(w)
        state['frame_height'] = int(h)
        state['last_frame_time'] = time.time()
        state['last_read_error'] = None
    if count == 1 or count % 10 == 0:
        mean, low, high = frame_luminance(frame)
        with state_lock:
            state['frame_mean'] = mean
            state['frame_min'] = low
            state['frame_max'] = high


def _probe_camera_isolated(index, backend_name, timeout=5.0):
    """Return camera probe result without loading a fragile UVC driver in HTTP process.

    A bad DirectShow/MSMF driver may crash cv2 native code (not a Python exception).
    A dedicated child process makes that a failed camera, not a dead KACA backend.
    """
    helper_path=os.path.join(os.path.dirname(os.path.abspath(__file__)),'camera_probe.py')
    args=[sys.executable,'-u',helper_path,str(index),backend_name]
    flags=getattr(subprocess,'CREATE_NO_WINDOW',0) if os.name=='nt' else 0
    try:
        proc=subprocess.run(args,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,
                            timeout=float(timeout),creationflags=flags,check=False,
                            text=True,errors='replace')
        for line in reversed(proc.stdout.splitlines()):
            if line.startswith('KACA_PROBE_RESULT='):
                result=json.loads(line.partition('=')[2])
                if proc.returncode==0 and result.get('ok') and result.get('index')==index:
                    return result
                break
        print('[SCAN_PROBE_FAILED]',index,backend_name,'exit='+str(proc.returncode),proc.stdout[-400:],flush=True)
    except subprocess.TimeoutExpired:
        print('[SCAN_PROBE_TIMEOUT]',index,backend_name,'(driver timeout)',flush=True)
    except Exception as exc:
        print('[SCAN_PROBE_ERROR]',index,backend_name,repr(exc),flush=True)
    return None


def scan_worker():
    """Scan webcams independently from Canon EDSDK, prioritizing the known laptop camera.

    The previous 0..9 x DirectShow+MSMF sweep could spend >20 seconds probing
    nonexistent/slow virtual devices. KACA.ID's confirmed laptop webcam is index 1,
    so probe it first and keep the scan bounded to the common Windows indices.
    """
    found = []
    started = time.monotonic()
    with state_lock:
        state['scan_stage'] = 'starting'
        state['scan_started_at'] = time.time()
    try:
        if cv2 is None:
            with state_lock:
                state['scan_done'] = True
                state['scan_running'] = False
                state['scan_stage'] = 'opencv_unavailable'
                state['error'] = 'OpenCV tidak tersedia pada Python yang menjalankan backend. Jalankan setup.bat.'
            print('[SCAN_ABORT] OpenCV module is unavailable in the active Python environment.', flush=True)
            return
        with state_lock:
            active_primary = state.get('selected') if state.get('camera_open') else None
            primary_backend = state.get('backend') or 'OpenCV'
        with secondary_lock:
            active_secondary = secondary_selected_index
        active_indices = set()
        for active_item in (active_primary, active_secondary):
            try:
                if active_item is not None: active_indices.add(int(active_item))
            except (TypeError, ValueError):
                # Canon EDSDK identifiers are not OpenCV numeric indices.
                continue

        # No fixed webcam index: every Windows PC may enumerate its cameras
        # differently. Prefer the configured device, then normal indices.
        configured_index=os.environ.get('KACA_PREFERRED_CAMERA_INDEX','0')
        try: preferred=int(configured_index)
        except (TypeError,ValueError): preferred=0
        indices=[preferred]+[idx for idx in range(6) if idx!=preferred]
        indices=[idx for idx in indices if 0<=idx<=10][:7]
        for index in indices:
            if len(found)>=6:break
            if index in active_indices:
                backend_name=primary_backend if index == active_primary else 'DirectShow'
                found.append({'id':index,'label':f'Kamera {index} (aktif, tidak dipindai ulang)','backend':backend_name,'active':True})
                continue
            for backend_name in ('DirectShow','MSMF'):
                with state_lock:state['scan_stage']=f'memindai_index_{index}_{backend_name.lower()}'
                probe_started=time.monotonic()
                result=_probe_camera_isolated(index,backend_name)
                if result is not None:
                    found.append({'id':index,'label':f'Kamera {index} ({backend_name})','backend':backend_name})
                    print(f'[SCAN] camera={index} backend={backend_name} frame={result.get("width",0)}x{result.get("height",0)} elapsed_ms={int((time.monotonic()-probe_started)*1000)}',flush=True)
                    break
        with state_lock:
            state['cameras'] = found
            state['scan_done'] = True
            state['scan_running'] = False
            state['scan_stage'] = 'complete'
            state['scan_duration_ms'] = int((time.monotonic() - started) * 1000)
            state['error'] = None if found else 'OpenCV/DirectShow tidak menemukan kamera yang dapat dibuka. Periksa apakah kamera sedang dipakai aplikasi lain.'
        print(f'[SCAN_COMPLETE] count={len(found)} duration_ms={int((time.monotonic()-started)*1000)} devices={[x["id"] for x in found]} python={sys.version.split()[0]} opencv={cv2.__version__}', flush=True)
    except Exception as e:
        with state_lock:
            state['scan_done'] = True
            state['scan_running'] = False
            state['scan_stage'] = 'error'
            state['scan_duration_ms'] = int((time.monotonic() - started) * 1000)
            state['error'] = str(e)
        traceback.print_exc()


def detect_canon_usb():
    """Detect Canon EOS cameras through EDSDK first, then report Windows PnP evidence."""
    edsdk_result = None

    try:
        with canon_secondary_lock:
            secondary_controller = canon_secondary_controller
            if secondary_controller is not None:
                try:
                    secondary_status = secondary_controller.status()
                    if secondary_status.get('active') or secondary_status.get('worker_alive') or (secondary_status.get('native') or {}).get('download_call_pending'):
                        edsdk_result = {'sdk_available': True, 'available': True, 'cameras': [{'id': 'canon_edsdk_0', 'name': 'Canon EOS (MultiCam Angle 2 aktif)'}], 'message': 'Canon sedang digunakan sebagai Kamera 2 MultiCam.', 'active': True, 'status': secondary_status}
                except Exception:
                    pass
        with canon_lifecycle_lock:
            controller = canon_controller

            # Jangan menjalankan deteksi/inisialisasi SDK ulang
            # ketika Canon sedang aktif atau proses penghentiannya belum selesai.
            if controller is not None:
                try:
                    current_status = controller.status()
                    if current_status.get('active') or current_status.get('worker_alive') or (current_status.get('native') or {}).get('download_call_pending'):
                        edsdk_result = {
                            'sdk_available': True,
                            'available': True,
                            'cameras': [{
                                'id': 'canon_edsdk_0',
                                'name': 'Canon EOS (Live View aktif)'
                            }],
                            'message': 'Canon sedang digunakan oleh KACA.ID.',
                            'active': True,
                            'status': current_status
                        }
                except Exception:
                    pass

            if edsdk_result is None:
                from canon_edsdk import detect_canon_cameras
                edsdk_result = detect_canon_cameras()

    except Exception as exc:
        edsdk_result = {
            'sdk_available': False,
            'available': False,
            'cameras': [],
            'message': f'EDSDK adapter gagal dimuat: {exc}'
        }

    pnp_devices = []
    pnp_error = None

    if sys.platform == 'win32':
        try:
            import subprocess

            windir = os.environ.get('WINDIR', r'C:\Windows')
            ps = os.path.join(
                windir,
                'System32',
                'WindowsPowerShell',
                'v1.0',
                'powershell.exe'
            )

            script = r"""$ErrorActionPreference='Stop'; $items=Get-PnpDevice -PresentOnly | Where-Object { ($_.FriendlyName -match 'Canon|EOS|1300D|REBEL T6') -or ($_.InstanceId -match 'VID_04A9') } | Select-Object Class,FriendlyName,InstanceId,Status; ConvertTo-Json -InputObject @($items) -Compress"""

            raw = subprocess.check_output(
                [
                    ps,
                    '-NoProfile',
                    '-NonInteractive',
                    '-Command',
                    script
                ],
                stderr=subprocess.STDOUT,
                timeout=12,
                text=True,
                creationflags=getattr(
                    subprocess,
                    'CREATE_NO_WINDOW',
                    0
                )
            )

            items = json.loads(raw or '[]')

            if isinstance(items, dict):
                items = [items]

            pnp_devices = [
                {
                    'class': str(x.get('Class') or ''),
                    'name': str(x.get('FriendlyName') or ''),
                    'instance_id': str(x.get('InstanceId') or ''),
                    'status': str(x.get('Status') or '')
                }
                for x in items
                if x.get('FriendlyName') or x.get('InstanceId')
            ]

        except Exception as exc:
            pnp_error = str(exc)
    canon_cameras = (edsdk_result or {}).get('cameras') or []
    if canon_cameras:
        return {
            'ok': True, 'available': True, 'sdk_available': True,
            'devices': canon_cameras, 'cameras': canon_cameras,
            'windows_devices': pnp_devices, 'edsdk': edsdk_result,
            'message': (edsdk_result or {}).get('message') or 'Canon EOS terdeteksi melalui EDSDK.'
        }

    if pnp_devices:
        edsdk_message = (edsdk_result or {}).get('message') or 'EDSDK belum berhasil mendeteksi kamera.'
        return {
            'ok': True, 'available': True, 'sdk_available': bool((edsdk_result or {}).get('sdk_available')),
            'devices': pnp_devices, 'cameras': [], 'windows_devices': pnp_devices,
            'edsdk': edsdk_result,
            'message': 'Windows mengenali perangkat Canon melalui USB, tetapi Canon EDSDK belum berhasil membuka/mendeteksi kameranya. ' + edsdk_message
        }

    detail = (edsdk_result or {}).get('message') or 'EDSDK belum menemukan kamera.'
    if pnp_error:
        detail += ' Pemeriksaan Windows PnP: ' + pnp_error
    return {
        'ok': bool((edsdk_result or {}).get('sdk_available')),
        'available': False,
        'sdk_available': bool((edsdk_result or {}).get('sdk_available')),
        'devices': [], 'cameras': [], 'windows_devices': [],
        'edsdk': edsdk_result,
        'message': detail
    }


def start_scan(force=False):
    with state_lock:
        if state['scan_running']:
            return
        if state.get('scan_done') and not force:
            return
        state['scan_running'] = True
        state['scan_done'] = False
        state['cameras'] = []
        state['error'] = None
        state['scan_stage'] = 'queued'
        state['scan_started_at'] = time.time()
        state['scan_duration_ms'] = 0
    threading.Thread(target=scan_worker, daemon=True).start()


def reader():
    global cap
    print('[CAMERA] reader thread started', flush=True)
    while not stop_reader.is_set():
        with capture_lock:
            current = cap
        if current is None:
            ok, frame = False, None
        else:
            try:
                ok, frame = current.read()
            except Exception as e:
                ok, frame = False, None
                with state_lock:
                    state['last_read_error'] = repr(e)
        if ok and frame is not None and getattr(frame, 'size', 0):
            publish_frame(frame)
        else:
            with state_lock:
                state['read_failures'] += 1
                if state['last_read_error'] is None:
                    state['last_read_error'] = 'VideoCapture.read() returned False or empty frame'
            time.sleep(0.05)
    with state_lock:
        state['reader_alive'] = False
    print('[CAMERA] reader thread stopped', flush=True)


def close_canon_camera():
    """Stop Canon safely; retain the controller if its native worker is still alive."""
    global canon_controller, latest_frame
    with canon_lifecycle_lock:
        controller = canon_controller
        if controller is not None:
            try:
                stopped = controller.stop()
            except Exception as exc:
                stopped = False
                print('[CANON_CLOSE_ERROR]', repr(exc), flush=True)
            if not stopped:
                print('[CANON_CLOSE_PENDING] Native EDSDK worker has not stopped; controller retained.', flush=True)
                return False
            if canon_controller is controller:
                canon_controller = None
        with frame_condition:
            if controller is not None:
                latest_frame = None
                frame_condition.notify_all()
        with state_lock:
            if state.get('backend') == 'Canon EDSDK Live View':
                state.update({'camera_open': False, 'reader_alive': False, 'selected': None})
        return True


def open_canon_camera(camera_id='canon_edsdk_0'):
    """Open one Canon session at a time; do not initialize over a live/stuck session."""
    global canon_controller, cap, latest_frame, frame_id
    match = re.fullmatch(r'canon_edsdk_(\d+)', str(camera_id))
    if not match:
        return {'ok': False, 'error': 'ID kamera Canon tidak valid.'}
    with canon_lifecycle_lock:
        if not close_canon_camera():
            return {
                'ok': False,
                'error': 'Canon sebelumnya belum berhasil ditutup. Silakan tutup dan buka ulang backend kamera.'
            }

        if not close_camera():
            return {
                'ok': False,
                'error': 'Kamera sebelumnya belum berhasil dihentikan. Canon tidak jadi dibuka.'
            }

        try:
            from canon_edsdk_live import CanonLiveView
            def receive_jpeg(payload):
                import numpy as np
                encoded = np.frombuffer(payload, dtype=np.uint8)
                frame = cv2.imdecode(encoded, cv2.IMREAD_COLOR)
                if frame is None or not frame.size:
                    raise RuntimeError('JPEG Live View Canon tidak dapat didekode OpenCV.')
                publish_frame(frame)
                return (frame.shape[1], frame.shape[0])
            controller = CanonLiveView(receive_jpeg, int(match.group(1)))
            canon_controller = controller
            with state_lock:
                state.update({'camera_open': True, 'selected': str(camera_id), 'backend': 'Canon EDSDK Live View', 'reader_alive': True, 'error': None, 'frames_read': 0, 'read_failures': 0, 'frame_width': 0, 'frame_height': 0, 'last_frame_time': None, 'last_read_error': None})
            result = controller.start()
            print(f"[CANON_LIVE] started {result.get('name')} {result.get('width')}x{result.get('height')}", flush=True)
            return result
        except Exception as exc:
            controller = canon_controller
            stopped = False
            if controller is not None:
                try:
                    stopped = controller.stop()
                except Exception:
                    stopped = False
                if stopped and canon_controller is controller:
                    canon_controller = None
            with frame_condition:
                if stopped or controller is None:
                    latest_frame = None
                    frame_condition.notify_all()
            with state_lock:
                state.update({'camera_open': bool(controller is not None and not stopped), 'reader_alive': bool(controller is not None and not stopped), 'selected': str(camera_id) if controller is not None and not stopped else None, 'error': str(exc), 'last_read_error': str(exc)})
            print('[CANON_LIVE_ERROR]', repr(exc), flush=True)
            return {'ok': False, 'error': str(exc), 'cleanup_pending': bool(controller is not None and not stopped)}


def close_camera():
    global cap, latest_frame, preview_jpeg_main, preview_jpeg_main_id, preview_encoded_main_source_id
    if not close_canon_camera():
        # Keep the active Canon controller and its state intact until the native
        # worker exits; never advertise a clean close while EDSDK is still busy.
        return False
    stop_reader.set()
    thread = reader_thread
    # Wait briefly for a pending DirectShow read before releasing the handle.
    if thread and thread.is_alive() and thread is not threading.current_thread():
        thread.join(timeout=1.5)
    with capture_lock:
        old = cap
        cap = None
    if old is not None:
        try: old.release()
        except Exception: pass
    with frame_condition:
        latest_frame = None
        frame_condition.notify_all()
    with preview_cache_lock:
        preview_jpeg_main = None
        preview_jpeg_main_id += 1
        preview_encoded_main_source_id = -1
    with state_lock:
        state['camera_open'] = False
        state['reader_alive'] = False
    try: close_secondary_camera()
    except Exception: pass
    return True


def open_camera(index):
    global cap, latest_frame, reader_thread, frame_id
    if not close_camera():
        return False
    last_error = None
    for backend_name, backend_id in camera_backends():
        candidate = None
        try:
            print(f'[CAMERA] opening index={index} backend={backend_name}', flush=True)
            candidate = cv2.VideoCapture(int(index), backend_id)
            if candidate is not None and candidate.isOpened():
                candidate.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                candidate.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
                candidate.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
                candidate.set(cv2.CAP_PROP_FPS, 30)
                # Verify first frame before publishing the handle.
                ok, frame = candidate.read()
                if ok and frame is not None and frame.size:
                    with capture_lock:
                        cap = candidate
                    with frame_condition:
                        latest_frame = frame.copy()
                        frame_id += 1
                        frame_condition.notify_all()
                    with state_lock:
                        state.update({
                            'selected': int(index), 'camera_open': True, 'backend': backend_name,
                            'error': None, 'frames_read': 1, 'read_failures': 0,
                            'frame_width': int(frame.shape[1]), 'frame_height': int(frame.shape[0]),
                            'last_frame_time': time.time(), 'last_read_error': None,
                            'reader_alive': True,
                            'frame_mean': frame_luminance(frame)[0],
                            'frame_min': frame_luminance(frame)[1],
                            'frame_max': frame_luminance(frame)[2]
                        })
                    stop_reader.clear()
                    reader_thread = threading.Thread(target=reader, daemon=True, name='KACA-Camera-Reader')
                    reader_thread.start()
                    print(f'[CAMERA] opened; first frame {frame.shape[1]}x{frame.shape[0]} via {backend_name}', flush=True)
                    return True
                last_error = f'{backend_name}: perangkat terbuka tetapi tidak menghasilkan frame pertama'
            else:
                last_error = f'{backend_name}: perangkat tidak dapat dibuka'
        except Exception as e:
            last_error = f'{backend_name}: {e}'
            print('[OPEN_ERROR]', repr(e), flush=True)
        if candidate is not None and candidate is not cap:
            try: candidate.release()
            except Exception: pass
    with state_lock:
        state['camera_open'] = False
        state['error'] = last_error or 'Kamera gagal dibuka.'
    return False


def secondary_reader():
    global latest_secondary_frame, shot_video_frame_count, secondary_frame_id
    while not stop_secondary_reader.is_set():
        with secondary_lock: current=secondary_cap
        if current is None: time.sleep(.05); continue
        try: ok, frame=current.read()
        except Exception: ok,frame=False,None
        if not ok or frame is None or not getattr(frame,'size',0):
            time.sleep(.02); continue
        with secondary_lock: latest_secondary_frame=frame.copy(); secondary_frame_id += 1
        write_booth_video_frame(frame, 1)
        now_mono=time.monotonic()
        with video_lock:
            if shot_video_path and shot_video_writer is not None and shot_video_source==1:
                try:
                    if now_mono-shot_video_last_write >= (1.0/max(1.0,shot_video_fps)):
                        out=_apply_camera_orientation(frame, shot_video_rotation, shot_video_flip_horizontal, shot_video_flip_vertical, shot_video_mirror)
                        if out.shape[1]!=shot_video_width or out.shape[0]!=shot_video_height: out=cv2.resize(out,(shot_video_width,shot_video_height),interpolation=cv2.INTER_AREA)
                        shot_video_writer.write(__import__('numpy').ascontiguousarray(out)); shot_video_frame_count+=1; shot_video_last_write=now_mono
                except Exception as exc: print('[MULTICAM_VIDEO_WRITE_ERROR]',repr(exc),flush=True)


def close_secondary_canon_camera():
    """Stop an EDSDK worker used as MultiCam angle 2."""
    global canon_secondary_controller, latest_secondary_frame, secondary_selected_index
    with canon_secondary_lock:
        controller = canon_secondary_controller
        if controller is not None:
            try:
                stopped = controller.stop()
            except Exception as exc:
                stopped = False
                print('[CANON_SECONDARY_CLOSE_ERROR]', repr(exc), flush=True)
            if not stopped:
                print('[CANON_SECONDARY_CLOSE_PENDING] Worker has not stopped.', flush=True)
                return False
            if canon_secondary_controller is controller:
                canon_secondary_controller = None
        with secondary_lock:
            if controller is not None:
                latest_secondary_frame = None
                secondary_selected_index = None
        return True


def open_secondary_canon_camera(camera_id='canon_edsdk_0'):
    """Open Canon EDSDK as MultiCam angle 2 without replacing the primary webcam."""
    global canon_secondary_controller, latest_secondary_frame, secondary_selected_index
    match = re.fullmatch(r'canon_edsdk_(\d+)', str(camera_id))
    if not match:
        return {'ok': False, 'error': 'ID Canon untuk kamera kedua tidak valid.'}
    if state.get('backend') == 'Canon EDSDK Live View' and state.get('camera_open'):
        return {'ok': False, 'error': 'Canon EDSDK sudah digunakan sebagai Kamera 1. Satu kamera Canon tidak dapat dipakai pada dua angle sekaligus.'}
    # Reuse an already-running secondary Canon Live View. Reopening the same
    # EDSDK device during session initialization can block while the worker exits.
    with canon_secondary_lock:
        existing = canon_secondary_controller
        if existing is not None and str(secondary_selected_index) == str(camera_id):
            with secondary_lock:
                frame_ready = latest_secondary_frame is not None
                frame_size = (int(latest_secondary_frame.shape[1]), int(latest_secondary_frame.shape[0])) if frame_ready else (0, 0)
            if frame_ready:
                return {'ok': True, 'id': str(camera_id), 'angle': 2, 'backend': 'Canon EDSDK Live View', 'width': frame_size[0], 'height': frame_size[1], 'reused': True}
    if not close_secondary_camera():
        return {'ok': False, 'error': 'Kamera kedua sebelumnya belum berhasil dihentikan.'}
    try:
        from canon_edsdk_live import CanonLiveView
        def receive_secondary_jpeg(payload):
            global latest_secondary_frame, secondary_frame_id
            import numpy as np
            encoded = np.frombuffer(payload, dtype=np.uint8)
            frame = cv2.imdecode(encoded, cv2.IMREAD_COLOR)
            if frame is None or not frame.size:
                raise RuntimeError('JPEG Live View Canon untuk Kamera 2 tidak dapat didekode.')
            with secondary_lock:
                latest_secondary_frame = frame.copy()
                secondary_frame_id += 1
                globals()['secondary_selected_index'] = str(camera_id)
            write_booth_video_frame(frame, 1)
            with video_lock:
                now_mono = time.monotonic()
                if shot_video_path and shot_video_writer is not None and shot_video_source == 1 and now_mono - shot_video_last_write >= (1.0 / max(1.0, shot_video_fps)):
                    out = _apply_camera_orientation(frame, shot_video_rotation, shot_video_flip_horizontal, shot_video_flip_vertical, shot_video_mirror)
                    if out.shape[1] != shot_video_width or out.shape[0] != shot_video_height:
                        out = cv2.resize(out, (shot_video_width, shot_video_height), interpolation=cv2.INTER_AREA)
                    shot_video_writer.write(__import__('numpy').ascontiguousarray(out))
                    globals()['shot_video_frame_count'] += 1
                    globals()['shot_video_last_write'] = now_mono
            return (frame.shape[1], frame.shape[0])
        controller = CanonLiveView(receive_secondary_jpeg, int(match.group(1)))
        with canon_secondary_lock:
            canon_secondary_controller = controller
        result = controller.start()
        with secondary_lock:
            secondary_selected_index = str(camera_id)
        print(f"[CANON_SECONDARY_LIVE] started {result.get('name')} {result.get('width')}x{result.get('height')}", flush=True)
        return {**result, 'ok': True, 'backend': 'Canon EDSDK Live View', 'id': str(camera_id), 'angle': 2}
    except Exception as exc:
        with canon_secondary_lock:
            controller = canon_secondary_controller
            stopped = False
            if controller is not None:
                try: stopped = controller.stop()
                except Exception: stopped = False
            if stopped: canon_secondary_controller = None
        with secondary_lock:
            latest_secondary_frame = None
            secondary_selected_index = None
        return {'ok': False, 'error': str(exc), 'cleanup_pending': bool(controller is not None and not stopped)}


def open_secondary_camera(index):
    global secondary_cap, latest_secondary_frame, secondary_thread, secondary_selected_index
    try:
        # Reuse the same OpenCV secondary device instead of releasing and reopening it.
        # DirectShow device reopen can stall for several seconds on Windows.
        with secondary_lock:
            existing_cap = secondary_cap
            existing_index = secondary_selected_index
            existing_frame = latest_secondary_frame
        if existing_cap is not None and existing_cap.isOpened() and str(existing_index) == str(index) and existing_frame is not None:
            return {'ok': True, 'index': int(index), 'backend': 'OpenCV (reuse)', 'width': int(existing_frame.shape[1]), 'height': int(existing_frame.shape[0]), 'reused': True}
        primary_selected = state.get('selected')
        # A Canon EDSDK identifier is not an OpenCV index; it may coexist with a webcam angle.
        if primary_selected is not None and str(primary_selected).isdigit() and int(index) == int(primary_selected):
            return {'ok':False,'error':'Kamera kedua sama dengan kamera utama. Pilih indeks perangkat yang berbeda.'}
        int(index)
    except (TypeError, ValueError):
        return {'ok':False,'error':'Indeks kamera kedua tidak valid.'}
    close_secondary_camera()
    last=None
    for backend_name,backend_id in camera_backends():
        candidate=None
        try:
            candidate=cv2.VideoCapture(int(index),backend_id)
            if candidate is not None and candidate.isOpened():
                candidate.set(cv2.CAP_PROP_BUFFERSIZE,1); candidate.set(cv2.CAP_PROP_FRAME_WIDTH,1280); candidate.set(cv2.CAP_PROP_FRAME_HEIGHT,720)
                ok,frame=candidate.read()
                if ok and frame is not None and frame.size:
                    with secondary_lock: secondary_cap=candidate; latest_secondary_frame=frame.copy(); secondary_selected_index=int(index)
                    stop_secondary_reader.clear(); secondary_thread=threading.Thread(target=secondary_reader,daemon=True,name='KACA-Secondary-Camera'); secondary_thread.start()
                    return {'ok':True,'index':int(index),'backend':backend_name,'width':int(frame.shape[1]),'height':int(frame.shape[0])}
                last=f'{backend_name}: tidak ada frame'
        except Exception as exc: last=str(exc)
        if candidate is not None:
            try: candidate.release()
            except Exception: pass
    return {'ok':False,'error':last or 'Kamera kedua tidak dapat dibuka.'}


def close_secondary_camera():
    global secondary_cap,latest_secondary_frame,secondary_selected_index,preview_jpeg_secondary,preview_jpeg_secondary_id,preview_encoded_secondary_source_id
    if not close_secondary_canon_camera():
        return False
    stop_secondary_reader.set()
    th=secondary_thread
    if th and th.is_alive() and th is not threading.current_thread(): th.join(timeout=1.0)
    with secondary_lock:
        old=secondary_cap; secondary_cap=None; latest_secondary_frame=None; secondary_selected_index=None
    if old is not None:
        try: old.release()
        except Exception: pass
    with preview_cache_lock:
        preview_jpeg_secondary = None
        preview_jpeg_secondary_id += 1
        preview_encoded_secondary_source_id = -1
    return True


def _camera_driver_slider_range(key, actual):
    """Conservative, clearly approximate camera-native ranges.

    OpenCV's get() doesn't expose UVC IAMVideoProcAmp minimum/maximum/step.
    Never pretend a normalized 0..2 setting works for webcams reporting 0..255.
    """
    import math
    if not math.isfinite(actual):
        return 0.0, 100.0, 1.0
    if key in ('brightness', 'contrast', 'saturation', 'gain', 'sharpness'):
        if key == 'brightness':
            bound = max(100.0, min(255.0, math.ceil(abs(actual) * 2)))
            return -bound if actual < 0 else 0.0, bound, 1.0
        upper = 255.0 if actual > 100 else 100.0
        return 0.0, upper, 1.0
    if key == 'exposure':
        return (min(-13.0, math.floor(actual - 4)), max(0.0, math.ceil(actual + 4)), 1.0)
    if key == 'iso':
        return 0.0, max(1600.0, math.ceil(actual / 100) * 100 * 2), 100.0
    if key == 'focus':return 0.0, max(255.0, actual * 2), 1.0
    if key == 'white_balance':return 2000.0, max(7500.0, actual * 1.5), 100.0
    return 0.0, 100.0, 1.0


def get_camera_control_capabilities(target):
    """Get readback and approximate per-camera ranges without modifying driver state."""
    mapping={
        'brightness':'CAP_PROP_BRIGHTNESS','contrast':'CAP_PROP_CONTRAST',
        'saturation':'CAP_PROP_SATURATION','exposure':'CAP_PROP_EXPOSURE',
        'iso':'CAP_PROP_ISO_SPEED','gain':'CAP_PROP_GAIN',
        'focus':'CAP_PROP_FOCUS','white_balance':'CAP_PROP_WB_TEMPERATURE',
        'sharpness':'CAP_PROP_SHARPNESS',
    }
    lock=capture_lock if int(target or 0)==0 else secondary_lock
    with lock:
        camera=cap if int(target or 0)==0 else secondary_cap
        if camera is None or not camera.isOpened():
            return {'ok':True,'open':False,'controls':{},'note':'Kamera belum dibuka.'}
        result={}
        for key,constant in mapping.items():
            prop=getattr(cv2,constant,None)
            if prop is None:
                result[key]={'readable':False,'available':False,'note':'Kontrol tidak disediakan OpenCV'}
                continue
            try:
                actual=float(camera.get(prop))
                readable=__import__('math').isfinite(actual)
                # Zero on ISO/focus/WB/sharpness normally means unsupported in
                # DirectShow/MSMF, unlike brightness and saturation where 0 is valid.
                available=readable and (abs(actual)>1e-9 or key in ('brightness','contrast','saturation','gain','exposure'))
                mn,mx,step=_camera_driver_slider_range(key,actual)
                result[key]={'readable':readable,'available':available,
                             'actual':actual if readable else None,
                             'min':mn,'max':mx,'step':step,
                             'note':('Rentang perkiraan dari nilai driver; perubahan dikonfirmasi dengan pembacaan balik.' if available
                                     else 'Driver tidak melaporkan nilai kontrol ini; tidak mengirim perubahan.')}
            except Exception as err:
                result[key]={'readable':False,'available':False,'note':str(err)[:120]}
    return {'ok':True,'open':True,'controls':result}


def set_camera_controls(target, values):
    """Apply only explicit user changes. Read actual driver value and reject mismatch."""
    props={'brightness':getattr(cv2,'CAP_PROP_BRIGHTNESS',10),
           'contrast':getattr(cv2,'CAP_PROP_CONTRAST',11),
           'saturation':getattr(cv2,'CAP_PROP_SATURATION',12),
           'hue':getattr(cv2,'CAP_PROP_HUE',13),
           'gain':getattr(cv2,'CAP_PROP_GAIN',14),
           'exposure':getattr(cv2,'CAP_PROP_EXPOSURE',15),
           'white_balance':getattr(cv2,'CAP_PROP_WB_TEMPERATURE',45),
           'focus':getattr(cv2,'CAP_PROP_FOCUS',28),
           'sharpness':getattr(cv2,'CAP_PROP_SHARPNESS',20),
           'iso':getattr(cv2,'CAP_PROP_ISO_SPEED',30),
           'auto_exposure':getattr(cv2,'CAP_PROP_AUTO_EXPOSURE',21)}
    import math
    lock=capture_lock if int(target or 0)==0 else secondary_lock
    with lock:
        camera=cap if int(target or 0)==0 else secondary_cap
        if camera is None or not camera.isOpened():return {'ok':False,'error':'Kamera belum aktif.'}
        result={}
        for key,value in (values or {}).items():
            if key not in props:continue
            try:
                target_value=float(value)
                if not math.isfinite(target_value):raise ValueError('Nilai harus berhingga.')
                previous=float(camera.get(props[key]))
                accepted=bool(camera.set(props[key],target_value))
                actual=float(camera.get(props[key]))
                # A driver can return success while silently snapping to a
                # different value. Treat that as not applied, not as success.
                tolerance=max(.1,abs(target_value)*.01)
                applied=accepted and math.isfinite(actual) and abs(actual-target_value)<=tolerance
                if not applied and accepted and math.isfinite(previous) and abs(actual-previous)>tolerance:
                    try:camera.set(props[key],previous);actual=float(camera.get(props[key]))
                    except Exception:pass
                result[key]={'requested':target_value,'actual':actual if math.isfinite(actual) else None,
                             'supported':bool(accepted),'applied':bool(applied),
                             'error':None if applied else 'Nilai tidak didukung atau dibulatkan driver.'}
            except Exception as err:
                result[key]={'requested':value,'supported':False,'applied':False,'error':str(err)[:160]}
    return {'ok':True,'controls':result,'note':'Status berdasarkan pembacaan balik perangkat. Tidak semua driver mengekspos rentang yang tepat.'}


def _webcam_neutral_target(key, cap):
    """Conservative normal-picture estimate, NOT a claimed UVC factory default.

    OpenCV generally cannot expose IAMVideoProcAmp.GetRange's default field.
    If the hardware reports a negative signed brightness range, zero is the
    natural neutral point. Otherwise choose a mid-scale *nonzero* brightness.
    """
    import math
    lo=float(cap.get('min',0) or 0)
    hi=float(cap.get('max',100) or 100)
    current=float(cap.get('actual',0) or 0)
    if key=='brightness':
        if lo < 0: return 0.0
        return min(hi,max(lo,128.0 if hi>100 else 50.0))
    if key in ('saturation','contrast'):
        return min(hi,max(lo,128.0 if hi>100 else 50.0))
    if key=='hue': return 0.0
    if key=='auto_wb': return 1.0
    return None


def recover_camera_controls(target, profile=None, keys=None):
    """Explicit operator recovery for driver controls; no blind stale snapshot.

    Saved operator-confirmed good profiles take precedence. Without one,
    only brightness/contrast/saturation are sent as conservative estimates;
    ISO, exposure, gain, focus and WB temperature are deliberately NOT reset
    to invented values. Returns the actual driver readback for every attempt.
    """
    angle=int(target or 0)
    if angle not in (0,1):return {'ok':False,'error':'Angle kamera harus 0 atau 1.'}
    caps=get_camera_control_capabilities(angle)
    if not caps.get('open'):return {'ok':False,'error':'Kamera belum aktif.'}
    allowed={'brightness','contrast','saturation','gain','exposure','iso','focus','white_balance','sharpness'}
    requested=set(keys or []) if isinstance(keys,list) else None
    saved={}
    if isinstance(profile,dict) and requested is None:
        for name,value in profile.items():
            if name not in allowed or name not in caps['controls']:continue
            try:
                actual=float(value)
                if not __import__('math').isfinite(actual):continue
                c=caps['controls'][name]
                if c.get('available') and float(c.get('min',-1e6)) <= actual <= float(c.get('max',1e6)):
                    # A saved profile is explicitly confirmed by the operator.
                    saved[name]=actual
            except (TypeError,ValueError):continue
    mode='saved_profile' if saved else 'safe_neutral'
    values=saved if saved else {}
    if not values:
        for name in ('brightness','contrast','saturation'):
            if requested is not None and name not in requested:continue
            cap=caps['controls'].get(name,{})
            if not cap.get('available'):continue
            target_value=_webcam_neutral_target(name,cap)
            if target_value is not None:values[name]=target_value
    results={}
    for name,value in values.items():
        part=set_camera_controls(angle,{name:value})
        results[name]=(part.get('controls') or {}).get(name,{'applied':False,'error':part.get('error')})
    return {'ok':True,'camera':angle,'source':mode,'approximate':mode!='saved_profile',
            'controls':results,'note':'Nilai netral bukan factory default driver. Hanya perubahan yang diterima driver dianggap berhasil.'}


class Handler(BaseHTTPRequestHandler):
    protocol_version = 'HTTP/1.1'

    def log_message(self, fmt, *args):
        print('[HTTP]', fmt % args, flush=True)

    def stream_file(self, file_path, content_type, download_name=None):
        size = os.path.getsize(file_path)
        self.send_response(200)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(size))
        self.send_header('Cache-Control', 'no-store')
        if download_name:
            safe_name = re.sub(r'[^A-Za-z0-9._-]', '_', download_name)
            self.send_header('Content-Disposition', f'attachment; filename=\"{safe_name}\"')
        self.end_headers()
        with open(file_path, 'rb') as stream:
            shutil.copyfileobj(stream, self.wfile, length=256 * 1024)

    def stream_video_range(self, file_path, content_type):
        """Single-range support for Electron/Chromium WebM/MP4 playback."""
        size=os.path.getsize(file_path)
        requested=self.headers.get('Range','').strip()
        start,end=0,size-1
        if requested:
            match=re.fullmatch(r'bytes=(\d*)-(\d*)',requested)
            if not match or not any(match.groups()):
                self.send_response(416)
                self.send_header('Content-Range',f'bytes */{size}')
                self.send_header('Content-Length','0');self.end_headers();return
            if match.group(1):
                start=int(match.group(1));end=int(match.group(2)) if match.group(2) else size-1
            else:
                start=max(0,size-int(match.group(2)))
            if start>=size or end<start:
                self.send_response(416)
                self.send_header('Content-Range',f'bytes */{size}')
                self.send_header('Content-Length','0');self.end_headers();return
            end=min(end,size-1)
        count=end-start+1
        self.send_response(206 if requested else 200)
        self.send_header('Content-Type',content_type)
        self.send_header('Accept-Ranges','bytes')
        if requested:self.send_header('Content-Range',f'bytes {start}-{end}/{size}')
        self.send_header('Content-Length',str(count))
        self.send_header('Cache-Control','no-store')
        self.end_headers()
        with open(file_path,'rb') as video:
            video.seek(start)
            while count:
                block=video.read(min(count,262144))
                if not block:break
                self.wfile.write(block);count-=len(block)

    def send_json(self, data, code=200):
        body = json.dumps(data).encode('utf-8')
        self.send_response(code)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization, X-Requested-With')
        self.send_header('Access-Control-Allow-Private-Network', 'true')
        self.send_header('Vary', 'Origin')
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        # Electron loads the UI from file:// and talks to the local camera API.
        # JSON requests trigger a CORS preflight; without OPTIONS, Chromium reports
        # the misleading browser error "Failed to fetch" before POST reaches Python.
        self.send_response(204)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization, X-Requested-With')
        self.send_header('Access-Control-Allow-Private-Network', 'true')
        self.send_header('Access-Control-Max-Age', '600')
        self.send_header('Content-Length', '0')
        self.send_header('Vary', 'Origin')
        self.end_headers()

    def do_GET(self):
        global latest_frame
        path = urlparse(self.path).path
        if path == '/health':
            # A live HTTP server is not a healthy camera backend when OpenCV failed
            # to import. Return 503 so Electron cannot report a false-positive READY.
            if cv2 is None:
                return self.send_json({'ok': False, 'pid': os.getpid(), 'opencv': None,
                    'error': 'OpenCV gagal dimuat. Jalankan setup.bat dan periksa log Python.'}, 503)
            return self.send_json({'ok': True, 'pid': os.getpid(), 'opencv': cv2.__version__, 'camera_engine': 'OpenCV', 'app_version': os.environ.get('KACA_APP_VERSION', '0.9.63'), 'backend_protocol': int(os.environ.get('KACA_BACKEND_PROTOCOL', '3'))})
        if path == '/api/google-drive/callback':
            try:
                query={k:v[0] for k,v in parse_qs(urlparse(self.path).query).items()}
                google_drive.callback(query)
                with session_lock:
                    pending_session_id = active_session.get('id') if active_session and active_session.get('status') == 'active' and not active_session.get('drive_folder_id') else None
                if pending_session_id:
                    _start_session_drive_folder_provision(pending_session_id)
                with drive_jobs_lock:
                    for _jid,_job in drive_jobs.items():
                        if _job.get('status') in ('waiting_auth','error') and os.path.exists(_job.get('local_path','')):
                            _job['status']='pending';_job['attempts']=0;_job['error']=None;drive_jobs[_jid]=_job;drive_jobs_queue.put(_jid)
                    _save_drive_jobs()
                page='<html><meta charset="utf-8"><body style="font-family:Segoe UI;background:#111;color:#eee;padding:40px"><h2>Google Drive berhasil dihubungkan.</h2><p>Kembali ke KACA.ID. Anda dapat menutup halaman ini.</p><script>setTimeout(()=>window.close(),1800)</script></body></html>'
                raw=page.encode();self.send_response(200);self.send_header('Content-Type','text/html; charset=utf-8');self.send_header('Content-Length',str(len(raw)));self.end_headers();self.wfile.write(raw);return
            except Exception as exc:
                page=('<html><meta charset="utf-8"><body style="font-family:Segoe UI;background:#111;color:#eee;padding:40px"><h2>Gagal menghubungkan Google Drive</h2><p>'+str(exc).replace('<','&lt;')+'</p><p>Kembali ke KACA.ID dan coba lagi.</p></body></html>').encode()
                self.send_response(400);self.send_header('Content-Type','text/html; charset=utf-8');self.send_header('Content-Length',str(len(page)));self.end_headers();self.wfile.write(page);return
        if path == '/api/google-drive/status':
            with drive_jobs_lock: jobs=[dict(v) for v in drive_jobs.values()]
            jobs.sort(key=lambda x:x.get('updated_at',''),reverse=True)
            return self.send_json({'ok':True,**google_drive.status(),'jobs':jobs[:30]})
        if path.startswith('/api/google-drive/job/'):
            job_id=path.rsplit('/',1)[-1]
            with drive_jobs_lock: job=drive_jobs.get(job_id)
            return self.send_json({'ok':bool(job),'job':dict(job) if job else None},200 if job else 404)
        if path == '/api/whatsapp/status':
            with whatsapp_jobs_lock: jobs=[dict(v) for v in whatsapp_jobs.values()]
            jobs.sort(key=lambda x:x.get('updated_at',''),reverse=True)
            return self.send_json({'ok':True,**whatsapp_cloud.status(),'jobs':jobs[:30]})
        if path.startswith('/api/whatsapp/job/'):
            job_id=path.rsplit('/',1)[-1]
            with whatsapp_jobs_lock: job=whatsapp_jobs.get(job_id)
            return self.send_json({'ok':bool(job),'job':dict(job) if job else None},200 if job else 404)
        if path == '/api/vouchers':
            with voucher_lock:
                rows=[]
                for v in vouchers_store:
                    item=_voucher_public(v); item['status']=_voucher_status(v); rows.append(item)
            rows.sort(key=lambda x:x.get('created_at',''), reverse=True)
            return self.send_json({'ok':True,'vouchers':rows})
        if path == '/api/qris/status':
            doku = doku_qris.public_config()
            mode = str(qris_config.get('mode', 'static_manual'))
            configured = doku['configured'] if mode == 'doku_checkout' else os.path.isfile(QRIS_IMAGE_PATH)
            return self.send_json({'ok': True, 'configured': configured, 'merchant_name': qris_config.get('merchant_name',''),
                                   'instructions': qris_config.get('instructions','Scan QRIS lalu tunggu verifikasi.'),
                                   'amount': qris_config.get('amount',0), 'mode': mode, 'doku': doku})
        if path == '/api/qris/checkout/status':
            invoice = parse_qs(urlparse(self.path).query).get('invoice', [''])[0]
            try: return self.send_json({'ok': True, **doku_qris.check(invoice)})
            except Exception as exc: return self.send_json({'ok': False, 'error': str(exc)}, 409)
        if path == '/api/whatsapp/fonnte/status':
            return self.send_json({'ok': True, **fonnte_gateway.status()})
        if path == '/api/whatsapp/fonnte/device':
            try: return self.send_json({'ok': True, **fonnte_gateway.device_profile()})
            except Exception as exc: return self.send_json({'ok': False, 'error': str(exc)}, 400)
        if path == '/api/qris/image':
            if not os.path.isfile(QRIS_IMAGE_PATH): return self.send_json({'ok':False,'error':'QRIS belum dikonfigurasi admin.'},404)
            self.stream_file(QRIS_IMAGE_PATH, 'image/png'); return
        if cv2 is None:
            return self.send_json({'ok': False, 'error': 'opencv-python belum terpasang. Jalankan setup.bat.'}, 503)
        if path == '/api/printers':
            import subprocess
            printers=[]; errors=[]
            if sys.platform=='win32':
                windir=os.environ.get('WINDIR',r'C:\Windows')
                candidates=[shutil.which('powershell.exe'),os.path.join(windir,'System32','WindowsPowerShell','v1.0','powershell.exe'),shutil.which('pwsh.exe')]
                ps=next((x for x in candidates if x and os.path.isfile(x)),None)
                if ps:
                    commands=["Get-Printer | Select-Object Name,Default,PrinterStatus | ConvertTo-Json -Compress","Get-CimInstance Win32_Printer | Select-Object Name,Default,WorkOffline | ConvertTo-Json -Compress"]
                    for command in commands:
                        try:
                            raw=subprocess.check_output([ps,'-NoLogo','-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass','-Command',command],stderr=subprocess.STDOUT,timeout=15,text=True,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
                            parsed=json.loads(raw or '[]'); parsed=parsed if isinstance(parsed,list) else ([parsed] if parsed else [])
                            for x in parsed:
                                name=x.get('Name')
                                if not name: continue
                                status=x.get('PrinterStatus',0)
                                offline=bool(x.get('WorkOffline',False)) or str(status).lower() in ('offline','7')
                                printers.append({'name':name,'default':bool(x.get('Default')),'offline':offline})
                            if printers: break
                        except Exception as exc: errors.append(str(exc))
                # Fallback for systems where PowerShell is unavailable or printer cmdlets fail.
                if not printers:
                    try:
                        import winreg
                        key=winreg.OpenKey(winreg.HKEY_CURRENT_USER,r'Software\Microsoft\Windows NT\CurrentVersion\Devices')
                        i=0
                        while True:
                            try:
                                name,_,_=winreg.EnumValue(key,i); i+=1
                                if name: printers.append({'name':name,'default':False,'offline':False})
                            except OSError: break
                        winreg.CloseKey(key)
                        try:
                            value=winreg.QueryValueEx(winreg.OpenKey(winreg.HKEY_CURRENT_USER,r'Software\Microsoft\Windows NT\CurrentVersion\Windows'),'Device')[0]
                            default_name=value.split(',',1)[0]
                            for item in printers: item['default']=item['name']==default_name
                        except Exception: pass
                    except Exception as exc: errors.append(str(exc))
            return self.send_json({'ok':True,'printers':printers,'platform':sys.platform,'error':'; '.join(errors) if not printers and errors else None})
        if path == '/api/session/active':
            with session_lock:
                if not active_session or active_session.get('status') != 'active':
                    return self.send_json({'ok': True, 'active': False, 'session': None, 'photos': []})
                current = dict(active_session)
                current_photos = list(active_session.get('photos', []))
            return self.send_json({'ok': True, 'active': True, 'session': current, 'photos': current_photos})
        if path == '/api/camera/controls/capabilities':
            try:
                requested = int(parse_qs(urlparse(self.path).query).get('camera',['0'])[0])
                if requested not in (0,1): raise ValueError('Angle harus 0 atau 1.')
                return self.send_json(get_camera_control_capabilities(requested))
            except (ValueError,TypeError) as err:
                return self.send_json({'ok':False,'error':str(err)},400)
        if path == '/api/cloud/video-sessions':
            # Completed standalone video jobs contribute visitor/session counts.
            # Revenue is left unverified (0) unless a payment receipt is recorded.
            with drive_jobs_lock:
                jobs=[dict(v) for v in drive_jobs.values() if v.get('kind')=='video' and not v.get('local_deleted_at')]
            return self.send_json({'ok':True,'sessions':[
                {'id':'video-'+str(v.get('reference_id') or v.get('id') or '')[:30],
                 'mode':'VIDEO','event_name':str(v.get('event_name') or ''),
                 'finished_at':v.get('created_at') or v.get('updated_at'),
                 'payment_method':'','amount_idr':0,'verified_paid':False,
                 'drive_url':v.get('url') or '', 'photo_count':0}
                for v in jobs if v.get('reference_id') or v.get('id') ]})
        if path == '/api/cloud/booth-state':
            # Local-only state for Cloud Agent; prevents mid-session remote writes.
            with session_lock:
                photo_active=bool(active_session and active_session.get('status')=='active')
            with video_lock:
                video_active=bool(booth_video_writer is not None or shot_video_path is not None)
            return self.send_json({'ok':True,'session_active':photo_active or video_active,
                                   'photo_active':photo_active,'video_active':video_active})
        if path == '/api/status':
            with state_lock:
                result = dict(state)
                result['secondary_camera_open'] = (secondary_cap is not None and secondary_cap.isOpened()) or canon_secondary_controller is not None
                result['active_camera_angle'] = active_camera_angle
                if state['last_frame_time']:
                    result['last_frame_age_ms'] = round((time.time() - state['last_frame_time']) * 1000)
                else:
                    result['last_frame_age_ms'] = None
            controller = canon_controller
            if controller is not None:
                try:
                    canon_diag = controller.status()
                    result['canon_diagnostics'] = canon_diag
                    if result.get('backend') == 'Canon EDSDK Live View':
                        result['reader_alive'] = bool(
                            canon_diag.get('worker_alive') and canon_diag.get('frame_reader_alive')
                        )
                except Exception as diag_exc:
                    result['canon_diagnostics'] = {'diagnostic_error': str(diag_exc)}
            with video_lock:
                result['live_photo_recording'] = bool(shot_video_path)
                result['live_photo_frames'] = shot_video_frame_count
                result['live_photo_target_seconds'] = shot_video_target_seconds if shot_video_path else 0
                result['live_photo_session_id'] = shot_video_session_id
                result['live_photo_number'] = shot_video_number
            return self.send_json(result)
        if path == '/api/video-test.mp4':
            fp=os.path.join(DATA_DIR,'video-test.mp4')
            if not os.path.isfile(fp): return self.send_json({'ok':False,'error':'Belum ada hasil uji video.'},404)
            self.stream_file(fp, 'video/mp4'); return
        video_status_match = re.fullmatch(r'/api/video/([a-f0-9]{12})/status', path)
        if video_status_match:
            vid=video_status_match.group(1)
            video_path=os.path.join(DATA_DIR,'video_sessions',vid+'.mp4')
            with drive_jobs_lock:job=dict(drive_jobs.get(vid) or {})
            if job.get('local_deleted_at'):
                return self.send_json({'ok':False,'error':'Rekaman video telah melewati masa penyimpanan.'},410)
            ready=os.path.isfile(video_path) and os.path.getsize(video_path)>1024
            qr_path=job.get('qr_path') or ''
            return self.send_json({'ok':True,'id':vid,'local_ready':ready,
              'video_url':f'http://127.0.0.1:{PORT}/api/video/{vid}.mp4' if ready else None,
              'preview_ready':os.path.isfile(os.path.join(DATA_DIR,'video_sessions',vid+'.webm')),
              'preview_url':f'http://127.0.0.1:{PORT}/api/video/{vid}.webm',
              'preview_error':video_preview_errors.get(vid),
              'poster_url':f'http://127.0.0.1:{PORT}/api/video/{vid}/poster.jpg',
              'drive_status':job.get('status') or 'local_only',
              'drive_url':job.get('url'), 'drive_error':job.get('error'),
              'drive_share_warning':job.get('share_warning'),
              'qr_available':bool(not job.get('share_warning') and qr_path and os.path.isfile(qr_path)),
              'qr_url':f'http://127.0.0.1:{PORT}/api/video/{vid}/qr.png'})
        video_poster_match=re.fullmatch(r'/api/video/([a-f0-9]{12})/poster\.jpg',path)
        if video_poster_match:
            vid=video_poster_match.group(1)
            with drive_jobs_lock:job=dict(drive_jobs.get(vid) or {})
            src=job.get('local_path') or ''
            poster=os.path.join(os.path.dirname(src),vid+'_Poster.jpg') if src else ''
            if poster and os.path.isfile(poster):self.stream_file(poster,'image/jpeg');return
            return self.send_json({'ok':False,'error':'Poster video belum tersedia.'},404)
        video_qr_match = re.fullmatch(r'/api/video/([a-f0-9]{12})/qr\.png', path)
        if video_qr_match:
            video_id = video_qr_match.group(1)
            with drive_jobs_lock:
                video_job = dict(drive_jobs.get(video_id) or {})
            if video_job.get('kind') != 'video' or not video_job.get('url') or video_job.get('drive_deleted_at'):
                return self.send_json({'ok':False,'error':'QR Google Drive video belum tersedia.'},404)
            qr_path = video_job.get('qr_path')
            if not qr_path or not os.path.isfile(qr_path):
                return self.send_json({'ok':False,'error':'QR Google Drive video belum dibuat.'},404)
            self.stream_file(qr_path, 'image/png'); return
        download_match=re.fullmatch(r'/api/video/([a-f0-9]{12})/download\.mp4',path)
        if download_match:
            video_id=download_match.group(1)
            fp=os.path.join(DATA_DIR,'video_sessions',video_id+'.mp4')
            if not os.path.isfile(fp):return self.send_json({'ok':False,'error':'Video tidak ditemukan.'},404)
            self.send_response(200)
            self.send_header('Content-Type','video/mp4')
            self.send_header('Content-Disposition',f'attachment; filename="KACA-ID-Video-{video_id}.mp4"')
            self.send_header('Content-Length',str(os.path.getsize(fp)))
            self.send_header('Cache-Control','no-store')
            self.end_headers()
            with open(fp,'rb') as stream:shutil.copyfileobj(stream,self.wfile)
            return
        video_webm_match=re.fullmatch(r'/api/video/([a-f0-9]{12})\.webm',path)
        if video_webm_match:
            vid=video_webm_match.group(1)
            fp=os.path.join(DATA_DIR,'video_sessions',vid+'.webm')
            if not os.path.isfile(fp):return self.send_json({'ok':False,'error':'Preview WebM masih disiapkan.'},404)
            self.stream_video_range(fp,'video/webm');return
        video_match = re.fullmatch(r'/api/video/([a-f0-9]{12})\.mp4', path)
        if video_match:
            fp=os.path.join(DATA_DIR,'video_sessions',video_match.group(1)+'.mp4')
            if not os.path.isfile(fp): return self.send_json({'ok':False,'error':'File video tidak ditemukan.'},404)
            self.stream_video_range(fp,'video/mp4');return
        if path == '/api/canon/status':
            controller = canon_controller
            canon_status = controller.status() if controller else None
            return self.send_json({
                'ok': True,
                'active': bool(canon_status and canon_status.get('active')),
                'canon': canon_status,
            })
        if path == '/api/cameras':
            query = parse_qs(urlparse(self.path).query)
            start_scan(force=(query.get('refresh', ['0'])[0] == '1'))
            with state_lock:
                return self.send_json(dict(state))
        if path == '/api/canon/detect':
            return self.send_json(detect_canon_usb())
        if path == '/api/jpeg-check':
            with frame_condition:
                frame = None if latest_frame is None else latest_frame.copy()
            if frame is None:
                return self.send_json({'ok': False, 'error': 'Belum ada frame dari kamera.'}, 503)
            ok, jpg = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 92])
            if not ok:
                return self.send_json({'ok': False, 'error': 'cv2.imencode gagal.'}, 500)
            data = jpg.tobytes()
            decoded = cv2.imdecode(jpg, cv2.IMREAD_COLOR)
            return self.send_json({
                'ok': True, 'jpeg_bytes': len(data),
                'jpeg_magic_hex': data[:4].hex(),
                'jpeg_end_hex': data[-2:].hex(),
                'backend_decode_ok': decoded is not None,
                'decoded_shape': list(decoded.shape) if decoded is not None else None,
                'frame_shape': list(frame.shape)
            })
        if path == '/api/snapshot.jpg':
            with frame_condition:
                frame = None if latest_frame is None else latest_frame.copy()
            if frame is None:
                return self.send_json({'ok': False, 'error': 'Belum ada frame dari kamera.'}, 503)
            ok, jpg = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 88])
            if not ok:
                return self.send_json({'ok': False, 'error': 'Gagal mengubah frame menjadi JPEG.'}, 500)
            data = jpg.tobytes()
            self.send_response(200)
            self.send_header('Content-Type', 'image/jpeg')
            self.send_header('Content-Length', str(len(data)))
            self.send_header('Cache-Control', 'no-store, no-cache, must-revalidate')
            self.send_header('Connection', 'close')
            self.send_header('X-KACA-JPEG-Bytes', str(len(data)))
            self.send_header('X-KACA-JPEG-Magic', data[:3].hex())
            self.end_headers()
            self.wfile.write(data)
            self.wfile.flush()
            self.close_connection = True
            return
        if path == '/api/stream-secondary.mjpg':
            stream_query = parse_qs(urlparse(self.path).query)
            stream_fps = max(5.0, min(30.0, float((stream_query.get('fps') or ['10'])[0])))
            stream_quality = max(40, min(95, int((stream_query.get('quality') or ['76'])[0])))
            self.send_response(200); self.send_header('Cache-Control','no-store'); self.send_header('Content-Type','multipart/x-mixed-replace; boundary=frame'); self.end_headers(); last_id=-1; last_sent_at=0.0
            try:
                while True:
                    payload, current_id = _get_preview_jpeg(secondary=True, quality=stream_quality); now=time.monotonic()
                    if payload is None or current_id==last_id or now-last_sent_at < (1.0/stream_fps): time.sleep(.01); continue
                    packet=b'--frame\r\nContent-Type: image/jpeg\r\nContent-Length: '+str(len(payload)).encode()+b'\r\n\r\n'+payload+b'\r\n'
                    self.wfile.write(packet); self.wfile.flush(); last_id=current_id; last_sent_at=now
            except (BrokenPipeError,ConnectionResetError,ConnectionAbortedError,OSError): pass
            return
        if path == '/api/stream.mjpg':
            stream_query = parse_qs(urlparse(self.path).query)
            stream_fps = max(5.0, min(30.0, float((stream_query.get('fps') or ['15'])[0])))
            stream_quality = max(40, min(95, int((stream_query.get('quality') or ['76'])[0])))
            self.send_response(200); self.send_header('Cache-Control','no-store, no-cache, must-revalidate'); self.send_header('Pragma','no-cache'); self.send_header('Content-Type','multipart/x-mixed-replace; boundary=frame'); self.send_header('Connection','keep-alive'); self.end_headers()
            last_sent_id=-1; last_sent_at=0.0
            try:
                while True:
                    payload,current_id=_get_preview_jpeg(secondary=False, quality=stream_quality); now=time.monotonic()
                    if payload is None or current_id==last_sent_id or now-last_sent_at < (1.0/stream_fps): time.sleep(.008); continue
                    packet=b'--frame\r\nContent-Type: image/jpeg\r\nContent-Length: '+str(len(payload)).encode()+b'\r\n\r\n'+payload+b'\r\n'
                    self.wfile.write(packet); self.wfile.flush(); last_sent_id=current_id; last_sent_at=now
            except (BrokenPipeError,ConnectionResetError,ConnectionAbortedError,OSError): pass
            return
        # Animation fallback for Electron builds whose codecs reject an otherwise valid WebM.
        if path.startswith('/api/session/') and path.endswith('/output_live.gif'):
            sid=path.split('/')[-2]
            if not re.fullmatch(r'[A-Za-z0-9_-]{1,80}',sid):return self.send_json({'ok':False,'error':'ID sesi tidak valid.'},400)
            manifest=read_manifest(sid)
            if not manifest:return self.send_json({'ok':False,'error':'Sesi tidak ditemukan.'},404)
            session_dir=os.path.realpath(os.path.join(SESSIONS_DIR,sid))
            archive_dir=os.path.realpath(str(manifest.get('local_archive_path') or '')) if manifest.get('local_archive_path') else ''
            candidates=[os.path.realpath(os.path.join(session_dir,'output_live.gif'))]
            if archive_dir:candidates.append(os.path.realpath(os.path.join(archive_dir,'Live_Photos','Live_Photo_Frame_Animasi.gif')))
            for p in candidates:
                if os.path.isfile(p) and os.path.getsize(p)>1024 and (p.startswith(session_dir+os.sep) or (archive_dir and p.startswith(archive_dir+os.sep))):
                    self.stream_file(p,'image/gif');return
            animation_status=_start_live_animation_generation(sid,manifest)
            return self.send_json({'ok':False,'status':animation_status,'error':'Animasi sedang dibuat.' if animation_status=='processing' else 'Klip video belum tersedia.'},202 if animation_status=='processing' else 404)
        if path.startswith('/api/session/') and (path.endswith('/session_live.mp4') or path.endswith('/output_live.mp4') or path.endswith('/session_live.webm') or path.endswith('/output_live.webm') or '/live/' in path) and (path.endswith('.mp4') or path.endswith('.webm')):
            parts = path.split('/')
            sid = parts[3] if len(parts) > 3 else ''
            filename = parts[-1]
            if not sid.replace('-', '').isalnum() or not (filename in ('session_live.mp4','output_live.mp4','session_live.webm','output_live.webm') or (filename.startswith('live_') and filename.endswith(('.mp4','.webm')))):
                return self.send_json({'ok':False,'error':'Path video tidak valid.'},400)
            # Resolve the requested logical asset from the session directory first,
            # then from the durable local archive. Archive copies are written by
            # _archive_session_outputs() under Live_Photos and may outlive previews.
            manifest = read_manifest(sid)
            if not manifest: return self.send_json({'ok':False,'error':'Sesi tidak ditemukan.'},404)
            session_dir = os.path.realpath(os.path.join(SESSIONS_DIR, sid))
            archive_dir = os.path.realpath(str(manifest.get('local_archive_path') or '')) if manifest.get('local_archive_path') else ''
            archive_names = {
                'output_live.mp4': os.path.join('Live_Photos', 'Live_Photo_Frame.mp4'),
                'session_live.mp4': os.path.join('Live_Photos', 'Live_Photo_Frame.mp4'),
                'output_live.webm': os.path.join('Live_Photos', 'Live_Photo_Frame.webm'),
                'session_live.webm': os.path.join('Live_Photos', 'Live_Photo_Frame.webm'),
            }
            candidates = [os.path.realpath(os.path.join(session_dir, filename))]
            if archive_dir and filename in archive_names:
                candidates.append(os.path.realpath(os.path.join(archive_dir, archive_names[filename])))
            file_path = next((candidate for candidate in candidates
                              if os.path.isfile(candidate) and
                              (candidate.startswith(session_dir + os.sep) or
                               (archive_dir and candidate.startswith(archive_dir + os.sep)))), None)
            if not file_path: return self.send_json({'ok':False,'error':'Video Live Photo belum tersedia di folder sesi maupun arsip lokal.'},404)
            # Chromium's HTML5 video element commonly requests byte ranges for
            # MP4 metadata/seeking. Support RFC-style single byte ranges.
            file_size = os.path.getsize(file_path)
            range_header = self.headers.get('Range')
            if range_header:
                match = re.match(r'^bytes=(\d*)-(\d*)$', range_header.strip())
                if not match or (not match.group(1) and not match.group(2)):
                    self.send_response(416)
                    self.send_header('Content-Range', f'bytes */{file_size}')
                    self.send_header('Content-Length', '0')
                    self.end_headers()
                    return
                if match.group(1):
                    start = int(match.group(1))
                    end = int(match.group(2)) if match.group(2) else file_size - 1
                else:
                    suffix = int(match.group(2))
                    start = max(0, file_size - suffix)
                    end = file_size - 1
                if start >= file_size or end < start:
                    self.send_response(416)
                    self.send_header('Content-Range', f'bytes */{file_size}')
                    self.send_header('Content-Length', '0')
                    self.end_headers()
                    return
                end = min(end, file_size - 1)
                length = end - start + 1
                with open(file_path, 'rb') as video_file:
                    video_file.seek(start)
                    data = video_file.read(length)
                self.send_response(206)
                self.send_header('Content-Type', 'video/webm' if filename.endswith('.webm') else 'video/mp4')
                self.send_header('Accept-Ranges', 'bytes')
                self.send_header('Content-Range', f'bytes {start}-{end}/{file_size}')
                self.send_header('Content-Length', str(len(data)))
                self.send_header('Cache-Control', 'no-store')
                self.end_headers()
                self.wfile.write(data)
                return
            with open(file_path, 'rb') as video_file:
                data = video_file.read()
            self.send_response(200)
            self.send_header('Content-Type', 'video/webm' if filename.endswith('.webm') else 'video/mp4')
            self.send_header('Accept-Ranges', 'bytes')
            self.send_header('Content-Length', str(len(data)))
            self.send_header('Cache-Control', 'no-store')
            self.end_headers()
            self.wfile.write(data)
            return
        if path == '/api/frames':
            frames=[]
            for name in os.listdir(FRAMES_DIR):
                if name.endswith('.png') and re.match(r'^[a-f0-9]{12,32}\.png$',name):
                    
                    meta_path=os.path.join(FRAMES_DIR,name[:-4]+'.json')
                    try:
                        with open(meta_path,'r',encoding='utf-8') as mf: meta=json.load(mf)
                    except Exception: meta={}
                    frames.append({'id':name[:-4],'name':meta.get('name',name[:-4]),'active':bool(meta.get('enabled',True)),'enabled':bool(meta.get('enabled',True)),'width':meta.get('width'),'height':meta.get('height'),'event_id':meta.get('event_id') or None,'url':f'http://127.0.0.1:{PORT}/api/frames/{name}'})
            return self.send_json({'ok':True,'frames':frames})
        if path.startswith('/api/frames/') and path.endswith('/activate'):
            fid=path.split('/')[-2]
            if not re.match(r'^[a-f0-9]{12,32}$',fid): return self.send_json({'ok':False,'error':'ID frame tidak valid.'},400)
            for fname in os.listdir(FRAMES_DIR):
                if fname.endswith('.json'):
                    mp=os.path.join(FRAMES_DIR,fname)
                    try:
                        meta=json.load(open(mp,'r',encoding='utf-8')); meta['active']=fname[:-5]==fid
                        with open(mp,'w',encoding='utf-8') as mf: json.dump(meta,mf,ensure_ascii=False)
                    except Exception: pass
            return self.send_json({'ok':True,'active_frame_id':fid})
        if path.startswith('/api/frames/') and path.endswith('/delete'):
            fid=path.split('/')[-2]
            if not re.match(r'^[a-f0-9]{12,32}$',fid): return self.send_json({'ok':False,'error':'ID frame tidak valid.'},400)
            for ext in ('.png','.json'):
                fp=os.path.join(FRAMES_DIR,fid+ext)
                if os.path.isfile(fp): os.remove(fp)
            return self.send_json({'ok':True,'deleted':fid})
        if path.startswith('/api/frames/') and path.endswith('.png'):
            name=os.path.basename(path)
            if not re.match(r'^[a-f0-9]{12,32}\.png$',name): return self.send_json({'ok':False,'error':'Nama frame tidak valid.'},400)
            fp=os.path.join(FRAMES_DIR,name)
            if not os.path.isfile(fp): return self.send_json({'ok':False,'error':'Frame tidak ditemukan.'},404)
            self.stream_file(fp, 'image/png'); return
        if path.startswith('/api/session/') and path.endswith('/qr.png'):
            sid=path.split('/')[-2]
            if not re.fullmatch(r'[A-Za-z0-9_-]{1,80}', sid): return self.send_json({'ok':False,'error':'ID sesi tidak valid.'},400)
            manifest=read_manifest(sid)
            if not manifest:
                return self.send_json({'ok':False,'error':'Sesi tidak ditemukan.'},404)
            # v0.9.44-compatible QR serving: use the persisted manifest path first,
            # then the session copy, then the customer archive copy. The archive copy
            # is important because it can outlive a cleaned session-preview directory.
            session_dir=os.path.realpath(os.path.join(SESSIONS_DIR,sid))
            archive_dir=os.path.realpath(str(manifest.get('local_archive_path') or '')) if manifest.get('local_archive_path') else ''
            candidates=[]
            for candidate in (manifest.get('drive_qr_path'), manifest.get('drive_qr_archive_path'),
                              os.path.join(session_dir,'google_drive_qr.png'),
                              os.path.join(archive_dir,'Final_Results','QR_Google_Drive.png') if archive_dir else ''):
                if not candidate: continue
                candidate=os.path.realpath(str(candidate))
                allowed=(candidate.startswith(session_dir+os.sep) or candidate==session_dir or
                         (archive_dir and (candidate.startswith(archive_dir+os.sep) or candidate==archive_dir)))
                if allowed and candidate not in candidates: candidates.append(candidate)
            qr_bytes=None
            qr_path=next((candidate for candidate in candidates if os.path.isfile(candidate)),None)
            if not qr_path and manifest.get('drive_url'):
                _write_session_qr(manifest)
                write_manifest(manifest)
                candidates=[]
                for candidate in (manifest.get('drive_qr_path'), manifest.get('drive_qr_archive_path'),
                                  os.path.join(session_dir,'google_drive_qr.png'),
                                  os.path.join(archive_dir,'Final_Results','QR_Google_Drive.png') if archive_dir else ''):
                    if candidate:
                        candidate=os.path.realpath(str(candidate))
                        if (candidate.startswith(session_dir+os.sep) or (archive_dir and candidate.startswith(archive_dir+os.sep))) and candidate not in candidates:
                            candidates.append(candidate)
                qr_path=next((candidate for candidate in candidates if os.path.isfile(candidate)),None)
            if qr_path:
                try:
                    with open(qr_path,'rb') as qr_file: qr_bytes=qr_file.read()
                except OSError:
                    qr_bytes=None
            if not qr_bytes:
                detail=manifest.get('drive_qr_error') or manifest.get('drive_error')
                if not manifest.get('drive_url'):
                    detail=detail or ('Google Drive belum terhubung.' if manifest.get('drive_folder_status')=='waiting_auth' else 'Tautan folder Google Drive belum berhasil dibuat; QR belum dapat dibentuk.')
                else:
                    detail=detail or 'Tautan folder tersedia, tetapi PNG QR belum berhasil dibuat atau disimpan.'
                return self.send_json({'ok':False,'error':detail,'drive_folder_status':manifest.get('drive_folder_status'),'drive_status':manifest.get('drive_status'),'drive_url_available':bool(manifest.get('drive_url')),'drive_qr_path':manifest.get('drive_qr_path')},503)
            self.send_response(200); self.send_header('Content-Type','image/png'); self.send_header('Content-Disposition','inline; filename=KACA-session-qr.png'); self.send_header('Content-Length',str(len(qr_bytes))); self.send_header('Cache-Control','no-store, max-age=0'); self.end_headers(); self.wfile.write(qr_bytes); return
        if path.startswith('/api/session/') and path.endswith('/render-status'):
            sid=path.split('/')[-2]
            manifest=read_manifest(sid)
            if not manifest: return self.send_json({'ok':False,'error':'Sesi tidak ditemukan.'},404)
            # Important recovery path: OAuth may complete after /finish has cleared
            # active_session. In that case the old callback cannot identify the finished
            # session, so status polling itself provisions its Drive folder and QR.
            if (google_drive.status().get('connected') and not manifest.get('drive_folder_id')
                    and manifest.get('drive_folder_status') in ('waiting_auth','error','pending',None)):
                manifest['drive_folder_status']='creating'
                manifest['drive_status']='provisioning'
                write_manifest(manifest)
                print('[GOOGLE_DRIVE_FOLDER_PROVISION_TRIGGERED_BY_STATUS]', sid, flush=True)
                _start_session_drive_folder_provision(sid)
            session_dir=os.path.join(SESSIONS_DIR,sid)
            still_name=manifest.get('output') or 'output.jpg'
            still_ready=os.path.isfile(os.path.join(session_dir,still_name))
            live_master=str(manifest.get('live_output') or 'output_live.mp4').replace('\\','/').split('/')[-1]
            live_preview=str(manifest.get('live_output_preview') or '').replace('\\','/').split('/')[-1]
            if live_preview not in ('output_live.webm','output_live.mp4'): live_preview=''
            archive_dir=os.path.realpath(str(manifest.get('local_archive_path') or '')) if manifest.get('local_archive_path') else ''
            def _live_asset_exists(name):
                if name not in ('output_live.mp4','output_live.webm'): return False
                session_candidate=os.path.join(session_dir,name)
                archive_candidate=os.path.join(archive_dir,'Live_Photos','Live_Photo_Frame.'+('webm' if name.endswith('.webm') else 'mp4')) if archive_dir else ''
                return os.path.isfile(session_candidate) or bool(archive_candidate and os.path.isfile(archive_candidate))
            live_master_ready=live_master in ('output_live.mp4','output_live.webm') and _live_asset_exists(live_master)
            live_preview_ready=bool(live_preview and _live_asset_exists(live_preview))
            if not live_preview_ready:
                for fallback_name in ('output_live.webm','output_live.mp4'):
                    if _live_asset_exists(fallback_name):
                        live_preview=fallback_name; live_preview_ready=True; break
            if not live_master_ready:
                live_master = 'output_live.mp4' if _live_asset_exists('output_live.mp4') else ('output_live.webm' if _live_asset_exists('output_live.webm') else '')
                live_master_ready=bool(live_master)
            qr_candidates=[]
            for raw_candidate in (manifest.get('drive_qr_path'), manifest.get('drive_qr_archive_path'),
                                  os.path.join(session_dir,'google_drive_qr.png'),
                                  os.path.join(archive_dir,'Final_Results','QR_Google_Drive.png') if archive_dir else ''):
                if not raw_candidate: continue
                candidate=os.path.realpath(str(raw_candidate))
                if (candidate.startswith(os.path.realpath(session_dir)+os.sep) or
                    (archive_dir and candidate.startswith(archive_dir+os.sep))):
                    qr_candidates.append(candidate)
            qr_available=any(os.path.isfile(candidate) and os.path.getsize(candidate)>0 for candidate in qr_candidates)
            return self.send_json({'ok':True,'status':manifest.get('status'),'render_status':manifest.get('render_status','ready' if still_ready else 'processing'),'still_ready':still_ready,'render_error':manifest.get('render_error'),'live_photo_enabled':bool(manifest.get('live_photo_enabled')),'live_output':manifest.get('live_output') or ('output_live.mp4' if live_master_ready else None),'live_output_available':bool(live_master_ready or live_preview_ready),'live_output_preview':live_preview if live_preview_ready else None,'live_output_preview_available':live_preview_ready,'gif_output':manifest.get('gif_output'),'gif_available':os.path.isfile(os.path.join(session_dir,'originals.gif')),'output':manifest.get('output'),'local_archive_path':manifest.get('local_archive_path'),'local_archive_status':manifest.get('local_archive_status'),'drive_status':manifest.get('drive_status'),'drive_url':manifest.get('drive_url'),'drive_folder_status':manifest.get('drive_folder_status'),'drive_folder_id':manifest.get('drive_folder_id'),'drive_error':manifest.get('drive_error'),'drive_share_warning':manifest.get('drive_share_warning'),'drive_qr_error':manifest.get('drive_qr_error'),'drive_qr_path_available':qr_available,'drive_qr_available':qr_available})
        if path.startswith('/api/session/') and path.endswith('/status'):
            sid=path.split('/')[3] if len(path.split('/'))>3 else ''
            if not sid.replace('-','').isalnum(): return self.send_json({'ok':False,'error':'ID sesi tidak valid.'},400)
            manifest=read_manifest(sid)
            if not manifest: return self.send_json({'ok':False,'error':'Sesi tidak ditemukan.'},404)
            return self.send_json({'ok':True,'session':manifest})
        if path == '/api/retention/status':
            return self.send_json({'ok': True, **session_retention.get()})
        if path == '/api/sessions':
            items = []
            try:
                for sid in os.listdir(SESSIONS_DIR):
                    item = read_manifest(sid)
                    if item and item.get('status') == 'finished' and not item.get('local_deleted_at'): items.append(item)
            except Exception: pass
            items.sort(key=lambda x: x.get('created_at',''), reverse=True)
            return self.send_json({'ok': True, 'sessions': items})
        if path.startswith('/api/session/') and '/photo/' in path and path.endswith('.jpg'):
            parts = path.split('/')
            if len(parts) != 6: return self.send_json({'ok':False,'error':'Path foto tidak valid.'},400)
            sid, filename = parts[3], unquote(parts[5])
            if not sid.replace('-', '').isalnum() or not filename.startswith('photo_') or not filename.endswith('.jpg'):
                return self.send_json({'ok':False,'error':'Path foto tidak valid.'},400)
            file_path = os.path.join(SESSIONS_DIR, sid, filename)
            if not os.path.isfile(file_path): return self.send_json({'ok':False,'error':'Foto tidak ditemukan.'},404)
            self.stream_file(file_path, 'image/jpeg'); return
        if path.startswith('/api/session/') and path.endswith('/download.zip'):
            sid = path.split('/')[3] if len(path.split('/')) > 3 else ''
            if not sid.replace('-', '').isalnum(): return self.send_json({'ok':False,'error':'ID sesi tidak valid.'},400)
            folder = os.path.join(SESSIONS_DIR, sid)
            manifest = read_manifest(sid)
            if not manifest or manifest.get('status') != 'finished': return self.send_json({'ok':False,'error':'Sesi belum selesai.'},404)
            archive_path = manifest.get('local_archive_path')
            archive_zip = os.path.join(archive_path, 'KACA-ID-Hasil-Sesi.zip') if archive_path else ''
            zip_path = archive_zip if archive_zip and os.path.isfile(archive_zip) else os.path.join(folder, 'KACA-ID-Hasil-Sesi.zip')
            try:
                if zip_path == os.path.join(folder, 'KACA-ID-Hasil-Sesi.zip'):
                    with zipfile.ZipFile(zip_path, 'w', compression=zipfile.ZIP_STORED) as bundle:
                        def add_file(filename, arcname):
                            full = os.path.join(folder, filename)
                            if os.path.isfile(full): bundle.write(full, arcname)
                        add_file('output.jpg', f'Frame/KACA-ID-{sid}-Frame.jpg')
                        add_file('output_live.mp4', f'Live Photo dalam Frame/KACA-ID-{sid}-Live-Frame.mp4')
                        add_file('originals.gif', f'GIF/KACA-ID-{sid}-Originals.gif')
                        for photo in manifest.get('photos', []):
                            original = photo.get('original', '')
                            if re.match(r'^original_\d+\.jpg$', original):
                                add_file(original, f'Foto Original/Foto-{int(photo.get("number", 0)):02d}.jpg')
                self.stream_file(zip_path, 'application/zip', f'KACA-ID-{sid}-Hasil.zip'); return
            except Exception as exc:
                return self.send_json({'ok':False,'error':f'Gagal membuat ZIP hasil: {exc}'},500)
        if path.startswith('/api/session/') and path.endswith('/output.jpg'):
            sid = path.split('/')[3]
            if not sid.replace('-', '').isalnum(): return self.send_json({'ok':False,'error':'ID sesi tidak valid.'},400)
            file_path = os.path.join(SESSIONS_DIR, sid, 'output.jpg')
            if not os.path.isfile(file_path): return self.send_json({'ok':False,'error':'Hasil sesi belum tersedia.'},404)
            self.stream_file(file_path, 'image/jpeg'); return
        # Preview the two OpenCV artistic filters before finalizing the session.
        # Restricted to same-session original JPEGs and fixed filter identifiers.
        if path.startswith('/api/session/') and '/filter-preview/' in path:
            parts=path.split('/')
            if len(parts)!=7:
                return self.send_json({'ok':False,'error':'Path preview filter tidak valid.'},400)
            sid,filter_id,filename=parts[3],parts[5],unquote(parts[6])
            if (not re.fullmatch(r'[A-Za-z0-9-]{1,64}',sid)
                    or filter_id not in ('pencil','cartoon')
                    or not re.fullmatch(r'original_\d+\.jpg',filename)):
                return self.send_json({'ok':False,'error':'Parameter preview filter tidak valid.'},400)
            file_path=os.path.join(SESSIONS_DIR,sid,filename)
            if not os.path.isfile(file_path):
                return self.send_json({'ok':False,'error':'Foto original tidak tersedia.'},404)
            try:
                source=cv2.imread(file_path,cv2.IMREAD_COLOR)
                if source is None: raise ValueError('JPG sumber tidak dapat dibaca.')
                height,width=source.shape[:2]
                if max(height,width)>900:
                    scale=900.0/max(height,width)
                    source=cv2.resize(source,(max(1,round(width*scale)),max(1,round(height*scale))),interpolation=cv2.INTER_AREA)
                filtered=apply_filter(source,filter_id)
                ok,data=cv2.imencode('.jpg',filtered,[int(cv2.IMWRITE_JPEG_QUALITY),87])
                if not ok: raise RuntimeError('Gagal mengodekan preview filter.')
                payload=data.tobytes()
                self.send_response(200)
                self.send_header('Content-Type','image/jpeg')
                self.send_header('Content-Length',str(len(payload)))
                self.send_header('Cache-Control','no-store')
                self.end_headers()
                self.wfile.write(payload)
            except Exception as exc:
                self.send_json({'ok':False,'error':'Gagal membuat preview: '+str(exc)},500)
            return
        if path.startswith('/api/session/') and '/preview/' in path and path.endswith('.jpg'):
            parts=path.split('/'); sid=parts[3] if len(parts)>3 else ''; filename=unquote(parts[-1])
            preview_path=_session_preview_thumbnail(sid, filename)
            if not preview_path: return self.send_json({'ok':False,'error':'Thumbnail preview tidak tersedia.'},404)
            self.stream_file(preview_path, 'image/jpeg'); return
        if path.startswith('/api/session/') and '/original/' in path and path.endswith('.jpg'):
            parts=path.split('/'); sid=parts[3] if len(parts)>3 else ''; filename=unquote(parts[-1])
            if not sid.replace('-','').isalnum() or not re.match(r'^original_\d+\.jpg$',filename): return self.send_json({'ok':False,'error':'Path foto original tidak valid.'},400)
            file_path=os.path.join(SESSIONS_DIR,sid,filename)
            if not os.path.isfile(file_path): return self.send_json({'ok':False,'error':'Foto original tidak ditemukan.'},404)
            self.stream_file(file_path, 'image/jpeg'); return
        if path.startswith('/api/session/') and path.endswith('/originals.gif'):
            sid=path.split('/')[3] if len(path.split('/'))>3 else ''
            if not sid.replace('-','').isalnum(): return self.send_json({'ok':False,'error':'ID sesi tidak valid.'},400)
            file_path=os.path.join(SESSIONS_DIR,sid,'originals.gif')
            if not os.path.isfile(file_path): return self.send_json({'ok':False,'error':'GIF sesi belum tersedia.'},404)
            self.stream_file(file_path, 'image/gif'); return
        return self.send_json({'ok': False, 'error': 'Not found'}, 404)

    def do_POST(self):
        try:
            return self._do_POST()
        except Exception as exc:
            print('[HTTP_POST_UNHANDLED]', repr(exc), flush=True)
            traceback.print_exc()
            try:
                return self.send_json({'ok': False, 'error': f'Kesalahan internal backend: {type(exc).__name__}: {exc}'}, 500)
            except Exception:
                # The client may already have disconnected; keep the traceback in
                # the backend log so the root cause is still visible.
                return None

    def _do_POST(self):
        global active_session, video_test_writer, video_test_path, video_test_started, video_test_frames, video_test_fps, video_test_width, video_test_height, video_test_passed
        path = urlparse(self.path).path
        if cv2 is None and not (path.startswith('/api/vouchers') or path.startswith('/api/qris/') or path.startswith('/api/whatsapp/fonnte/') or path.startswith('/api/retention/')):
            return self.send_json({'ok': False, 'error': 'opencv-python belum terpasang.'}, 503)
        length = int(self.headers.get('Content-Length', '0'))
        try:
            data = json.loads(self.rfile.read(length) or b'{}')
        except Exception:
            data = {}
        if path == '/api/retention/config':
            try:
                return self.send_json({'ok': True, **session_retention.set(data)})
            except (TypeError, ValueError) as exc:
                return self.send_json({'ok': False, 'error': str(exc)}, 400)
        if path == '/api/retention/run':
            # Used by operator after saving policy, not an unconditional deletion.
            try:
                return self.send_json({'ok': True, **_retention_sweep_once()})
            except Exception as exc:
                return self.send_json({'ok': False, 'error': str(exc)}, 500)
        if path == '/api/vouchers/import':
            try:
                rows=data.get('vouchers') or []
                if not isinstance(rows,list) or not rows: raise ValueError('File CSV tidak berisi baris voucher.')
                now=datetime.datetime.now(); created=[]; skipped=[]
                with voucher_lock:
                    existing={str(v.get('code','')).upper() for v in vouchers_store}
                    for idx,row in enumerate(rows, start=2):
                        if not isinstance(row,dict): skipped.append({'row':idx,'reason':'Format baris tidak valid'}); continue
                        code=str(row.get('code') or row.get('kode') or row.get('kode_voucher') or '').strip().upper()
                        if not re.fullmatch(r'[A-Z0-9]{3,32}',code): skipped.append({'row':idx,'code':code,'reason':'Kode harus 3–32 karakter huruf/angka'}); continue
                        if code in existing: skipped.append({'row':idx,'code':code,'reason':'Kode sudah ada'}); continue
                        try:
                            uses=max(1,min(100000,int(row.get('max_uses') or row.get('batas_penggunaan') or 1)))
                            used=max(0,min(uses,int(row.get('used_count') or row.get('sudah_digunakan') or 0)))
                            expiry=str(row.get('expires_at') or row.get('kadaluarsa') or '').strip()
                            if expiry:
                                if re.fullmatch(r'\d{4}-\d{2}-\d{2}',expiry): expiry += 'T23:59:59'
                                try: expires=datetime.datetime.fromisoformat(expiry.replace('Z','+00:00')).replace(tzinfo=None).isoformat(timespec='seconds')
                                except Exception: raise ValueError('Format expires_at gunakan YYYY-MM-DD atau YYYY-MM-DDTHH:MM:SS')
                            else:
                                days=max(1,min(3650,int(row.get('expiry_days') or row.get('masa_berlaku_hari') or 30)))
                                expires=(now+datetime.timedelta(days=days)).isoformat(timespec='seconds')
                            active=str(row.get('active','true')).strip().lower() not in ('0','false','no','nonaktif')
                            item={'code':code,'created_at':now.isoformat(timespec='seconds'),'expires_at':expires,'max_uses':uses,'used_count':used,'active':active,'custom':True}
                            vouchers_store.append(item); existing.add(code); created.append(_voucher_public(item))
                        except Exception as exc: skipped.append({'row':idx,'code':code,'reason':str(exc)})
                    if created: _save_vouchers()
                return self.send_json({'ok':True,'imported':len(created),'skipped':skipped,'created':created})
            except Exception as exc: return self.send_json({'ok':False,'error':str(exc)},400)
        if path == '/api/vouchers/generate':
            try:
                import secrets, string
                count=max(1,min(1000,int(data.get('count',1))))
                uses=max(1,min(100000,int(data.get('max_uses',1))))
                expiry_days=max(1,min(3650,int(data.get('expiry_days',30))))
                custom=str(data.get('custom_code') or '').strip().upper()
                if custom and (count != 1 or not re.fullmatch(r'[A-Z0-9]{3,32}',custom)):
                    raise ValueError('Kode custom harus 3–32 karakter huruf besar/angka dan jumlah dibuat 1.')
                now=datetime.datetime.now(); expires=(now+datetime.timedelta(days=expiry_days)).isoformat(timespec='seconds')
                alphabet=string.ascii_uppercase+string.digits
                created=[]
                with voucher_lock:
                    existing={str(v.get('code','')).upper() for v in vouchers_store}
                    for i in range(count):
                        if custom:
                            code=custom
                            if code in existing: raise ValueError('Kode voucher custom sudah pernah digunakan.')
                        else:
                            code=''
                            for _ in range(100):
                                candidate=''.join(secrets.choice(alphabet) for _ in range(5))
                                if candidate not in existing: code=candidate; break
                            if not code: raise RuntimeError('Gagal membuat kode unik. Coba lagi.')
                        existing.add(code)
                        row={'code':code,'created_at':now.isoformat(timespec='seconds'),'expires_at':expires,'max_uses':uses,'used_count':0,'active':True,'custom':bool(custom)}
                        vouchers_store.append(row); created.append(_voucher_public(row))
                    _save_vouchers()
                return self.send_json({'ok':True,'created':created,'count':len(created)})
            except Exception as exc: return self.send_json({'ok':False,'error':str(exc)},400)
        if path == '/api/vouchers/validate':
            code=str(data.get('code') or '').strip().upper()
            if not code: return self.send_json({'ok':False,'error':'Masukkan kode voucher.'},400)
            with voucher_lock:
                voucher=next((v for v in vouchers_store if str(v.get('code','')).upper()==code),None)
                if not voucher: return self.send_json({'ok':False,'error':'Kode voucher tidak ditemukan.'},404)
                status=_voucher_status(voucher)
                if status!='aktif':
                    messages={'nonaktif':'Voucher sudah dinonaktifkan.','kedaluwarsa':'Voucher sudah kedaluwarsa.','habis':'Batas penggunaan voucher sudah tercapai.'}
                    return self.send_json({'ok':False,'error':messages.get(status,'Voucher tidak dapat digunakan.'),'status':status},409)
                return self.send_json({'ok':True,'voucher':_voucher_public(voucher),'remaining_uses':max(0,int(voucher.get('max_uses',1))-int(voucher.get('used_count',0)))})
        if path == '/api/vouchers/redeem':
            code=str(data.get('code') or '').strip().upper()
            if not code: return self.send_json({'ok':False,'error':'Masukkan kode voucher.'},400)
            with voucher_lock:
                voucher=next((v for v in vouchers_store if str(v.get('code','')).upper()==code),None)
                if not voucher: return self.send_json({'ok':False,'error':'Kode voucher tidak ditemukan.'},404)
                status=_voucher_status(voucher)
                if status!='aktif':
                    messages={'nonaktif':'Voucher sudah dinonaktifkan.','kedaluwarsa':'Voucher sudah kedaluwarsa.','habis':'Batas penggunaan voucher sudah tercapai.'}
                    return self.send_json({'ok':False,'error':messages.get(status,'Voucher tidak dapat digunakan.'),'status':status},409)
                voucher['used_count']=int(voucher.get('used_count',0))+1
                voucher['last_used_at']=datetime.datetime.now().isoformat(timespec='seconds')
                _save_vouchers()
                return self.send_json({'ok':True,'voucher':_voucher_public(voucher),'remaining_uses':max(0,int(voucher.get('max_uses',1))-int(voucher['used_count']))})
        if path == '/api/vouchers/delete':
            try:
                mode = str(data.get('mode') or '').strip().lower()
                codes = data.get('codes') or []
                if mode not in ('', 'all', 'expired'):
                    raise ValueError('Mode penghapusan tidak dikenal.')
                if mode == 'all':
                    with voucher_lock:
                        deleted = len(vouchers_store)
                        vouchers_store.clear()
                        _save_vouchers()
                    return self.send_json({'ok': True, 'deleted': deleted, 'mode': 'all'})
                with voucher_lock:
                    if mode == 'expired':
                        kept = [v for v in vouchers_store if not _voucher_is_expired(v)]
                        deleted = len(vouchers_store) - len(kept)
                        vouchers_store[:] = kept
                    else:
                        if not isinstance(codes, list) or not codes:
                            raise ValueError('Pilih minimal satu kode voucher untuk dihapus.')
                        normalized = {str(code or '').strip().upper() for code in codes if str(code or '').strip()}
                        if not normalized:
                            raise ValueError('Daftar kode voucher kosong.')
                        kept = [v for v in vouchers_store if str(v.get('code', '')).upper() not in normalized]
                        deleted = len(vouchers_store) - len(kept)
                        vouchers_store[:] = kept
                    if deleted: _save_vouchers()
                return self.send_json({'ok': True, 'deleted': deleted, 'mode': mode or 'selected'})
            except Exception as exc:
                return self.send_json({'ok': False, 'error': str(exc)}, 400)
        if path == '/api/vouchers/toggle':
            code=str(data.get('code') or '').strip().upper()
            with voucher_lock:
                voucher=next((v for v in vouchers_store if str(v.get('code','')).upper()==code),None)
                if not voucher: return self.send_json({'ok':False,'error':'Voucher tidak ditemukan.'},404)
                voucher['active']=bool(data.get('active',False)); _save_vouchers()
                return self.send_json({'ok':True,'voucher':_voucher_public(voucher),'status':_voucher_status(voucher)})
        if path == '/api/qris/gateway/config':
            try:
                mode = str(data.get('mode') or 'static_manual')
                if mode not in ('static_manual', 'doku_checkout'):
                    raise ValueError('Metode QRIS tidak dikenal.')
                if mode == 'doku_checkout':
                    doku = doku_qris.configure(data)
                else:
                    doku = doku_qris.public_config()
                qris_config['mode'] = mode
                with open(qris_config_path + '.tmp', 'w', encoding='utf-8') as f:
                    json.dump(qris_config, f, ensure_ascii=False, indent=2)
                os.replace(qris_config_path + '.tmp', qris_config_path)
                return self.send_json({'ok': True, 'mode': mode, 'doku': doku})
            except Exception as exc:
                return self.send_json({'ok': False, 'error': str(exc)}, 400)
        if path == '/api/qris/checkout/create':
            try:
                if qris_config.get('mode') != 'doku_checkout':
                    raise ValueError('Mode DOKU QRIS belum aktif.')
                amount = int(qris_config.get('amount') or 0)
                return self.send_json({'ok': True, **doku_qris.create(amount)})
            except Exception as exc:
                return self.send_json({'ok': False, 'error': str(exc)}, 400)
        if path == '/api/whatsapp/fonnte/config':
            try: return self.send_json({'ok': True, **fonnte_gateway.configure(data.get('token'))})
            except Exception as exc: return self.send_json({'ok': False, 'error': str(exc)}, 400)
        if path == '/api/whatsapp/fonnte/send':
            try:
                kind=str(data.get('kind') or 'session').lower()
                sid = str(data.get('video_id') if kind=='video' else data.get('session_id') or '')
                if not re.fullmatch(r'[a-f0-9]{12}', sid):raise ValueError('ID sesi/video tidak valid.')
                if kind=='video':
                    with drive_jobs_lock:job=dict(drive_jobs.get(sid) or {})
                    if job.get('kind')!='video':raise ValueError('Arsip video tidak ditemukan.')
                    if job.get('share_warning'):raise ValueError('Folder video belum dapat dibuka publik.')
                    url=str(job.get('url') or '')
                elif kind=='session':
                    manifest=read_manifest(sid)
                    if not manifest:raise ValueError('Sesi hasil tidak ditemukan.')
                    url=str(manifest.get('drive_url') or manifest.get('drive_share_url') or '')
                else:raise ValueError('Jenis hasil tidak didukung.')
                return self.send_json(fonnte_gateway.send(sid, data.get('phone'), url, data.get('consent')))
            except Exception as exc:
                return self.send_json({'ok': False, 'error': str(exc)}, 400)
        if path == '/api/qris/config':
            try:
                # base64 is imported at module scope; do not shadow it locally.
                merchant=str(data.get('merchant_name') or '').strip()[:100]
                instructions=str(data.get('instructions') or '').strip()[:500]
                amount=max(0,int(data.get('amount') or 0))
                data_url=str(data.get('image_data_url') or '')
                if data_url:
                    if not data_url.startswith('data:image/') or ';base64,' not in data_url: raise ValueError('File QRIS harus berupa gambar PNG atau JPEG.')
                    mime,encoded=data_url.split(';base64,',1)
                    if mime not in ('data:image/png','data:image/jpeg','data:image/jpg'): raise ValueError('Format gambar QRIS harus PNG atau JPEG.')
                    raw=base64.b64decode(encoded,validate=True)
                    if not raw or len(raw)>5*1024*1024: raise ValueError('Ukuran gambar QRIS maksimal 5 MB.')
                    import numpy as np
                    arr=cv2.imdecode(np.frombuffer(raw,dtype=np.uint8),cv2.IMREAD_UNCHANGED) if cv2 is not None else None
                    if arr is None: raise ValueError('Gambar QRIS tidak dapat dibaca.')
                    cv2.imwrite(QRIS_IMAGE_PATH,arr)
                if not os.path.isfile(QRIS_IMAGE_PATH) and qris_config.get('mode') != 'doku_checkout': raise ValueError('Unggah gambar QRIS terlebih dahulu.')
                qris_config.update({'merchant_name':merchant,'instructions':instructions or 'Scan QRIS, lalu tunjukkan bukti pembayaran kepada operator.','amount':amount,'updated_at':datetime.datetime.now().isoformat(timespec='seconds')})
                with open(qris_config_path+'.tmp','w',encoding='utf-8') as qf: json.dump(qris_config,qf,ensure_ascii=False,indent=2)
                os.replace(qris_config_path+'.tmp',qris_config_path)
                return self.send_json({'ok':True,'configured':True,'mode':'static_manual'})
            except Exception as exc: return self.send_json({'ok':False,'error':str(exc)},400)
        if path == '/api/google-drive/config':
            try:
                result=google_drive.configure(data.get('client_id'),data.get('client_secret'))
                return self.send_json({'ok':True,**result})
            except Exception as exc: return self.send_json({'ok':False,'error':str(exc)},400)
        if path == '/api/google-drive/auth-url':
            try: return self.send_json({'ok':True,'url':google_drive.auth_url()})
            except Exception as exc: return self.send_json({'ok':False,'error':str(exc)},400)
        if path == '/api/google-drive/disconnect':
            return self.send_json({'ok':True,**google_drive.disconnect()})
        if path == '/api/google-drive/retry':
            count=0
            with drive_jobs_lock:
                for jid,job in drive_jobs.items():
                    if job.get('status') in ('waiting_auth','error','pending'):
                        job['status']='pending';job['attempts']=0;job['error']=None;drive_jobs[jid]=job;drive_jobs_queue.put(jid);count+=1
                _save_drive_jobs()
            return self.send_json({'ok':True,'queued':count})
        if path == '/api/whatsapp/config':
            try: return self.send_json({'ok':True,**whatsapp_cloud.configure(data)})
            except Exception as exc: return self.send_json({'ok':False,'error':str(exc)},400)
        if path == '/api/whatsapp/send':
            try:
                if data.get('consent') is not True: raise ValueError('Pelanggan harus menyetujui pengiriman hasil melalui WhatsApp.')
                kind=str(data.get('kind') or 'session').strip().lower()
                reference_id=str(data.get('video_id') if kind == 'video' else data.get('session_id') or '').strip()
                job, duplicate = enqueue_whatsapp_job(reference_id, data.get('phone'), kind=kind)
                return self.send_json({'ok':True,'job':job,'duplicate':duplicate},200)
            except Exception as exc: return self.send_json({'ok':False,'error':str(exc)},400)
        if path == '/api/whatsapp/retry':
            job_id=str(data.get('job_id') or '').strip()
            with whatsapp_jobs_lock:
                job=whatsapp_jobs.get(job_id)
                if not job: return self.send_json({'ok':False,'error':'Antrean WhatsApp tidak ditemukan.'},404)
                if job.get('status') == 'sent': return self.send_json({'ok':True,'job':dict(job),'already_sent':True})
                job.update({'status':'waiting_drive','error':None,'attempts':0,'updated_at':datetime.datetime.now().isoformat(timespec='seconds')})
                whatsapp_jobs[job_id]=job; _save_whatsapp_jobs()
            whatsapp_jobs_queue.put(job_id)
            return self.send_json({'ok':True,'job':dict(job)})
        if path == '/api/storage/location':
            global LOCAL_ARCHIVE_ROOT
            raw_path = str(data.get('path') or '').strip()
            candidate = os.path.abspath(os.path.expanduser(raw_path)) if raw_path else DEFAULT_LOCAL_ARCHIVE_ROOT
            if raw_path and not os.path.isabs(os.path.expanduser(raw_path)):
                return self.send_json({'ok': False, 'error': 'Folder penyimpanan harus berupa path absolut.'}, 400)
            try:
                os.makedirs(candidate, exist_ok=True)
                probe = os.path.join(candidate, '.kaca_write_test')
                with open(probe, 'w', encoding='utf-8') as test_file: test_file.write('ok')
                os.remove(probe)
            except OSError as exc:
                return self.send_json({'ok': False, 'error': f'Folder tidak dapat ditulis: {exc}'}, 400)
            LOCAL_ARCHIVE_ROOT = candidate
            return self.send_json({'ok': True, 'path': LOCAL_ARCHIVE_ROOT})
        if path == '/api/camera/secondary/open':
            result=open_secondary_camera(data.get('index'))
            return self.send_json(result,200 if result.get('ok') else 500)
        if path == '/api/camera/secondary/canon/open':
            result=open_secondary_canon_camera(data.get('id') or 'canon_edsdk_0')
            return self.send_json(result,200 if result.get('ok') else 500)
        if path == '/api/camera/secondary/close':
            close_secondary_camera(); return self.send_json({'ok':True})
        if path == '/api/camera/angle':
            global active_camera_angle
            angle=int(data.get('angle',0) or 0)
            if angle not in (0,1): return self.send_json({'ok':False,'error':'Angle kamera harus 0 atau 1.'},400)
            if angle==1 and latest_secondary_frame is None: return self.send_json({'ok':False,'error':'Kamera kedua belum aktif.'},409)
            active_camera_angle=angle
            if active_session and active_session.get('status')=='active': active_session['camera_angle']=angle; write_manifest(active_session)
            return self.send_json({'ok':True,'angle':angle})
        if path == '/api/camera/controls/recover':
            result=recover_camera_controls(data.get('camera',0),data.get('profile'),data.get('keys'))
            return self.send_json(result,200 if result.get('ok') else 409)
        if path == '/api/camera/controls':
            result=set_camera_controls(int(data.get('camera',0) or 0),data.get('values') or {})
            return self.send_json(result,200 if result.get('ok') else 409)
        if path == '/api/frames/enabled':
            fid=str(data.get('frame_id') or '')
            enabled=bool(data.get('enabled',False))
            if not re.match(r'^[a-f0-9]{12,32}$',fid): return self.send_json({'ok':False,'error':'ID frame tidak valid.'},400)
            meta_path=os.path.join(FRAMES_DIR,fid+'.json')
            if not os.path.isfile(os.path.join(FRAMES_DIR,fid+'.png')): return self.send_json({'ok':False,'error':'Frame tidak ditemukan.'},404)
            try:
                try:
                    with open(meta_path,'r',encoding='utf-8') as mf: meta=json.load(mf)
                except Exception: meta={}
                meta['enabled']=enabled
                with open(meta_path,'w',encoding='utf-8') as mf: json.dump(meta,mf,ensure_ascii=False)
                return self.send_json({'ok':True,'frame_id':fid,'enabled':enabled})
            except Exception as exc: return self.send_json({'ok':False,'error':f'Gagal menyimpan status frame: {exc}'},500)
        if path == '/api/frames/import':
            try:
                name=str(data.get('name') or 'Frame PNG')[:80]
                encoded=str(data.get('data_url') or '')
                if not encoded.startswith('data:image/png;base64,'): return self.send_json({'ok':False,'error':'File harus PNG.'},400)
                raw=base64.b64decode(encoded.split(',',1)[1],validate=True)
                if len(raw)>15*1024*1024: return self.send_json({'ok':False,'error':'Ukuran PNG maksimal 15 MB.'},413)
                import numpy as np
                arr=cv2.imdecode(np.frombuffer(raw,dtype=np.uint8),cv2.IMREAD_UNCHANGED)
                if arr is None or len(arr.shape)!=3 or arr.shape[2] not in (3,4): return self.send_json({'ok':False,'error':'PNG tidak dapat dibaca.'},400)
                if arr.shape[2]==3: return self.send_json({'ok':False,'error':'PNG harus memiliki transparansi alpha pada area foto.'},400)
                event_id=str(data.get('event_id') or '').strip()
                if event_id and not re.fullmatch(r'[a-f0-9]{16}',event_id): return self.send_json({'ok':False,'error':'ID event frame tidak valid.'},400)
                fid=uuid.uuid4().hex[:16]; cv2.imwrite(os.path.join(FRAMES_DIR,fid+'.png'),arr)
                with open(os.path.join(FRAMES_DIR,fid+'.json'),'w',encoding='utf-8') as mf: json.dump({'name':name,'width':int(arr.shape[1]),'height':int(arr.shape[0]),'enabled':True,'event_id':event_id or None},mf,ensure_ascii=False)
                return self.send_json({'ok':True,'frame':{'id':fid,'name':name,'event_id':event_id or None,'width':int(arr.shape[1]),'height':int(arr.shape[0]),'url':f'http://127.0.0.1:{PORT}/api/frames/{fid}.png'}})
            except Exception as exc: return self.send_json({'ok':False,'error':f'Gagal mengimpor PNG: {exc}'},400)
        if path == '/api/video-test/start':
            with video_lock:
                if video_test_writer is not None:
                    return self.send_json({'ok':False,'error':'Uji video sedang berjalan.'},409)
                with frame_condition: first = None if latest_frame is None else latest_frame.copy()
                if first is None: return self.send_json({'ok':False,'error':'Aktifkan preview kamera terlebih dahulu.'},409)
                h,w=first.shape[:2]; fps=30.0
                try:
                    with capture_lock:
                        if cap is not None and cap.isOpened():
                            reported=float(cap.get(cv2.CAP_PROP_FPS) or 0)
                            if 5<=reported<=60: fps=reported
                except Exception: pass
                test_path=os.path.join(DATA_DIR,'video-test.mp4')
                writer=None; codec=None
                for candidate in ('mp4v','avc1','H264','MP4V'):
                    trial=cv2.VideoWriter(test_path,cv2.VideoWriter_fourcc(*candidate),fps,(w,h))
                    if trial is not None and trial.isOpened(): writer,codec=trial,candidate; break
                    if trial is not None: trial.release()
                if writer is None: return self.send_json({'ok':False,'error':'Encoder video tidak dapat dibuka pada komputer ini.'},500)
                video_test_writer=writer; video_test_path=test_path; video_test_started=time.monotonic(); video_test_frames=0; video_test_fps=fps; video_test_width=w; video_test_height=h; video_test_passed=False
                return self.send_json({'ok':True,'recording':True,'width':w,'height':h,'fps':fps,'codec':codec})
        if path == '/api/video-test/stop':
            with video_lock:
                writer=video_test_writer; test_path=video_test_path; started=video_test_started; count=video_test_frames; fps=video_test_fps; w=video_test_width; h=video_test_height
                video_test_writer=None; video_test_path=None; video_test_started=None; video_test_frames=0
            if writer is None: return self.send_json({'ok':False,'error':'Tidak ada uji video yang sedang berjalan.'},409)
            writer.release(); size=os.path.getsize(test_path) if test_path and os.path.isfile(test_path) else 0; duration=(time.monotonic()-started) if started else 0
            valid=count>=20 and size>1000 and duration>=3.0
            video_test_passed=bool(valid)
            return self.send_json({'ok':valid,'recording':False,'frames':count,'duration_seconds':round(duration,2),'fps':fps,'width':w,'height':h,'size_bytes':size,'file':'video-test.mp4','message':'Rekaman berhasil dibuat.' if valid else 'Rekaman tidak valid atau terlalu pendek.'},200 if valid else 500)
        if path.startswith('/api/session/') and path.endswith('/print'):
            import subprocess
            sid=path.split('/')[3] if len(path.split('/'))>3 else ''
            if not sid.replace('-','').isalnum(): return self.send_json({'ok':False,'error':'ID sesi tidak valid.'},400)
            folder=os.path.join(SESSIONS_DIR,sid); image_path=os.path.join(folder,'output.jpg')
            # The still JPG is rendered before the slower Live Photo/GIF jobs. Wait briefly
            # for that JPG only; never wait for video composition before sending a print job.
            deadline=time.monotonic()+25.0
            manifest=read_manifest(sid)
            while (not os.path.isfile(image_path)) and time.monotonic()<deadline:
                time.sleep(.2)
            manifest=read_manifest(sid) or manifest
            if not manifest or not os.path.isfile(image_path): return self.send_json({'ok':False,'error':'Hasil JPG belum selesai dirender. Tunggu sebentar lalu tekan Cetak Hasil kembali.'},409)
            if manifest.get('drive_qr_enabled'):
                if not manifest.get('drive_url'):
                    return self.send_json({'ok':False,'error':'QR Drive untuk frame cetak belum tersedia. Tunggu folder Drive siap sebelum mencetak.','retryable':True},409)
                if not _refresh_drive_qr_output(manifest):
                    return self.send_json({'ok':False,'error':'QR untuk frame cetak belum selesai dibuat: '+str(manifest.get('print_qr_error') or 'sedang memproses'),'retryable':True},409)
                image_path=os.path.join(folder,'output_print_qr.jpg')
                write_manifest(manifest)
            if bool(data.get('auto_print')) and manifest.get('auto_print_completed'):
                return self.send_json({'ok':True,'already_printed':True,'message':'Cetak otomatis sudah pernah dikirim untuk sesi ini.'})
            if sys.platform!='win32': return self.send_json({'ok':False,'error':'Cetak langsung hanya didukung pada Windows.'},501)
            printer=str(data.get('printer_name') or '').strip()
            if not printer: return self.send_json({'ok':False,'error':'Pilih dan simpan printer pada menu Printer & Kertas terlebih dahulu.'},400)
            paper=str(data.get('paper_size') or manifest.get('paper_size') or '4R')
            width=max(1.0,min(20.0,float(data.get('custom_width') or 4)))
            height=max(1.0,min(20.0,float(data.get('custom_height') or 6)))
            if paper=='2R Strip': width,height=2.0,6.0
            elif paper=='4R':
                # Keep the native frame orientation when available.
                try:
                    from PIL import Image
                    with Image.open(image_path) as im:
                        iw,ih=im.size
                    width,height=(4.0,6.0) if ih>iw else (6.0,4.0)
                except Exception: width,height=6.0,4.0
            copies=max(1,min(20,int(data.get('copies') or 1)))
            payload={'printer':printer,'image':image_path,'width':width,'height':height,'copies':copies,'borderless':bool(data.get('borderless',False)),'dpi':int(data.get('dpi') or 300),'driver_paper_name':str(data.get('driver_paper_name') or '').strip()}
            encoded=base64.b64encode(json.dumps(payload).encode('utf-8')).decode('ascii')
            ps=r'''
$ErrorActionPreference='Stop'
Add-Type -AssemblyName System.Drawing
$payload=[Text.Encoding]::UTF8.GetString([Convert]::FromBase64String($env:KACA_PRINT_PAYLOAD)) | ConvertFrom-Json
$doc=New-Object System.Drawing.Printing.PrintDocument
$doc.PrinterSettings.PrinterName=[string]$payload.printer
if(-not $doc.PrinterSettings.IsValid){ throw "Printer tidak ditemukan atau tidak valid: $($payload.printer)" }
$doc.PrinterSettings.Copies=[int]$payload.copies
$wantedDpi=[int]$payload.dpi; $resList=@($doc.PrinterSettings.PrinterResolutions); if($resList.Count -gt 0){$bestRes=$resList | Sort-Object { [Math]::Abs([Math]::Max($_.X,$_.Y)-$wantedDpi) } | Select-Object -First 1; if($null -ne $bestRes){$doc.DefaultPageSettings.PrinterResolution=$bestRes}}
$doc.DocumentName='KACA.ID Photobooth'
$doc.OriginAtMargins=$false
$doc.DefaultPageSettings.Margins=New-Object System.Drawing.Printing.Margins(0,0,0,0)
$targetW=[int][Math]::Round([double]$payload.width*100)
$targetH=[int][Math]::Round([double]$payload.height*100)
$doc.DefaultPageSettings.Landscape=($targetW -gt $targetH)
$best=$null; $bestScore=[double]::MaxValue
$allPaper=@($doc.PrinterSettings.PaperSizes)
# Borderless paper names are not standardized across printer drivers. Keep all driver sizes and honor the exact selected driver paper when supplied.
if(-not [string]::IsNullOrWhiteSpace([string]$payload.driver_paper_name)){$exact=@($allPaper | Where-Object { $_.PaperName -eq [string]$payload.driver_paper_name }); if($exact.Count -eq 0){throw "Ukuran kertas driver yang dipilih tidak tersedia atau tidak cocok dengan mode borderless: $($payload.driver_paper_name)"}; $best=$exact[0]; $bestScore=0}
foreach($psize in $allPaper){ if($null -ne $best -and $bestScore -eq 0){break}
  $direct=[Math]::Abs($psize.Width-$targetW)+[Math]::Abs($psize.Height-$targetH)
  $rot=[Math]::Abs($psize.Width-$targetH)+[Math]::Abs($psize.Height-$targetW)
  $score=[Math]::Min($direct,$rot)
  if($score -lt $bestScore){$bestScore=$score;$best=$psize}
}
if($null -ne $best -and $bestScore -le 30){$doc.DefaultPageSettings.PaperSize=$best}
else{$doc.DefaultPageSettings.PaperSize=New-Object System.Drawing.Printing.PaperSize('KACA Custom',$targetW,$targetH)}
$img=[System.Drawing.Image]::FromFile([string]$payload.image)
$printImage=$img
$doc.add_PrintPage({
  param($sender,$e)
  $bounds=$e.PageBounds
  $iw=$printImage.Width; $ih=$printImage.Height
  $scale=[Math]::Min($bounds.Width/[double]$iw,$bounds.Height/[double]$ih)
  $dw=[int][Math]::Round($iw*$scale); $dh=[int][Math]::Round($ih*$scale)
  $x=$bounds.X+[int](($bounds.Width-$dw)/2); $y=$bounds.Y+[int](($bounds.Height-$dh)/2)
  $e.Graphics.DrawImage($printImage,$x,$y,$dw,$dh)
  $e.HasMorePages=$false
}.GetNewClosure())
try{$doc.Print()}finally{$img.Dispose();$doc.Dispose()}
Write-Output ('PRINT_OK|'+$payload.printer+'|'+$payload.width+'x'+$payload.height+'|'+$payload.copies+'|borderless='+$payload.borderless)
'''
            try:
                windir=os.environ.get('WINDIR',r'C:\Windows')
                ps_path=os.path.join(windir,'System32','WindowsPowerShell','v1.0','powershell.exe')
                if not os.path.isfile(ps_path): ps_path=shutil.which('powershell.exe') or 'powershell.exe'
                env=os.environ.copy(); env['KACA_PRINT_PAYLOAD']=encoded
                result=subprocess.check_output([ps_path,'-NoLogo','-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass','-Command',ps],stderr=subprocess.STDOUT,timeout=45,text=True,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0),env=env)
                if bool(data.get('auto_print')):
                    updated=read_manifest(sid) or manifest
                    updated['auto_print_completed']=True
                    updated['auto_print_completed_at']=datetime.datetime.now().isoformat(timespec='seconds')
                    write_manifest(updated)
                return self.send_json({'ok':True,'message':f'Hasil sesi berhasil dikirim ke antrean printer {printer} ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬Ãƒâ€¦Ã‚Â¡ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â· {paper} ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬Ãƒâ€¦Ã‚Â¡ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â· {copies} salinan.','printer':printer,'paper_size':paper,'copies':copies,'details':result.strip()})
            except subprocess.CalledProcessError as exc:
                detail=(exc.output or str(exc)).strip()[-1800:]
                return self.send_json({'ok':False,'error':'Windows gagal mengirim pekerjaan cetak: '+detail},500)
            except Exception as exc: return self.send_json({'ok':False,'error':'Gagal mencetak: '+str(exc)},500)
        if path == '/api/printers/paper-sizes':
            import subprocess
            if sys.platform!='win32': return self.send_json({'ok':False,'error':'Hanya tersedia pada Windows.'},501)
            printer=str(data.get('name') or '').strip()
            if not printer: return self.send_json({'ok':False,'error':'Pilih printer.'},400)
            ps=r"""Add-Type -AssemblyName System.Drawing; $p=New-Object System.Drawing.Printing.PrinterSettings; $p.PrinterName=$env:KACA_PRINTER; if(-not $p.IsValid){throw 'Printer tidak valid'}; @($p.PaperSizes | ForEach-Object { [pscustomobject]@{name=$_.PaperName;width=$_.Width;height=$_.Height} }) | ConvertTo-Json -Compress"""
            try:
                windir=os.environ.get('WINDIR',r'C:\Windows'); ps_path=os.path.join(windir,'System32','WindowsPowerShell','v1.0','powershell.exe'); env=os.environ.copy(); env['KACA_PRINTER']=printer
                raw=subprocess.check_output([ps_path,'-NoProfile','-NonInteractive','-Command',ps],stderr=subprocess.STDOUT,timeout=15,text=True,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0),env=env)
                sizes=json.loads(raw or '[]'); sizes=sizes if isinstance(sizes,list) else [sizes]
                return self.send_json({'ok':True,'paper_sizes':sizes,'borderless_available':None,'borderless_detection':'manual_driver_property'})
            except Exception as exc: return self.send_json({'ok':False,'error':str(exc)},500)
        if path == '/api/printers/default':
            import subprocess
            name=str(data.get('name') or '').strip()
            if not name: return self.send_json({'ok':False,'error':'Pilih printer terlebih dahulu.'},400)
            if sys.platform!='win32': return self.send_json({'ok':False,'error':'Pengaturan printer langsung hanya didukung pada Windows.'},501)
            try:
                windir=os.environ.get('WINDIR',r'C:\Windows')
                candidates=[shutil.which('powershell.exe'),os.path.join(windir,'System32','WindowsPowerShell','v1.0','powershell.exe'),shutil.which('pwsh.exe')]
                ps=next((x for x in candidates if x and os.path.isfile(x)),None)
                if ps:
                    escaped=name.replace("'","''")
                    subprocess.check_output([ps,'-NoLogo','-NoProfile','-NonInteractive','-Command',f"(New-Object -ComObject WScript.Network).SetDefaultPrinter('{escaped}')"],stderr=subprocess.STDOUT,timeout=12,text=True,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
                else:
                    # PrintUIEntry is a native Windows fallback and does not require PowerShell.
                    subprocess.check_output(['rundll32.exe','printui.dll,PrintUIEntry','/y','/n',name],stderr=subprocess.STDOUT,timeout=12,text=True,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
                return self.send_json({'ok':True,'default_printer':name})
            except Exception as exc: return self.send_json({'ok':False,'error':str(exc)},500)
        if path == '/api/canon/open':
            result = open_canon_camera(data.get('id') or 'canon_edsdk_0')
            return self.send_json(result, 200 if result.get('ok') else 500)
        if path == '/api/canon/capture':
            with canon_lifecycle_lock:
                controller = canon_controller
                if controller is None:
                    return self.send_json({'ok': False, 'error': 'Canon Live View belum aktif.'}, 409)
                try:
                    return self.send_json(controller.take_picture())
                except Exception as exc:
                    return self.send_json({'ok': False, 'error': str(exc)}, 500)
        if path == '/api/canon/close':
            close_canon_camera()
            return self.send_json({'ok': True, 'closed': True})
        if path == '/api/camera/open':
            idx = data.get('index')
            if idx is None:
                return self.send_json({'ok': False, 'error': 'Index kamera belum dipilih.'}, 400)
            ok = open_camera(idx)
            with state_lock:
                result = dict(state)
            result['ok'] = ok
            return self.send_json(result, 200 if ok else 500)
        if path == '/api/camera/close':
            close_camera()
            with state_lock:
                return self.send_json({'ok': True, **state})
        if path in ('/api/video/start', '/api/booth/video/start'):
            try:
                angle = 1 if int(data.get('angle', 0) or 0) == 1 else 0
                if angle == 1:
                    with secondary_lock: first_frame=None if latest_secondary_frame is None else latest_secondary_frame.copy()
                else:
                    with frame_condition: first_frame=None if latest_frame is None else latest_frame.copy()
                if first_frame is None:
                    return self.send_json({'ok':False,'error':f'Preview kamera angle {angle+1} belum mengirim frame. Aktifkan preview kamera terlebih dahulu.'},409)
                frame_id=str(data.get('frame_id') or '')
                frame_error=event_frame_owner_error(frame_id,data.get('event_id'))
                if frame_error:return self.send_json({'ok':False,'error':frame_error},409)
                # Reuse the existing verified checkout and voucher rules.
                method=str(data.get('payment_method') or '')
                if method=='qris_manual' and qris_config.get('mode')=='doku_checkout':
                    return self.send_json({'ok':False,'error':'QRIS dinamis memerlukan verifikasi DOKU.'},409)
                if method=='qris_doku':
                    try:doku_qris.consume_paid(str(data.get('payment_invoice') or ''))
                    except ValueError as exc:return self.send_json({'ok':False,'error':str(exc)},409)
                if method=='voucher':
                    code=str(data.get('voucher_code') or '').strip().upper()
                    with voucher_lock:
                        voucher=next((v for v in vouchers_store if str(v.get('code','')).upper()==code),None)
                        if not voucher or _voucher_status(voucher)!='aktif':
                            return self.send_json({'ok':False,'error':'Voucher tidak valid atau habis.'},409)
                        voucher['used_count']=int(voucher.get('used_count',0))+1
                        voucher['last_used_at']=datetime.datetime.now().isoformat(timespec='seconds')
                        _save_vouchers()
                return self.send_json(start_booth_video(first_frame, angle, data.get('event_id'), data.get('event_name'), frame_id, bool(data.get('mirror',False)), int(data.get('camera_rotation',0) or 0), bool(data.get('camera_flip_horizontal',False)), bool(data.get('camera_flip_vertical',False))))
            except Exception as exc:
                return self.send_json({'ok':False,'error':str(exc)},500)
        if path == '/api/video/stop':
            try:
                return self.send_json(stop_booth_video())
            except Exception as exc:
                return self.send_json({'ok':False,'error':str(exc)},500)
        if path == '/api/session/start':
            frame_error=event_frame_owner_error(data.get('frame_id'),data.get('event_id'))
            if frame_error: return self.send_json({'ok':False,'error':frame_error},409)
            with session_lock:
                if active_session and active_session.get('status') == 'active':
                    return self.send_json({'ok':False,'error':'Masih ada sesi yang aktif. Selesaikan sesi sebelumnya.'},409)
                requested_angle = 1 if int(data.get('camera_angle', 0) or 0) == 1 else 0
                if requested_angle == 1:
                    with secondary_lock:
                        selected_frame = None if latest_secondary_frame is None else latest_secondary_frame
                    if selected_frame is None:
                        return self.send_json({'ok':False,'error':'Preview Kamera Angle 2 belum aktif atau belum mengirim frame. Aktifkan kamera kedua terlebih dahulu.'},409)
                elif not state.get('camera_open') or latest_frame is None:
                    return self.send_json({'ok':False,'error':'Aktifkan preview kamera Angle 1 sebelum memulai sesi.'},409)
                payment_method=str(data.get('payment_method') or '').strip().lower()
                voucher_code=str(data.get('voucher_code') or '').strip().upper()
                if payment_method == 'qris_manual' and qris_config.get('mode') == 'doku_checkout':
                    return self.send_json({'ok': False, 'error': 'QRIS otomatis aktif; verifikasi manual tidak dapat digunakan.'}, 409)
                if payment_method == 'qris_doku':
                    try:
                        if qris_config.get('mode') != 'doku_checkout':
                            raise ValueError('Mode QRIS otomatis belum aktif.')
                        doku_qris.consume_paid(str(data.get('payment_invoice') or ''))
                    except ValueError as exc:
                        return self.send_json({'ok': False, 'error': str(exc)}, 409)
                payment_verified=False
                verified_amount=0
                if payment_method == 'qris_doku':
                    item=doku_qris.ledger.get(str(data.get('payment_invoice') or ''),{})
                    payment_verified=bool(item.get('status')=='paid' and item.get('consumed'))
                    verified_amount=int(item.get('amount') or 0) if payment_verified else 0
                if payment_method == 'voucher':
                    with voucher_lock:
                        voucher=next((v for v in vouchers_store if str(v.get('code','')).upper()==voucher_code),None)
                        if not voucher: return self.send_json({'ok':False,'error':'Kode voucher tidak ditemukan.'},404)
                        voucher_state=_voucher_status(voucher)
                        if voucher_state!='aktif':
                            msg={'nonaktif':'Voucher sudah dinonaktifkan.','kedaluwarsa':'Voucher sudah kedaluwarsa.','habis':'Batas penggunaan voucher sudah tercapai.'}.get(voucher_state,'Voucher tidak dapat digunakan.')
                            return self.send_json({'ok':False,'error':msg},409)
                        voucher['used_count']=int(voucher.get('used_count',0))+1
                        voucher['last_used_at']=datetime.datetime.now().isoformat(timespec='seconds')
                        _save_vouchers()
                sid = uuid.uuid4().hex[:12]
                now = datetime.datetime.now().isoformat(timespec='seconds')
                mode = data.get('session_mode', 'fixed_count')
                frame_slots = max(1, min(8, int(data.get('frame_slots', 4))))
                session = {'id':sid,'created_at':now,'status':'active','photos':[],'settings':data,'filter':data.get('filter','Natural'),'paper_size':data.get('paper_size','4R'),'print_dpi':int(data.get('print_dpi',300) or 300),'session_mode':mode,'frame_slots':frame_slots,'frame_id':data.get('frame_id'),'layout_slots':data.get('layout_slots') or [],'drive_qr_enabled':bool(data.get('drive_qr_enabled',False)),'drive_qr_layout':data.get('drive_qr_layout') or {'x':.78,'y':.78,'w':.16,'h':.16},'mirror':bool(data.get('mirror',False)),'multicam_enabled':bool(data.get('multicam_enabled',False)),'camera_angle':int(data.get('camera_angle',0) or 0),'camera_rotation':int(data.get('camera_rotation',0) or 0)%360,'camera_flip_horizontal':bool(data.get('camera_flip_horizontal',False)),'camera_flip_vertical':bool(data.get('camera_flip_vertical',False)),
                'camera_rotation2':int(data.get('camera_rotation2',0) or 0)%360,'camera_flip_horizontal2':bool(data.get('camera_flip_horizontal2',False)),'camera_flip_vertical2':bool(data.get('camera_flip_vertical2',False)),'event_id':_event_storage_key(data.get('event_id')),'event_name':str(data.get('event_name') or '')[:100],'payment_method':payment_method,'payment_amount_idr':verified_amount,'payment_verification':'success' if payment_verified else 'unverified','payment_invoice':str(data.get('payment_invoice') or '') if payment_method=='qris_doku' else None,'voucher_code':voucher_code if payment_method=='voucher' else None,'capture_open':True,'recording':False}
                os.makedirs(os.path.join(SESSIONS_DIR,sid),exist_ok=True)
                session['live_photo_enabled'] = bool(data.get('live_photo_enabled', False))
                session['live_photo_duration_seconds'] = max(5, min(30, int(data.get('live_photo_duration', 5) or 5)))
                session['recording'] = False
                session['live_video'] = None
                create_local_session_archive(session)
                if google_drive.status().get('connected'):
                    session['drive_folder_status'] = 'creating'
                    session['drive_status'] = 'provisioning'
                    session['drive_error'] = None
                else:
                    session['drive_folder_status'] = 'waiting_auth'
                    session['drive_status'] = 'waiting_auth'
                    session['drive_error'] = 'Hubungkan Google Drive untuk membuat tautan dan QR sesi.'
                _write_local_session_info(session)
                write_manifest(session); active_session=session
                if session['drive_folder_status'] == 'creating':
                    _start_session_drive_folder_provision(sid)
                return self.send_json({'ok':True,'session':session,'recording':False,'live_photo_enabled':session['live_photo_enabled'],'recording_warning':None})
        if path == '/api/session/mirror':
            with session_lock:
                if not active_session or active_session.get('status') != 'active':
                    return self.send_json({'ok':False,'error':'Belum ada sesi aktif.'},409)
                active_session['mirror'] = bool(data.get('mirror', False))
                write_manifest(active_session)
                return self.send_json({'ok':True,'mirror':active_session['mirror']})
        if path == '/api/session/live/start':
            with session_lock:
                if not active_session or active_session.get('status') != 'active':
                    return self.send_json({'ok':False,'error':'Belum ada sesi aktif.'},409)
                if not active_session.get('live_photo_enabled'):
                    return self.send_json({'ok':True,'recording':False,'disabled':True})
                if not state.get('camera_open') or latest_frame is None:
                    return self.send_json({'ok':False,'error':'Kamera belum mengirim frame.'},503)
                next_number=max([int(p.get('number',0)) for p in active_session.get('photos',[])] or [0])+1
                source=int(active_session.get('camera_angle',0) or 0)
                if source==1:
                    with secondary_lock: first_frame=None if latest_secondary_frame is None else latest_secondary_frame.copy()
                else:
                    with frame_condition: first_frame=None if latest_frame is None else latest_frame.copy()
                if first_frame is None: return self.send_json({'ok':False,'error':'Kamera angle yang dipilih belum menghasilkan frame.'},503)
                duration_seconds=max(5,min(30,int(data.get('duration_seconds',active_session.get('live_photo_duration_seconds',5)) or 5)))
                active_session['live_photo_duration_seconds']=duration_seconds
                ok=start_shot_live_photo(active_session['id'],next_number,first_frame,duration_seconds,active_session.get('mirror',False),source,(active_session.get('settings',{}) or {}).get('video_quality','high'),*_session_camera_orientation(active_session,source))
                active_session['live_recording']=bool(ok)
                write_manifest(active_session)
                return self.send_json({'ok':True,'recording':bool(ok),'photo_number':next_number,'frames_written':0,'codec':'buffered-camera-frames' if ok else None,'warning':None if ok else 'Encoder MP4 tidak tersedia. Foto tetap dapat diambil; hanya Live Photo untuk foto ini yang tidak tersimpan.'})
        if path == '/api/session/live/cancel':
            with session_lock:
                stop_shot_live_photo(discard=True)
                if active_session:
                    active_session['live_recording']=False
                    write_manifest(active_session)
                return self.send_json({'ok':True,'recording':False,'discarded':True})
        if path == '/api/session/stop-recording':
            with session_lock:
                if not active_session or active_session.get('status') != 'active': return self.send_json({'ok':False,'error':'Tidak ada sesi aktif.'},409)
                active_session['capture_open'] = False
                active_session['recording'] = False
                active_session['live_recording'] = False
                stop_shot_live_photo(discard=True)
                stop_session_video()
                write_manifest(active_session)
                return self.send_json({'ok':True,'session_id':active_session['id'],'recording_stopped':True})
        if path == '/api/session/capture':
            with session_lock:
                if not active_session or active_session.get('status') != 'active': return self.send_json({'ok':False,'error':'Belum ada sesi aktif.'},409)
                if not active_session.get('capture_open', True): return self.send_json({'ok':False,'error':'Waktu pemotretan sudah selesai. Pilih foto untuk frame.'},409)
                if active_session.get('session_mode') == 'fixed_count' and len(active_session.get('photos', [])) >= int(active_session.get('frame_slots', 4)): return self.send_json({'ok':False,'error':'Kesempatan foto sesuai jumlah slot frame sudah habis.'},409)
                session=active_session
                if int(session.get('camera_angle',0) or 0)==1:
                    with secondary_lock: frame=None if latest_secondary_frame is None else latest_secondary_frame.copy()
                else:
                    with frame_condition: frame = None if latest_frame is None else latest_frame.copy()
                if frame is None: return self.send_json({'ok':False,'error':'Frame kamera untuk angle terpilih belum tersedia. Pastikan preview kamera aktif.'},503)
                canon_shutter = None

                angle = int(session.get('camera_angle', 0) or 0)
                try:
                    if angle == 0:
                        with canon_lifecycle_lock:
                            controller = canon_controller
                    else:
                        with canon_secondary_lock:
                            controller = canon_secondary_controller
                    if controller is not None:
                        canon_shutter = controller.take_picture()
                    if canon_shutter is not None:
                        time.sleep(0.18)
                        if angle == 0:
                            with frame_condition: frame = None if latest_frame is None else latest_frame.copy()
                        else:
                            with secondary_lock: frame = None if latest_secondary_frame is None else latest_secondary_frame.copy()
                except Exception as exc:
                    return self.send_json({'ok': False, 'error': f'Shutter Canon gagal: {exc}'}, 500)
                if frame is None: return self.send_json({'ok':False,'error':'Kamera menerima shutter tetapi frame preview belum tersedia.'},503)
                frame = _apply_camera_orientation(frame, *_session_camera_orientation(session,angle), session.get('mirror',False))
                number=max([int(p.get('number',0)) for p in session['photos']] or [0])+1
                # Countdown has ended: close this shot's MP4 before freezing the still image.
                live_file=stop_shot_live_photo(discard=False) if session.get('live_photo_enabled') else None
                live_diag=dict(shot_video_last_result) if session.get('live_photo_enabled') else {'frames':0,'duration':0.0,'codec':None,'size_bytes':0}
                session['live_recording']=False
                folder=os.path.join(SESSIONS_DIR,session['id'])
                original=f'original_{number:02d}.jpg'; edited=f'photo_{number:02d}.jpg'
                original_path=os.path.join(folder,original); edited_path=os.path.join(folder,edited)
                if not cv2.imwrite(original_path,frame,[int(cv2.IMWRITE_JPEG_QUALITY),max(60,min(100,int((session.get('settings',{}) or {}).get('jpeg_quality',100) or 100)))]):
                    if live_file:
                        try: os.remove(os.path.join(folder,live_file))
                        except OSError: pass
                    return self.send_json({'ok':False,'error':'Gagal menyimpan foto asli.'},500)
                filtered=frame.copy()  # keep capture-session photos original; apply the chosen filter only on Finish
                if not cv2.imwrite(edited_path,filtered,[int(cv2.IMWRITE_JPEG_QUALITY),max(60,min(100,int((session.get('settings',{}) or {}).get('jpeg_quality',100) or 100)))]):
                    if live_file:
                        try: os.remove(os.path.join(folder,live_file))
                        except OSError: pass
                    return self.send_json({'ok':False,'error':'Gagal menyimpan foto hasil.'},500)
                preview_file=live_diag.get('preview') if live_file else None
                preview_path=os.path.join(SESSIONS_DIR,session['id'],preview_file) if preview_file else None
                if preview_path and not os.path.isfile(preview_path): preview_file=None
                photo={'number':number,'original':original,'edited':edited,'live_photo':live_file,'live_photo_preview':preview_file,'live_photo_frames':live_diag.get('frames',0),'live_photo_duration':live_diag.get('duration',0.0),'live_photo_codec':live_diag.get('codec'),'live_photo_size_bytes':live_diag.get('size_bytes',0),'live_photo_url':(f"http://127.0.0.1:{PORT}/api/session/{session['id']}/live/{live_file}" if live_file else None),'live_photo_preview_url':(f"http://127.0.0.1:{PORT}/api/session/{session['id']}/live/{preview_file}" if preview_file else None),'url':f"http://127.0.0.1:{PORT}/api/session/{session['id']}/photo/{edited}",'captured_at':datetime.datetime.now().isoformat(timespec='seconds'),'width':int(frame.shape[1]),'height':int(frame.shape[0]),'camera_source':'Canon EOS EDSDK' if canon_shutter else 'OpenCV','canon_shutter':canon_shutter}
                session['photos'].append(photo); write_manifest(session)
                enqueue_local_session_archive(session, final=False)
                return self.send_json({'ok':True,'photo':photo,'count':len(session['photos']),'session_id':session['id'],'live_photo_created':bool(live_file),'live_photo_diagnostics':live_diag})
        if path == '/api/session/retake':
            with session_lock:
                if not active_session or active_session.get('status') != 'active': return self.send_json({'ok':False,'error':'Tidak ada sesi aktif.'},409)
                stop_shot_live_photo(discard=True)
                active_session['live_recording']=False
                # A completed filter-stage preview is stale after a retake. A running
                # render is allowed to finish before the UI invokes this endpoint.
                with render_jobs_lock:
                    render_job=render_jobs.get(active_session['id'])
                    if render_job and render_job.get('running'):
                        return self.send_json({'ok':False,'error':'Preview hasil akhir masih diproses. Tunggu sebentar lalu ulangi foto.'},409)
                    render_jobs.pop(active_session['id'],None)
                photos=active_session.get('photos',[])
                if not photos: return self.send_json({'ok':False,'error':'Belum ada foto untuk diulang.'},409)
                photo=photos.pop(); folder=os.path.join(SESSIONS_DIR,active_session['id'])
                for key in ('original','edited','live_photo'):
                    if not photo.get(key): continue
                    try: os.remove(os.path.join(folder,photo[key]))
                    except OSError: pass
                # Renumber remaining metadata while retaining the stored file names.
                write_manifest(active_session)
                return self.send_json({'ok':True,'removed':photo,'count':len(photos),'photos':photos})
        if path == '/api/session/prepare':
            with session_lock:
                if not active_session or active_session.get('status') != 'active': return self.send_json({'ok':False,'error':'Tidak ada sesi aktif.'},409)
                selected=data.get('selected_numbers') or [p.get('number') for p in active_session.get('photos',[])]
                if not selected: return self.send_json({'ok':False,'error':'Belum ada foto untuk diproses.'},400)
                if active_session.get('session_mode')=='timed' and len(selected)>int(active_session.get('frame_slots',4)):
                    return self.send_json({'ok':False,'error':'Jumlah foto pilihan melebihi slot frame.'},400)
                active_session['capture_open']=False
                active_session['recording']=False
                active_session['live_recording']=False
                stop_shot_live_photo(discard=True)
                stop_session_video()
                if data.get('filter'): active_session['filter']=data.get('filter')
                if data.get('frame_id') is not None: active_session['frame_id']=data.get('frame_id')
                if data.get('layout_slots'): active_session['layout_slots']=data.get('layout_slots')
                if 'drive_qr_enabled' in data: active_session['drive_qr_enabled']=bool(data.get('drive_qr_enabled'))
                if isinstance(data.get('drive_qr_layout'),dict): active_session['drive_qr_layout']=data.get('drive_qr_layout')
                if data.get('frame_slots') is not None: active_session['frame_slots']=max(1,min(8,int(data.get('frame_slots'))))
                snapshot=queue_session_render(active_session,selected,data.get('filter'),False,data.get('frame_id'),data.get('layout_slots'),data.get('frame_slots'))
                active_session['render_status']=snapshot.get('render_status','processing')
                if active_session['render_status']=='ready':
                    write_manifest(snapshot)
                else:
                    write_manifest(active_session)
                return self.send_json({'ok':True,'render_status':active_session['render_status'],'session_id':active_session['id']})
        if path.startswith('/api/session/') and path.endswith('/cleanup-previews'):
            sid = path.split('/')[-2]
            if not re.fullmatch(r'[A-Za-z0-9_-]{1,80}', sid):
                return self.send_json({'ok':False,'error':'ID sesi tidak valid.'},400)
            manifest = read_manifest(sid)
            if not manifest:
                return self.send_json({'ok':False,'error':'Sesi tidak ditemukan.'},404)
            source_dir = os.path.join(SESSIONS_DIR, sid)
            # The final output_live.webm is a local application preview asset and must survive
            # leaving the customer result slide so Output/session detail can play it later.
            candidates = [p.get('live_photo_preview') for p in manifest.get('photos',[]) if isinstance(p,dict)]
            removed = 0
            for name in candidates:
                if not name or not str(name).lower().endswith('.webm') or os.path.basename(str(name)) != str(name):
                    continue
                target = os.path.join(source_dir, str(name))
                try:
                    if os.path.isfile(target):
                        os.remove(target); removed += 1
                except OSError as exc:
                    print('[SESSION_PREVIEW_CLEANUP_WARNING]', sid, repr(exc), flush=True)
            for photo in manifest.get('photos',[]):
                if isinstance(photo,dict): photo['live_photo_preview'] = None; photo['live_photo_preview_url'] = None
            write_manifest(manifest)
            return self.send_json({'ok':True,'removed':removed,'webm_persisted':True})
        if path == '/api/session/finish':
            with session_lock:
                if active_session:
                    frame_error=event_frame_owner_error(data.get('frame_id') or active_session.get('frame_id'),active_session.get('event_id'))
                    if frame_error: return self.send_json({'ok':False,'error':frame_error},409)
                if not active_session or active_session.get('status') != 'active': return self.send_json({'ok':False,'error':'Belum ada sesi aktif.'},409)
                try:
                    selected=data.get('selected_numbers')
                    if selected is None: selected=[p.get('number') for p in active_session.get('photos',[])]
                    slots=data.get('frame_slots')
                    if active_session.get('session_mode')=='timed' and len(selected)>int(slots or active_session.get('frame_slots',4)):
                        return self.send_json({'ok':False,'error':f'Pilih maksimal {slots or active_session.get("frame_slots",4)} foto sesuai slot frame.'},400)
                    stop_shot_live_photo(discard=True)
                    stop_session_video()
                    active_session['live_recording']=False
                    active_session['capture_open']=False
                    active_session['recording']=False
                    if 'drive_qr_enabled' in data: active_session['drive_qr_enabled']=bool(data.get('drive_qr_enabled'))
                    if isinstance(data.get('drive_qr_layout'),dict): active_session['drive_qr_layout']=data.get('drive_qr_layout')
                    snapshot=queue_session_render(active_session,selected,data.get('filter'),True,data.get('frame_id'),data.get('layout_slots'),slots)
                    sid=active_session['id']
                    active_session=None
                    result=dict(snapshot)
                    result['status']='processing'
                    result['render_status']='processing'
                    base=f'http://127.0.0.1:{PORT}/api/session/{sid}'
                    return self.send_json({'ok':True,'processing':True,'session':result,'output_url':base+'/output.jpg','live_output_url':base+'/output_live.mp4' if result.get('live_photo_enabled') else None,'live_output_preview_url':None,'gif_url':base+'/originals.gif'})
                except Exception as e: return self.send_json({'ok':False,'error':str(e)},500)
        return self.send_json({'ok': False, 'error': 'Not found'}, 404)


if __name__ == '__main__':
    print(f'[BACKEND_DIAGNOSTIC] python={sys.executable} version={sys.version.split()[0]} platform={sys.platform}', flush=True)
    if cv2 is None:
        print('ERROR: OpenCV gagal diimpor pada interpreter ini. Jalankan setup.bat.', flush=True)
    else:
        print(f'[BACKEND_DIAGNOSTIC] opencv={cv2.__version__}', flush=True)
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    server.daemon_threads = True
    print(f'KACA_CAMERA_BACKEND_READY http://{HOST}:{PORT} opencv={cv2.__version__ if cv2 else "UNAVAILABLE"}', flush=True)
    try:
        server.serve_forever(poll_interval=.25)
    except KeyboardInterrupt:
        pass
    finally:
        stop_session_video()
        close_camera()
        server.server_close()
