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
 let config={},outbox={pending:{},synced:{}},remoteUntil=0,busy=false,lastError='',lastSync=0;
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
 try{outbox=JSON.parse(fs.readFileSync(outboxFile,'utf8'));if(!outbox.pending||!outbox.synced)throw Error('bad outbox')}catch{outbox={pending:{},synced:{}}}
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
 const status=()=>{const active=validOffline();const connected=active && lastSync>0 && Date.now()-lastSync<90000;return {connected,licenseActive:active,required:true,server:config.server||DEFAULT_CLOUD_ORIGIN,boothId:config.boothId||'',boothName:config.boothName||'',licenseExpires:config.licenseExpires||null,remoteUntil,shareThumbnails:!!config.shareThumbnails,lastSync,lastError};};
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
   const verified=(pay==='qris_doku'&&String(s.payment_verification||'').toLowerCase()==='success')||s.verified_paid===true;
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
 const screenshots=setInterval(()=>{void snapshot()},4000);
 tick.unref?.();screenshots.unref?.();
 setTimeout(()=>{void sync()},3500);
 return {status,sync,openActivation,stop:()=>{clearInterval(tick);clearInterval(screenshots)},validOffline};
}
module.exports={initCloudAgent,verifyLicense,hardwareId};
