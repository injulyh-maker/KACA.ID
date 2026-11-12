"""No real Drive data is mutated. Exercises opt-in TTL, safety, and clip timing."""
import datetime as dt
import json
import os
import sys
import tempfile
import time
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'backend'))
from session_retention import SessionRetention, within_root
from google_drive import GoogleDriveManager, FOLDER_MIME

class RetentionTest(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='kaca-retention-')
        self.base=Path(self.temp.name)
        self.sessions=self.base/'sessions';self.sessions.mkdir()
        self.archive=self.base/'KACA STUDIO';self.archive.mkdir()
        self.manager=SessionRetention(self.base/'data')
        self.rows={}
        self.trashed=[]
        outer=self
        class MockDrive:
            def trash_session_folder(self, folder_id, event_id=None):
                outer.trashed.append((folder_id,event_id))
        self.drive=MockDrive()
        self.now=dt.datetime(2026,11,9,15,0,tzinfo=dt.timezone.utc).timestamp()
    def tearDown(self): self.temp.cleanup()
    def add(self, sid, age_days, *, event=None, finished=True, malicious_path=None):
        folder=self.archive/('Events/Event_'+event if event else '')/('Sesi_'+sid)
        folder.mkdir(parents=True)
        (folder/'foto.jpg').write_bytes(b'local_jpg')
        session=self.sessions/sid;session.mkdir()
        (session/'output.jpg').write_bytes(b'final_jpg')
        row={'id':sid,'status':'finished' if finished else 'active',
             'finished_at':dt.datetime.fromtimestamp(self.now-age_days*86400,dt.timezone.utc).isoformat(),
             'drive_folder_id':'drive_'+sid,'event_id':event,'local_archive_path':str(malicious_path or folder),
             'drive_url':'https://drive.google.com/drive/folders/drive_'+sid}
        self.rows[sid]=row
        (session/'session.json').write_text(json.dumps(row))
        return folder
    def run_sweep(self, active_id=None):
        def write(row):
            self.rows[row['id']]=row
            (self.sessions/row['id']/'session.json').write_text(json.dumps(row))
        return self.manager.sweep(str(self.sessions),str(self.archive),self.rows.get,write,self.drive,
                                  active_id=active_id,now=self.now)
    def test_default_off_and_independent_expiry(self):
        a='aabbccddeeff';older='112233445566'
        af=self.add(a,8,event='0123456789abcdef')
        bf=self.add(older,45)
        result=self.run_sweep()
        self.assertEqual(result['local_deleted'],0)
        self.assertTrue(af.exists())
        self.manager.set({'local_enabled':True,'local_days':7,'drive_enabled':True,'drive_days':30})
        result=self.run_sweep()
        self.assertEqual(result['local_deleted'],2)
        self.assertEqual(result['drive_trashed'],1)
        self.assertFalse(af.exists());self.assertFalse(bf.exists())
        self.assertEqual(self.trashed,[('drive_'+older,None)])
        self.assertTrue((self.sessions/a/'session.json').is_file())
        self.assertFalse((self.sessions/a/'output.jpg').exists())
        self.assertEqual(self.rows[a]['drive_folder_id'],'drive_'+a)
        # Move simulated clock past Drive expiry: local tombstone remains usable.
        self.now+=25*86400
        result=self.run_sweep()
        self.assertIn(('drive_'+a,'0123456789abcdef'),self.trashed)
        self.assertEqual(self.rows[a]['drive_url'],None)
    def test_active_and_unfinished_excluded(self):
        a='aabbccddeeff'; b='112233445566'
        af=self.add(a,100)
        bf=self.add(b,100,finished=False)
        self.manager.set({'local_enabled':True,'local_days':1,'drive_enabled':True,'drive_days':1})
        result=self.run_sweep(active_id=a)
        self.assertEqual(result['local_deleted'],0)
        self.assertTrue(af.exists() and bf.exists())
    def test_refuse_outside_root(self):
        sid='aabbccddeeff'
        outside=self.base/'precious-data';outside.mkdir();(outside/'important').write_text('KEEP')
        self.add(sid,100,malicious_path=outside)
        self.manager.set({'local_enabled':True,'local_days':1,'drive_enabled':False,'drive_days':30})
        result=self.run_sweep()
        self.assertEqual(result['local_deleted'],0)
        self.assertTrue((outside/'important').is_file())
        self.assertTrue(result['errors'])
    def test_video_retention_independent(self):
        video_dir=self.base/'data'/'video_sessions';video_dir.mkdir(parents=True)
        vid='012345abcdef'
        archived=self.archive/'Events'/'Event_0123456789abcdef'/'Video_Results'
        archived.mkdir(parents=True)
        for suffix in ('.mp4','.json','_Poster.jpg','_QR_Google_Drive.png'):
            (archived/(vid+suffix)).write_text('sample')
        (video_dir/(vid+'.mp4')).write_bytes(b'mp4')
        (video_dir/(vid+'.webm')).write_bytes(b'webm')
        created=dt.datetime.fromtimestamp(self.now-12*86400,dt.timezone.utc).isoformat()
        jobs={vid:{'id':vid,'kind':'video','local_path':str(archived/(vid+'.mp4')),
                   'created_at':created,'status':'ready','folder_id':'drive_012345abcdef',
                   'url':'https://drive.google.com/drive/folders/drive_012345abcdef',
                   'event_id':'0123456789abcdef'}}
        saved=[]
        self.manager.set({'local_enabled':True,'local_days':7,'drive_enabled':True,'drive_days':30})
        result=self.manager.sweep_videos(jobs,str(video_dir),str(self.archive),self.drive,
                                         lambda:saved.append(True),now=self.now)
        self.assertEqual(result['video_local_deleted'],1)
        self.assertEqual(result['video_drive_trashed'],0)
        self.assertFalse((archived/(vid+'.mp4')).exists())
        self.assertFalse((video_dir/(vid+'.webm')).exists())
        self.assertTrue(jobs[vid]['url'])
        self.now+=20*86400
        result=self.manager.sweep_videos(jobs,str(video_dir),str(self.archive),self.drive,
                                         lambda:saved.append(True),now=self.now)
        self.assertEqual(result['video_drive_trashed'],1)
        self.assertEqual(jobs[vid]['url'],None)
        self.assertEqual(self.trashed[-1][1],'0123456789abcdef')

    def test_historical_video_metadata_persists_across_local_delete(self):
        vid='abcdef123456'
        videos=self.base/'data'/'video_sessions';videos.mkdir(parents=True)
        archive=self.archive/'Video_Results';archive.mkdir()
        file=archive/(vid+'.mp4');file.write_bytes(b'oldvideo')
        (archive/(vid+'.json')).write_text(json.dumps({'created_at':dt.datetime.fromtimestamp(
            self.now-40*86400,dt.timezone.utc).isoformat()}))
        row={'kind':'video','id':vid,'local_path':str(file),'folder_id':'drive_'+vid,
             'event_id':None,'status':'ready'}
        jobs={vid:row}
        self.manager.set({'local_enabled':True,'local_days':7,'drive_enabled':True,'drive_days':90})
        self.manager.sweep_videos(jobs,str(videos),str(self.archive),self.drive,lambda:None,now=self.now)
        self.assertIn('created_at',row)
        self.assertFalse(file.exists())
        self.now+=55*86400
        result=self.manager.sweep_videos(jobs,str(videos),str(self.archive),self.drive,lambda:None,now=self.now)
        self.assertEqual(result['video_drive_trashed'],1)

    def test_defer_local_delete_during_incomplete_upload(self):
        sid='aabbccddeeff';archive=self.add(sid,60)
        self.manager.set({'local_enabled':True,'local_days':7,'drive_enabled':False,'drive_days':30})
        summary=self.manager.sweep(str(self.sessions),str(self.archive),self.rows.get,
                                    lambda row:self.rows.update({row['id']:row}),self.drive,
                                    upload_pending=lambda sid:True,now=self.now)
        self.assertEqual(summary['local_deleted'],0)
        self.assertTrue(archive.exists())
        self.assertTrue(summary['errors'])

    def test_invalid_duration_rejected(self):
        self.assertFalse(self.manager.get()['local_enabled'])
        for days in [0,-1,4000,'x']:
            with self.assertRaises(ValueError): self.manager.set({'local_enabled':True,'local_days':days,'drive_enabled':False,'drive_days':30})

