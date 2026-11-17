"""No-network payment and QR-local-only regression tests."""
import ast,json,sys,time,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from doku_qris import DokuQris
from midtrans_snap import MidtransSnap
from google_drive import GoogleDriveManager

class PaymentTests(unittest.TestCase):
    def test_doku_decimal_invoice_and_one_time_use(self):
        with tempfile.TemporaryDirectory() as folder:
            d=DokuQris(folder)
            d.configure({'client_id':'BRN-TEST','secret_key':'test-key','environment':'sandbox'})
            d._request=lambda *a,**k:{'response':{'payment':{'url':'https://checkout.doku.com/test'}}}
            item=d.create(1000);invoice=item['invoice']
            d._request=lambda *a,**k:{'order':{'invoice_number':invoice,'amount':'1000.00'},'transaction':{'status':'SUCCESS'}}
            self.assertEqual(d.check(invoice,now=item['created_at']+61)['status'],'paid')
            d.consume_paid(invoice)
            with self.assertRaises(ValueError):d.consume_paid(invoice)

    def test_doku_wrong_amount_stays_pending(self):
        with tempfile.TemporaryDirectory() as folder:
            d=DokuQris(folder)
            d.configure({'client_id':'BRN-TEST','secret_key':'test-key','environment':'sandbox'})
            d._request=lambda *a,**k:{'response':{'payment':{'url':'https://checkout.doku.com/test'}}}
            item=d.create(1000);invoice=item['invoice']
            d._request=lambda *a,**k:{'order':{'invoice_number':invoice,'amount':'900'},'transaction':{'status':'SUCCESS'}}
            with self.assertRaises(RuntimeError):d.check(invoice,now=item['created_at']+61)
            self.assertEqual(d.public_payment(invoice)['status'],'pending')

    def test_sandbox_http400_exposes_safe_message(self):
        with tempfile.TemporaryDirectory() as folder:
            d=DokuQris(folder,http=lambda *a:(400,b'{"error":{"message":"QRIS channel not enabled"}}',{}))
            d.configure({'client_id':'BRN-TEST','secret_key':'private-test-secret','environment':'sandbox'})
            with self.assertRaisesRegex(RuntimeError,'QRIS channel not enabled') as ctx:d.create(1000)
            self.assertNotIn('private-test-secret',str(ctx.exception))

    def _midtrans(self,folder,gross='1500.00',state='settlement',return404=False):
        memory={}
        def fake(method,url,headers,body):
            self.assertTrue(headers['Authorization'].startswith('Basic '))
            if '/snap/v1/transactions' in url:
                req=json.loads(body)
                memory['invoice']=req['transaction_details']['order_id']
                self.assertEqual(req['enabled_payments'],['other_qris'])
                return 201,b'{"redirect_url":"https://app.sandbox.midtrans.com/snap/v2/vtweb/test"}'
            if return404:return 404,b'{}'
            return 200,json.dumps({'order_id':memory['invoice'],'gross_amount':gross,
                'transaction_status':state,'fraud_status':'accept','status_code':'200'}).encode()
        m=MidtransSnap(folder,http=fake)
        m.configure({'environment':'sandbox','server_key':'SB-Mid-server-TEST','qris_channel':'other_qris'})
        return m

    def test_midtrans_paid_replay_and_mismatch(self):
        with tempfile.TemporaryDirectory() as folder:
            m=self._midtrans(folder)
            item=m.create(1500)
            self.assertEqual(m.check(item['invoice'],now=time.time()+6)['status'],'paid')
            m.consume_paid(item['invoice'])
            with self.assertRaises(ValueError):m.consume_paid(item['invoice'])
        with tempfile.TemporaryDirectory() as folder:
            m=self._midtrans(folder,gross='1501.00')
            item=m.create(1500)
            with self.assertRaises(RuntimeError):m.check(item['invoice'],now=time.time()+6)
            self.assertEqual(m.public_payment(item['invoice'])['status'],'pending')

    def test_midtrans_404_pending_not_paid(self):
        with tempfile.TemporaryDirectory() as folder:
            m=self._midtrans(folder,return404=True)
            item=m.create(1500)
            self.assertEqual(m.check(item['invoice'],now=time.time()+6)['status'],'pending')
            with self.assertRaises(ValueError):m.consume_paid(item['invoice'])

    def test_no_upload_of_standalone_or_print_qr(self):
        with tempfile.TemporaryDirectory() as folder:
            base=Path(folder)/'archive'/'Final_Results'
            base.mkdir(parents=True)
            for name in ('QR_Google_Drive.png','Hasil_Frame_Dengan_QR.jpg','Hasil_Frame.jpg'):
                (base/name).write_bytes(b'mock')
            manager=GoogleDriveManager(folder)
            names=[]
            manager._upload_resumable=lambda path,parent:names.append(Path(path).name) or {'id':'ok'}
            manager.create_session_folder=lambda *a,**k:{'folder_id':'test','share_warning':None}
            manager.ensure_folder=lambda *a,**k:'test'
            for name in ('QR_Google_Drive.png','Hasil_Frame_Dengan_QR.jpg'):
                outcome=manager.upload_session_asset(str(base/name),'test','Final_Results/'+name)
                self.assertEqual(outcome['reason'],'local_qr_only')
            manager.upload_session_folder(str(base.parent),'Sesi 01')
            self.assertEqual(names,['Hasil_Frame.jpg'])

    def test_price_policy_zero_fixed_percent(self):
        tree=ast.parse((ROOT/'camera_server.py').read_text(encoding='utf-8'))
        fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='_payment_quote')
        env={'qris_config':{'base_price':0,'discount_type':'nominal','discount_value':0}}
        exec(compile(ast.Module(body=[fn],type_ignores=[]),'payment','exec'),env)
        self.assertEqual(env['_payment_quote']()['amount'],0)
        env['qris_config']={'base_price':10000,'discount_type':'percent','discount_value':25}
        self.assertEqual(env['_payment_quote']()['amount'],7500)
        env['qris_config']={'base_price':10000,'discount_type':'nominal','discount_value':2000}
        self.assertEqual(env['_payment_quote']()['amount'],8000)

if __name__=='__main__':unittest.main()
