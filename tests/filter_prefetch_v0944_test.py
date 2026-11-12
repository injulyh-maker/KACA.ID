from pathlib import Path
import ast

ROOT = Path(__file__).resolve().parents[1]
APP = (ROOT / 'src' / 'app.js').read_text(encoding='utf-8')
BACKEND = (ROOT / 'backend' / 'camera_server.py').read_text(encoding='utf-8')

# Filter slide may pre-render in the background, but customer navigation to results
# must not block on a long render wait.
assert "api('/api/session/prepare'" in APP
assert 'const waitForPreparedPreview=async()=>{' in APP
assert 'await waitForPreparedPreview();' not in APP[APP.index("$('#flowFilterNext').onclick=async()=>"):APP.index("$cap('#flowCaptureStart').hidden=true")]
assert "state.render_status==='ready'" in APP
assert "state.render_status==='error'" in APP
assert "if(st.render_status==='error')" in APP and 'st.live_output_available' in APP
assert "if(st.render_status==='ready'&&st.local_archive_status==='ready'" in APP
assert 'const scheduleBackgroundRender=()=>{}' not in APP
assert "liveVideo.hidden=true" in APP and "slide.classList.add('has-live-preview')" in APP
assert '.result-slide.has-live-preview' in (ROOT / 'src' / 'style.css').read_text(encoding='utf-8')

# The prepare endpoint already exists and queues the render without finalizing session.
prepare_route = BACKEND.index("if path == '/api/session/prepare':")
finish_route = BACKEND.index("if path == '/api/session/finish':", prepare_route)
prepare_body = BACKEND[prepare_route:finish_route]
assert 'queue_session_render(active_session,selected,data.get(\'filter\'),False' in prepare_body

# Re-renders during filter selection must preserve source Live Photo clips.
worker_start = BACKEND.index('def _render_session_worker(')
queue_start = BACKEND.index('def queue_session_render(', worker_start)
worker = BACKEND[worker_start:queue_start]
assert '_cleanup_session_live_sources(snapshot)' in worker
assert 'if finish_requested:' in worker
assert 'os.remove(os.path.join(SESSIONS_DIR, session_id, temporary_clip))' not in worker
assert '_cleanup_session_live_sources(snapshot)' in BACKEND[queue_start:]

# Ensure edited JS parses structurally enough for Python to see the expected function tokens.
assert 'LANJUT KE HASIL' in APP
assert 'MENYIMPAN HASIL' in APP
print('PASS: background filter pre-render, non-blocking result navigation, upload-independent preview, and Live Photo source retention')

# Reusing an already-ready pre-render must not enqueue a duplicate expensive render.
queue = BACKEND[BACKEND.index('def queue_session_render('):BACKEND.index('\ndef camera_backends', BACKEND.index('def queue_session_render('))]
assert 'if same_request and job.get(\'ready\'):' in queue
assert 'if same_request and job.get(\'running\'):' in queue
assert 'if finish_requested:' in queue
assert 'enqueue_local_session_archive(snapshot, final=True)' in queue

# The prepare route must preserve a ready manifest when it reuses a completed render.
prepare_body = BACKEND[prepare_route:finish_route]
assert 'snapshot=queue_session_render(' in prepare_body
assert "active_session['render_status']=snapshot.get('render_status','processing')" in prepare_body
assert "if active_session['render_status']=='ready':" in prepare_body

# Intermediate filter renders do not enqueue local archive copies.
worker_commit = worker[worker.index("finish_requested=bool(job.get('finish_requested'))"):]
assert 'enqueue_local_session_archive(snapshot, final=finish_requested)' in worker_commit
print('PASS: ready-render reuse, prepare manifest state, and no intermediate archive copy')

# Exercise the backend render worker with fake files: a filter-stage render keeps
# the source clip available, while finalization removes it and queues the archive.
import os
import sys
import tempfile
import threading
sys.path.insert(0, str(ROOT / 'backend'))
import camera_server as camera_server

with tempfile.TemporaryDirectory(prefix='kaca-v0944-render-') as temp_dir:
    camera_server.SESSIONS_DIR = temp_dir
    camera_server.render_jobs = {}
    camera_server.render_jobs_lock = threading.RLock()
    archived = []
    camera_server.write_manifest = lambda snapshot: None
    camera_server.enqueue_local_session_archive = lambda snapshot, final=False: archived.append(bool(final))
    def fake_compose_output(snapshot, selected, mark_finished=False):
        snapshot['output'] = 'output.jpg'
        return 'output.jpg'
    def fake_compose_live(snapshot, selected_photos):
        source = os.path.join(temp_dir, snapshot['id'], selected_photos[0]['live_photo'])
        assert os.path.isfile(source), 'source Live Photo must exist while composing'
        snapshot['live_output_preview'] = 'output_live.webm'
        return 'output_live.mp4'
    camera_server.compose_output = fake_compose_output
    camera_server.compose_live_output = fake_compose_live
    sid = 'prefetch-test'
    session_dir = os.path.join(temp_dir, sid)
    os.makedirs(session_dir)
    for name in ('shot.mp4', 'shot.webm'):
        open(os.path.join(session_dir, name), 'wb').write(b'fake-video')
    snapshot = {
        'id': sid, 'photos': [{'number': 1, 'original': 'shot.jpg', 'edited': 'shot-edited.jpg',
                               'live_photo': 'shot.mp4', 'live_photo_preview': 'shot.webm'}],
        'live_photo_enabled': True, 'filter': None, 'frame_id': None,
        'layout_slots': [], 'frame_slots': 1
    }
    camera_server.render_jobs[sid] = {'session': snapshot, 'selected_numbers': [1], 'version': 1,
                                      'finish_requested': False, 'running': True, 'ready': False}
    camera_server._render_session_worker(sid)
    job = camera_server.render_jobs[sid]
    assert job['ready'] and job['session']['render_status'] == 'ready'
    assert os.path.isfile(os.path.join(session_dir, 'shot.mp4'))
    assert os.path.isfile(os.path.join(session_dir, 'shot.webm'))
    assert archived == [False], 'intermediate render should sync assets locally without final ZIP packaging'
    finalized = camera_server.queue_session_render(snapshot, [1], None, True, None, [], 1)
    assert finalized['status'] == 'finished' and finalized['render_status'] == 'ready'
    assert not os.path.exists(os.path.join(session_dir, 'shot.mp4'))
    assert not os.path.exists(os.path.join(session_dir, 'shot.webm'))
    assert finalized['photos'][0]['live_photo'] is None
    assert archived == [False, True]
    assert sid not in camera_server.render_jobs
print('PASS: backend pre-render retains Live Photo sources and finalization cleans them after archive queue')
