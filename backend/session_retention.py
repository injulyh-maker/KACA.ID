"""Opt-in retention policies for KACA-owned session assets only.

Never deletes the KACA root, user folders unrelated to KACA, or a Drive folder
unless its parent is the KACA STUDIO root/event folder. Drive deletion moves an
owned session folder to Trash, where Google can still recover it.
"""
import datetime as dt
import json
import os
import re
import shutil
import threading
import time

DEFAULT = {'local_enabled': False, 'local_days': 30,
           'drive_enabled': False, 'drive_days': 30}


def parse_time(value):
    try:
        parsed = dt.datetime.fromisoformat(str(value or '').replace('Z', '+00:00'))
        # Existing KACA manifests use naive device-local ISO timestamps.
        # Python timestamp() interprets naive values in the computer's local TZ.
        return parsed.timestamp()
    except (ValueError, TypeError, OverflowError):
        return None


def validate_config(value):
    if not isinstance(value, dict):
        raise ValueError('Konfigurasi retensi tidak valid.')
    output = {}
    for storage in ('local', 'drive'):
        enabled = value.get(storage + '_enabled', False)
        if not isinstance(enabled, bool):
            raise ValueError('Status retensi harus berupa pilihan aktif/nonaktif.')
        try:
            days = int(value.get(storage + '_days', 30))
        except (TypeError, ValueError):
            raise ValueError('Durasi retensi wajib berupa angka hari.')
        if not 1 <= days <= 3650:
            raise ValueError('Durasi retensi harus 1–3650 hari.')
        output[storage + '_enabled'] = enabled
        output[storage + '_days'] = days
    return output


def within_root(path, root):
    try:
        path = os.path.realpath(path)
        root = os.path.realpath(root)
        return path != root and os.path.commonpath([path, root]) == root
    except (ValueError, OSError, TypeError):
        return False


