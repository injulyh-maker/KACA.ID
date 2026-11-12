"""KACA.ID Cloud Control -- runnable multi-booth control-plane MVP.

Offline-first booth agents use an Ed25519 signed device-bound license and keep
camera + session data local. This server does NOT accept arbitrary OS commands.

For public deployment use HTTPS reverse proxy, a managed DB/backups, monitoring,
secret management, and a security review. SQLite is used for local testing.
"""
from __future__ import annotations

import argparse
import csv
import io
import base64
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import smtplib
import html
from email.message import EmailMessage
from urllib.parse import quote
import sqlite3
import sys
import threading
import time
import uuid
from contextlib import contextmanager

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, VerificationError
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from fastapi import FastAPI, Header, HTTPException, Request, Depends, Query
from fastapi.responses import FileResponse, HTMLResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, field_validator

ROOT = Path(__file__).resolve().parent
DATA = Path(os.getenv('KACA_CLOUD_DATA_DIR', str(ROOT / 'data'))).resolve()
DATA.mkdir(parents=True, exist_ok=True)
DB = DATA / 'cloud.sqlite3'
KEY_FILE = DATA / 'ed25519-private.pem'
PASSWORD = PasswordHasher(time_cost=2, memory_cost=65536, parallelism=2)
DATA_LOCK = threading.RLock()
ALLOWED_SETTINGS = {'sessionPrice','countdown','captureInterval','sessionMode',
                    'sessionDurationMinutes','enablePhotoMode','enableVideoMode',
                    'livePhotoEnabled','livePhotoDuration','printCopies','autoPrintEnabled',
                    'voucherEnabled','enableQrisPayment','dashboardTitle'}
SETTINGS_BOUNDS = {
    'sessionPrice': (0, 50000000), 'countdown': (1, 30),
    'captureInterval': (0, 30), 'sessionDurationMinutes': (1, 120),
    'livePhotoDuration': (3, 30), 'printCopies': (1, 10),
}
COMMANDS = {'settings.patch','voucher.create','ui.dashboard','ui.refresh','remote.request',
            'remote.click','remote.key','remote.text','remote.stop','camera.control'}
MAX_SNAPSHOT = 300_000
# Remote screen is opt-in at deployment; keep disabled for public releases.
REMOTE_ENABLED=os.getenv('KACA_CLOUD_REMOTE_ENABLED','0')=='1'
# Default reporting day is WITA (UTC+8); configurable for other booth regions.
REPORT_TZ_MINUTES = max(-720, min(840, int(os.getenv('KACA_CLOUD_REPORT_TZ_MINUTES','480'))))
def report_today():
    return dt.datetime.now(dt.timezone(dt.timedelta(minutes=REPORT_TZ_MINUTES))).date()


def sql():
    con = sqlite3.connect(str(DB), timeout=15, isolation_level=None)
    con.row_factory = sqlite3.Row
    con.execute('PRAGMA foreign_keys=ON')
    con.execute('PRAGMA busy_timeout=15000')
    return con


@contextmanager
def transaction():
    with DATA_LOCK:
        con=sql()
        try:
            con.execute('BEGIN IMMEDIATE')
            yield con
            con.execute('COMMIT')
        except Exception:
            try: con.execute('ROLLBACK')
            except Exception: pass
            raise
        finally: con.close()


@contextmanager
def closing_sql():
    con=sql()
    try: yield con
    finally: con.close()

def init_db():
    with DATA_LOCK:
        con=sql()
        try:
            con.executescript('''
        CREATE TABLE IF NOT EXISTS users (
          id TEXT PRIMARY KEY, email TEXT NOT NULL UNIQUE, name TEXT NOT NULL,
          password_hash TEXT NOT NULL, role TEXT NOT NULL DEFAULT 'user',
          created_at INTEGER NOT NULL
        );
        CREATE TABLE IF NOT EXISTS tokens (
          hash TEXT PRIMARY KEY, user_id TEXT NOT NULL REFERENCES users(id),
          expires_at INTEGER NOT NULL, created_at INTEGER NOT NULL
        );
        CREATE TABLE IF NOT EXISTS licenses (
          id TEXT PRIMARY KEY, owner_id TEXT NOT NULL REFERENCES users(id),
          code_hash TEXT NOT NULL UNIQUE, display_code TEXT NOT NULL,
          expires_at INTEGER NOT NULL, status TEXT NOT NULL DEFAULT 'active',
          booth_id TEXT UNIQUE, created_by TEXT NOT NULL, created_at INTEGER NOT NULL
        );
        CREATE TABLE IF NOT EXISTS booths (
          id TEXT PRIMARY KEY, owner_id TEXT NOT NULL REFERENCES users(id),
          license_id TEXT NOT NULL UNIQUE REFERENCES licenses(id),
          name TEXT NOT NULL, device_hash TEXT NOT NULL, secret_hash TEXT NOT NULL,
          online INTEGER NOT NULL DEFAULT 0, last_seen INTEGER NOT NULL DEFAULT 0,
          remote_until INTEGER NOT NULL DEFAULT 0, current_version TEXT,
          camera_caps TEXT NOT NULL DEFAULT '{}', created_at INTEGER NOT NULL
        );
        CREATE TABLE IF NOT EXISTS sessions (
          booth_id TEXT NOT NULL REFERENCES booths(id), session_id TEXT NOT NULL,
          finished_at TEXT, event_name TEXT, mode TEXT, payment_method TEXT,
          amount_idr INTEGER NOT NULL DEFAULT 0,
          verified_paid INTEGER NOT NULL DEFAULT 0,
          drive_url TEXT, photo_count INTEGER NOT NULL DEFAULT 0,
          thumb_jpeg BLOB, PRIMARY KEY(booth_id,session_id)
        );
        CREATE TABLE IF NOT EXISTS commands (
          id TEXT PRIMARY KEY, booth_id TEXT NOT NULL REFERENCES booths(id),
          author_id TEXT NOT NULL REFERENCES users(id), type TEXT NOT NULL,
          payload TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'pending',
          created_at INTEGER NOT NULL, updated_at INTEGER NOT NULL,
          result TEXT
        );
        CREATE TABLE IF NOT EXISTS vouchers (
          id TEXT PRIMARY KEY, booth_id TEXT NOT NULL REFERENCES booths(id),
          code TEXT NOT NULL, uses INTEGER NOT NULL, expires_at TEXT,
          created_by TEXT NOT NULL, created_at INTEGER NOT NULL
        );
        CREATE TABLE IF NOT EXISTS audit (
          id TEXT PRIMARY KEY, actor TEXT NOT NULL, action TEXT NOT NULL,
          booth_id TEXT, detail TEXT, created_at INTEGER NOT NULL
        );
        CREATE TABLE IF NOT EXISTS plans (
          days INTEGER PRIMARY KEY CHECK(days IN (30,90,365)),
          price_idr INTEGER NOT NULL DEFAULT 0, updated_at INTEGER NOT NULL DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS auth_mail_tokens (
          token_hash TEXT PRIMARY KEY, user_id TEXT NOT NULL REFERENCES users(id),
          purpose TEXT NOT NULL CHECK(purpose IN ('verify','reset')),
          expires_at INTEGER NOT NULL, created_at INTEGER NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_auth_mail_tokens_user ON auth_mail_tokens(user_id,purpose);
        CREATE TABLE IF NOT EXISTS snapshots (
          booth_id TEXT PRIMARY KEY REFERENCES booths(id), image BLOB,
          captured_at INTEGER NOT NULL
        );
        ''')
            for days in (30,90,365):
                con.execute('INSERT OR IGNORE INTO plans(days,price_idr,updated_at) VALUES(?,?,?)',(days,0,0))
            usercols=[x['name'] for x in con.execute('PRAGMA table_info(users)').fetchall()]
            if 'email_verified_at' not in usercols:
                # Existing production customers keep their access and all original data.
                con.execute('ALTER TABLE users ADD COLUMN email_verified_at INTEGER NOT NULL DEFAULT 1')
                con.execute('UPDATE users SET email_verified_at=? WHERE email_verified_at=1',(int(time.time()),))
            cols=[x['name'] for x in con.execute('PRAGMA table_info(booths)').fetchall()]
            if 'camera_caps' not in cols:con.execute("ALTER TABLE booths ADD COLUMN camera_caps TEXT NOT NULL DEFAULT '{}'")
        finally:
            con.close()


