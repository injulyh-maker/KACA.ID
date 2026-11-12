"""Integration-style tests using isolated temp DB, no internet or real customer data."""
import base64
import importlib
import os
from pathlib import Path
import secrets
import sqlite3
import sys
import tempfile
import unittest

from fastapi.testclient import TestClient

class CloudControlTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory(prefix='kaca-cloud-test-')
        os.environ['KACA_CLOUD_DATA_DIR']=cls.tmp.name
        sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
        from cloud_control import server
        cls.s=server
        server.REMOTE_ENABLED=True
        server.mail_enabled=lambda: True
        server.send_security_mail=lambda *args,**kwargs: None
        cls.client=TestClient(server.app)
        server.create_superadmin('admin@kaca.test','KACA Admin','SuperSecretPassword2026!')

    @classmethod
    def tearDownClass(cls):
        cls.client.close()
        cls.tmp.cleanup()

    def post(self,url,data,token=None,booth=None):
        headers={}
        if token:headers['Authorization']='Bearer '+token
        if booth:headers.update({'X-Booth-Id':booth['booth_id'],'X-Booth-Key':booth['booth_key']})
        return self.client.post(url,json=data,headers=headers)
    def get(self,url,token=None,booth=None):
        headers={}
        if token:headers['Authorization']='Bearer '+token
        if booth:headers.update({'X-Booth-Id':booth['booth_id'],'X-Booth-Key':booth['booth_key']})
        return self.client.get(url,headers=headers)

    def test_accounts_multibooth_offline_licenses_remote_and_finances(self):
        admin=self.post('/api/auth/login',{'email':'admin@kaca.test','password':'SuperSecretPassword2026!'})
        self.assertEqual(admin.status_code,200,admin.text)
        a=admin.json()['token']
        u=self.post('/api/auth/register',{'email':'owner@kaca.test','name':'Booth Owner','password':'StrongCustomer2026!'})
        self.assertEqual(u.status_code,200,u.text)
        with self.s.transaction() as con:con.execute('UPDATE users SET email_verified_at=? WHERE email=?',(self.s.unix(),'owner@kaca.test'))
        user=self.post('/api/auth/login',{'email':'owner@kaca.test','password':'StrongCustomer2026!'}).json()['token']
        other=self.post('/api/auth/register',{'email':'other@kaca.test','name':'Other Owner','password':'AnotherCustomer2026!'})
        self.assertEqual(other.status_code,200)
        with self.s.transaction() as con:con.execute('UPDATE users SET email_verified_at=? WHERE email=?',(self.s.unix(),'other@kaca.test'))
        other_token=self.post('/api/auth/login',{'email':'other@kaca.test','password':'AnotherCustomer2026!'}).json()['token']
        self.assertEqual(self.post('/api/admin/licenses',{'owner_email':'owner@kaca.test'},user).status_code,403)
        codes=[]
        for days in [180,365]:
            created=self.post('/api/admin/licenses',{'owner_email':'owner@kaca.test','days':days},a)
            self.assertEqual(created.status_code,200,created.text)
            codes.append(created.json()['code'])
        licenses=self.get('/api/licenses',user).json()['licenses']
        self.assertEqual(len(licenses),2)
        self.assertNotIn(codes[0],str(licenses))
        b1=self.post('/api/booths/activate',{'license_code':codes[0],'device_id':'PC-1234567890-A','name':'Wedding Booth 1'},user)
        b2=self.post('/api/booths/activate',{'license_code':codes[1],'device_id':'PC-1234567890-B','name':'Wedding Booth 2'},user)
        self.assertEqual(b1.status_code,200,b1.text)
        self.assertEqual(b2.status_code,200,b2.text)
        one=b1.json();two=b2.json()
        payload=self.s.verify_license(one['offline_license'])
        self.assertEqual(payload['booth_id'],one['booth_id'])
        self.assertEqual(payload['device_hash'],self.s.hash_token('PC-1234567890-A'))
        self.assertEqual(self.post('/api/booths/activate',{'license_code':codes[0],'device_id':'PC-1234567890-OTHER','name':'Rogue Booth'},user).status_code,409)
        self.assertEqual(self.get('/api/booths',other_token).json()['booths'],[])
        self.assertEqual(len(self.get('/api/booths',user).json()['booths']),2)
        # Offline queue sync uses sessions as idempotent source-of-truth.
        sync={'version':'0.9.86','sessions':[{'id':'aabbccdd1122','event_name':'Wedding Test','mode':'PHOTO',
             'finished_at':'2026-11-10T18:00:00','amount_idr':25000,'verified_paid':True,
             'payment_method':'qris_doku','drive_url':'https://drive.google.com/drive/folders/TEST','photo_count':3},
             {'id':'ddeeff001122','event_name':'Wedding Test','mode':'VIDEO','amount_idr':15000,'verified_paid':False,'photo_count':0}]}
        r=self.post('/api/agent/sync',sync,booth=one)
        self.assertEqual(r.status_code,200,r.text)
        self.assertEqual(r.json()['accepted_sessions'],2)
        self.assertEqual(self.post('/api/agent/sync',sync,booth=one).status_code,200)
        summary=self.get('/api/analytics',user).json()['totals']
        self.assertEqual(summary['booths'],2)
        self.assertEqual(summary['visitors'],2)
        self.assertEqual(summary['revenue_idr'],25000)
        self.assertEqual(summary['unverified_estimate_idr'],15000)
        self.assertEqual(len(self.get('/api/sessions',user).json()['sessions']),2)
        self.assertEqual(self.get(f'/api/booths/{one["booth_id"]}/preview',user).status_code,403)
        self.assertEqual(self.post(f'/api/booths/{one["booth_id"]}/commands',{'type':'remote.click','payload':{'x':0.4,'y':0.5,'action':'down'}},user).status_code,403)
        # A request reaches the booth, which must authorize locally.
        requested=self.post(f'/api/booths/{one["booth_id"]}/commands',{'type':'remote.request','payload':{}},user)
        self.assertEqual(requested.status_code,200)
        commands=self.get('/api/agent/commands',booth=one)
        self.assertEqual(commands.status_code,200)
        self.assertEqual(commands.json()['commands'][0]['type'],'remote.request')
        command_id=commands.json()['commands'][0]['id']
        self.assertEqual(self.post('/api/agent/commands/ack',{'command_id':command_id,'ok':True},booth=one).status_code,200)
        # In this test an operator has consented and the booth reports its grant.
        sync['remote_until']=self.s.unix()+500
        self.assertEqual(self.post('/api/agent/sync',sync,booth=one).status_code,200)
        # JPEG magic bytes + mocked data: render a tiny valid JPEG elsewhere, binary check only here.
        image=b'\xff\xd8'+b'jpeg-mock' * 40
        self.assertEqual(self.post('/api/agent/snapshot',{'jpeg_b64':base64.b64encode(image).decode()},booth=one).status_code,200)
        self.assertEqual(self.get(f'/api/booths/{one["booth_id"]}/preview',user).status_code,200)
        self.assertEqual(self.get(f'/api/booths/{one["booth_id"]}/preview',other_token).status_code,404)
        self.assertEqual(self.post(f'/api/booths/{one["booth_id"]}/commands',{'type':'settings.patch','payload':{'sessionPrice':25000,'countdown':3}},user).status_code,200)
        self.assertEqual(self.post(f'/api/booths/{one["booth_id"]}/commands',{'type':'settings.patch','payload':{'cloudToken':'leak'}},user).status_code,400)
        self.assertEqual(self.post(f'/api/booths/{one["booth_id"]}/commands',{'type':'executeShell','payload':{'cmd':'danger'}},user).status_code,400)
        self.assertEqual(self.get('/api/admin/users',user).status_code,403)
        self.assertEqual(self.get('/api/admin/users',a).status_code,200)

if __name__=='__main__':unittest.main(verbosity=2)