class SessionRetention:
    def __init__(self, data_dir):
        self.path = os.path.join(data_dir, 'retention-config.json')
        self.lock = threading.RLock()
        self.last_result = {'scanned': 0, 'local_deleted': 0, 'drive_trashed': 0, 'errors': []}

    def get(self):
        with self.lock:
            try:
                with open(self.path, encoding='utf-8') as file:
                    saved = json.load(file)
                config = validate_config(saved)
            except (OSError, ValueError, TypeError):
                config = dict(DEFAULT)
            return {**config, 'last_run': dict(self.last_result)}

    def set(self, payload):
        config = validate_config(payload)
        with self.lock:
            os.makedirs(os.path.dirname(self.path), exist_ok=True)
            temporary = self.path + '.tmp'
            with open(temporary, 'w', encoding='utf-8') as file:
                json.dump(config, file, indent=2)
            os.replace(temporary, self.path)
        return self.get()

    def sweep(self, session_dir, archive_root, load, save, drive,
              *, active_id=None, on_expire=None, upload_pending=None, now=None):
        """One bounded pass. All functions can be replaced with mocks for tests."""
        now = time.time() if now is None else float(now)
        cfg = self.get()
        result = {'scanned': 0, 'local_deleted': 0, 'drive_trashed': 0,
                  'errors': [], 'checked_at': dt.datetime.fromtimestamp(now,dt.timezone.utc).isoformat()}
        with self.lock:
            if not (cfg['local_enabled'] or cfg['drive_enabled']):
                self.last_result = result
                return result
            if not os.path.isdir(session_dir):
                self.last_result = result
                return result
            for sid in os.listdir(session_dir):
                if not re.fullmatch(r'[a-f0-9]{12}', sid) or sid == active_id:
                    continue
                try:
                    row = load(sid)
                    if not row or row.get('status') != 'finished':
                        continue
                    finished = parse_time(row.get('finished_at'))
                    if finished is None or finished > now:
                        continue  # Never expire active/unfinished/unknown-age sessions.
                    result['scanned'] += 1
                    local_due = cfg['local_enabled'] and not row.get('local_deleted_at') and (now - finished >= cfg['local_days']*86400)
                    drive_due = cfg['drive_enabled'] and not row.get('drive_deleted_at') and (now - finished >= cfg['drive_days']*86400)
                    if drive_due:
                        folder = row.get('drive_folder_id')
                        if folder:
                            try:
                                drive.trash_session_folder(folder, event_id=row.get('event_id'))
                            except Exception as exc:
                                result['errors'].append(sid + ' Drive: ' + str(exc)[:150])
                            else:
                                if on_expire: on_expire(sid, 'drive')
                                row['drive_deleted_at'] = result['checked_at']
                                row['drive_status'] = 'expired'
                                row['drive_folder_status'] = 'expired'
                                row['drive_folder_id'] = None
                                row['drive_url'] = None
                                row['drive_qr_available'] = False
                                row['drive_uploaded_assets'] = []
                                # An expired Drive link must no longer appear via a stale QR.
                                for qr in (os.path.join(session_dir,sid,'qr.png'),
                                           os.path.join(row.get('local_archive_path') or '', 'Final_Results','QR_Google_Drive.png')):
                                    if os.path.isfile(qr):
                                        try: os.remove(qr)
                                        except OSError: pass
                                result['drive_trashed'] += 1
                                save(row)
                        elif row.get('drive_folder_status') not in ('creating', 'pending'):
                            # No folder was ever provisioned; nothing exists remotely.
                            row['drive_deleted_at'] = result['checked_at']
                            row['drive_status'] = 'expired'
                            row['drive_url'] = None
                            if on_expire: on_expire(sid, 'drive')
                            save(row)
                    if local_due:
                        if upload_pending and upload_pending(sid):
                            result['errors'].append(sid + ': menghindari penghapusan lokal selama upload Drive belum selesai.')
                            continue
                        archive = row.get('local_archive_path')
                        try:
                            if archive:
                                if not within_root(archive, archive_root):
                                    raise RuntimeError('Path arsip di luar folder KACA; dilewati.')
                                if os.path.isdir(archive):
                                    shutil.rmtree(archive)
                            session_path = os.path.join(session_dir, sid)
                            if not within_root(session_path, session_dir):
                                raise RuntimeError('Path sesi tidak aman.')
                            # Keep a small tombstone manifest for Drive's independent TTL.
                            for entry in os.listdir(session_path):
                                if entry == 'session.json': continue
                                target = os.path.join(session_path, entry)
                                if os.path.isdir(target) and not os.path.islink(target):
                                    shutil.rmtree(target)
                                else:
                                    os.remove(target)
                        except Exception as exc:
                            result['errors'].append(sid + ' lokal: ' + str(exc)[:150])
                        else:
                            if on_expire: on_expire(sid, 'local')
                            row['local_deleted_at'] = result['checked_at']
                            row['local_archive_status'] = 'expired'
                            result['local_deleted'] += 1
                            save(row)
                except Exception as exc:
                    result['errors'].append(sid + ': ' + str(exc)[:150])
            self.last_result = result
        return result

    def sweep_videos(self, jobs, video_dir, archive_root, drive, save_jobs,
                     *, active_id=None, now=None):
        """Apply the same independent TTL policy to standalone VIDEO sessions."""
        now = time.time() if now is None else float(now)
        cfg = self.get()
        result = {'videos_scanned': 0, 'video_local_deleted': 0,
                  'video_drive_trashed': 0, 'video_errors': []}
        if not cfg['local_enabled'] and not cfg['drive_enabled']:
            return result
        with self.lock:
            for vid, row in list(jobs.items()):
                if not re.fullmatch(r'[a-f0-9]{12}', str(vid)) or row.get('kind') != 'video' or vid == active_id:
                    continue
                try:
                    metadata_file = os.path.join(os.path.dirname(row.get('local_path') or ''), vid+'.json')
                    meta = {}
                    if os.path.isfile(metadata_file):
                        try:
                            with open(metadata_file,encoding='utf-8') as file: meta=json.load(file)
                        except (OSError,ValueError): pass
                    finished = parse_time(row.get('created_at') or meta.get('created_at'))
                    if finished is None:
                        local_file = row.get('local_path') or ''
                        finished = os.path.getmtime(local_file) if os.path.isfile(local_file) else None
                    if finished is None or finished > now:
                        continue
                    # Historical VIDEO jobs (before v0.9.81) did not store
                    # created_at in the queue. Persist it before local files
                    # are removed so Drive can expire independently later.
                    if not row.get('created_at'):
                        row['created_at'] = dt.datetime.fromtimestamp(finished,dt.timezone.utc).isoformat()
                        save_jobs()
                    result['videos_scanned'] += 1
                    if cfg['drive_enabled'] and not row.get('drive_deleted_at') and now-finished >= cfg['drive_days']*86400:
                        folder = row.get('folder_id')
                        if folder:
                            try: drive.trash_session_folder(folder,event_id=row.get('event_id'))
                            except Exception as exc:
                                result['video_errors'].append(vid+' Drive: '+str(exc)[:140])
                            else:
                                row.update({'drive_deleted_at':dt.datetime.fromtimestamp(now,dt.timezone.utc).isoformat(),
                                            'url':None, 'folder_id':None, 'status':'expired', 'qr_path':None})
                                result['video_drive_trashed'] += 1
                                save_jobs()
                        elif row.get('status') not in ('pending','uploading'):
                            row.update({'drive_deleted_at':dt.datetime.fromtimestamp(now,dt.timezone.utc).isoformat(),
                                        'url':None, 'status':'expired', 'qr_path':None})
                            save_jobs()
                    if cfg['local_enabled'] and not row.get('local_deleted_at') and now-finished >= cfg['local_days']*86400:
                        if row.get('status') in ('pending','uploading','waiting_auth','error') and not row.get('drive_deleted_at'):
                            result['video_errors'].append(vid+': upload belum selesai; lokal tetap diamankan.')
                            continue
                        local_path = row.get('local_path') or ''
                        try:
                            if local_path:
                                if not within_root(local_path, archive_root):
                                    raise RuntimeError('Video berada di luar folder KACA.')
                                for suffix in ('.mp4','.json','_Poster.jpg','_QR_Google_Drive.png'):
                                    target=os.path.join(os.path.dirname(local_path),vid+suffix)
                                    if os.path.isfile(target):os.remove(target)
                            # Internal VIDEO preview is always beneath KACA data root.
                            for extension in ('.mp4','.webm'):
                                target=os.path.join(video_dir,vid+extension)
                                if within_root(target,video_dir) and os.path.isfile(target):os.remove(target)
                        except Exception as exc:
                            result['video_errors'].append(vid+' lokal: '+str(exc)[:140])
                        else:
                            row['local_deleted_at']=dt.datetime.fromtimestamp(now,dt.timezone.utc).isoformat()
                            result['video_local_deleted'] += 1
                            save_jobs()
                except Exception as exc:
                    result['video_errors'].append(vid+': '+str(exc)[:140])
        return result
