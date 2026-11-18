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
import zipfile

from fastapi import Depends, HTTPException, Query, Request
from fastapi.responses import FileResponse, HTMLResponse, Response, StreamingResponse
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
            'url':public_origin+'/session/'+row['token'],
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

    @app.post('/api/agent/gallery/preferences')
    def agent_save_gallery_preferences(body:BoothPreference,b=Depends(agent_auth)):
        # A licensed booth may change only its own storage preference.
        if body.booth_id != b['id']:
            raise HTTPException(403,'Booth tidak sesuai dengan lisensi perangkat.')
        if body.share=='web' and body.mode not in ('web','both'):
            raise HTTPException(400,'Aktifkan penyimpanan Web sebelum memilih QR Web.')
        with transaction() as db:
            db.execute('''INSERT INTO gallery_preferences(booth_id,mode,share) VALUES(?,?,?)
                    ON CONFLICT(booth_id) DO UPDATE SET mode=excluded.mode,share=excluded.share''',
                    (b['id'],body.mode,body.share))
        return {'ok':True,'mode':body.mode,'share':body.share}

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

    def _archive_items(row):
        """Expose only recognized files from an uploaded ZIP without extracting paths."""
        archive=_safe_file(row,'archive')
        if not archive:return []
        items=[]
        try:
            with zipfile.ZipFile(archive) as z:
                for info in z.infolist():
                    if len(items)>=80:break
                    if info.is_dir() or info.file_size>150*1024*1024:continue
                    name=info.filename.replace('\\','/')
                    basename=name.rsplit('/',1)[-1]
                    lower=name.lower()
                    if (lower.startswith('foto original/') or lower.startswith('photos/')) and basename.lower().endswith(('.jpg','.jpeg')):
                        category='original';mime='image/jpeg';label='Foto Original'
                    elif (lower.startswith('frame/') or
                          (lower.startswith('final_results/') and basename.lower()=='hasil_frame.jpg')) and basename.lower().endswith(('.jpg','.jpeg')):
                        category='frame';mime='image/jpeg';label='Foto dalam Frame'
                    elif (lower.startswith('gif/') or (lower.startswith('final_results/') and basename.lower()=='gif_originals.gif')) and basename.lower().endswith('.gif'):
                        category='gif';mime='image/gif';label='GIF'
                    elif ((lower.startswith('live photo dalam frame/') and basename.lower().endswith('.mp4')) or
                          (lower.startswith('live_photos/') and basename.lower() in ('live_photo_frame.mp4','live_photo_frame.webm'))):
                        category='live';mime='video/webm' if basename.lower().endswith('.webm') else 'video/mp4';label='Live Photo'
                    else:continue
                    items.append({'filename':info.filename,'name':basename,'category':category,
                                  'label':label,'mime':mime,'bytes':info.file_size})
        except (OSError,zipfile.BadZipFile,RuntimeError):return []
        return items

    @app.get('/api/public/session/{token}/assets/{index}')
    def public_archive_asset(token:str,index:int):
        row,_,_=_token_lookup(token)
        items=_archive_items(row)
        if index<0 or index>=len(items):raise HTTPException(404,'File sesi tidak ditemukan.')
        item=items[index]
        archive=_safe_file(row,'archive')
        if not archive:raise HTTPException(404,'Arsip sesi belum tersedia.')
        def chunks():
            with zipfile.ZipFile(archive) as z:
                with z.open(item['filename']) as stream:
                    remaining=item['bytes']
                    while remaining>0:
                        block=stream.read(min(65536,remaining))
                        if not block:break
                        remaining-=len(block)
                        yield block
        return StreamingResponse(chunks(),media_type=item['mime'],
                 headers={'Cache-Control':'private,no-store','X-Content-Type-Options':'nosniff'})

    @app.get('/api/public/session/{token}/items')
    def public_archive_items(token:str):
        row,_,_=_token_lookup(token)
        items=_archive_items(row)
        return {'items':[{'label':item['label'],'category':item['category'],
                          'name':item['name'],'url':'/api/public/session/'+token+'/assets/'+str(i)}
                          for i,item in enumerate(items)]}

    @app.get('/session/{token}',response_class=HTMLResponse)
    @app.get('/api/public/session/{token}',response_class=HTMLResponse)
    def public_session(token:str):
        row,brand,owner_id=_token_lookup(token)
        label=html.escape(brand['title'])
        sub=html.escape(brand['subtitle'])
        accent=brand['accent'] if COLOR_RE.fullmatch(brand['accent']) else '#375EDB'
        session_label=html.escape(row['event_name'] or 'Hasil Foto & Video')
        public_url=public_origin+'/session/'+token
        items=_archive_items(row)
        cards=[]
        for idx,item in enumerate(items):
            kind=item['category']
            src='/api/public/session/'+token+'/assets/'+str(idx)
            if kind=='live':
                view='<video controls playsinline preload="metadata" src="'+src+'"></video>'
            else:
                view='<img loading="lazy" alt="'+html.escape(item['label'])+'" src="'+src+'">'
            cards.append('<article class="media-card" data-kind="'+kind+'">'+
                         '<div class="media-preview">'+view+'</div>'+
                         '<div class="media-info"><b>'+html.escape(item['label'])+'</b>'+
                         '<span>'+html.escape(item['name'])+'</span>'+
                         '<a class="download" download href="'+src+'">↓ Unduh</a></div></article>')
        if not items and _safe_file(row,'preview'):
            src='/api/public/session/'+token+'/media'
            cards.append('<article class="media-card" data-kind="frame"><div class="media-preview">'+
                         '<img alt="Foto dalam Frame" src="'+src+'"></div><div class="media-info"><b>Foto dalam Frame</b>'+
                         '<a class="download" download href="'+src+'">↓ Unduh</a></div></article>')
        if row['mode']=='VIDEO' and _safe_file(row,'video'):
            src='/api/public/session/'+token+'/media'
            cards.append('<article class="media-card" data-kind="video"><div class="media-preview">'+
                         '<video controls playsinline src="'+src+'"></video></div><div class="media-info"><b>Video Sesi</b>'+
                         '<a class="download" href="'+src+'" download>↓ Unduh Video</a></div></article>')
        if not cards:
            cards.append('<div class="empty">File sesi sedang dipersiapkan. Muat ulang setelah beberapa saat.</div>')
        logo=('<img class="brand-logo" alt="Logo Studio" src="/api/public/brand/'+html.escape(owner_id)+'/logo">'
              if brand['logo_mime'] else '<div class="brand-logo brand-fallback">K</div>')
        page="""<!doctype html><html lang="id"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>__BRAND__ — Hasil Sesi</title>
<style>
:root{--accent:__ACCENT__;--night:#111525;--panel:#22293a;--muted:#b5bfd3}
*{box-sizing:border-box}body{margin:0;background:linear-gradient(115deg,#7dbafa,#98d2ff);
font-family:system-ui,-apple-system,Segoe UI,Arial,sans-serif;color:white}
main{max-width:1040px;margin:0 auto;background:#141826;min-height:100vh;box-shadow:0 8px 60px #14204b35}
.hero{padding:42px 22px 55px;text-align:center;background:linear-gradient(125deg,#0b175d,#342b68)}
.brand-logo{width:88px;height:88px;object-fit:contain;margin:0 auto 16px;display:block}
.brand-fallback{display:grid;place-items:center;font-size:52px;font-weight:900}
h1{font-size:clamp(28px,4.5vw,46px);margin:12px 0 5px;letter-spacing:.3px}
.hero p{color:#e0defd;margin:8px 0}.session{background:#ffffff18;border:1px solid #ffffff36;border-radius:15px;
padding:16px;margin:20px auto 0;max-width:480px;font-size:13px;line-height:1.8}
.content{padding:38px clamp(16px,5vw,52px) 72px;text-align:center}
h2{font-size:clamp(22px,3vw,30px);margin:8px 0 14px}
.sub{color:#d1d7e9;font-size:15px;line-height:1.7}
.actions{display:flex;justify-content:center;gap:12px;flex-wrap:wrap;margin:26px 0 24px}
.button,.download{display:inline-flex;justify-content:center;align-items:center;text-decoration:none;color:#fff;
border:0;background:var(--accent);border-radius:12px;font-weight:700;padding:14px 20px;font-size:14px;cursor:pointer}
.button.alt{background:#2b3345}.filters{display:flex;gap:10px;flex-wrap:wrap;justify-content:center;margin:25px 0}
.filter{color:#eee;background:transparent;border:1px solid #596078;padding:11px 18px;border-radius:30px;cursor:pointer}
.filter.active{border-color:var(--accent);background:var(--accent);font-weight:700}
.message{background:linear-gradient(90deg,#fff2c6,#f8e79a);color:#874214;border-radius:13px;
padding:22px;margin:26px 0;font-size:15px}
.gallery{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:26px;text-align:left}
.media-card{background:#242c3b;border:1px solid #3a435b;border-radius:15px;overflow:hidden}
.media-card[hidden]{display:none}.media-preview{height:310px;background:#282469;display:flex;align-items:center;justify-content:center}
.media-preview img,.media-preview video{width:100%;height:100%;object-fit:contain}
.media-info{padding:15px;display:flex;gap:9px;flex-direction:column;font-size:14px}
.media-info span{color:var(--muted);font-size:12px;overflow-wrap:anywhere}
.media-info .download{width:100%;margin-top:7px}.empty{grid-column:1/-1;padding:55px;color:var(--muted)}
.privacy{color:#9ba5bf;margin:30px 0 0;font-size:12px;line-height:1.6}
@media(max-width:650px){.gallery{grid-template-columns:1fr}.media-preview{height:270px}
.hero{padding:30px 14px}.content{padding:26px 14px}.actions .button{flex:1}}
</style></head><body><main>
<header class="hero">__LOGO__<h1>__BRAND__</h1><p>__SUBTITLE__</p>
<div class="session"><strong>__SESSION_NAME__</strong><div>Sesi: __SESSION_ID__</div></div></header>
<section class="content"><h2>↓ Download Your Photos</h2>
<p class="sub">Terima kasih telah berfoto bersama kami! Lihat, putar, dan unduh hasil foto atau video pilihan Anda.</p>
<div class="actions"><a class="button" href="/api/public/session/__TOKEN__/download">↓ Download All Files</a>
<button type="button" class="button alt" id="shareLink">↗ Bagikan Link</button></div>
<div class="filters"><button class="filter active" data-filter="all">Semua</button>
<button class="filter" data-filter="frame">Foto Frame</button>
<button class="filter" data-filter="original">Original</button>
<button class="filter" data-filter="gif">GIF</button>
<button class="filter" data-filter="live">Live Photo</button>
<button class="filter" data-filter="video">Video</button></div>
<div class="message">♥ Pesan Spesial<br>Semoga momen indah ini menjadi kenangan yang berharga.</div>
<div class="gallery">__CARDS__</div>
<p class="privacy">Tautan ini bersifat privat: siapa pun yang memiliki link atau QR dapat melihat hasil sampai masa simpan berakhir.</p>
</section></main>
<script>
document.querySelectorAll('[data-filter]').forEach(b=>b.addEventListener('click',()=>{
 const category=b.dataset.filter;document.querySelectorAll('[data-filter]').forEach(x=>x.classList.toggle('active',x===b));
 document.querySelectorAll('.media-card').forEach(c=>c.hidden=category!=='all'&&c.dataset.kind!==category);
}));
document.getElementById('shareLink').addEventListener('click',async()=>{
 if(navigator.share){try{await navigator.share({title:document.title,url:location.href});return;}catch(e){}}
 try{await navigator.clipboard.writeText(location.href);alert('Link hasil berhasil disalin.');}
 catch(e){prompt('Salin link hasil:',location.href);}
});
</script></body></html>"""
        page=(page.replace('__ACCENT__',accent).replace('__BRAND__',label)
               .replace('__SUBTITLE__',sub).replace('__SESSION_NAME__',session_label)
               .replace('__SESSION_ID__',html.escape(row['session_id']))
               .replace('__LOGO__',logo).replace('__TOKEN__',token)
               .replace('__CARDS__',''.join(cards)))
        return HTMLResponse(page,headers={'Cache-Control':'private,no-store','Content-Security-Policy':
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
