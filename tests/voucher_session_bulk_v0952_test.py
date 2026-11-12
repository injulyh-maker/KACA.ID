from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
app=(ROOT/'src/app.js').read_text(encoding='utf-8')
server=(ROOT/'backend/camera_server.py').read_text(encoding='utf-8')
# Customer controls must be locked until the async capture initializer has declared all state.
assert 'captureUiReady=false' in app
assert 'btn.disabled=true' in app and "if(!captureUiReady)" in app
assert 'captureUiReady=true;transactionPanel.querySelectorAll' in app
# The customer handler must not invoke a TDZ-sensitive step before capture setup is complete.
assert app.index('captureUiReady=false') < app.index('await api(\'/api/frames\')')
assert app.index('captureUiReady=true;transactionPanel') > app.index("start.onclick=async")
# Admin bulk selection and destructive actions are wired to backend.
for token in ['voucherSelectAll','data-voucher-select','deleteSelectedVouchers','deleteExpiredVouchers','deleteAllVouchers']:
    assert token in app
assert "api('/api/vouchers/delete'" in app
assert "path == '/api/vouchers/delete'" in server
assert "mode == 'expired'" in server and "mode == 'all'" in server
assert 'def _voucher_is_expired' in server
print('voucher init guard + bulk selection/delete + expired-only deletion v0.9.52: PASS')
