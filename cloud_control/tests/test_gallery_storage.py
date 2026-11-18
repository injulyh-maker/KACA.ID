"""End-to-end gallery and license smoke test with fake media, no external network."""
import os
from pathlib import Path
import sys
import tempfile
import unittest

from fastapi.testclient import TestClient

class GalleryCloudTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory(prefix='kaca-cloud-gallery-')
        os.environ['KACA_CLOUD_DATA_DIR']=cls.tmp.name
        sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
        from cloud_control import server
        cls.s=server
        server.mail_enabled=lambda:True
        server.send_security_mail=lambda *args,**kwargs:None
        cls.client=TestClient(server.app)
        server.create_superadmin('admin-gallery@kaca.test','Gallery Admin','StrongTestPassword123!')
        r=cls.client.post('/api/auth/login',json={'email':'admin-gallery@kaca.test','password':'StrongTestPassword123!'})
        assert r.status_code==200,r.text
        cls.admin=r.json()['token']
        r=cls.client.post('/api/auth/register',json={'name':'Studio Owner','email':'owner-gallery@kaca.test','password':'StrongCustomerPassword123!'})
        assert r.status_code==200,r.text
        with server.transaction() as con:
            con.execute('UPDATE users SET email_verified_at=? WHERE email=?',(server.unix(),'owner-gallery@kaca.test'))
        r=cls.client.post('/api/auth/login',json={'email':'owner-gallery@kaca.test','password':'StrongCustomerPassword123!'})
        assert r.status_code==200,r.text
        cls.owner=r.json()['token']
        lic=cls.client.post('/api/admin/licenses',headers={'Authorization':'Bearer '+cls.admin},
                            json={'owner_email':'owner-gallery@kaca.test','days':1})
        assert lic.status_code==200,lic.text
        cls.issued=lic.json()
        activation=cls.client.post('/api/booths/activate',headers={'Authorization':'Bearer '+cls.owner},
                                  json={'license_code':cls.issued['code'],'device_id':'WIN-TEST-DEVICE-01','name':'Booth Gallery'})
        assert activation.status_code==200,activation.text
        cls.booth=activation.json()
        cls.bh={'X-Booth-Id':cls.booth['booth_id'],'X-Booth-Key':cls.booth['booth_key']}
        cls.oh={'Authorization':'Bearer '+cls.owner}
        cls.ah={'Authorization':'Bearer '+cls.admin}

    @classmethod
    def tearDownClass(cls):
        cls.client.close();cls.tmp.cleanup()

    def test_one_day_license(self):
        self.assertGreater(self.issued['expires_at'],self.s.unix()+23*3600)
        self.assertLessEqual(self.issued['expires_at'],self.s.unix()+86400+60)

    def test_gallery_upload_brand_qr_and_access_control(self):
        gallery=self.client.get('/api/gallery',headers=self.oh)
        self.assertEqual(gallery.status_code,200,gallery.text)
        self.assertEqual(gallery.json()['items'],[])
        preview=b'\xff\xd8\xff'+b'0'*150
        sid='session_gal_1234'
        noauth=self.client.post('/api/agent/gallery/'+sid+'/upload?kind=preview&mode=PHOTO',
                                content=preview,headers={})
        self.assertEqual(noauth.status_code,401)
        disabled=self.client.post('/api/agent/gallery/'+sid+'/upload?kind=preview&mode=PHOTO',
                                content=preview,headers=self.bh)
        self.assertEqual(disabled.status_code,403)
        settings=self.client.post('/api/gallery/preferences',headers=self.oh,
                            json={'booth_id':self.booth['booth_id'],'mode':'web','share':'web'})
        self.assertEqual(settings.status_code,200,settings.text)
        self.assertEqual(self.client.get('/api/agent/gallery/preferences',headers=self.bh).json()['mode'],'web')
        brand=self.client.post('/api/gallery/brand',headers=self.oh,json={'title':'KACA Poso','subtitle':'Galeri Event Wedding',
                                                            'accent':'#cc8844','retention_days':3})
        self.assertEqual(brand.status_code,200,brand.text)
        uploaded=self.client.post('/api/agent/gallery/'+sid+'/upload?kind=preview&mode=PHOTO&event_name=Wedding',
                    content=preview,headers={**self.bh,'Content-Type':'application/octet-stream'})
        self.assertEqual(uploaded.status_code,200,uploaded.text)
        item=uploaded.json()
        self.assertTrue(item['url'].startswith('https://kacastudio.id/session/'))
        token=item['url'].split('/')[-1]
        self.assertGreater(len(token),35)
        public=self.client.get('/session/'+token)
        self.assertEqual(public.status_code,200,public.text)
        self.assertIn('KACA Poso',public.text)
        self.assertIn('Cetak Foto',public.text)
        self.assertIn('#cc8844',public.text)
        media=self.client.get('/session/'+token+'/media')
        self.assertEqual(media.status_code,200)
        self.assertEqual(media.content,preview)
        self.assertEqual(self.client.get('/session/not-a-valid-token').status_code,404)
        listing=self.client.get('/api/gallery',headers=self.oh).json()
        self.assertEqual(listing['total'],1)
        unauth=self.client.get('/api/gallery')
        self.assertEqual(unauth.status_code,401)
        denied=self.client.post('/api/gallery/preferences',headers=self.oh,
               json={'booth_id':self.booth['booth_id'],'mode':'local','share':'web'})
        self.assertEqual(denied.status_code,400)
        removed=self.client.delete('/api/gallery/'+self.booth['booth_id']+'/'+sid,headers=self.oh)
        self.assertEqual(removed.status_code,200,removed.text)
        self.assertEqual(self.client.get('/session/'+token).status_code,404)

    def test_non_existent_media_rejected(self):
        r=self.client.post('/api/agent/gallery/../../../bad/upload?kind=video',content=b'\x00'*100,headers=self.bh)
        self.assertIn(r.status_code,(400,404))
        r=self.client.post('/api/agent/gallery/valid_identifier_1234/upload?kind=video',
                           content=b'not-an-mp4'+b'x'*100,headers=self.bh)
        self.assertEqual(r.status_code,400,r.text)

if __name__=='__main__':unittest.main()