def unix() -> int: return int(time.time())
def uid() -> str: return uuid.uuid4().hex

def one(con, q, params=()):
    row=con.execute(q,params).fetchone()
    return dict(row) if row is not None else None


def many(con, q, params=()):
    return [dict(r) for r in con.execute(q,params).fetchall()]


def b64u(raw:bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b'=').decode('ascii')


def unb64u(s:str) -> bytes:
    return base64.urlsafe_b64decode(s+'='*(-len(s)%4))


def load_keys() -> Ed25519PrivateKey:
    if KEY_FILE.exists():
        return serialization.load_pem_private_key(KEY_FILE.read_bytes(),password=None)
    private=Ed25519PrivateKey.generate()
    pem=private.private_bytes(serialization.Encoding.PEM,
               serialization.PrivateFormat.PKCS8,serialization.NoEncryption())
    try:
        fd=os.open(KEY_FILE,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
        with os.fdopen(fd,'wb') as f:f.write(pem)
    except FileExistsError:
        return serialization.load_pem_private_key(KEY_FILE.read_bytes(),password=None)
    return private


def public_pem() -> str:
    return load_keys().public_key().public_bytes(
        serialization.Encoding.PEM,serialization.PublicFormat.SubjectPublicKeyInfo).decode()


def sign_license(payload:dict) -> str:
    body=b64u(json.dumps(payload,sort_keys=True,separators=(',',':')).encode())
    sig=b64u(load_keys().sign(body.encode()))
    return body+'.'+sig


def verify_license(token:str, public_key=None):
    body,sig=token.split('.')
    (public_key or load_keys().public_key()).verify(unb64u(sig),body.encode())
    payload=json.loads(unb64u(body))
    if payload.get('exp',0)<unix():raise ValueError('Lisensi kedaluwarsa')
    return payload


def hash_token(s):return hashlib.sha256(s.encode()).hexdigest()


def audit(con, actor, action, booth_id='', detail=''):
    con.execute('INSERT INTO audit VALUES(?,?,?,?,?,?)',
                (uid(),actor,action,booth_id,str(detail)[:1000],unix()))


init_db()
app=FastAPI(title='KACA.ID Cloud Control',version='0.9.90-publish-reference',docs_url='/developer/docs')
app.mount('/static',StaticFiles(directory=str(ROOT/'web')),name='static')

@app.middleware('http')
async def safe_response_headers(request:Request,call_next):
    response=await call_next(request)
    response.headers['X-Content-Type-Options']='nosniff'
    response.headers['Referrer-Policy']='strict-origin-when-cross-origin'
    response.headers['X-Frame-Options']='DENY'
    response.headers['Permissions-Policy']='camera=(), microphone=(), geolocation=()'
    if request.url.path.startswith('/api/'):
        response.headers['Cache-Control']='no-store'
    return response



@app.get('/favicon.ico', include_in_schema=False)
def favicon(): return FileResponse(str(ROOT/'web'/'favicon.ico'), media_type='image/x-icon')



@app.get('/',response_class=HTMLResponse)
def index():return (ROOT/'web'/'index.html').read_text('utf-8')


@app.get('/api/public/plans')
def public_plans():
    with closing_sql() as con:
        rows=many(con,'SELECT days,price_idr FROM plans ORDER BY days')
    return {'plans':[{'days':r['days'],'price_idr':r['price_idr'] if r['price_idr']>0 else None} for r in rows],
            'whatsapp':'6281934386108'}

class PlanPrice(BaseModel):
    days:int
    price_idr:int=Field(ge=0,le=1000000000)

@app.get('/paket',response_class=HTMLResponse)
def public_packages():
    return (ROOT/'web'/'paket.html').read_text('utf-8')

@app.get('/verifikasi-email',response_class=HTMLResponse)
def public_verify_email():return (ROOT/'web'/'verifikasi-email.html').read_text('utf-8')

@app.get('/reset-sandi',response_class=HTMLResponse)
def public_reset_password():return (ROOT/'web'/'reset-sandi.html').read_text('utf-8')

@app.get('/api/health')
def health():
    try:
        with closing_sql() as con:
            con.execute('SELECT 1').fetchone()
        return {'ok':True,'service':'KACA.ID Cloud Control','database':'ready','server_time':unix()}
    except sqlite3.Error:
        fail('Database Cloud Control tidak tersedia',503)


@app.get('/api/public-key')
def key_info():return {'algorithm':'Ed25519','public_key':public_pem()}


def fail(msg,code=400):raise HTTPException(code,msg)


def user_auth(authorization:str=Header(default='')):
    token=authorization.removeprefix('Bearer ').strip()
    if not token:fail('Silakan login',401)
    with closing_sql() as con:
        row=one(con,'''SELECT u.id,u.email,u.name,u.role FROM users u JOIN tokens t ON u.id=t.user_id
                        WHERE t.hash=? AND t.expires_at>?''',(hash_token(token),unix()))
    if not row:fail('Login kedaluwarsa',401)
    return row


def admin_auth(user=Depends(user_auth)):
    if user['role']!='superadmin':fail('Hanya Super Admin',403)
    return user


@app.get('/api/admin/plans')
def admin_plans(u=Depends(admin_auth)):
    with closing_sql() as con:return {'plans':many(con,'SELECT days,price_idr,updated_at FROM plans ORDER BY days')}

@app.post('/api/admin/plans')
def set_plan_price(body:PlanPrice,u=Depends(admin_auth)):
    if body.days not in (30,90,365):fail('Durasi paket tidak didukung',400)
    with transaction() as con:
        con.execute('UPDATE plans SET price_idr=?,updated_at=? WHERE days=?',(body.price_idr,unix(),body.days))
        audit(con,u['id'],'plan.price_updated',detail=f'{body.days} days')
    return {'ok':True,'days':body.days,'price_idr':body.price_idr}

def scope_booth(con, user, booth_id):
    booth=one(con,'SELECT * FROM booths WHERE id=?',(booth_id,))
    if not booth or (user['role']!='superadmin' and booth['owner_id']!=user['id']):
        fail('Booth tidak ditemukan / tidak memiliki akses',404)
    return booth


def agent_auth(x_booth_id:str=Header(default=''),x_booth_key:str=Header(default='')):
    if not x_booth_id or not x_booth_key:fail('Kredensial booth tidak ada',401)
    with closing_sql() as con:
        row=one(con,'SELECT b.*,l.status,l.expires_at FROM booths b JOIN licenses l ON b.license_id=l.id WHERE b.id=?',(x_booth_id,))
    if not row or row['status']!='active' or row['expires_at']<unix() or not secrets.compare_digest(row['secret_hash'],hash_token(x_booth_key)):
        fail('Kredensial booth tidak valid',401)
    return row


class Register(BaseModel):
    name:str=Field(min_length=2,max_length=90)
    email:str=Field(min_length=5,max_length=180)
    password:str=Field(min_length=10,max_length=256)

    @field_validator('email')
    @classmethod
    def email_format(cls,v):
        v=v.strip().lower()
        if not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+',v):raise ValueError('Alamat email tidak valid')
        return v

class Login(BaseModel):email:str;password:str
class EmailAddress(BaseModel):email:str=Field(min_length=5,max_length=180)
class MailToken(BaseModel):token:str=Field(min_length=30,max_length=256)
class ResetPassword(BaseModel):token:str=Field(min_length=30,max_length=256);password:str=Field(min_length=10,max_length=256)

PUBLIC_CLOUD_ORIGIN=os.getenv('KACA_CLOUD_PUBLIC_ORIGIN','https://kacastudio.id').rstrip('/')
EMAIL_GENERIC='Jika alamat email tersebut terdaftar, petunjuk akan dikirim apabila layanan email tersedia.'

def mail_enabled():
    return all(os.getenv(k) for k in ('KACA_SMTP_HOST','KACA_SMTP_FROM'))

def send_security_mail(destination:str,subject:str,content:str):
    if not mail_enabled(): fail('Layanan email belum dikonfigurasi oleh administrator.',503)
    msg=EmailMessage()
    msg['From']=os.environ['KACA_SMTP_FROM']
    msg['To']=destination
    msg['Subject']=subject
    msg.set_content(content)
    host=os.environ['KACA_SMTP_HOST'];port=int(os.getenv('KACA_SMTP_PORT','587'))
    username=os.getenv('KACA_SMTP_USERNAME','');password=os.getenv('KACA_SMTP_PASSWORD','')
    import ssl
    sslctx=ssl.create_default_context()
    if port==465:
        with smtplib.SMTP_SSL(host,port,timeout=15,context=sslctx) as smtp:
            if username:smtp.login(username,password)
            smtp.send_message(msg)
    else:
        with smtplib.SMTP(host,port,timeout=15) as smtp:
            smtp.ehlo();smtp.starttls(context=sslctx);smtp.ehlo()
            if username:smtp.login(username,password)
            smtp.send_message(msg)

def issue_mail_token(con,user_id,purpose):
    con.execute('DELETE FROM auth_mail_tokens WHERE user_id=? AND purpose=?',(user_id,purpose))
    raw=secrets.token_urlsafe(40)
    expiry=unix()+(86400 if purpose=='verify' else 1200)
    con.execute('INSERT INTO auth_mail_tokens VALUES(?,?,?,?,?)',(hash_token(raw),user_id,purpose,expiry,unix()))
    return raw

def limit_mail_request(con,email,purpose):
    # Limit email-based bursts without requiring an IP address database.
    row=one(con,'''SELECT mt.created_at FROM auth_mail_tokens mt JOIN users u ON mt.user_id=u.id
                 WHERE u.email=? AND mt.purpose=? ORDER BY mt.created_at DESC LIMIT 1''',(email,purpose))
    return bool(row and row['created_at'] > unix()-60)

class NewLicense(BaseModel):owner_email:str;days:int=Field(default=365,ge=1,le=1825)
class Activation(BaseModel):license_code:str;device_id:str=Field(min_length=12,max_length=255);name:str=Field(min_length=2,max_length=90)


def session_token(con,user_id):
    value=secrets.token_urlsafe(40)
    con.execute('INSERT INTO tokens VALUES(?,?,?,?)',(hash_token(value),user_id,unix()+30*86400,unix()))
    return value

@app.post('/api/auth/register')
def register(body:Register):
    if not mail_enabled():fail('Verifikasi email belum tersedia. Hubungi administrator Cloud.',503)
    with transaction() as con:
        if one(con,'SELECT id FROM users WHERE email=?',(body.email,)):fail('Email sudah digunakan',409)
        user_id=uid()
        con.execute('INSERT INTO users(id,email,name,password_hash,role,created_at,email_verified_at) VALUES(?,?,?,?,?,?,?)',
                    (user_id,body.email,body.name,PASSWORD.hash(body.password),'user',unix(),0))
        raw=issue_mail_token(con,user_id,'verify')
        audit(con,user_id,'account.created.pending_verification')
    link=f'{PUBLIC_CLOUD_ORIGIN}/verifikasi-email#token={quote(raw)}'
    try:send_security_mail(body.email,'Verifikasi akun KACA.ID',
        f'Halo {body.name},\n\nBuka tautan berikut untuk verifikasi akun Anda (berlaku 24 jam):\n{link}\n\nAbaikan email ini jika Anda tidak mendaftar.')
    except Exception:
        # Account stays pending. Resend endpoint can recover after SMTP is fixed.
        fail('Akun dibuat tetapi email belum terkirim. Gunakan Kirim Ulang Verifikasi.',503)
    return {'ok':True,'requires_verification':True,'message':'Periksa email dan verifikasi akun sebelum login.'}

@app.post('/api/auth/resend-verification')
def resend_verification(body:EmailAddress):
    email=body.email.strip().lower()
    if not mail_enabled():return {'ok':True,'message':EMAIL_GENERIC}
    with transaction() as con:
        u=one(con,'SELECT id,name,email,email_verified_at FROM users WHERE email=?',(email,))
        if not u or u['email_verified_at'] or limit_mail_request(con,email,'verify'):
            return {'ok':True,'message':EMAIL_GENERIC}
        raw=issue_mail_token(con,u['id'],'verify')
    try:send_security_mail(email,'Verifikasi akun KACA.ID',
        f'Halo {u["name"]},\n\nVerifikasi akun di:\n{PUBLIC_CLOUD_ORIGIN}/verifikasi-email#token={quote(raw)}\nBerlaku 24 jam.')
    except Exception:pass
    return {'ok':True,'message':EMAIL_GENERIC}

@app.post('/api/auth/verify-email')
def verify_email(body:MailToken):
    with transaction() as con:
        row=one(con,"SELECT user_id FROM auth_mail_tokens WHERE token_hash=? AND purpose='verify' AND expires_at>?",(hash_token(body.token),unix()))
        if not row:fail('Tautan verifikasi tidak valid atau kedaluwarsa',400)
        con.execute('UPDATE users SET email_verified_at=? WHERE id=?',(unix(),row['user_id']))
        con.execute("DELETE FROM auth_mail_tokens WHERE user_id=? AND purpose='verify'",(row['user_id'],))
        audit(con,row['user_id'],'account.email_verified')
    return {'ok':True,'message':'Email terverifikasi. Silakan login.'}

@app.post('/api/auth/forgot-password')
def forgot_password(body:EmailAddress):
    email=body.email.strip().lower()
    if not mail_enabled():return {'ok':True,'message':EMAIL_GENERIC}
    with transaction() as con:
        u=one(con,'SELECT id,name,email FROM users WHERE email=?',(email,))
        if not u or limit_mail_request(con,email,'reset'):return {'ok':True,'message':EMAIL_GENERIC}
        raw=issue_mail_token(con,u['id'],'reset')
        audit(con,u['id'],'password.reset_requested')
    try:send_security_mail(email,'Atur ulang sandi KACA.ID',
        f'Halo {u["name"]},\n\nBuka tautan berikut untuk mengganti sandi (berlaku 20 menit):\n{PUBLIC_CLOUD_ORIGIN}/reset-sandi#token={quote(raw)}\n\nJika Anda tidak meminta ini, abaikan email.')
    except Exception:pass
    return {'ok':True,'message':EMAIL_GENERIC}

@app.post('/api/auth/reset-password')
def reset_password(body:ResetPassword):
    with transaction() as con:
        row=one(con,"SELECT user_id FROM auth_mail_tokens WHERE token_hash=? AND purpose='reset' AND expires_at>?",(hash_token(body.token),unix()))
        if not row:fail('Tautan reset tidak valid atau kedaluwarsa',400)
        con.execute('UPDATE users SET password_hash=? WHERE id=?',(PASSWORD.hash(body.password),row['user_id']))
        con.execute("DELETE FROM auth_mail_tokens WHERE user_id=? AND purpose='reset'",(row['user_id'],))
        con.execute('DELETE FROM tokens WHERE user_id=?',(row['user_id'],))
        audit(con,row['user_id'],'password.reset_completed')
    return {'ok':True,'message':'Sandi berhasil diubah. Data booth, lisensi, dan sesi tidak berubah.'}

@app.post('/api/auth/login')
def login(body:Login):
    with transaction() as con:
        row=one(con,'SELECT * FROM users WHERE email=?',(body.email.strip().lower(),))
        if not row:fail('Email atau kata sandi tidak sesuai',401)
        try: ok=PASSWORD.verify(row['password_hash'],body.password)
        except (VerifyMismatchError,VerificationError):ok=False
        if not ok:fail('Email atau kata sandi tidak sesuai',401)
        if not row['email_verified_at']:fail('Email belum diverifikasi. Periksa email atau kirim ulang verifikasi.',403)
        token=session_token(con,row['id'])
        audit(con,row['id'],'account.login')
        return {'token':token,'user':{k:row[k] for k in ('id','email','name','role')}}

@app.post('/api/auth/logout')
def logout(authorization:str=Header(default=''),u=Depends(user_auth)):
    with transaction() as con:
        con.execute('DELETE FROM tokens WHERE hash=?',(hash_token(authorization.removeprefix('Bearer ').strip()),))
    return {'ok':True}

@app.get('/api/me')
def me(u=Depends(user_auth)):return u

@app.post('/api/admin/licenses')
def issue_license(body:NewLicense,u=Depends(admin_auth)):
    with transaction() as con:
        owner=one(con,'SELECT id FROM users WHERE email=?',(body.owner_email.strip().lower(),))
        if not owner:fail('Akun pelanggan belum terdaftar',404)
        code='KACA-'+secrets.token_hex(4).upper()+'-'+secrets.token_hex(5).upper()
        lid=uid()
        expiry=unix()+body.days*86400
        con.execute('INSERT INTO licenses VALUES(?,?,?,?,?,?,?,?,?)',
                    (lid,owner['id'],hash_token(code),code[:9]+'••••••',expiry,'active',None,u['id'],unix()))
        audit(con,u['id'],'license.issued',detail=lid)
        return {'id':lid,'code':code,'expires_at':expiry,'owner_email':body.owner_email}

class LicenseStatus(BaseModel):
    status:str
    @field_validator('status')
    @classmethod
    def check(cls,value):
        if value not in ('active','suspended'):raise ValueError('Status tidak didukung')
        return value


@app.get('/api/admin/licenses')
def admin_licenses(u=Depends(admin_auth)):
    with closing_sql() as con:
        return {'licenses':many(con,'''SELECT l.id,l.display_code,l.expires_at,l.status,l.booth_id,
                        l.created_at,u.email owner_email,b.name booth_name
                        FROM licenses l JOIN users u ON u.id=l.owner_id
                        LEFT JOIN booths b ON b.id=l.booth_id
                        ORDER BY l.created_at DESC LIMIT 1000''')}


@app.post('/api/admin/licenses/{license_id}/status')
def update_license_status(license_id:str,body:LicenseStatus,u=Depends(admin_auth)):
    with transaction() as con:
        lic=one(con,'SELECT * FROM licenses WHERE id=?',(license_id,))
        if not lic:fail('Lisensi tidak ditemukan',404)
        con.execute('UPDATE licenses SET status=? WHERE id=?',(body.status,license_id))
        if body.status=='suspended' and lic['booth_id']:
            # Stop agent authentication and interactive remote access on next request.
            con.execute('UPDATE booths SET remote_until=0 WHERE id=?',(lic['booth_id'],))
            con.execute("UPDATE commands SET status='failed',result='Lisensi ditangguhkan',updated_at=? WHERE booth_id=? AND status IN ('pending','delivered')",
                        (unix(),lic['booth_id']))
            con.execute('DELETE FROM snapshots WHERE booth_id=?',(lic['booth_id'],))
        audit(con,u['id'],'license.'+body.status,lic['booth_id'] or '',license_id)
        return {'ok':True,'status':body.status,'license_id':license_id,
                'notice':'Perubahan akses cloud berlaku segera. Lisensi offline pada perangkat yang tidak terhubung tetap berlaku hingga kedaluwarsa.'}


@app.get('/api/admin/users')
def admin_users(u=Depends(admin_auth)):
    with closing_sql() as con:return {'users':many(con,'SELECT id,name,email,role,created_at FROM users ORDER BY created_at DESC')}

@app.get('/api/licenses')
def licenses(u=Depends(user_auth)):
    with closing_sql() as con:
        q='SELECT id,display_code,expires_at,status,booth_id,created_at FROM licenses'
        if u['role']=='superadmin': return {'licenses':many(con,q+' ORDER BY created_at DESC')}
        return {'licenses':many(con,q+' WHERE owner_id=? ORDER BY created_at DESC',(u['id'],))}

@app.post('/api/booths/activate')
def activate(data:Activation,u=Depends(user_auth)):
    with transaction() as con:
        lic=one(con,'SELECT * FROM licenses WHERE code_hash=?',(hash_token(data.license_code.strip().upper()),))
        if not lic or lic['owner_id']!=u['id'] or lic['status']!='active' or lic['expires_at']<unix():
            fail('Kode lisensi tidak tersedia, bukan milik akun ini, atau kedaluwarsa',403)
        device_hash=hash_token(data.device_id)
        if lic['booth_id']:
            existing=one(con,'SELECT * FROM booths WHERE id=?',(lic['booth_id'],))
            if not existing or existing['device_hash']!=device_hash:
                fail('Lisensi sudah terikat pada perangkat lain',409)
            booth_id=existing['id']
            # Regenerate API key only after the same owner reauthenticates.
            key=secrets.token_urlsafe(40)
            con.execute('UPDATE booths SET secret_hash=?,name=? WHERE id=?',
                        (hash_token(key),data.name,booth_id))
        else:
            booth_id=uid();key=secrets.token_urlsafe(40)
            con.execute('INSERT INTO booths(id,owner_id,license_id,name,device_hash,secret_hash,created_at) VALUES(?,?,?,?,?,?,?)',
                        (booth_id,u['id'],lic['id'],data.name,device_hash,hash_token(key),unix()))
            con.execute('UPDATE licenses SET booth_id=? WHERE id=?',(booth_id,lic['id']))
        license_payload={'ver':1,'license_id':lic['id'],'booth_id':booth_id,'owner_id':u['id'],
                         'device_hash':device_hash,'iat':unix(),'exp':lic['expires_at'],'max_booths':1}
        audit(con,u['id'],'booth.activated',booth_id)
        return {'booth_id':booth_id,'booth_key':key,'offline_license':sign_license(license_payload),
                'license_public_key':public_pem(),'expires_at':lic['expires_at']}

@app.get('/api/booths')
def booths(u=Depends(user_auth)):
    with closing_sql() as con:
        q='''SELECT b.id,b.name,b.owner_id,b.last_seen,b.current_version,b.remote_until,
             l.expires_at AS license_expires_at, COUNT(s.session_id) AS visitors,
             COALESCE(SUM(CASE WHEN s.verified_paid=1 THEN s.amount_idr ELSE 0 END),0) AS revenue_idr
             FROM booths b JOIN licenses l ON l.id=b.license_id
             LEFT JOIN sessions s ON s.booth_id=b.id'''
        where='' if u['role']=='superadmin' else ' WHERE b.owner_id=?'
        group=' GROUP BY b.id ORDER BY b.created_at DESC'
        values=() if u['role']=='superadmin' else (u['id'],)
        rows=many(con,q+where+group,values)
        for r in rows:r['online']=r['last_seen']>unix()-90
        return {'booths':rows}

@app.get('/api/analytics')
def analytics(booth_id:str='',u=Depends(user_auth)):
    with closing_sql() as con:
        if booth_id:scope_booth(con,u,booth_id)
        q='''SELECT b.id booth_id,b.name,COUNT(s.session_id) visitors,
          COALESCE(SUM(CASE WHEN s.verified_paid=1 THEN s.amount_idr ELSE 0 END),0) revenue,
          COALESCE(SUM(CASE WHEN s.verified_paid=0 AND s.amount_idr>0 THEN s.amount_idr ELSE 0 END),0) estimated
          FROM booths b LEFT JOIN sessions s ON s.booth_id=b.id'''
        where=[];params=[]
        if u['role']!='superadmin':where.append('b.owner_id=?');params.append(u['id'])
        if booth_id:where.append('b.id=?');params.append(booth_id)
        if where:q+=' WHERE '+' AND '.join(where)
        rows=many(con,q+' GROUP BY b.id ORDER BY b.name',params)
        return {'totals':{'booths':len(rows),'visitors':sum(x['visitors'] for x in rows),
                          'revenue_idr':sum(x['revenue'] for x in rows),
                          'unverified_estimate_idr':sum(x['estimated'] for x in rows)},'per_booth':rows}

@app.get('/api/analytics/timeline')
def analytics_timeline(days:int=Query(default=30,ge=7,le=90),booth_id:str='',u=Depends(user_auth)):
    if days not in (7,30,90):fail('Periode harus 7, 30, atau 90 hari')
    today=report_today()
    first=today-dt.timedelta(days=days-1)
    with closing_sql() as con:
        if booth_id:scope_booth(con,u,booth_id)
        query='''SELECT substr(s.finished_at,1,10) day, COUNT(*) sessions,
              SUM(CASE WHEN s.mode='PHOTO' THEN 1 ELSE 0 END) photos,
              SUM(CASE WHEN s.mode='VIDEO' THEN 1 ELSE 0 END) videos,
              COALESCE(SUM(CASE WHEN s.verified_paid=1 THEN s.amount_idr ELSE 0 END),0) verified_revenue,
              COALESCE(SUM(CASE WHEN s.verified_paid=0 AND s.amount_idr>0 THEN s.amount_idr ELSE 0 END),0) estimate
              FROM sessions s JOIN booths b ON b.id=s.booth_id
              WHERE s.finished_at>=? AND s.finished_at<?'''
        params=[first.isoformat(), (today+dt.timedelta(days=1)).isoformat()]
        if u['role']!='superadmin':query+=' AND b.owner_id=?';params.append(u['id'])
        if booth_id:query+=' AND b.id=?';params.append(booth_id)
        results=many(con,query+' GROUP BY substr(s.finished_at,1,10) ORDER BY day',tuple(params))
    by_day={r['day']:r for r in results}
    dates=[]
    for step in range(days):
        day=(first+dt.timedelta(days=step)).isoformat()
        r=by_day.get(day,{})
        dates.append({'day':day,'sessions':r.get('sessions',0), 'photos':r.get('photos',0),
            'videos':r.get('videos',0),'verified_revenue_idr':r.get('verified_revenue',0),
            'estimated_idr':r.get('estimate',0)})
    return {'days':days,'booth_id':booth_id or None,'daily':dates,
            'note':'Tanggal dihitung dari tanggal sesi yang dikirim booth; pendapatan belum terverifikasi terpisah.'}


@app.get('/api/booths/{booth_id}/camera-capabilities')
def camera_capabilities(booth_id:str,u=Depends(user_auth)):
    with closing_sql() as con:
        b=scope_booth(con,u,booth_id)
        try: return {'cameras':json.loads(b.get('camera_caps') or '{}')}
        except (ValueError,TypeError):return {'cameras':{}}

def _session_filters(con,user,booth_id='',mode='',date_from='',date_to=''):
    clauses=[];params=[]
    if booth_id:
        scope_booth(con,user,booth_id)
        clauses.append('s.booth_id=?');params.append(booth_id)
    if user['role']!='superadmin':
        clauses.append('b.owner_id=?');params.append(user['id'])
    if mode:
        if mode not in ('PHOTO','VIDEO'):fail('Mode sesi tidak dikenal')
        clauses.append('s.mode=?');params.append(mode)
    for value,op in ((date_from,'>='),(date_to,'<=')):
        if value:
            try:
                parsed=dt.date.fromisoformat(value)
                if parsed.isoformat()!=value:raise ValueError('date must match ISO')
            except ValueError:fail('Tanggal harus YYYY-MM-DD')
            clauses.append('substr(s.finished_at,1,10) '+op+' ?');params.append(value)
    if date_from and date_to and date_from>date_to:fail('Tanggal awal harus sebelum tanggal akhir')
    return (' WHERE '+' AND '.join(clauses)) if clauses else '',tuple(params)


@app.get('/api/sessions')
def sessions(booth_id:str='',limit:int=Query(default=20,ge=1,le=200),
             offset:int=Query(default=0,ge=0,le=1000000),mode:str='',date_from:str='',date_to:str='',
             u=Depends(user_auth)):
    with closing_sql() as con:
        where,params=_session_filters(con,u,booth_id,mode,date_from,date_to)
        base=' FROM sessions s JOIN booths b ON b.id=s.booth_id'+where
        total=con.execute('SELECT COUNT(*)'+base,params).fetchone()[0]
        q='''SELECT s.booth_id,b.name booth_name,s.session_id,s.finished_at,s.event_name,s.mode,
             s.payment_method,s.amount_idr,s.verified_paid,s.drive_url,s.photo_count,
             CASE WHEN s.thumb_jpeg IS NOT NULL THEN 1 ELSE 0 END AS has_thumb'''+base
        rows=many(con,q+' ORDER BY s.finished_at DESC,s.session_id DESC LIMIT ? OFFSET ?',params+(limit,offset))
    return {'sessions':rows,'total':total,'limit':limit,'offset':offset,
            'has_more':offset+len(rows)<total}


def _safe_csv_value(value):
    text=str(value if value is not None else '').replace('\r',' ').replace('\n',' ')
    # Prevent spreadsheet formula injection when opening CSV with Excel.
    if text.lstrip().startswith(('=','+','-','@')):text="'"+text
    return text


@app.get('/api/sessions/export.csv')
def export_sessions(booth_id:str='',mode:str='',date_from:str='',date_to:str='',u=Depends(user_auth)):
    with closing_sql() as con:
        where,params=_session_filters(con,u,booth_id,mode,date_from,date_to)
        q='''SELECT b.name,s.session_id,s.finished_at,s.event_name,s.mode,s.payment_method,
              s.amount_idr,s.verified_paid,s.drive_url,s.photo_count
              FROM sessions s JOIN booths b ON b.id=s.booth_id'''+where
        rows=many(con,q+' ORDER BY s.finished_at DESC,s.session_id DESC LIMIT 10000',params)
    buffer=io.StringIO()
    writer=csv.writer(buffer,delimiter=';',lineterminator='\r\n')
    writer.writerow(('Booth','ID Sesi','Tanggal Selesai','Event','Mode','Metode Bayar',
                     'Nominal IDR','Terverifikasi','Tautan Google Drive','Jumlah Foto'))
    for r in rows:
        writer.writerow([_safe_csv_value(r[k]) for k in ('name','session_id','finished_at','event_name',
                          'mode','payment_method','amount_idr','verified_paid','drive_url','photo_count')])
    return Response(content=('\ufeff'+buffer.getvalue()).encode('utf-8'),media_type='text/csv; charset=utf-8',
        headers={'Content-Disposition':'attachment; filename="KACA-ID-Laporan-Sesi.csv"',
                 'Cache-Control':'private, no-store'})

@app.get('/api/sessions/{booth_id}/{session_id}/thumbnail')
def thumb(booth_id:str,session_id:str,u=Depends(user_auth)):
    with closing_sql() as con:
        scope_booth(con,u,booth_id)
        r=one(con,'SELECT thumb_jpeg FROM sessions WHERE booth_id=? AND session_id=?',(booth_id,session_id))
        if not r or r['thumb_jpeg'] is None:fail('Thumbnail belum disinkronkan',404)
        return Response(bytes(r['thumb_jpeg']),media_type='image/jpeg',headers={'Cache-Control':'private,no-store'})


class AgentSync(BaseModel):
    version:str=Field(default='',max_length=80)
    cameras:dict=Field(default_factory=dict)
    sessions:list[dict]=Field(default_factory=list,max_length=250)
    remote_until:int=0

@app.post('/api/agent/sync')
def agent_sync(body:AgentSync,b=Depends(agent_auth)):
    updated=0
    with transaction() as con:
        cams={}
        for angle in ('0','1'):
            raw=body.cameras.get(angle,{})
            if isinstance(raw,dict) and isinstance(raw.get('controls'),dict):
                cams[angle]={'open':bool(raw.get('open')),'controls':{
                  key:{k:v for k,v in val.items() if k in ('available','actual','min','max','step','note')}
                  for key,val in raw['controls'].items() if key in ('brightness','contrast','saturation','gain','exposure','white_balance','focus','sharpness','iso') and isinstance(val,dict)}}
        con.execute('UPDATE booths SET last_seen=?,current_version=?,remote_until=?,camera_caps=? WHERE id=?',
                    (unix(),body.version[:80],min(unix()+1200,max(0,body.remote_until)) if REMOTE_ENABLED else 0,json.dumps(cams),b['id']))
        for s in body.sessions:
            sid=str(s.get('id') or '')[:100]
            if not re.fullmatch(r'[A-Za-z0-9_-]{6,100}',sid):continue
            raw_date=str(s.get('finished_at') or s.get('created_at') or '')[:40]
            drive_url=str(s.get('drive_url') or '')[:512]
            if drive_url and not re.fullmatch(r'https://drive\.google\.com/[^\s<>]*',drive_url):drive_url=''
            price=max(0,min(50000000,int(s.get('amount_idr') or 0)))
            confirmed=int(s.get('verified_paid') is True)
            try:
                img=base64.b64decode(s.get('thumb_b64') or '',validate=True) if s.get('thumb_b64') else None
                if img and (len(img)>140000 or not img.startswith(b'\xff\xd8')):img=None
            except Exception:img=None
            con.execute('''INSERT INTO sessions(booth_id,session_id,finished_at,event_name,mode,payment_method,
                              amount_idr,verified_paid,drive_url,photo_count,thumb_jpeg)
                              VALUES(?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT(booth_id,session_id) DO UPDATE SET
                              finished_at=excluded.finished_at,event_name=excluded.event_name,
                              mode=excluded.mode,payment_method=excluded.payment_method,
                              amount_idr=excluded.amount_idr,verified_paid=excluded.verified_paid,
                              drive_url=excluded.drive_url,photo_count=excluded.photo_count,
                              thumb_jpeg=COALESCE(excluded.thumb_jpeg,sessions.thumb_jpeg)''',
                        (b['id'],sid,raw_date,str(s.get('event_name') or '')[:100],str(s.get('mode') or 'PHOTO')[:20],
                         str(s.get('payment_method') or '')[:40],price,confirmed,drive_url,
                         max(0,min(100,int(s.get('photo_count') or 0))),img))
            updated+=1
        cmds=many(con,"SELECT id,type,payload FROM commands WHERE booth_id=? AND status='pending'"+
             (" AND (type NOT LIKE 'remote.%' OR type='remote.stop')" if not REMOTE_ENABLED else "")+
             " ORDER BY created_at LIMIT 30",(b['id'],))
        # Mark delivered (not completed) so a disconnect can retry safely.
        for c in cmds:con.execute("UPDATE commands SET status='delivered',updated_at=? WHERE id=?",(unix(),c['id']))
        return {'ok':True,'accepted_sessions':updated,'server_time':unix(),
                'commands':[{'id':c['id'],'type':c['type'],'payload':json.loads(c['payload'])} for c in cmds]}

@app.get('/api/agent/commands')
def agent_commands(b=Depends(agent_auth)):
    with transaction() as con:
        # Redeliver commands without acknowledgement after 60s.
        con.execute("UPDATE commands SET status='pending' WHERE booth_id=? AND status='delivered' AND updated_at<?",(b['id'],unix()-60))
        cmds=many(con,"SELECT id,type,payload FROM commands WHERE booth_id=? AND status='pending'"+
             (" AND (type NOT LIKE 'remote.%' OR type='remote.stop')" if not REMOTE_ENABLED else "")+
             " ORDER BY created_at LIMIT 30",(b['id'],))
        for c in cmds:con.execute("UPDATE commands SET status='delivered',updated_at=? WHERE id=?",(unix(),c['id']))
        return {'commands':[{'id':c['id'],'type':c['type'],'payload':json.loads(c['payload'])} for c in cmds]}

class Ack(BaseModel): command_id:str;ok:bool;message:str=''
@app.post('/api/agent/commands/ack')
def ack(body:Ack,b=Depends(agent_auth)):
    with transaction() as con:
        con.execute("UPDATE commands SET status=?,result=?,updated_at=? WHERE id=? AND booth_id=?",
                    ('completed' if body.ok else 'failed',body.message[:500],unix(),body.command_id,b['id']))
        return {'ok':True}

class Snapshot(BaseModel):jpeg_b64:str=Field(max_length=450000)
@app.post('/api/agent/snapshot')
def agent_snapshot(body:Snapshot,b=Depends(agent_auth)):
    if not REMOTE_ENABLED:fail('Remote dinonaktifkan di Cloud',403)
    with transaction() as con:
        booth=one(con,'SELECT remote_until FROM booths WHERE id=?',(b['id'],))
        if not booth or booth['remote_until']<=unix():fail('Operator booth belum memberi izin remote',403)
        try:image=base64.b64decode(body.jpeg_b64,validate=True)
        except Exception:fail('JPEG tidak valid')
        if len(image)>MAX_SNAPSHOT or not image.startswith(b'\xff\xd8'):fail('Ukuran/format JPEG tidak valid')
        con.execute('''INSERT INTO snapshots VALUES(?,?,?) ON CONFLICT(booth_id)
                     DO UPDATE SET image=excluded.image,captured_at=excluded.captured_at''',
                    (b['id'],image,unix()))
        return {'ok':True}

@app.get('/api/booths/{booth_id}/preview')
def preview(booth_id:str,u=Depends(user_auth)):
    if not REMOTE_ENABLED:fail('Remote dinonaktifkan di Cloud',403)
    with closing_sql() as con:
        booth=scope_booth(con,u,booth_id)
        if booth['remote_until']<unix():fail('Operator belum memberi izin, atau izin berakhir',403)
        r=one(con,'SELECT image,captured_at FROM snapshots WHERE booth_id=?',(booth_id,))
        if not r or not r['image'] or r['captured_at']<unix()-20:fail('Tangkapan layar belum tersedia',404)
        return Response(bytes(r['image']),media_type='image/jpeg',headers={'Cache-Control':'private,no-store'})

class NewCommand(BaseModel):
    type:str
    payload:dict=Field(default_factory=dict)


def validate_command(t,p):
    if t not in COMMANDS:fail('Jenis perintah tidak diizinkan')
    if t=='settings.patch':
        if not p or any(k not in ALLOWED_SETTINGS for k in p):fail('Ada pengaturan yang tidak diizinkan')
        for k,v in p.items():
            if k in SETTINGS_BOUNDS:
                lo,hi=SETTINGS_BOUNDS[k]
                if isinstance(v,bool) or not isinstance(v,(int,float)) or not lo<=v<=hi:fail(f'Nilai {k} di luar batas')
            elif k in {'enablePhotoMode','enableVideoMode','livePhotoEnabled','autoPrintEnabled','voucherEnabled','enableQrisPayment'}:
                if not isinstance(v,bool):fail(f'{k} harus boolean')
            elif k=='sessionMode' and v not in ('fixed_count','timed'):fail('Mode sesi tidak valid')
            elif k=='dashboardTitle' and (not isinstance(v,str) or len(v)>80):fail('Judul tidak valid')
    if t=='voucher.create':
        if not re.fullmatch(r'[A-Za-z0-9_-]{4,35}',str(p.get('code') or '')):fail('Kode voucher tidak valid')
        if isinstance(p.get('uses'),bool) or not isinstance(p.get('uses'),int) or not 1<=p['uses']<=500:fail('Jumlah penggunaan voucher tidak valid')
    if t=='camera.control':
        if p.get('camera') not in (0,1) or p.get('key') not in ('brightness','contrast','saturation','gain','exposure','white_balance','focus','sharpness','iso'):
            fail('Kontrol kamera tidak diizinkan')
        if isinstance(p.get('value'),bool) or not isinstance(p.get('value'),(int,float)) or not -10000<=p['value']<=10000:
            fail('Nilai kontrol kamera di luar batas')
    if t=='remote.click':
        try:valid_position=(p.get('action') in ('down','up') and 0<=float(p.get('x',-1))<=1 and 0<=float(p.get('y',-1))<=1)
        except (TypeError,ValueError,OverflowError):valid_position=False
        if not valid_position:fail('Posisi remote tidak valid')
    if t=='remote.key' and p.get('key') not in ('Enter','Escape','Tab','Backspace','Up','Down','Left','Right'):fail('Tombol tidak diizinkan')
    if t=='remote.text' and (not isinstance(p.get('text'),str) or len(p['text'])>120 or any(ord(c)<32 for c in p['text'])):fail('Teks remote tidak valid')
    if len(json.dumps(p))>6000:fail('Payload terlalu besar')

@app.post('/api/booths/{booth_id}/commands')
def send_command(booth_id:str,body:NewCommand,u=Depends(user_auth)):
    if not REMOTE_ENABLED and body.type.startswith('remote.') and body.type!='remote.stop':fail('Remote dinonaktifkan di Cloud',403)
    validate_command(body.type,body.payload)
    with transaction() as con:
        b=scope_booth(con,u,booth_id)
        if body.type.startswith('remote.') and body.type not in ('remote.request','remote.stop') and b['remote_until']<unix():
            fail('Remote membutuhkan persetujuan operator booth',403)
        cmd=uid()
        con.execute('INSERT INTO commands(id,booth_id,author_id,type,payload,created_at,updated_at) VALUES(?,?,?,?,?,?,?)',
                    (cmd,booth_id,u['id'],body.type,json.dumps(body.payload),unix(),unix()))
        audit(con,u['id'],'command.'+body.type,booth_id,cmd)
        return {'ok':True,'command_id':cmd}

@app.get('/api/booths/{booth_id}/commands')
def command_history(booth_id:str,u=Depends(user_auth)):
    with closing_sql() as con:
        scope_booth(con,u,booth_id)
        return {'commands':many(con,'SELECT id,type,status,result,created_at FROM commands WHERE booth_id=? ORDER BY created_at DESC LIMIT 40',(booth_id,))}

@app.get('/api/audit')
def audit_log(limit:int=Query(default=50,le=200),u=Depends(admin_auth)):
    with closing_sql() as con:return {'items':many(con,'SELECT * FROM audit ORDER BY created_at DESC LIMIT ?',(limit,))}


def create_superadmin(email,name,password):
    if len(password)<12:raise ValueError('Admin password minimal 12 karakter')
    email=email.strip().lower()
    with transaction() as con:
        if one(con,'SELECT id FROM users WHERE email=?',(email,)):
            raise ValueError('Email sudah terdaftar')
        user_id=uid()
        con.execute('INSERT INTO users(id,email,name,password_hash,role,created_at,email_verified_at) VALUES(?,?,?,?,?,?,?)',(user_id,email,name,PASSWORD.hash(password),'superadmin',unix(),unix()))
    print(f'Super Admin created: {email}')


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    subs=parser.add_subparsers(dest='command')
    admin=subs.add_parser('init-admin');admin.add_argument('--email',required=True);admin.add_argument('--name',default='KACA Admin')
    args=parser.parse_args()
    if args.command=='init-admin':
        import getpass
        pw=getpass.getpass('Password Super Admin (min 12 chars): ')
        create_superadmin(args.email,args.name,pw)
    else:
        print('Run: python -m uvicorn cloud_control.server:app --host 127.0.0.1 --port 8086')
