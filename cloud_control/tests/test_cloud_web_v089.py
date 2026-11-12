"""Isolated Cloud Control v0.9.89 web API: analytics, exports, licenses."""
import csv
import io
import os
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path
from fastapi.testclient import TestClient

class CloudWebTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory(prefix='kaca-cloud-v089-')
        os.environ['KACA_CLOUD_DATA_DIR']=cls.temp.name
        sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
        from cloud_control import server
        cls.s=server
        server.REMOTE_ENABLED=True
        server.mail_enabled=lambda: True
        server.send_security_mail=lambda *args,**kwargs: None
        cls.client=TestClient(server.app)
        server.create_superadmin('super@kaca.test','Super Admin','VeryStrongAdminPassword!2026')
        def post(url,data,token=None,booth=None):
            headers={}
            if token:headers['Authorization']='Bearer '+token
            if booth:headers.update({'X-Booth-Id':booth['booth_id'],'X-Booth-Key':booth['booth_key']})
            return cls.client.post(url,json=data,headers=headers)
        cls.post=staticmethod(post)
        cls.admin=post('/api/auth/login',{'email':'super@kaca.test','password':'VeryStrongAdminPassword!2026'}).json()['token']
        assert post('/api/auth/register',{'email':'owner@kaca.test','name':'Test Owner','password':'UserPasswordTest!2026'}).status_code==200
        assert post('/api/auth/register',{'email':'other@kaca.test','name':'Other Owner','password':'AnotherPassword!2026'}).status_code==200
        with server.transaction() as con:
            con.execute('UPDATE users SET email_verified_at=? WHERE role=?',(server.unix(),'user'))
        cls.owner=post('/api/auth/login',{'email':'owner@kaca.test','password':'UserPasswordTest!2026'}).json()['token']
        cls.other=post('/api/auth/login',{'email':'other@kaca.test','password':'AnotherPassword!2026'}).json()['token']
        issued=[]
        for email in ['owner@kaca.test','owner@kaca.test','other@kaca.test']:
            result=post('/api/admin/licenses',{'owner_email':email,'days':365},cls.admin)
            assert result.status_code==200,result.text
            issued.append(result.json())
        cls.owner_license=issued[0]['id']
        cls.owner_booths=[]
        for i,token in [(0,cls.owner),(1,cls.owner),(2,cls.other)]:
            result=post('/api/booths/activate',{'license_code':issued[i]['code'],
                'device_id':f'PC-TEST-ABCDEFGHI{i}','name':f'Booth {i+1}'},token)
            assert result.status_code==200,result.text
            if i<2:cls.owner_booths.append(result.json())
            else:cls.other_booth=result.json()
        import datetime as dt
        today=server.report_today()
        dates=[(today-dt.timedelta(days=n)).isoformat()+'T12:00:00' for n in (2,1,0)]
        cls.dates=dates
        sessions=[]
        for i in range(24):
            sessions.append({'id':f'session{i:06d}','finished_at':dates[i%3],
                'event_name':'=SUM(1+1)' if i==0 else 'Wedding',
                'mode':'PHOTO' if i%2==0 else 'VIDEO','photo_count':2 if i%2==0 else 0,
                'amount_idr':40000,'verified_paid':i%3==0,
                'drive_url':'https://drive.google.com/drive/folders/example'})
        assert post('/api/agent/sync',{'version':'0.9.88','sessions':sessions},booth=cls.owner_booths[0]).status_code==200
        assert post('/api/agent/sync',{'version':'0.9.88','sessions':[{'id':'another00001',
               'finished_at':dates[2],'mode':'PHOTO','verified_paid':True,'amount_idr':50000}]},booth=cls.other_booth).status_code==200

    @classmethod
    def tearDownClass(cls):
        cls.client.close()
        cls.temp.cleanup()

    def get(self,path,token=None):
        return self.client.get(path,headers={'Authorization':'Bearer '+token} if token else {})

    def test_status_timeline_account_separation_and_filters(self):
        r=self.get('/api/health');self.assertEqual(r.status_code,200);self.assertTrue(r.json()['ok'])
        timeline=self.get('/api/analytics/timeline?days=7',self.owner)
        self.assertEqual(timeline.status_code,200,timeline.text)
        days=timeline.json()['daily']
        self.assertEqual(len(days),7)
        self.assertEqual(sum(x['sessions'] for x in days),24)
        self.assertEqual(sum(x['verified_revenue_idr'] for x in days),8*40000)
        self.assertEqual(sum(x['estimated_idr'] for x in days),16*40000)
        self.assertEqual(self.get('/api/analytics/timeline?days=14',self.owner).status_code,400)
        self.assertEqual(self.get('/api/analytics/timeline?days=7&booth_id='+self.other_booth['booth_id'],self.owner).status_code,404)
        other=self.get('/api/analytics/timeline?days=7',self.other).json()['daily']
        self.assertEqual(sum(x['sessions'] for x in other),1)
        r=self.get('/api/sessions?limit=10&offset=0',self.owner)
        self.assertEqual(len(r.json()['sessions']),10)
        self.assertEqual(r.json()['total'],24)
        self.assertTrue(r.json()['has_more'])
        self.assertEqual(len(self.get('/api/sessions?limit=10&offset=20',self.owner).json()['sessions']),4)
        self.assertEqual(self.get('/api/sessions?mode=PHOTO',self.owner).json()['total'],12)
        self.assertEqual(self.get('/api/sessions?date_from='+self.dates[1][:10]+'&date_to='+self.dates[1][:10],self.owner).json()['total'],8)
        self.assertEqual(self.get('/api/sessions?date_from='+self.dates[2][:10]+'&date_to='+self.dates[1][:10],self.owner).status_code,400)
        self.assertEqual(self.get('/api/sessions?booth_id='+self.other_booth['booth_id'],self.owner).status_code,404)
        self.assertEqual(self.get('/api/sessions',self.other).json()['total'],1)

    def test_csv_export_uses_scope_filters_and_prevents_formulas(self):
        r=self.get('/api/sessions/export.csv?mode=PHOTO',self.owner)
        self.assertEqual(r.status_code,200,r.text)
        self.assertIn('attachment;',r.headers.get('content-disposition',''))
        data=r.content.decode('utf-8-sig')
        rows=list(csv.reader(io.StringIO(data),delimiter=';'))
        self.assertEqual(len(rows),13)
        self.assertTrue(any(row[3].startswith("'=SUM") for row in rows[1:]))
        self.assertEqual(len(list(csv.reader(io.StringIO(self.get('/api/sessions/export.csv',self.other).content.decode('utf-8-sig')),delimiter=';'))),2)
        self.assertEqual(self.get('/api/sessions/export.csv?booth_id='+self.other_booth['booth_id'],self.owner).status_code,404)
        self.assertEqual(self.get('/api/sessions/export.csv').status_code,401)

    def test_admin_license_suspension_blocks_agent_not_owner_view(self):
        self.assertEqual(self.get('/api/admin/licenses',self.owner).status_code,403)
        ls=self.get('/api/admin/licenses',self.admin)
        self.assertEqual(ls.status_code,200)
        self.assertEqual(len(ls.json()['licenses']),3)
        status=self.post(f'/api/admin/licenses/{self.owner_license}/status',{'status':'suspended'},self.admin)
        self.assertEqual(status.status_code,200,status.text)
        self.assertIn('offline',status.json()['notice'])
        self.assertEqual(self.post('/api/agent/sync',{'version':'test'},booth=self.owner_booths[0]).status_code,401)
        self.assertEqual(self.post(f'/api/admin/licenses/{self.owner_license}/status',{'status':'active'},self.owner).status_code,403)
        self.assertEqual(self.post(f'/api/admin/licenses/{self.owner_license}/status',{'status':'deleted'},self.admin).status_code,422)
        self.assertEqual(self.post(f'/api/admin/licenses/{self.owner_license}/status',{'status':'active'},self.admin).status_code,200)
        self.assertEqual(self.post('/api/agent/sync',{'version':'test'},booth=self.owner_booths[0]).status_code,200)
        actions=[x['action'] for x in self.get('/api/audit',self.admin).json()['items']]
        self.assertIn('license.suspended',actions)
        self.assertIn('license.active',actions)
        self.assertEqual(self.get('/api/audit',self.owner).status_code,403)

if __name__=='__main__':unittest.main(verbosity=2)
