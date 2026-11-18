"""Private owner gallery and opt-in public session sharing for KACA.ID Cloud.

Booth media uploads require a valid, unexpired booth credential. Public session
URLs contain a cryptographically random bearer token. Never expose listings
without the corresponding account or session token.
"""
import base64
import hashlib
import html
import json
import os
from pathlib import Path
import re
import secrets
import sqlite3
import time
import uuid

from fastapi import Depends, HTTPException, Query, Request
from fastapi.responses import FileResponse, HTMLResponse, Response
from pydantic import BaseModel, Field, field_validator

MODE_CHOICES={'local','drive','web','both'}
SHARE_CHOICES={'drive','web'}
MIME={'preview':'image/jpeg','archive':'application/zip','video':'video/mp4'}
EXT={'preview':'.jpg','archive':'.zip','video':'.mp4'}
MAX_BYTES={'preview':20*1024*1024,'archive':80*1024*1024,'video':150*1024*1024}
TOKEN_RE=re.compile(r'[A-Za-z0-9_-]{32,80}')
SESSION_RE=re.compile(r'[A-Za-z0-9_-]{6,100}')
COLOR_RE=re.compile(r'#[0-9a-fA-F]{6}')

class BrandConfig(BaseModel):
    title:str=Field(min_length=1,max_length=70)
    subtitle:str=Field(default='Hasil sesi foto & video',max_length=120)
    accent:str=Field(default='#375EDB')
    retention_days:int=Field(default=7,ge=1,le=365)
    logo_b64:str=Field(default='',max_length=600000)
    @field_validator('accent')
    @classmethod
    def valid_color(cls,v):
        if not COLOR_RE.fullmatch(v):raise ValueError('Warna harus #RRGGBB.')
        return v

class BoothPreference(BaseModel):
    booth_id:str=Field(min_length=16,max_length=64)
    mode:str
    share:str
    @field_validator('mode')
    @classmethod
    def valid_mode(cls,v):
        if v not in MODE_CHOICES:raise ValueError('Mode penyimpanan tidak valid.')
        return v
    @field_validator('share')
    @classmethod
    def valid_share(cls,v):
        if v not in SHARE_CHOICES:raise ValueError('Metode berbagi tidak valid.')
        return v

