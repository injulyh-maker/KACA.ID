"""Midtrans Snap QRIS checkout with server-side verification and single-use invoices.

Only the authenticated Get Transaction Status endpoint can confirm paid. The Snap
page, redirect URL and browser callbacks are never considered payment evidence.
"""
import base64
import datetime as dt
from decimal import Decimal, InvalidOperation
import json
import os
import secrets
import threading
import time
import urllib.error
import urllib.parse
import urllib.request

class MidtransSnap:
    def __init__(self, data_dir, http=None):
        self.config_path=os.path.join(data_dir,'midtrans-config.json')
        self.ledger_path=os.path.join(data_dir,'midtrans-payments.json')
        self.lock=threading.RLock()
        self.config=self._read(self.config_path,{})
        self.ledger=self._read(self.ledger_path,{})
        self.http=http or self._http

    @staticmethod
    def _read(path,default):
        try:
            with open(path,encoding='utf-8') as f: obj=json.load(f)
            return obj if isinstance(obj,dict) else default
        except (OSError,ValueError):return default

    @staticmethod
    def _save(path,obj):
        os.makedirs(os.path.dirname(path),exist_ok=True)
        tmp=path+'.tmp'
        with open(tmp,'w',encoding='utf-8') as f:json.dump(obj,f,ensure_ascii=False,indent=2)
        os.replace(tmp,path)

    def public_config(self):
        with self.lock:
            return {'environment':self.config.get('environment','sandbox'),
                'configured':bool(self.config.get('server_key')),
                'server_key_saved':bool(self.config.get('server_key')),
                'qris_channel':self.config.get('qris_channel','other_qris')}

    def configure(self,config):
        env=str(config.get('environment') or 'sandbox').strip()
        channel=str(config.get('qris_channel') or 'other_qris').strip()
        if env not in ('sandbox','production'):raise ValueError('Lingkungan Midtrans tidak valid.')
        if channel not in ('other_qris','gopay'):raise ValueError('Channel QRIS Midtrans tidak valid.')
        key=str(config.get('server_key') or '').strip()
        with self.lock:
            if not key and env==self.config.get('environment'):key=self.config.get('server_key','')
            if not key:raise ValueError('Server Key Midtrans wajib diisi untuk environment ini.')
            if len(key)>250:raise ValueError('Server Key terlalu panjang.')
            self.config={'environment':env,'qris_channel':channel,'server_key':key}
            self._save(self.config_path,self.config)
        return self.public_config()

    @staticmethod
    def _http(method,url,headers,body):
        req=urllib.request.Request(url,data=body,headers=headers,method=method)
        try:
            with urllib.request.urlopen(req,timeout=20) as res:
                return res.status,res.read(1024*1024)
        except urllib.error.HTTPError as exc:
            return exc.code,exc.read(8192)

    def _request(self,method,path,payload=None):
        with self.lock: cfg=dict(self.config)
        if not cfg.get('server_key'):raise ValueError('Server Key Midtrans belum dikonfigurasi.')
        base=('https://app.sandbox.midtrans.com' if cfg['environment']=='sandbox' else 'https://app.midtrans.com') if path.startswith('/snap/') else (
            'https://api.sandbox.midtrans.com' if cfg['environment']=='sandbox' else 'https://api.midtrans.com')
        auth=base64.b64encode((cfg['server_key']+':').encode('utf-8')).decode('ascii')
        data=json.dumps(payload,separators=(',',':')).encode('utf-8') if payload is not None else None
        code,raw=self.http(method,base+path,{'Authorization':'Basic '+auth,'Accept':'application/json','Content-Type':'application/json'},data)
        try:obj=json.loads(raw.decode('utf-8'))
        except (ValueError,UnicodeError):obj={}
        if code==404 and method=='GET':
            # Snap may return 404 until the customer selects a payment method.
            return {'transaction_status':'pending','pending_reason':'snap_not_selected'}
        if not 200<=code<300:
            detail=obj.get('error_messages') or obj.get('status_message') or obj.get('message') if isinstance(obj,dict) else ''
            if isinstance(detail,list):detail='; '.join(map(str,detail))
            detail=str(detail or '')[:160].replace(cfg['server_key'],'[REDACTED]')
            raise RuntimeError('Midtrans HTTP '+str(code)+(': '+detail if detail else '')+
                               '. Periksa Server Key, channel QRIS dan environment.')
        if not isinstance(obj,dict):raise RuntimeError('Respons Midtrans tidak valid.')
        return obj

    def create(self,amount):
        amount=int(amount)
        if amount<=0 or amount>999999999999:
            raise ValueError('Midtrans hanya menerima nominal transaksi positif.')
        with self.lock:env=self.config.get('environment','sandbox');channel=self.config.get('qris_channel','other_qris')
        invoice='KACAM'+dt.datetime.now(dt.timezone.utc).strftime('%y%m%d%H%M%S')+secrets.token_hex(4).upper()
        response=self._request('POST','/snap/v1/transactions',{'transaction_details':{'order_id':invoice,'gross_amount':amount},
            'enabled_payments':[channel]})
        url=str(response.get('redirect_url') or '')
        parsed=urllib.parse.urlparse(url)
        expected='app.sandbox.midtrans.com' if env=='sandbox' else 'app.midtrans.com'
        if parsed.scheme!='https' or parsed.hostname!=expected:
            raise RuntimeError('Midtrans tidak mengembalikan Checkout HTTPS yang sesuai environment.')
        with self.lock:
            self.ledger[invoice]={'invoice':invoice,'amount':amount,'status':'pending','created_at':time.time(),
                    'checked_at':0,'environment':env,'checkout_url':url,'consumed':False}
            self._save(self.ledger_path,self.ledger)
        return self.public_payment(invoice)

    def public_payment(self,invoice):
        with self.lock:
            item=self.ledger.get(str(invoice))
            if not item:raise ValueError('Invoice Midtrans tidak ditemukan.')
            return {**{k:item.get(k) for k in ('invoice','amount','status','checkout_url','created_at')},'provider':'midtrans'}

    def check(self,invoice,*,now=None):
        invoice=str(invoice or '')
        now=time.time() if now is None else now
        with self.lock:
            item=self.ledger.get(invoice)
            if not item:raise ValueError('Invoice Midtrans tidak ditemukan.')
            if item.get('status')=='paid':return self.public_payment(invoice)
            if item.get('environment')!=self.config.get('environment'):
                raise RuntimeError('Environment Midtrans berubah sejak invoice dibuat.')
            if now-item.get('checked_at',0)<5:return self.public_payment(invoice)
            item['checked_at']=now
            self._save(self.ledger_path,self.ledger)
        response=self._request('GET','/v2/'+urllib.parse.quote(invoice,safe='')+'/status')
        state=str(response.get('transaction_status') or '').lower()
        if state=='pending':return self.public_payment(invoice)
        if str(response.get('order_id') or '')!=invoice:
            raise RuntimeError('Order ID Midtrans tidak sesuai invoice.')
        try:
            amount=Decimal(str(response['gross_amount']))
            expected=Decimal(str(item['amount']))
            if not amount.is_finite() or amount!=expected:raise ValueError('nominal berbeda')
        except (KeyError,TypeError,InvalidOperation,ValueError):
            raise RuntimeError('Nominal Midtrans tidak cocok atau kosong; sesi tetap terkunci.')
        with self.lock:
            item=self.ledger[invoice]
            if state in ('settlement','capture'):
                if str(response.get('status_code') or '')!='200' or str(response.get('fraud_status') or 'accept').lower()!='accept':
                    raise RuntimeError('Midtrans belum mengonfirmasi pembayaran dengan status dan fraud check yang valid.')
                item['status']='paid'
                item['paid_at']=now
            elif state in ('expire','cancel','deny','failure'):
                item['status']='expired' if state=='expire' else 'failed'
            self._save(self.ledger_path,self.ledger)
        return self.public_payment(invoice)

    def consume_paid(self,invoice):
        with self.lock:
            item=self.ledger.get(str(invoice))
            if not item or item.get('status')!='paid' or item.get('consumed'):
                raise ValueError('Pembayaran Midtrans belum terverifikasi atau invoice sudah digunakan.')
            item['consumed']=True
            item['consumed_at']=time.time()
            self._save(self.ledger_path,self.ledger)
        return True
