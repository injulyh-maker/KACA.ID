import json, os, sys, tempfile, unittest
from unittest.mock import patch
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))
from whatsapp_cloud import WhatsAppCloudManager, normalize_whatsapp_number

class FakeResponse:
    def __init__(self, data): self.data=data
    def __enter__(self): return self
    def __exit__(self,*a): return False
    def read(self): return json.dumps(self.data).encode()

class WhatsAppCloudTests(unittest.TestCase):
    def test_config_persistence_and_secret_not_exposed(self):
        with tempfile.TemporaryDirectory() as d:
            m=WhatsAppCloudManager(d)
            s=m.configure({'phone_number_id':'123456789012345','access_token':'x'*40,'template_name':'kaca_hasil_photobooth','language':'id','api_version':'v26.0'})
            self.assertTrue(s['configured']); self.assertTrue(s['token_saved'])
            self.assertNotIn('access_token',s)
            m.configure({'phone_number_id':'123456789012345','access_token':'','template_name':'kaca_hasil_photobooth','language':'id','api_version':'v26.0'})
            self.assertEqual(m._read()['access_token'],'x'*40)
    def test_indonesian_number_normalization(self):
        self.assertEqual(normalize_whatsapp_number('081234567890'),'6281234567890')
        self.assertEqual(normalize_whatsapp_number('+62 812-3456-7890'),'6281234567890')
        self.assertEqual(normalize_whatsapp_number('006281234567890'),'6281234567890')
        with self.assertRaises(ValueError): normalize_whatsapp_number('123')
    def test_invalid_config_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            m=WhatsAppCloudManager(d)
            with self.assertRaises(ValueError): m.configure({'phone_number_id':'bad','access_token':'x'*40})
            with self.assertRaises(ValueError): m.configure({'phone_number_id':'123456789012345','access_token':'x'*40,'template_name':'Bad Template'})
    def test_send_template_payload(self):
        with tempfile.TemporaryDirectory() as d:
            m=WhatsAppCloudManager(d)
            m.configure({'phone_number_id':'123456789012345','access_token':'x'*40,'template_name':'kaca_hasil_photobooth','language':'id','api_version':'v26.0'})
            captured={}
            def fake_urlopen(req,timeout=0):
                captured['url']=req.full_url; captured['headers']=dict(req.header_items()); captured['body']=json.loads(req.data.decode())
                return FakeResponse({'messages':[{'id':'wamid.test-123'}]})
            with patch('urllib.request.urlopen',fake_urlopen):
                result=m.send_result_template('6281234567890','https://drive.google.com/drive/folders/abc','SESSION1')
            self.assertEqual(result['message_id'],'wamid.test-123')
            self.assertTrue(captured['url'].endswith('/v26.0/123456789012345/messages'))
            self.assertEqual(captured['body']['type'],'template')
            self.assertEqual(captured['body']['to'],'6281234567890')
            self.assertEqual(captured['body']['template']['components'][0]['parameters'][0]['text'],'https://drive.google.com/drive/folders/abc')

if __name__=='__main__': unittest.main()
