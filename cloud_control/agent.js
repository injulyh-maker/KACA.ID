/* KACA.ID Cloud Agent (Electron main process)
 * - Offline-first sync: no dependency on internet while booth captures photos.
 * - Signed Ed25519 offline license, account+device bound.
 * - Remote viewing/control only after explicit local operator confirmation.
 * - No arbitrary shell, filesystem or unrestricted OS desktop control.
 */
'use strict';
const fs=require('fs'),path=require('path'),os=require('os'),crypto=require('crypto');
const DEFAULT_CLOUD_ORIGIN='https://kacastudio.id';
const http=require('http'),https=require('https'),{execFileSync}=require('child_process');
const {BrowserWindow,dialog,ipcMain,nativeImage}=require('electron');

const ALLOWED_KEYS=new Set(['sessionPrice','countdown','captureInterval','sessionMode','sessionDurationMinutes',
 'enablePhotoMode','enableVideoMode','livePhotoEnabled','livePhotoDuration','printCopies',
 'autoPrintEnabled','voucherEnabled','enableQrisPayment','dashboardTitle']);
const REMOTE_CODES={Enter:'Return',Escape:'Escape',Tab:'Tab',Backspace:'Backspace',Up:'Up',Down:'Down',Left:'Left',Right:'Right'};
const WAIT=ms=>new Promise(r=>setTimeout(r,ms));
const hash=text=>crypto.createHash('sha256').update(String(text)).digest('hex');
const b64url=s=>Buffer.from(s.replace(/-/g,'+').replace(/_/g,'/'),'base64');

function httpJSON(url,{method='GET',headers={},json=null,timeout=10000,raw=false}={}){
 return new Promise((resolve,reject)=>{
  const u=new URL(url),localhost=(u.hostname==='127.0.0.1'||u.hostname==='localhost');
  if(!(u.protocol==='https:'||(localhost&&u.protocol==='http:')))return reject(Error('Cloud hanya boleh HTTPS (localhost boleh HTTP untuk pengujian)'));
  const content=json===null?null:Buffer.from(JSON.stringify(json));
  const req=(u.protocol==='https:'?https:http).request(u,{method,timeout,headers:{'Accept':'application/json',...(content?{'Content-Type':'application/json','Content-Length':content.length}:{}),...headers}},res=>{
    const buffers=[];let size=0;
    res.on('data',c=>{size+=c.length;if(size>2*1024*1024){req.destroy(Error('Respons terlalu besar'));return;}buffers.push(c)});
    res.on('end',()=>{try{const all=Buffer.concat(buffers);let data;if(raw)data=all;else data=JSON.parse(all.toString()||'{}');if(res.statusCode<200||res.statusCode>=300)throw Error(String(data.detail||data.error||`HTTP ${res.statusCode}`));resolve(data)}catch(e){reject(e)}});
  });
  req.on('timeout',()=>req.destroy(Error('Cloud timeout')));req.on('error',reject);req.end(content||undefined);
 });
}
function hardwareId(userDir){
 let machine='';
 if(process.platform==='win32'){
  try{const raw=execFileSync('reg.exe',['query','HKLM\\SOFTWARE\\Microsoft\\Cryptography','/v','MachineGuid'],{encoding:'utf8',timeout:2500,windowsHide:true});machine=(raw.match(/MachineGuid\s+REG_\w+\s+([^\s]+)/i)||[])[1]||'';}catch{}
 }
 if(!machine){const file=path.join(userDir,'cloud-device-id');try{machine=fs.readFileSync(file,'utf8').trim();}catch{machine=crypto.randomUUID();fs.writeFileSync(file,machine,{mode:0o600})}}
 return hash('kaca-cloud-device-v1:'+machine+':'+os.platform());
}
function verifyLicense(signed,pem,device){
 const parts=String(signed||'').split('.');if(parts.length!==2)throw Error('Lisensi digital tidak valid');
 if(!crypto.verify(null,Buffer.from(parts[0]),pem,b64url(parts[1])))throw Error('Tanda tangan lisensi tidak valid');
 const payload=JSON.parse(b64url(parts[0]).toString());
 if(payload.device_hash!==hash(device))throw Error('Lisensi tidak cocok dengan komputer ini');
 if(payload.exp*1000<Date.now())throw Error('Lisensi kadaluarsa');
 return payload;
}
function atomicJSON(file,obj){fs.mkdirSync(path.dirname(file),{recursive:true});const tmp=file+'.tmp';fs.writeFileSync(tmp,JSON.stringify(obj,null,2),{mode:0o600});fs.renameSync(tmp,file)}

