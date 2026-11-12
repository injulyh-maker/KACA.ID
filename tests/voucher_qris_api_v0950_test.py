"""HTTP integration test for local voucher APIs and QRIS static configuration."""
import os, sys, tempfile, threading, json, urllib.request, urllib.error, base64
from pathlib import Path
import numpy as np

with tempfile.TemporaryDirectory(prefix='kaca-voucher-api-') as temp:
    os.environ['KACA_DATA_DIR'] = str(Path(temp) / 'data')
    os.environ['KACA_LOCAL_ARCHIVE_DIR'] = str(Path(temp) / 'archive')
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'backend'))
    import camera_server as mod
    mod.latest_frame = np.zeros((64, 64, 3), dtype=np.uint8)
    mod.state.update({'camera_open': True, 'selected': 'test', 'frame_width': 64, 'frame_height': 64})
    server = mod.ThreadingHTTPServer(('127.0.0.1', 0), mod.Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
    base = f'http://127.0.0.1:{server.server_port}'
    def call(path, payload=None):
        data=None if payload is None else json.dumps(payload).encode()
        req=urllib.request.Request(base+path,data=data,headers={'Content-Type':'application/json'} if data is not None else {})
        try:
            with urllib.request.urlopen(req,timeout=5) as r: return r.status,json.loads(r.read())
        except urllib.error.HTTPError as e: return e.code,json.loads(e.read())
    try:
        status, created = call('/api/vouchers/generate', {'count':2,'expiry_days':10,'max_uses':2})
        assert status==200 and created['count']==2
        code=created['created'][0]['code']
        assert len(code)==5 and code.isalnum() and code.upper()==code
        status, valid = call('/api/vouchers/validate', {'code':code.lower()})
        assert status==200 and valid['ok'] and valid['voucher']['used_count']==0
        status, started = call('/api/session/start', {'payment_method':'voucher','voucher_code':code,'frame_slots':1,'photo_count':1})
        assert status==200 and started['ok'] and started['session']['voucher_code']==code
        status, listing = call('/api/vouchers')
        row=next(v for v in listing['vouchers'] if v['code']==code)
        assert row['used_count']==1
        # Valid PNG payload (1x1 pixel) tests upload path; no network/payment gateway is called.
        ok, encoded_png = mod.cv2.imencode('.png', np.full((32, 32, 3), 255, dtype=np.uint8))
        assert ok
        png=base64.b64encode(encoded_png.tobytes()).decode()
        status, qris = call('/api/qris/config', {'merchant_name':'KACA TEST','amount':25000,'image_data_url':'data:image/png;base64,'+png})
        assert status==200 and qris['configured']
        status, qstatus = call('/api/qris/status')
        assert status==200 and qstatus['configured'] and qstatus['amount']==25000
        status, imported = call('/api/vouchers/import', {'vouchers':[{'code':'CSV55','expires_at':'2026-12-31','max_uses':3,'used_count':0,'active':'true'},{'code':code}]})
        assert status==200 and imported['imported']==1 and len(imported['skipped'])==1
        status, listing = call('/api/vouchers')
        csv_row=next(v for v in listing['vouchers'] if v['code']=='CSV55')
        assert csv_row['expires_at'].endswith('23:59:59') and csv_row['max_uses']==3
    finally:
        server.shutdown(); server.server_close(); thread.join(timeout=2)
print('Voucher API validation/use counting and QRIS static configuration HTTP integration: PASS')
