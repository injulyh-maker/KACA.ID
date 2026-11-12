from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
app=(ROOT/'src/app.js').read_text(encoding='utf-8')
server=(ROOT/'backend/camera_server.py').read_text(encoding='utf-8')
main=(ROOT/'main.js').read_text(encoding='utf-8')
assert 'requestVoucherCode()' in app and "const code=await requestVoucherCode()" in app
assert "prompt('Masukkan kode voucher" not in app
assert "'/api/vouchers/import'" in server and "'/api/vouchers/import'" in app
assert 'downloadVoucherCsvTemplate' in app and 'parseCsv=' in app
assert 'enableVoucherPayment' in app and 'enableQrisPayment' in app
assert 'if(!transactionEnabled)' in app and 'setFlowStep(2)' in app
assert 'borderCandidates' not in server and 'manual_driver_property' in server
assert 'Found stale/incompatible KACA backend' in main and 'backend_protocol===3' in main
print('payment, voucher CSV, health adoption, borderless tolerance v0.9.51: PASS')
