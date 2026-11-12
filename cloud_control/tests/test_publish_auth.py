"""Run separately: python -m unittest cloud_control.tests.test_publish_auth -v.
No SMTP, remote VPS, or real user data is touched.
"""
import os
import re
import sys
import tempfile
import unittest
from pathlib import Path
from fastapi.testclient import TestClient


class PublishAuthTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory(prefix='kaca-publish-auth-')
        os.environ['KACA_CLOUD_DATA_DIR'] = cls.tmp.name
        sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
        from cloud_control import server
        cls.s = server
        cls.mails = []
        server.mail_enabled = lambda: True
        server.send_security_mail = lambda recipient,subject,body: cls.mails.append((recipient,subject,body))
        cls.client = TestClient(server.app)
        server.create_superadmin('admin@kaca.test', 'Super Admin', 'SuperStrongPassword2026!')

    @classmethod
    def tearDownClass(cls):
        cls.client.close()
        cls.tmp.cleanup()

    def post(self, path, data, token=None):
        headers = {'Authorization': 'Bearer ' + token} if token else {}
        return self.client.post(path, json=data, headers=headers)

    def test_registration_email_verification_reset_preserves_license(self):
        user = {'name':'Test Customer','email':'verified@kaca.test','password':'StrongPasswordTest123!'}
        r = self.post('/api/auth/register', user)
        self.assertEqual(r.status_code,200,r.text)
        self.assertNotIn('token',r.json())
        self.assertTrue(r.json()['requires_verification'])
        login=self.post('/api/auth/login', {'email':user['email'],'password':user['password']})
        self.assertEqual(login.status_code,403)
        link=re.search(r'/verifikasi-email#token=([A-Za-z0-9_-]+)',self.mails[-1][2])
        self.assertIsNotNone(link)
        self.assertEqual(self.post('/api/auth/verify-email',{'token':link.group(1)}).status_code,200)
        self.assertEqual(self.post('/api/auth/verify-email',{'token':link.group(1)}).status_code,400)
        login=self.post('/api/auth/login', {'email':user['email'],'password':user['password']})
        self.assertEqual(login.status_code,200,login.text)
        old_token=login.json()['token']
        admin=self.post('/api/auth/login', {'email':'admin@kaca.test','password':'SuperStrongPassword2026!'})
        self.assertEqual(admin.status_code,200)
        issue=self.post('/api/admin/licenses',{'owner_email':user['email'],'days':30},admin.json()['token'])
        self.assertEqual(issue.status_code,200)
        activated=self.post('/api/booths/activate',{'license_code':issue.json()['code'],'device_id':'TABLET-A-DEVICE-123456','name':'Booth Test'},old_token)
        self.assertEqual(activated.status_code,200)
        signed=self.s.verify_license(activated.json()['offline_license'])
        self.assertEqual(signed['exp'],issue.json()['expires_at'])
        self.assertEqual(self.post('/api/auth/forgot-password',{'email':user['email']}).status_code,200)
        reset=re.search(r'/reset-sandi#token=([A-Za-z0-9_-]+)',self.mails[-1][2])
        self.assertIsNotNone(reset)
        result=self.post('/api/auth/reset-password',{'token':reset.group(1),'password':'AnotherSecurePassword2026!'})
        self.assertEqual(result.status_code,200,result.text)
        self.assertEqual(self.client.get('/api/booths',headers={'Authorization':'Bearer '+old_token}).status_code,401)
        self.assertEqual(self.post('/api/auth/login',{'email':user['email'],'password':user['password']}).status_code,401)
        fresh=self.post('/api/auth/login',{'email':user['email'],'password':'AnotherSecurePassword2026!'}).json()['token']
        self.assertEqual(len(self.client.get('/api/booths',headers={'Authorization':'Bearer '+fresh}).json()['booths']),1)
        self.assertEqual(self.post('/api/auth/reset-password',{'token':reset.group(1),'password':'ThirdSecurePassword2026!'}).status_code,400)
        self.assertEqual(self.post('/api/admin/plans',{'days':30,'price_idr':100000},fresh).status_code,403)
        self.assertEqual(self.post('/api/admin/plans',{'days':30,'price_idr':100000},admin.json()['token']).status_code,200)
        public=self.client.get('/api/public/plans').json()
        self.assertEqual(public['plans'][0]['price_idr'],100000)
        self.assertEqual(self.client.get('/api/public/plans').json()['whatsapp'],'6281934386108')
        for path in ['/paket','/verifikasi-email','/reset-sandi']:
            self.assertEqual(self.client.get(path).status_code,200)


if __name__=='__main__': unittest.main()
