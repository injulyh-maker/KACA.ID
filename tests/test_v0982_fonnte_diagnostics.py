"""Test Fonnte diagnostics and send path without exposing or requiring a real token."""
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'backend'))
from whatsapp_gateway import FonnteGateway

class TestFonnteDiagnostics(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.requests=[]
        self.response={'status':True,'id':['message123'],'requestid':982,'detail':'success! message in queue'}
        self.gateway=FonnteGateway(self.temp.name,http=self.fake_send)
        self.gateway._device_http=lambda token:{'status':True,'device':'6282396674553','device_status':'connect','quota':'20'}
        self.gateway.configure('TEST-TOKEN-NOT-REAL')
    def tearDown(self):self.temp.cleanup()
    def fake_send(self,fields,token):
        self.requests.append((fields,token))
        return self.response
    def test_device_connected_without_leaking_token(self):
        self.gateway._device_http=lambda token:{'status':True,'device':'6282396674553','device_status':'connect','quota':'20','package':'Basic'}
        result=self.gateway.device_profile()
        self.assertEqual(result['device_status'],'connect')
        self.assertEqual(result['quota'],'20')
        self.assertNotIn('token',result)
        self.assertNotIn('TEST-TOKEN',str(result))
    def test_invalid_token_device_disconnected(self):
        self.gateway._device_http=lambda token:{'status':False,'reason':'token invalid'}
        with self.assertRaisesRegex(ValueError,'token invalid'): self.gateway.device_profile()
        self.gateway._device_http=lambda token:{'status':True,'device_status':'disconnect','quota':0}
        self.assertIn('belum terhubung',self.gateway.device_profile()['warning'])
    def test_send_accepted_queue_only_and_duplicate_protection(self):
        url='https://drive.google.com/drive/folders/TEST-SESSION'
        result=self.gateway.send('abcdef123456','082312345678',url,True)
        self.assertEqual(result['status'],'accepted')
        self.assertEqual(result['request_id'],'982')
        self.assertEqual(result['message_id'],'message123')
        self.assertEqual(self.requests[0][0]['target'],'6282312345678')
        self.assertEqual(self.requests[0][0]['connectOnly'],'true')
        self.assertNotIn('delivered',result['status'])
        again=self.gateway.send('abcdef123456','082312345678',url,True)
        self.assertTrue(again['duplicate'])
        self.assertEqual(len(self.requests),1)
        # new manager loads persistent send guard and does not send again
        manager=FonnteGateway(self.temp.name,http=self.fake_send)
        self.assertTrue(manager.send('abcdef123456','082312345678',url,True)['duplicate'])
        self.assertEqual(len(self.requests),1)
    def test_provider_decline_gives_actionable_reason(self):
        self.response={'status':False,'reason':'insufficient quota'}
        with self.assertRaisesRegex(RuntimeError,'Kuota pesan Fonnte habis'):
            self.gateway.send('abcdef123456','081234567890','https://drive.google.com/drive/folders/ABC',True)
        self.assertFalse(self.gateway.sent)
    def test_consent_required(self):
        with self.assertRaisesRegex(ValueError,'menyetujui'):
            self.gateway.send('abcdef123456','081234567890','https://drive.google.com/drive/folders/ABC',False)

if __name__=='__main__':unittest.main(verbosity=2)
