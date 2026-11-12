from pathlib import Path
import ast, json, os, tempfile

ROOT = Path(__file__).resolve().parents[1]
BACKEND = (ROOT / 'backend' / 'camera_server.py').read_text(encoding='utf-8')
tree = ast.parse(BACKEND)
selected = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in ('session_manifest', 'read_manifest')]
ns = {'os': os, 'json': json}
exec(compile(ast.Module(body=selected, type_ignores=[]), '<manifest-recovery-test>', 'exec'), ns)
tmp = tempfile.mkdtemp()
ns['SESSIONS_DIR'] = tmp
sid = 'manifestrecoverytest'
folder, manifest = ns['session_manifest'](sid)
os.makedirs(folder, exist_ok=True)
raw = json.dumps({'id': sid, 'still_ready': True}) + '\n' + json.dumps({'drive_url': 'https://drive.google.com/drive/folders/test', 'drive_folder_status': 'ready'})
Path(manifest).write_text(raw, encoding='utf-8')
result = ns['read_manifest'](sid)
assert result['id'] == sid and result['still_ready'] is True
assert result['drive_url'].endswith('/test') and result['drive_folder_status'] == 'ready'
assert Path(manifest + '.corrupt-backup').read_text(encoding='utf-8') == raw
assert json.loads(Path(manifest).read_text(encoding='utf-8')) == result
assert 'if str(relative_path).lower().endswith(\'.webm\')' not in BACKEND
assert 'WebM upload is independent' in BACKEND
print('Manifest JSON recovery + WebM realtime queue source checks: PASS')
