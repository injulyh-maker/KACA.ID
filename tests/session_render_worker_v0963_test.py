from pathlib import Path
import os
import tempfile
import threading

ROOT=Path(__file__).resolve().parents[1]
SOURCE=(ROOT/'backend/camera_server.py').read_text(encoding='utf-8')
worker=SOURCE[SOURCE.index('def _render_session_worker(session_id):'):SOURCE.index('def queue_session_render(')]
assert "snapshot.get('settings',{})" in worker
assert "(session.get('settings',{})" not in worker
assert "[SESSION_RENDER_ERROR]" in worker

# Exercise the exact filter-render branch that previously raised NameError.
import sys
sys.path.insert(0, str(ROOT/'backend'))
import camera_server as backend
import cv2
import numpy as np

with tempfile.TemporaryDirectory(prefix='kaca-v0963-render-') as temp:
    backend.SESSIONS_DIR=temp
    backend.render_jobs={}
    backend.render_jobs_lock=threading.RLock()
    backend.write_manifest=lambda snapshot: None
    backend.enqueue_local_session_archive=lambda snapshot, final=False: None
    backend.compose_output=lambda snapshot, selected, mark_finished=False: 'output.jpg'
    backend.compose_live_output=lambda snapshot, selected: None
    sid='filter-worker-test'
    os.makedirs(os.path.join(temp,sid))
    original=os.path.join(temp,sid,'original.jpg')
    assert cv2.imwrite(original, np.full((32,32,3), 120, dtype=np.uint8))
    session={
        'id':sid, 'photos':[{'number':1,'original':'original.jpg','edited':'edited.jpg'}],
        'filter':'sepia', 'settings':{'jpeg_quality':87}, 'live_photo_enabled':False,
        'frame_id':None, 'layout_slots':[], 'frame_slots':1
    }
    backend.render_jobs[sid]={
        'session':session, 'selected_numbers':[1], 'version':1,
        'finish_requested':False, 'running':True, 'ready':False
    }
    backend._render_session_worker(sid)
    job=backend.render_jobs[sid]
    assert job['ready'] is True, job
    assert job['session']['render_status']=='ready'
    assert os.path.isfile(os.path.join(temp,sid,'edited.jpg'))

print('KACA.ID v0.9.63 render worker filter branch uses isolated snapshot settings: PASS')