function initCloudAgent({app,getMainWindow,readSettings,writeSettings,log}){
 const userDir=app.getPath('userData');const configFile=path.join(userDir,'kaca-cloud-agent.json');
 const outboxFile=path.join(userDir,'kaca-cloud-outbox.json');
 let config={},outbox={pending:{},synced:{}},remoteUntil=0,busy=false,webUploadBusy=false,lastError='',lastSync=0;
 let onRemoteFrame=null,remoteTimer=null,configWin=null,lastInput=0;
 try{config=JSON.parse(fs.readFileSync(configFile,'utf8'))}catch{}
 // Published installers require a valid signed license even when disconnected.
 // Migrate the deprecated localhost address without touching the existing
 // signed license, booth key, or the customer's media archive.
 config.required=true;
 if(!config.server || /^http:\/\/(?:127\.0\.0\.1|localhost):8086\/?$/i.test(config.server)){
   config.server=DEFAULT_CLOUD_ORIGIN;
  config._migratedCloudServer=true;
 }
 if(!config.lastObservedAt)config.lastObservedAt=0;
 try{outbox=JSON.parse(fs.readFileSync(outboxFile,'utf8'));if(!outbox.pending||!outbox.synced)throw Error('bad outbox')}catch{outbox={pending:{},synced:{}}}if(!outbox.webSynced||typeof outbox.webSynced!=='object')outbox.webSynced={};
 const deviceId=hardwareId(userDir);
 const save=()=>atomicJSON(configFile,config);
 if(config._migratedCloudServer){delete config._migratedCloudServer;save();}
 // Store a high-water timestamp so ordinary backdating of the Windows clock
 // does not silently revive an expired license. Fully offline clients cannot
 // offer a hardware-secure trusted clock; see release security notes.
 let lastClockPersisted=0;
 const validOffline=()=>{
  try{
   if(!config.offlineLicense||!config.publicKey)throw Error('Aktifkan lisensi melalui menu Lisensi KACA.ID (internet hanya untuk aktivasi awal).');
   const now=Math.floor(Date.now()/1000);
   if(now+300<Number(config.lastObservedAt||0))throw Error('Jam komputer mundur. Perbaiki tanggal/jam untuk memvalidasi lisensi.');
   const payload=verifyLicense(config.offlineLicense,config.publicKey,deviceId);
   if(now>Number(config.lastObservedAt||0)+300 && now-lastClockPersisted>300){
     config.lastObservedAt=now;lastClockPersisted=now;save();
   }
   return !!payload;
  }catch(e){lastError=e.message;return false;}
 };
 const status=()=>{const active=validOffline();const connected=active && lastSync>0 && Date.now()-lastSync<90000;return {connected,licenseActive:active,required:true,server:config.server||DEFAULT_CLOUD_ORIGIN,boothId:config.boothId||'',boothName:config.boothName||'',licenseExpires:config.licenseExpires||null,remoteUntil,shareThumbnails:!!config.shareThumbnails,storageMode:config.storageMode||'drive',shareProvider:config.shareProvider||'drive',lastSync,lastError};};
 const validServer=(value)=>{const u=new URL(String(value||''));if(!(u.protocol==='https:'||((u.hostname==='localhost'||u.hostname==='127.0.0.1')&&u.protocol==='http:')))throw Error('Server cloud harus HTTPS, kecuali localhost untuk uji');return u.origin;};
 const cloud=(route,opts)=>httpJSON(config.server+'/api'+route,{...opts,headers:{'X-Booth-Id':config.boothId||'','X-Booth-Key':config.boothKey||'',...(opts?.headers||{})}});
 async function activate({server,email,password,licenseCode,boothName}){
  const origin=validServer(server);
  if(!email||!password||!licenseCode||!boothName)throw Error('Email, password, lisensi, dan nama booth harus diisi');
  const login=await httpJSON(origin+'/api/auth/login',{method:'POST',json:{email,password}});
  if(!login.token)throw Error('Login Cloud membutuhkan verifikasi tambahan. Selesaikan autentikasi di Cloud sebelum aktivasi.');
  const r=await httpJSON(origin+'/api/booths/activate',{method:'POST',headers:{Authorization:'Bearer '+login.token},json:{license_code:licenseCode,device_id:deviceId,name:boothName}});
  if(config.publicKey && config.publicKey!==r.license_public_key)throw Error('Kunci server Cloud berbeda dengan yang sebelumnya. Hubungi admin untuk verifikasi.');
  const pinned=process.env.KACA_CLOUD_PINNED_PUBLIC_KEY;
  if(pinned && pinned.replace(/\\n/g,'\n')!==r.license_public_key)throw Error('Kunci publik server tidak cocok dengan KACA_CLOUD_PINNED_PUBLIC_KEY');
  verifyLicense(r.offline_license,r.license_public_key,deviceId);
  config={...config,server:origin,boothId:r.booth_id,boothKey:r.booth_key,offlineLicense:r.offline_license,publicKey:r.license_public_key,licenseExpires:r.expires_at,boothName,required:true,lastObservedAt:Math.max(Number(config.lastObservedAt||0),Math.floor(Date.now()/1000))};
  save();lastError='';log('info',`KACA.ID Cloud activated booth=${r.booth_id}`);getMainWindow()?.webContents?.send('cloud:settings-updated');void sync();return status();
 }
 async function localJSON(route,{method='GET',json=null}={}){
  return httpJSON('http://127.0.0.1:8765'+route,{method,json,timeout:4200});
 }
 async function sessionsFromLocal(){
  const response=await localJSON('/api/sessions');
  const samples=Array.isArray(response.sessions)?response.sessions:[];
  try{const videos=await localJSON('/api/cloud/video-sessions');
    if(Array.isArray(videos.sessions))samples.push(...videos.sessions);
  }catch{}
  for(const s of samples){
   const sid=String(s.id||'');if(!/^[A-Za-z0-9_-]{6,100}$/.test(sid))continue;
   const pay=String(s.payment_method||'');
   // Never infer financial income by guessing current settings for historic sessions.
   const known=Number(s.payment_amount_idr??s.payment_amount??s.amount_idr??0);
   const verified=(['qris_doku','qris_midtrans'].includes(pay)&&String(s.payment_verification||'').toLowerCase()==='success')||s.verified_paid===true;
   const item={id:sid,finished_at:s.finished_at||s.created_at||'',event_name:s.event_name||'',
      mode:s.session_type||s.mode||'PHOTO',payment_method:pay,
      amount_idr:Number.isFinite(known)?Math.max(0,Math.min(50000000,known)):0,
      verified_paid:verified,drive_url:s.drive_url||'',photo_count:Array.isArray(s.photos)?s.photos.length:0};
   if(config.shareThumbnails && s.output){
     try{const data=await httpJSON('http://127.0.0.1:8765/api/session/'+sid+'/output.jpg',{raw:true,timeout:2500});
       const img=nativeImage.createFromBuffer(data).resize({width:240});const buf=img.toJPEG(60);
       if(buf.length<140000)item.thumb_b64=buf.toString('base64');
     }catch{}
   }
   const fingerprint=hash(JSON.stringify(item));
   if(outbox.synced[sid]!==fingerprint){outbox.pending[sid]={data:item,fingerprint};}
  }
  const keys=Object.keys(outbox.synced);
  if(keys.length>15000)for(const k of keys.slice(0,keys.length-15000))delete outbox.synced[k];
  atomicJSON(outboxFile,outbox);
 }
 function busySession(){
  // Local backend may be offline or temporarily starting; defer modifying settings.
  return localJSON('/api/cloud/booth-state').then(s=>!!s.session_active).catch(()=>true);
 }
 async function applyCommand(c){
  const type=c.type,p=c.payload||{};
  const win=getMainWindow();
  switch(type){
   case 'settings.patch': {
    if(await busySession())throw Error('Sesi aktif atau kamera backend tidak siap; perintah ditunda');
    if(!Object.keys(p).length||Object.keys(p).some(k=>!ALLOWED_KEYS.has(k)))throw Error('Pengaturan tidak diizinkan');
    const old=readSettings();writeSettings({...old,...p});
    // Only refresh idle UI; do not terminate camera session or reset payment.
    if(win&&!win.isDestroyed())win.webContents.send('cloud:settings-updated');
    break;
   }
   case 'camera.control':{
    if(await busySession())throw Error('Sedang sesi aktif; pengaturan kamera ditunda');
    const angle=Number(p.camera),key=String(p.key||''),value=Number(p.value);
    if(![0,1].includes(angle)||!['brightness','contrast','saturation','gain','exposure','white_balance','focus','sharpness','iso'].includes(key)||!Number.isFinite(value))throw Error('Kontrol kamera tidak valid');
    const caps=await localJSON('/api/camera/controls/capabilities?camera='+angle);
    const control=caps.controls?.[key];
    if(!control?.available || value<Number(control.min) || value>Number(control.max))throw Error('Kamera/driver tidak mendukung nilai tersebut');
    const result=await localJSON('/api/camera/controls',{method:'POST',json:{camera:angle,values:{[key]:value}}});
    if(!result.results?.[key]?.applied && !result.controls?.[key]?.applied && !result[key]?.applied)throw Error('Driver tidak mengonfirmasi perubahan kamera');
    break;
   }
   case 'voucher.create':{
    if(await busySession())throw Error('Sesi masih aktif; voucher ditunda');
    const code=String(p.code||'').toUpperCase();const uses=Number(p.uses||1);
    if(!/^[A-Z0-9]{4,32}$/.test(code)||!Number.isInteger(uses)||uses<1||uses>500)throw Error('Voucher tidak valid');
    await localJSON('/api/vouchers/generate',{method:'POST',json:{count:1,max_uses:uses,custom_code:code,expiry_days:30}});
    break;
   }
   case 'ui.dashboard':
    if(await busySession())throw Error('Sedang melakukan sesi; tidak boleh mengalihkan halaman');
    if(win&&!win.isDestroyed())win.webContents.send('cloud:open-dashboard');break;
   case 'ui.refresh':
    if(await busySession())throw Error('Sesi aktif; tidak bisa refresh');
    if(win&&!win.isDestroyed())win.webContents.reloadIgnoringCache();break;
   case 'remote.request':{
    if(!win||win.isDestroyed())throw Error('Jendela KACA.ID belum aktif');
    const answer=await dialog.showMessageBox(win,{type:'question',title:'Permintaan Remote KACA.ID',
      message:'Pemilik akun Cloud ingin melihat dan mengontrol tampilan KACA.ID selama 15 menit.',
      detail:'Hanya jendela aplikasi KACA.ID, bukan seluruh desktop Windows. Aktivitas dapat dihentikan melalui Cloud Control di aplikasi.',
      buttons:['Tolak','Izinkan 15 Menit'],defaultId:0,cancelId:0,noLink:true});
    if(answer.response!==1)throw Error('Operator booth menolak permintaan remote');
    remoteUntil=Date.now()+15*60*1000;break;
   }
   case 'remote.stop':remoteUntil=0;break;
   case 'remote.click':{
    if(Date.now()>remoteUntil)throw Error('Izin remote tidak aktif');
    if(!win||win.isDestroyed())throw Error('Jendela booth tidak tersedia');
    if(Date.now()-lastInput<40)await WAIT(45);lastInput=Date.now();
    const width=win.webContents.getZoomFactor()?Math.floor(win.getContentSize()[0]):1000;
    const height=win.getContentSize()[1];
    const x=Math.round(Math.max(0,Math.min(1,Number(p.x)))*width),y=Math.round(Math.max(0,Math.min(1,Number(p.y)))*height);
    win.webContents.sendInputEvent({type:p.action==='up'?'mouseUp':'mouseDown',button:'left',x,y,clickCount:1});break;
   }
   case 'remote.key':{
    if(Date.now()>remoteUntil)throw Error('Izin remote tidak aktif');
    if(!REMOTE_CODES[p.key])throw Error('Tombol remote tidak didukung');
    if(!win||win.isDestroyed())throw Error('Jendela booth tidak tersedia');
    win.webContents.sendInputEvent({type:'keyDown',keyCode:REMOTE_CODES[p.key]});
    win.webContents.sendInputEvent({type:'keyUp',keyCode:REMOTE_CODES[p.key]});break;
   }
   case 'remote.text':{
    if(Date.now()>remoteUntil)throw Error('Izin remote tidak aktif');
    if(!win||win.isDestroyed())throw Error('Jendela booth tidak tersedia');
    if(typeof p.text!=='string'||p.text.length>120||/[\x00-\x1f]/.test(p.text))throw Error('Teks tidak diizinkan');
    win.webContents.insertText(p.text);break;
   }
   default:throw Error('Perintah remote tidak didukung');
  }
  return true;
 }
 async function processCommand(c){
  try{await applyCommand(c);await cloud('/agent/commands/ack',{method:'POST',json:{command_id:c.id,ok:true}})}
  catch(e){
   const retry=String(e.message||'').includes('ditunda');
   // To protect idempotency, fail and let the admin reissue after the session.
   await cloud('/agent/commands/ack',{method:'POST',json:{command_id:c.id,ok:false,message:String(e.message||e).slice(0,300)}}).catch(()=>{});
   log('warn',`Cloud command ${c.type} ${retry?'deferred':'failed'}: ${e.message}`);
  }
 }

 // Stream large session files from the local backend to Cloud without buffering
 // videos in Electron memory. Only fixed local routes and authenticated Cloud URLs.
 async function uploadLocalGalleryAsset(sid,kind,mode,eventName){
  const videoId=String(sid).replace(/^video-/,'');
  const route=kind==='preview'?(mode==='VIDEO'
       ?'/api/video/'+encodeURIComponent(videoId)+'/poster.jpg'
       :'/api/session/'+encodeURIComponent(sid)+'/output.jpg'):
      kind==='archive'?'/api/session/'+encodeURIComponent(sid)+'/download.zip':
      '/api/video/'+encodeURIComponent(videoId)+'.mp4';
  const limit={preview:20,archive:200,video:150}[kind]*1024*1024;
  const dest=config.server+'/api/agent/gallery/'+encodeURIComponent(sid)+'/upload?'+
      new URLSearchParams({kind,mode,event_name:String(eventName||'').slice(0,100)});
  return new Promise((resolve,reject)=>{
    let settled=false,localReq=null,post=null;
    const finish=(error,result)=>{
      if(settled)return;
      settled=true;
      if(error)reject(error);else resolve(result);
    };
    const localUrl='http://127.0.0.1:8765'+route;
    localReq=http.get(localUrl,{timeout:25000},res=>{
      if(res.statusCode!==200){
        res.resume();
        return finish(Error('File lokal belum tersedia: '+res.statusCode+' '+route));
      }
      const size=Number(res.headers['content-length']||0);
      if(size>limit){res.destroy();return finish(Error('File melewati batas upload Web '+kind));}
      const parsed=new URL(dest);
      post=(parsed.protocol==='https:'?https:http).request(parsed,{method:'POST',timeout:180000,
        headers:{'X-Booth-Id':config.boothId,'X-Booth-Key':config.boothKey,
          'Content-Type':'application/octet-stream',
          ...(size>0?{'Content-Length':size}:{}),'Accept':'application/json'}},reply=>{
        const chunks=[];let responseBytes=0;
        reply.on('data',chunk=>{responseBytes+=chunk.length;if(responseBytes<1024*1024)chunks.push(chunk);});
        reply.on('end',()=>{
          try{
            const result=JSON.parse(Buffer.concat(chunks).toString('utf8'));
            if(reply.statusCode<200||reply.statusCode>=300)throw Error(String(result.detail||result.error||reply.statusCode));
            finish(null,result);
          }catch(e){finish(e);}
        });
      });
      let sent=0;
      res.on('data',chunk=>{sent+=chunk.length;if(sent>limit){res.destroy(Error('File lokal melewati batas '+kind));post.destroy();}});
      res.on('error',e=>{post.destroy();finish(e)});
      post.on('timeout',()=>post.destroy(Error('Cloud upload timeout')));
      post.on('error',finish);
      res.pipe(post);
    });
    localReq.on('timeout',()=>localReq.destroy(Error('Local capture backend timeout')));
    localReq.on('error',finish);
  });
 }
 async function uploadGallerySessions(preferences,{videoOnly=false}={}){
  if(webUploadBusy||!['web','both'].includes(preferences.mode))return;
  webUploadBusy=true;
  try{
  const photos=await localJSON('/api/sessions').then(x=>x.sessions||[]).catch(()=>[]);
  const videos=await localJSON('/api/cloud/video-sessions').then(x=>x.sessions||[]).catch(()=>[]);
  // One upload per sync cycle to avoid stalling booth control and previews.
  const records=videoOnly?videos.map(x=>({...x,mode:'VIDEO'})):
    [...photos.filter(x=>x.status==='finished').map(x=>({...x,mode:'PHOTO'})),
    ...videos.map(x=>({...x,mode:'VIDEO'}))];
  // New sessions must receive their customer-facing link before historical backfill.
  const stamp=x=>{
    const value=x.finished_at||x.created_at||x.updated_at||'';
    if(typeof value==='number')return value;
    const n=Date.parse(String(value));return Number.isFinite(n)?n/1000:0;
  };
  records.sort((a,b)=>stamp(b)-stamp(a));
  for(const item of records){
    const sid=String(item.id||'');
    if(!/^[A-Za-z0-9_-]{6,100}$/.test(sid))continue;
    const video=item.mode==='VIDEO',kind=video?'video':'preview';
    const done=outbox.webSynced[sid]||{};
    // Retry local QR registration even when the Web media upload already succeeded.
    // Previously a transient local backend error left a permanent QR-less session.
    if(done.web_url && !done.qr_registered){
      try{
        const ack=await localJSON('/api/cloud/web-share',{method:'POST',json:{
          session_id:sid,video,url:done.web_url}});
        if(!ack.ok)throw Error(ack.error||'Gagal membuat QR Web');
        done.qr_registered=true;outbox.webSynced[sid]=done;atomicJSON(outboxFile,outbox);
      }catch(err){log('warn','Ulang QR hasil Web: '+err.message);}
    }
    if(done[kind]){
      if(!video&&!done.archive){
        try{
          // Wait for the final frame/Live Photo render before publishing the ZIP.
          // Otherwise the first archive can permanently miss the Live Photo.
          const render=await localJSON('/api/session/'+encodeURIComponent(sid)+'/render-status');
          if(render.render_status!=='ready'||(render.live_photo_enabled&&!render.live_output_available))
            break;
          await uploadLocalGalleryAsset(sid,'archive','PHOTO',item.event_name);
          outbox.webSynced[sid].archive=true;atomicJSON(outboxFile,outbox);
        }catch(err){log('warn','Arsip ZIP web ditunda: '+err.message);}
        break;
      }
      if(video&&!done.preview){
        try{
          await uploadLocalGalleryAsset(sid,'preview','VIDEO',item.event_name);
          outbox.webSynced[sid].preview=true;atomicJSON(outboxFile,outbox);
        }catch(err){log('warn','Thumbnail video web ditunda: '+err.message);}
        break;
      }
      continue;
    }
    try{
      const created=await uploadLocalGalleryAsset(sid,kind,item.mode,item.event_name);
      let qrRegistered=false;
      if(created.url){
        try{
          // QR is generated and persisted on the booth, never in the public server.
          const ack=await localJSON('/api/cloud/web-share',{method:'POST',json:{
            session_id:sid,video,url:created.url}});
          if(!ack.ok)throw Error(ack.error||'Gagal menyimpan tautan QR Web');
          qrRegistered=true;
        }catch(err){log('warn','QR Web akan dicoba ulang: '+err.message);}
      }
      outbox.webSynced[sid]={...done,[kind]:true,web_url:created.url,qr_registered:qrRegistered};
      atomicJSON(outboxFile,outbox);
    }catch(err){
      log('warn','Upload galeri web tertunda: '+String(err.message).slice(0,180));
    }
    break;
  }
  } finally {webUploadBusy=false;}
 }
 // Incremental Web upload: upload a new ZIP as soon as each original photo
 // has been persisted by the camera backend. Later revisions add the frame,
 // GIF and Live Photo to the SAME reserved session URL.
 async function uploadRealtimeGallery(){
  if(webUploadBusy||!validOffline()||!config.boothKey||
     !['web','both'].includes(config.storageMode||''))return;
  webUploadBusy=true;
  try{
   const progress=await localJSON('/api/cloud/gallery-progress');
   const sessions=Array.isArray(progress.sessions)?progress.sessions:[];
   for(const session of sessions){
    const sid=String(session.id||'');
    if(!/^[A-Za-z0-9_-]{6,100}$/.test(sid)||!session.revision)continue;
    const done=outbox.webSynced[sid]||{};
    if(done.archive_revision===session.revision)continue;
    try{
     const created=await uploadLocalGalleryAsset(sid,'archive','PHOTO',session.event_name);
     const next={...done,archive:true,archive_revision:session.revision,
                 web_url:created.url||done.web_url};
     outbox.webSynced[sid]=next;atomicJSON(outboxFile,outbox);
     if(next.web_url&&!next.qr_registered){
      try{
       const ack=await localJSON('/api/cloud/web-share',{method:'POST',json:{
         session_id:sid,video:false,url:next.web_url}});
       if(ack.ok&&ack.qr_available){
        next.qr_registered=true;outbox.webSynced[sid]=next;atomicJSON(outboxFile,outbox);
       }
      }catch(err){log('warn','QR Web foto akan dicoba lagi: '+err.message);}
     }
    }catch(err){
     log('warn','Upload foto Web real-time '+sid+': '+String(err.message).slice(0,180));
    }
    // Only one bounded ZIP transfer per poll; avoid saturation during capture.
    break;
   }
  }catch(err){log('warn','Polling foto Web real-time: '+String(err.message).slice(0,160));}
  finally{webUploadBusy=false;}
 }
 async function realtimeGalleryTick(){
  if(!validOffline()||!config.boothKey||!['web','both'].includes(config.storageMode||''))return;
  await uploadRealtimeGallery();
  // Completed video becomes playable only after MP4 finalization.
  if(!webUploadBusy){
   void uploadGallerySessions({mode:config.storageMode,share:config.shareProvider},{videoOnly:true})
    .catch(err=>log('warn','Sinkronisasi video Web: '+err.message));
  }
 }
 async function sync(){
  if(busy||!validOffline()||!config.server||!config.boothKey)return;
  busy=true;
  try{
   await sessionsFromLocal().catch(()=>{});
   const sessions=Object.values(outbox.pending).slice(0,150);
   const cameras={};
   for(const angle of [0,1]){
     try{cameras[String(angle)]=await localJSON('/api/camera/controls/capabilities?camera='+angle)}catch{}
   }
   const r=await cloud('/agent/sync',{method:'POST',json:{version:app.getVersion(),cameras,remote_until:Math.floor(remoteUntil/1000),sessions:sessions.map(x=>x.data)}});
   for(const {data,fingerprint} of sessions){const sid=data.id;if(outbox.pending[sid]?.fingerprint===fingerprint){delete outbox.pending[sid];outbox.synced[sid]=fingerprint;}}
   try{
     const preferences=await cloud('/agent/gallery/preferences');
     config.storageMode=preferences.mode||'local';config.shareProvider=preferences.share||'drive';save();
     await localJSON('/api/cloud/media-policy',{method:'POST',json:{mode:config.storageMode,share:config.shareProvider}});
     void uploadGallerySessions(preferences).catch(err=>log('warn','Sinkronisasi galeri web: '+err.message));
   }catch(e){log('warn','Sinkronisasi media web: '+e.message);}
   atomicJSON(outboxFile,outbox);lastSync=Date.now();lastError='';
   for(const c of r.commands||[])await processCommand(c);
   const next=await cloud('/agent/commands');
   for(const c of next.commands||[])await processCommand(c);
  }catch(e){lastError='Sinkronisasi offline: '+e.message;log('warn',lastError)}finally{busy=false;}
 }
 async function snapshot(){
  if(!validOffline()||Date.now()>remoteUntil||!config.server)return;
  const win=getMainWindow();if(!win||win.isDestroyed()||win.isMinimized())return;
  try{
   const image=await win.webContents.capturePage();
   const bytes=image.resize({width:850}).toJPEG(55);
   if(bytes.length>285000)return;
   await cloud('/agent/snapshot',{method:'POST',json:{jpeg_b64:bytes.toString('base64')}});
  }catch(e){log('warn',`Cloud preview unavailable: ${e.message}`)}
 }
 // Do not overwrite operational settings from the cloud unless the operator enables cloud control.
 // Reserve a stable Web session link during capture, before any media file is ready.
 async function reserveWebSession(sessionId,mode,eventName){
  if(!validOffline()||!config.boothId||!config.boothKey)return {enabled:false};
  const prefs=await cloud('/agent/gallery/preferences');
  if(!['web','both'].includes(prefs.mode)||prefs.share!=='web')return {enabled:false};
  const id=String(sessionId||'');
  if(!/^[A-Za-z0-9_-]{6,100}$/.test(id)||!['PHOTO','VIDEO'].includes(mode))throw Error('ID sesi tidak valid.');
  const reserved=await cloud('/agent/gallery/'+encodeURIComponent(id)+'/reserve?'+new URLSearchParams({mode,event_name:String(eventName||'').slice(0,100)}),{method:'POST'});
  if(!reserved.url)throw Error('Cloud tidak menyediakan tautan sesi.');
  outbox.webSynced[id]={...(outbox.webSynced[id]||{}),web_url:reserved.url,qr_registered:false};
  atomicJSON(outboxFile,outbox);
  const saved=await localJSON('/api/cloud/web-share',{method:'POST',json:{session_id:id,video:mode==='VIDEO',url:reserved.url}});
  if(!saved.ok||!saved.qr_available)throw Error(saved.error||'QR Web belum siap pada backend lokal.');
  outbox.webSynced[id].qr_registered=true;atomicJSON(outboxFile,outbox);
  return {enabled:true,url:reserved.url,qr_available:true};
 }
 ipcMain.handle('cloud:gallery-reserve',(_event,payload)=>reserveWebSession(payload?.sessionId,payload?.mode,payload?.eventName));
 ipcMain.handle('cloud:gallery-upload-now',()=>{
  // IPC request only triggers background work; never stall shutter or video UI.
  void realtimeGalleryTick().catch(err=>log('warn','Unggah sesi Web: '+err.message));
  return {ok:true,queued:true};
 });
 ipcMain.handle('cloud:gallery-preferences',async()=>{
  if(!validOffline()||!config.boothId||!config.boothKey)throw Error('Aktifkan lisensi Cloud untuk mengatur penyimpanan Web.');
  const remote=await cloud('/agent/gallery/preferences',{timeout:25000});
  config.storageMode=remote.mode;config.shareProvider=remote.share;save();
  return {mode:remote.mode,share:remote.share,boothId:config.boothId,boothName:config.boothName||''};
 });
 ipcMain.handle('cloud:gallery-save-preferences',async(_event,choice)=>{
  if(!validOffline()||!config.boothId||!config.boothKey)throw Error('Lisensi Cloud belum aktif.');
  const mode=String(choice?.mode||''),share=String(choice?.share||'');
  if(!['local','drive','web','both'].includes(mode)||!['drive','web'].includes(share))throw Error('Pilihan penyimpanan tidak valid.');
  if(share==='web'&&!['web','both'].includes(mode))throw Error('Untuk QR Web, aktifkan penyimpanan Web.');
  // Gallery uploads and SQLite writes may briefly delay API responses.
  // A POST timeout is ambiguous: first read back the persisted preference
  // before retrying, so we never report a successful write as definitely failed.
  let response;
  try{
    response=await cloud('/agent/gallery/preferences',{
      method:'POST',json:{booth_id:config.boothId,mode,share},timeout:30000});
  }catch(err){
    try{
      const current=await cloud('/agent/gallery/preferences',{timeout:20000});
      if(current.mode===mode&&current.share===share)response=current;
    }catch(checkError){log('warn','Verifikasi pengaturan Cloud: '+checkError.message);}
    if(!response)throw Error('Pengaturan belum terkonfirmasi di Cloud: '+err.message+'. Periksa koneksi VPS lalu gunakan Periksa Pengaturan Cloud.');
  }
  config.storageMode=response.mode;config.shareProvider=response.share;save();
  let localSynced=true;
  try{
    await localJSON('/api/cloud/media-policy',{
      method:'POST',json:{mode:response.mode,share:response.share}});
  }catch(localErr){
    localSynced=false;
    log('warn','Pengaturan tersimpan di Cloud, sinkronisasi backend lokal tertunda: '+localErr.message);
  }
  void sync();
  return {mode:response.mode,share:response.share,boothId:config.boothId,localSynced};
 });
 ipcMain.handle('cloud:status',()=>status());
 ipcMain.handle('cloud:assert-license',()=>{if(!validOffline())throw Error(lastError||'Lisensi tidak aktif.');return {ok:true,expires_at:config.licenseExpires};});
 ipcMain.handle('cloud:activate',(_event,data)=>activate(data));
 ipcMain.handle('cloud:share-thumbnails',(_event,enabled)=>{config.shareThumbnails=!!enabled;save();return status()});
 ipcMain.handle('cloud:stop-remote',()=>{remoteUntil=0;return status()});
 ipcMain.handle('cloud:open-activation',()=>openActivation());
 ipcMain.handle('cloud:sync-now',async()=>{await sync();return status()});
 async function openActivation(){
  if(configWin&&!configWin.isDestroyed()){configWin.show();configWin.focus();return;}
  configWin=new BrowserWindow({width:540,height:730,modal:true,parent:getMainWindow()||undefined,
   autoHideMenuBar:true,backgroundColor:'#0b1832',webPreferences:{preload:path.join(__dirname,'activate-preload.js'),contextIsolation:true,nodeIntegration:false,sandbox:true}});
  configWin.setMenuBarVisibility(false);
  // Allow closing this settings window. PHOTO/VIDEO remain separately license-gated.
  configWin.on('closed',()=>{configWin=null});
  await configWin.loadFile(path.join(__dirname,'activate.html'));
 }
 // Permit browsing Settings and activating from the dedicated License menu.
 // Session start is independently gated by cloud:assert-license.
 const tick=setInterval(()=>{void sync()},30000);
 const galleryTick=setInterval(()=>{void realtimeGalleryTick()},5000);
 const screenshots=setInterval(()=>{void snapshot()},4000);
 tick.unref?.();galleryTick.unref?.();screenshots.unref?.();
 setTimeout(()=>{void sync()},3500);
 return {status,sync,openActivation,stop:()=>{clearInterval(tick);clearInterval(galleryTick);clearInterval(screenshots)},validOffline};
}
module.exports={initCloudAgent,verifyLicense,hardwareId};
