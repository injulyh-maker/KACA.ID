"""Regression for v0.9.66's UnboundLocalError in Handler.do_GET."""
from pathlib import Path
import ast
root=Path(__file__).resolve().parents[1]
tree=ast.parse((root/'backend'/'camera_server.py').read_text(encoding='utf8'))
handler=next(x for x in tree.body if isinstance(x,ast.ClassDef) and x.name=='Handler')
method=next(x for x in handler.body if isinstance(x,ast.FunctionDef) and x.name=='do_GET')
# A local assignment anywhere in this function shadows the global camera state,
# even on unrelated routes like /api/cameras and /api/status.
assigned=[x.lineno for x in ast.walk(method) if isinstance(x,ast.Name) and isinstance(x.ctx,ast.Store) and x.id=='state']
assert not assigned,'GET handler must not rebind global camera state: '+repr(assigned)
s=(root/'backend'/'camera_server.py').read_text(encoding='utf8')
assert 'animation_status=_start_live_animation_generation(sid,manifest)' in s
assert 'return self.send_json(dict(state))' in s
assert "if path == '/api/status':" in s
print('PASS: no local state shadowing in GET; camera status routes safe')
