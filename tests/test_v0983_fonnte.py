"""Fonnte device-token validation and requested friendly message template."""
import os,sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'backend'))
from whatsapp_gateway import FonnteGateway

class GatewayTest(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory()
  self.sent=[]
  self.gw=FonnteGateway(self.temp.name,http=lambda fields,token:(self.sent.append((fields,token)) or {'status':True,'id':['msg1']}))
  self.gw._device_http=lambda token:{'status':True,'device':'6282396674553','device_status':'connect','quota':'30'} if token=='device-ok' else {'status':False,'reason':'token invalid'}
 def tearDown(self):self.temp.cleanup()
 def test_valid_token_from_devices_and_message(self):
  saved=self.gw.configure('Bearer device-ok')
  self.assertTrue(saved['verified'])
  self.assertEqual(saved['device_status'],'connect')
  self.assertNotIn('token',saved)
  url='https://drive.google.com/drive/folders/abc-123'
  response=self.gw.send('abcdef012345','081234567891',url,True)
  self.assertEqual(response['status'],'accepted')
  message=self.sent[0][0]['message']
  self.assertTrue(message.startswith('Halo, kami dari KACA.ID Photobooth Studio 😊'))
  self.assertIn(url,message)
  self.assertIn('Terima kasih',message)
  self.assertNotIn('delivered',str(response))
 def test_invalid_token_does_not_replace_saved(self):
  self.gw.configure('device-ok')
  with self.assertRaisesRegex(ValueError,'Token Fonnte ditolak'):
   self.gw.configure('device-invalid')
  self.assertEqual(self.gw.config.get('token'),'device-ok')
  with open(self.gw.path,encoding='utf-8') as handle:
   self.assertIn('device-ok',handle.read())
 def test_account_token_confusion_explained(self):
  with self.assertRaisesRegex(ValueError,'menu Devices'):
   self.gw.configure('account-token-incompatible')

if __name__=='__main__':unittest.main(verbosity=2)
