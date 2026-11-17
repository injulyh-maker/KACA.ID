"""Regression tests for local Drive recovery and token diagnostics without network access."""
import ast
import datetime
import os
import queue
import sys
import tempfile
import threading
import unittest
from pathlib import Path

SERVER = Path(__file__).resolve().parents[1] / 'camera_server.py'
sys.path.insert(0, str(SERVER.parent))
from google_drive import GoogleDriveManager

tree = ast.parse(SERVER.read_text(encoding='utf-8'), str(SERVER))
wanted = {'enqueue_drive_asset_job', '_resume_folder_assets'}
defs = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in wanted]
assert len(defs) == len(wanted), 'Missing Drive job queue functions'

class ManagerStub:
    def __init__(self, connected=True):
        self.connected = connected
    def status(self):
        return {'connected': self.connected}

class DriveQueueTests(unittest.TestCase):
    def test_waiting_for_folder_does_not_block_upload_queue(self):
        with tempfile.TemporaryDirectory() as temporary:
            image = Path(temporary) / 'Hasil_Frame.jpg'
            image.write_bytes(b'JPEG test bytes')
            manifest = {'id':'session-12345678', 'drive_folder_status':'creating'}
            manager = ManagerStub()
            jobs = {}
            pending = queue.Queue()
            state = {
                '__builtins__':__builtins__,'os':os,'datetime':datetime,
                'threading':threading,'str':str,'drive_jobs_lock':threading.RLock(),
                'drive_jobs':jobs,'drive_jobs_queue':pending,'google_drive':manager,
                'read_manifest':lambda sid:manifest,'_save_drive_jobs':lambda:None
            }
            exec(compile(ast.Module(body=defs,type_ignores=[]),str(SERVER),'exec'),state)
            entry=state['enqueue_drive_asset_job']('session-12345678',str(image),'Final_Results/Hasil_Frame.jpg')
            self.assertEqual(entry['status'],'waiting_folder')
            self.assertTrue(pending.empty(), 'Asset must not queue until Drive folder exists')
            manifest['drive_folder_id']='google-folder-1234'
            self.assertEqual(state['_resume_folder_assets']('session-12345678'),1)
            self.assertEqual(pending.get_nowait(),'session-12345678:Final_Results/Hasil_Frame.jpg')
            self.assertEqual(state['_resume_folder_assets']('session-12345678'),0)
            self.assertTrue(pending.empty())

    def test_diagnose_checks_actual_api_and_does_not_expose_secrets(self):
        with tempfile.TemporaryDirectory() as directory:
            manager=GoogleDriveManager(directory)
            manager._write({'client_id':'test.apps.googleusercontent.com',
                            'client_secret':'private-example-secret',
                            'refresh_token':'private-example-refresh'})
            def ok_api(method,path,params=None):
                if path=='/about':return {'user':{'emailAddress':'tester@example.org'}}
                if path=='/files':return {'files':[]}
                raise AssertionError(path)
            manager._api=ok_api
            report=manager.diagnose()
            self.assertTrue(report['verified'])
            self.assertEqual(report['account_email'],'tester@example.org')
            self.assertNotIn('refresh_token',report)
            self.assertNotIn('client_secret',report)
            def fail_api(*args,**kwargs):raise RuntimeError('Google API HTTP 401: invalid_grant')
            manager._api=fail_api
            report=manager.diagnose()
            self.assertFalse(report['verified'])
            self.assertIn('invalid_grant',report['error'])

if __name__=='__main__':unittest.main()
