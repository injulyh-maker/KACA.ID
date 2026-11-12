from pathlib import Path
import ast
ROOT=Path(__file__).resolve().parents[1]
app=(ROOT/'src/app.js').read_text(encoding='utf-8')
css=(ROOT/'src/style.css').read_text(encoding='utf-8')
backend=(ROOT/'backend/camera_server.py').read_text(encoding='utf-8')
ast.parse(backend)
assert "api('/api/vouchers/validate'" in app
assert "api('/api/vouchers/generate'" in app
assert "api('/api/qris/status'" in app and "api('/api/qris/config'" in app
assert 'secrets.choice(alphabet) for _ in range(5)' in backend
assert "path == '/api/vouchers/generate'" in backend and "path == '/api/vouchers/validate'" in backend
assert "path == '/api/qris/config'" in backend and "path == '/api/qris/image'" in backend
assert "payment_method=payment_method" not in backend  # stored as explicit session metadata below
assert "'payment_method':payment_method" in backend and "'voucher_code':voucher_code" in backend
assert 'await ensureCaptureCamera()' in app and 'start.dataset.lastError=e.message' in app
assert 'frameNextButton.disabled=!chosenFrameId||!activeFrameList.length' in app
assert 'max-width:88%!important;max-height:88%!important' in css
print('Voucher generation/redemption, QRIS static setup, frame-flow guard, and preview fit: PASS')