def attach_gallery(app, *, data, transaction, closing_sql, user_auth, agent_auth, scope_booth, unix, public_origin):
    media_root=(Path(data)/'gallery-media').resolve()
    media_root.mkdir(parents=True,exist_ok=True)
    with closing_sql() as db:
        db.executescript('''
        CREATE TABLE IF NOT EXISTS gallery_brands(
          owner_id TEXT PRIMARY KEY REFERENCES users(id),
          title TEXT NOT NULL DEFAULT 'KACA.ID',
          subtitle TEXT NOT NULL DEFAULT 'Hasil sesi foto & video',
          accent TEXT NOT NULL DEFAULT '#375EDB',
          retention_days INTEGER NOT NULL DEFAULT 7,
          logo BLOB, logo_mime TEXT
        );
        CREATE TABLE IF NOT EXISTS gallery_preferences(
          booth_id TEXT PRIMARY KEY REFERENCES booths(id) ON DELETE CASCADE,
          mode TEXT NOT NULL DEFAULT 'drive',
          share TEXT NOT NULL DEFAULT 'drive'
        );
        CREATE TABLE IF NOT EXISTS gallery_sessions(
          booth_id TEXT NOT NULL REFERENCES booths(id),
          session_id TEXT NOT NULL, token TEXT NOT NULL UNIQUE,
          mode TEXT NOT NULL, event_name TEXT NOT NULL DEFAULT '',
          created_at INTEGER NOT NULL, expires_at INTEGER NOT NULL,
          preview_path TEXT,preview_bytes INTEGER NOT NULL DEFAULT 0,
          archive_path TEXT,archive_bytes INTEGER NOT NULL DEFAULT 0,
          video_path TEXT,video_bytes INTEGER NOT NULL DEFAULT 0,
          PRIMARY KEY(booth_id,session_id)
        );
        CREATE INDEX IF NOT EXISTS idx_gallery_expiry ON gallery_sessions(expires_at);
        ''')

    def _prefs(db,booth_id):
        row=db.execute('SELECT mode,share FROM gallery_preferences WHERE booth_id=?',(booth_id,)).fetchone()
        return dict(row) if row else {'mode':'drive','share':'drive'}

    def _brand(db,owner_id):
        row=db.execute('SELECT title,subtitle,accent,retention_days,logo_mime FROM gallery_brands WHERE owner_id=?',(owner_id,)).fetchone()
        return dict(row) if row else {'title':'KACA.ID','subtitle':'Hasil sesi foto & video','accent':'#375EDB','retention_days':7,'logo_mime':None}

    def _row(db,booth_id,session_id):
        r=db.execute('SELECT * FROM gallery_sessions WHERE booth_id=? AND session_id=?',(booth_id,session_id)).fetchone()
        return dict(r) if r else None

    def _public(row):
        return {
            'booth_id':row['booth_id'],'session_id':row['session_id'],
            'mode':row['mode'],'event_name':row['event_name'],
            'created_at':row['created_at'],'expires_at':row['expires_at'],
            'url':public_origin+'/api/public/session/'+row['token'],
            'has_preview':bool(row['preview_path']),
            'has_archive':bool(row['archive_path']),
            'has_video':bool(row['video_path']),
            'bytes':sum(row[k] or 0 for k in ('preview_bytes','archive_bytes','video_bytes'))
        }

    def _safe_file(row,kind):
        path=row.get(kind+'_path')
        if not path:return None
        real=(media_root/path).resolve()
        if media_root not in real.parents or not real.is_file():return None
        return real

    def _delete_paths(row):
        for kind in MIME:
            p=_safe_file(row,kind)
            if p:
                try:p.unlink()
                except OSError:pass

    def _purge():
        with transaction() as db:
            expired=[dict(r) for r in db.execute('SELECT * FROM gallery_sessions WHERE expires_at<=?',(unix(),)).fetchall()]
            db.execute('DELETE FROM gallery_sessions WHERE expires_at<=?',(unix(),))
        for r in expired:_delete_paths(r)

    @app.get('/api/gallery/config')
    def gallery_config(u=Depends(user_auth)):
        with closing_sql() as db:
            booths=[dict(r) for r in db.execute(
                'SELECT id,name FROM booths'+('' if u['role']=='superadmin' else ' WHERE owner_id=?'),
                () if u['role']=='superadmin' else (u['id'],))]
            prefs=[{**r,**_prefs(db,r['id'])} for r in booths]
            brand=_brand(db,u['id'])
        return {'brand':brand,'booths':prefs}

    @app.post('/api/gallery/brand')
    def save_brand(body:BrandConfig,u=Depends(user_auth)):
        logo,logo_mime=None,None
        if body.logo_b64:
            try:logo=base64.b64decode(body.logo_b64,validate=True)
            except (ValueError,TypeError):raise HTTPException(400,'Logo bukan Base64.')
            if not logo or len(logo)>300000:raise HTTPException(413,'Logo maksimal 300 KB.')
            if logo.startswith(b'\x89PNG\r\n\x1a\n'):logo_mime='image/png'
            elif logo.startswith(b'\xff\xd8\xff'):logo_mime='image/jpeg'
            else:raise HTTPException(400,'Logo wajib PNG atau JPEG.')
        with transaction() as db:
            current=db.execute('SELECT logo,logo_mime FROM gallery_brands WHERE owner_id=?',(u['id'],)).fetchone()
            if logo is None and current:logo,logo_mime=current['logo'],current['logo_mime']
            db.execute('''INSERT INTO gallery_brands(owner_id,title,subtitle,accent,retention_days,logo,logo_mime)
                      VALUES(?,?,?,?,?,?,?) ON CONFLICT(owner_id) DO UPDATE SET
                      title=excluded.title,subtitle=excluded.subtitle,accent=excluded.accent,
                      retention_days=excluded.retention_days,logo=excluded.logo,logo_mime=excluded.logo_mime''',
                      (u['id'],body.title.strip(),body.subtitle.strip(),body.accent,body.retention_days,logo,logo_mime))
        return {'ok':True}

    @app.post('/api/gallery/preferences')
    def gallery_prefs(body:BoothPreference,u=Depends(user_auth)):
        with transaction() as db:
            scope_booth(db,u,body.booth_id)
            if body.mode not in ('web','both') and body.share=='web':
                raise HTTPException(400,'Penyimpanan web harus aktif sebelum memilih tautan web.')
            db.execute('''INSERT INTO gallery_preferences(booth_id,mode,share) VALUES(?,?,?)
                    ON CONFLICT(booth_id) DO UPDATE SET mode=excluded.mode,share=excluded.share''',
                    (body.booth_id,body.mode,body.share))
        return {'ok':True,**body.model_dump()}

    @app.get('/api/gallery')
    def gallery_list(booth_id:str='',limit:int=Query(default=24,ge=1,le=100),
                     offset:int=Query(default=0,ge=0,le=100000),
                     date_from:str='',date_to:str='',sort:str='newest',
                     u=Depends(user_auth)):
        _purge()
        if sort not in ('newest','oldest'):
            raise HTTPException(400,'Urutan galeri tidak valid.')
        from datetime import date,datetime,timezone,timedelta
        clauses=[]
        args=[]
        with closing_sql() as db:
            if booth_id:
                scope_booth(db,u,booth_id)
                clauses.append('g.booth_id=?')
                args.append(booth_id)
            elif u['role']!='superadmin':
                clauses.append('b.owner_id=?')
                args.append(u['id'])
            for key,value in (('from',date_from),('to',date_to)):
                if not value:continue
                try:
                    if not re.fullmatch(r'\d{4}-\d{2}-\d{2}',value):
                        raise ValueError('invalid date')
                    day=date.fromisoformat(value)
                    start=int(datetime.combine(day,datetime.min.time(),tzinfo=timezone.utc).timestamp())
                except ValueError:
                    raise HTTPException(400,'Tanggal galeri harus YYYY-MM-DD.')
                if key=='from':
                    clauses.append('g.created_at>=?')
                    args.append(start)
                else:
                    clauses.append('g.created_at<?')
                    args.append(start+86400)
            condition=' WHERE '+' AND '.join(clauses) if clauses else ''
            base=' FROM gallery_sessions g JOIN booths b ON b.id=g.booth_id'+condition
            stats=db.execute('SELECT COUNT(*),COALESCE(SUM(g.preview_bytes+g.archive_bytes+g.video_bytes),0)'+base,tuple(args)).fetchone()
            total,bytes_used=stats[0],stats[1]
            order='ASC' if sort=='oldest' else 'DESC'
            rows=db.execute('SELECT g.*,b.name booth_name'+base+
                            ' ORDER BY g.created_at '+order+' LIMIT ? OFFSET ?',tuple(args)+(limit,offset)).fetchall()
        return {'items':[{**_public(dict(r)),'booth_name':r['booth_name']} for r in rows],
                'total':total,'storage_used_bytes':bytes_used,
                'has_more':offset+len(rows)<total}

    @app.delete('/api/gallery/{booth_id}/{session_id}')
    def delete_gallery(booth_id:str,session_id:str,u=Depends(user_auth)):
        with transaction() as db:
            scope_booth(db,u,booth_id)
            row=_row(db,booth_id,session_id)
            if not row:raise HTTPException(404,'Sesi web tidak ditemukan.')
            db.execute('DELETE FROM gallery_sessions WHERE booth_id=? AND session_id=?',(booth_id,session_id))
        _delete_paths(row)
        return {'ok':True}

    @app.get('/api/gallery/{booth_id}/{session_id}/preview')
    def gallery_preview(booth_id:str,session_id:str,u=Depends(user_auth)):
        with closing_sql() as db:
            scope_booth(db,u,booth_id)
            row=_row(db,booth_id,session_id)
        if not row:raise HTTPException(404,'Sesi tidak ditemukan.')
        kind='preview' if row['preview_path'] else 'video'
        file=_safe_file(row,kind)
        if not file:raise HTTPException(404,'Media tidak tersedia.')
        return FileResponse(file,media_type=MIME[kind],headers={'Cache-Control':'private,no-store'})

    @app.get('/api/agent/gallery/preferences')
    def agent_gallery_config(b=Depends(agent_auth)):
        with closing_sql() as db:
            return {'ok':True,**_prefs(db,b['id'])}

    @app.post('/api/agent/gallery/{session_id}/upload')
    async def upload_gallery(session_id:str,request:Request,kind:str=Query(default='preview'),mode:str=Query(default='PHOTO'),
                             event_name:str=Query(default='',max_length=100),b=Depends(agent_auth)):
        if not SESSION_RE.fullmatch(session_id):raise HTTPException(400,'ID sesi tidak valid.')
        if kind not in MIME:raise HTTPException(400,'Jenis file tidak diperbolehkan.')
        if mode not in ('PHOTO','VIDEO'):raise HTTPException(400,'Mode sesi tidak valid.')
        with closing_sql() as db:
            prefs=_prefs(db,b['id'])
            brand=_brand(db,b['owner_id'])
            used=db.execute('''SELECT COALESCE(SUM(preview_bytes+archive_bytes+video_bytes),0)
                    FROM gallery_sessions WHERE booth_id=?''',(b['id'],)).fetchone()[0]
        if prefs['mode'] not in ('web','both'):raise HTTPException(403,'Penyimpanan web belum diaktifkan pemilik booth.')
        if used>=2*1024*1024*1024:raise HTTPException(507,'Kuota booth 2 GB tercapai.')
        dest_dir=(media_root/b['id']).resolve()
        dest_dir.mkdir(parents=True,exist_ok=True)
        tmp=dest_dir/(uuid.uuid4().hex+'.part')
        size=0
        try:
            with tmp.open('wb') as f:
                async for chunk in request.stream():
                    size+=len(chunk)
                    if size>MAX_BYTES[kind] or size+used>2*1024*1024*1024:
                        raise HTTPException(413,'File terlalu besar atau kuota booth habis.')
                    f.write(chunk)
            if size<32:raise HTTPException(400,'File hasil sesi terlalu kecil.')
            with tmp.open('rb') as f:head=f.read(16)
            if kind=='preview' and not head.startswith(b'\xff\xd8\xff'):raise HTTPException(400,'Preview wajib JPEG.')
            if kind=='archive' and not head.startswith(b'PK\x03\x04'):raise HTTPException(400,'Arsip wajib ZIP.')
            if kind=='video' and head[4:8]!=b'ftyp':raise HTTPException(400,'Video wajib MP4.')
            filename=session_id+'-'+kind+EXT[kind]
            dest=dest_dir/filename
            tmp.replace(dest)
            relative=str(dest.relative_to(media_root))
            with transaction() as db:
                row=_row(db,b['id'],session_id)
                if row:
                    db.execute('''UPDATE gallery_sessions SET
                        preview_path=CASE WHEN ?='preview' THEN ? ELSE preview_path END,
                        archive_path=CASE WHEN ?='archive' THEN ? ELSE archive_path END,
                        video_path=CASE WHEN ?='video' THEN ? ELSE video_path END,
                        preview_bytes=CASE WHEN ?='preview' THEN ? ELSE preview_bytes END,
                        archive_bytes=CASE WHEN ?='archive' THEN ? ELSE archive_bytes END,
                        video_bytes=CASE WHEN ?='video' THEN ? ELSE video_bytes END
                        WHERE booth_id=? AND session_id=?''',
                        (kind,relative,kind,relative,kind,relative,
                         kind,size,kind,size,kind,size,b['id'],session_id))
                else:
                    token=secrets.token_urlsafe(32)
                    days=brand['retention_days']
                    db.execute('''INSERT INTO gallery_sessions
                        (booth_id,session_id,token,mode,event_name,created_at,expires_at,
                        preview_path,preview_bytes,archive_path,archive_bytes,video_path,video_bytes)
                        VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)''',
                        (b['id'],session_id,token,mode,event_name[:100],unix(),unix()+days*86400,
                         relative if kind=='preview' else None,size if kind=='preview' else 0,
                         relative if kind=='archive' else None,size if kind=='archive' else 0,
                         relative if kind=='video' else None,size if kind=='video' else 0))
                saved=_row(db,b['id'],session_id)
            return {'ok':True,**_public(saved)}
        finally:
            try:tmp.unlink(missing_ok=True)
            except OSError:pass

    def _token_lookup(token):
        if not TOKEN_RE.fullmatch(token):raise HTTPException(404,'Sesi tidak ditemukan.')
        with closing_sql() as db:
            row=db.execute('SELECT * FROM gallery_sessions WHERE token=? AND expires_at>?',
                           (token,unix())).fetchone()
            if not row:raise HTTPException(404,'Tautan tidak tersedia atau sudah kedaluwarsa.')
            r=dict(row)
            booth=db.execute('SELECT owner_id,name FROM booths WHERE id=?',(r['booth_id'],)).fetchone()
            brand=_brand(db,booth['owner_id'])
            owner_id=booth['owner_id']
        return r,brand,owner_id

    @app.get('/session/{token}',response_class=HTMLResponse)
    @app.get('/api/public/session/{token}',response_class=HTMLResponse)
    def public_session(token:str):
        row,brand,owner_id=_token_lookup(token)
        label=html.escape(brand['title'])
        sub=html.escape(brand['subtitle'])
        color=brand['accent'] if COLOR_RE.fullmatch(brand['accent']) else '#375EDB'
        title=html.escape(row['event_name'] or 'Hasil Sesi')
        safe_token=html.escape(token)
        media=('video' if row['video_path'] and row['mode']=='VIDEO' else 'preview')
        if _safe_file(row,media):
            view=('<video controls playsinline preload="metadata" src="/api/public/session/'+safe_token+'/media"></video>'
                  if media=='video' else '<img alt="Hasil foto sesi" src="/api/public/session/'+safe_token+'/media">')
        else:view='<p>File hasil masih diproses.</p>'
        logo=('<img class="brand-logo" alt="Logo studio" src="/api/public/brand/'+html.escape(owner_id)+'/logo">'
              if brand['logo_mime'] else '')
        body=f'''<!doctype html><html lang="id"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{label} — Hasil Sesi</title>
<style>body{{font-family:system-ui,Arial,sans-serif;background:#f5f7fb;color:#101525;margin:0}}
main{{max-width:960px;margin:40px auto;padding:24px}}header{{text-align:center;margin-bottom:22px}}
.brand-logo{{width:88px;height:88px;object-fit:contain}}h1{{font-size:2rem;margin:10px 0}}
.small{{color:#62708a}}.card{{background:white;border:1px solid #dde3ee;border-radius:22px;padding:22px;text-align:center;box-shadow:0 8px 30px #1720360d}}
img:not(.brand-logo),video{{width:100%;max-height:70vh;object-fit:contain;border-radius:12px;background:#f1f3f9}}
.actions{{display:flex;justify-content:center;flex-wrap:wrap;gap:12px;margin-top:20px}}
a,button{{background:{color};color:white;border:0;border-radius:10px;padding:13px 20px;text-decoration:none;font-size:1rem;cursor:pointer}}
@media print{{header,.actions,.small{{display:none}}body{{background:white}}main,.card{{margin:0;padding:0;border:0;box-shadow:none}}img{{max-height:none}}}}
</style></head><body><main><header>{logo}<h1>{label}</h1><p class="small">{sub}</p></header>
<section class="card"><h2>{title}</h2>{view}
<div class="actions"><a href="/api/public/session/{safe_token}/download">Unduh Hasil</a><button onclick="window.print()">Cetak Foto</button></div>
<p class="small">Tautan privat: siapa pun yang menerima link/QR ini dapat melihat hasil sampai kedaluwarsa.</p>
</section></main></body></html>'''
        return HTMLResponse(body,headers={'Cache-Control':'no-store','Content-Security-Policy':
            "default-src 'none'; img-src 'self'; media-src 'self'; style-src 'unsafe-inline'; script-src 'unsafe-inline'; base-uri 'none'; form-action 'none'"})

    @app.get('/session-brand/{owner_id}/logo')
    @app.get('/api/public/brand/{owner_id}/logo')
    def brand_logo(owner_id:str):
        with closing_sql() as db:
            row=db.execute('SELECT logo,logo_mime FROM gallery_brands WHERE owner_id=?',(owner_id,)).fetchone()
        if not row or not row['logo']:raise HTTPException(404,'Logo belum tersedia.')
        return Response(content=bytes(row['logo']),media_type=row['logo_mime'],
                        headers={'Cache-Control':'public,max-age=300'})

    @app.get('/session/{token}/media')
    @app.get('/api/public/session/{token}/media')
    def public_media(token:str):
        row,_,_=_token_lookup(token)
        kind='video' if row['mode']=='VIDEO' and row['video_path'] else 'preview'
        file=_safe_file(row,kind)
        if not file:raise HTTPException(404,'Media sesi belum tersedia.')
        return FileResponse(file,media_type=MIME[kind],headers={'Cache-Control':'private,no-store'})

    @app.get('/session/{token}/download')
    @app.get('/api/public/session/{token}/download')
    def public_download(token:str):
        row,_,_=_token_lookup(token)
        kind='archive' if row['archive_path'] else ('video' if row['video_path'] else 'preview')
        file=_safe_file(row,kind)
        if not file:raise HTTPException(404,'File unduhan belum tersedia.')
        return FileResponse(file,filename='KACA-ID-'+row['session_id']+EXT[kind],
                            media_type=MIME[kind],headers={'Cache-Control':'private,no-store'})