class DriveSafety(unittest.TestCase):
    def test_trash_only_owned_child(self):
        with tempfile.TemporaryDirectory() as td:
            g=GoogleDriveManager(td)
            records=[]
            g.event_parent_folder=lambda event_id=None:'KACA_ROOT'
            def fake_api(method,path,payload=None,params=None):
                records.append((method,path,payload))
                if method=='GET':return {'id':'id-abcdef12345','mimeType':FOLDER_MIME,'parents':['KACA_ROOT'],'trashed':False}
                return {'id':'id-abcdef12345','trashed':True}
            g._api=fake_api
            self.assertTrue(g.trash_session_folder('id-abcdef12345')['trashed'])
            self.assertEqual(records[-1][2],{'trashed':True})
            records.clear()
            with self.assertRaises(ValueError):g.trash_session_folder('KACA_ROOT')
            self.assertFalse(records)
            g._api=lambda *args,**kwargs:{'mimeType':FOLDER_MIME,'parents':['OTHER_ROOT'],'trashed':False}
            with self.assertRaises(ValueError):g.trash_session_folder('id-abcdef12345')

class LiveDuration(unittest.TestCase):
    def test_retime_3sec_source_to_5sec_clip(self):
        import cv2, numpy as np
        # Bring in the isolated helper without booting the camera backend threads.
        import ast
        file=Path(__file__).resolve().parents[1]/'backend/camera_server.py'
        script=ast.parse(file.read_text(encoding='utf-8'))
        fn=next(n for n in script.body if isinstance(n,ast.FunctionDef) and n.name=='_normalize_live_photo_duration')
        namespace={'cv2':cv2,'os':os}
        exec(compile(ast.Module(body=[fn],type_ignores=[]),str(file),'exec'),namespace)
        with tempfile.TemporaryDirectory() as td:
            video=os.path.join(td,'live.mp4')
            writer=cv2.VideoWriter(video,cv2.VideoWriter_fourcc(*'mp4v'),10,(128,96))
            self.assertTrue(writer.isOpened())
            for i in range(30):writer.write(np.full((96,128,3),i*4,dtype=np.uint8))
            writer.release()
            new_count,duration=namespace['_normalize_live_photo_duration'](video,5,10)
            self.assertEqual(new_count,50)
            self.assertAlmostEqual(duration,5,delta=.1)
            cap=cv2.VideoCapture(video)
            self.assertAlmostEqual(cap.get(cv2.CAP_PROP_FRAME_COUNT)/cap.get(cv2.CAP_PROP_FPS),5,delta=.1)
            cap.release()

if __name__=='__main__':unittest.main(verbosity=2)
