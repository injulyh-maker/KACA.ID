const { app, BrowserWindow, ipcMain, Menu } = require('electron');
const path = require('path');
const fs = require('fs');
const { spawn, execFileSync } = require('child_process');
const { dialog, shell } = require('electron');
const { pathToFileURL } = require('url');
const http = require('http');
const net = require('net');
const {initCloudAgent}=require('./cloud_control/agent');
let cloudAgent=null;
let backend = null;
let mainWindow = null;
// v0.9.67: recover a backend that unexpectedly exits (e.g. native camera driver).
let appClosing = false, backendRestartTimer = null, backendRestartCount = 0;
let backendRestarting = false, backendStartedAt = 0;
const MAX_BACKEND_RESTARTS = 5;
function scheduleBackendRecovery(reason){
  if(appClosing || backendRestartTimer || backendRestarting)return;
  if(Date.now()-backendStartedAt>120000)backendRestartCount=0;
  if(backendRestartCount>=MAX_BACKEND_RESTARTS){
    writeAppLog('fatal',`Backend failed repeatedly. Recovery stopped after ${MAX_BACKEND_RESTARTS} attempts. Inspect backend diagnostics, camera drivers and logs. Last: ${reason}`);
    return;
  }
  const delay=Math.min(8000,1000*Math.pow(2,backendRestartCount));backendRestartCount++;
  writeAppLog('warn',`Camera backend stopped unexpectedly (${reason}); scheduled recovery attempt ${backendRestartCount}/${MAX_BACKEND_RESTARTS} in ${delay}ms.`);
  backendRestartTimer=setTimeout(async()=>{
    backendRestartTimer=null;
    if(appClosing || backendRestarting)return;
    backendRestarting=true;
    let recoveryFailure=null;
    try{
      await startBackend();
      const ok=await waitBackend(15000);
      if(!ok){writeAppLog('error','Recovery process started but backend health did not become ready.');
        // If the process exited, the exit listener will schedule the next retry.
        if(!backend || backend.exitCode!==null) recoveryFailure='health not ready';}
      else writeAppLog('info','Camera backend recovery succeeded. Camera list may be refreshed now.');
    }catch(err){writeAppLog('error',`Backend recovery failed: ${err.stack||err.message}`);recoveryFailure=err.message;}
    finally{backendRestarting=false;if(recoveryFailure)scheduleBackendRecovery(recoveryFailure);}
  },delay);
}

const hasSingleInstanceLock = app.requestSingleInstanceLock();
if (!hasSingleInstanceLock) app.quit();
else app.on('second-instance', () => { if (mainWindow && !mainWindow.isDestroyed()) { if (mainWindow.isMinimized()) mainWindow.restore(); mainWindow.focus(); } });
const PORT = 8765;
const KACA_APP_ICON = path.join(__dirname, 'build', 'icon.png');
if (process.platform === 'win32') app.setAppUserModelId('id.kaca.photobooth');
function setWindowFullscreen(win, value) {
  if (!win || win.isDestroyed()) return false;
  const next = Boolean(value);
  if (win.isFullScreen() !== next) win.setFullScreen(next);
  return win.isFullScreen();
}
const dataFile = () => path.join(app.getPath('userData'), 'kaca-settings.json');
const logDir = () => path.join(app.getPath('userData'), 'logs');
const logFile = () => path.join(logDir(), 'kaca-app.log');
function writeAppLog(level, message) {
  try {
    fs.mkdirSync(logDir(), { recursive: true });
    const line = `[${new Date().toISOString()}] [${String(level).toUpperCase()}] ${String(message).replace(/[\r\n]+/g, ' ').slice(0, 5000)}\n`;
    try { if (fs.existsSync(logFile()) && fs.statSync(logFile()).size > 2 * 1024 * 1024) { for (let i=3;i>=1;i--) { const from=i===1?logFile():`${logFile()}.${i-1}`; const to=`${logFile()}.${i}`; if(fs.existsSync(from)){if(i===3)fs.rmSync(to,{force:true});fs.renameSync(from,to);} } } } catch {}
    fs.appendFileSync(logFile(), line, 'utf8');
  } catch {}
}
const originalConsoleLog=console.log.bind(console), originalConsoleError=console.error.bind(console);
console.log=(...args)=>{writeAppLog('info',args.join(' '));originalConsoleLog(...args);};
console.error=(...args)=>{writeAppLog('error',args.join(' '));originalConsoleError(...args);};
process.on('uncaughtException', error => { writeAppLog('fatal', error?.stack || error); process.exit(1); });
process.on('unhandledRejection', reason => { writeAppLog('error', reason?.stack || reason); });
ipcMain.on('app:renderer-log', (_event, entry) => { if(entry && typeof entry.message==='string') writeAppLog(entry.level||'error', `[renderer] ${entry.message}`); });
ipcMain.handle('app:logs-read', () => { try { const files=[logFile(),...Array.from({length:3},(_,i)=>`${logFile()}.${i+1}`)]; const chunks=files.filter(f=>fs.existsSync(f)).map(f=>fs.readFileSync(f,'utf8')); return chunks.join('\n').split(/\r?\n/).filter(Boolean).slice(-500); } catch(e) { return [`Gagal membaca log: ${e.message}`]; } });
ipcMain.handle('app:logs-open', async () => { fs.mkdirSync(logDir(),{recursive:true}); await shell.openPath(logDir()); return true; });
ipcMain.handle('app:logs-clear', () => { try { for(let i=0;i<=3;i++) fs.rmSync(i?`${logFile()}.${i}`:logFile(),{force:true}); writeAppLog('info','Log dibersihkan oleh pengguna.'); return true; } catch(e) { writeAppLog('error',`Gagal membersihkan log: ${e.message}`); return false; } });
function readSettings(){
  for(const file of [dataFile(),dataFile()+'.bak']){
    try{const value=JSON.parse(fs.readFileSync(file,'utf8'));if(value&&typeof value==='object'&&!Array.isArray(value))return value;}
    catch{} 
  }
  return {};
}
function writeSettings(value){
  if(!value || typeof value!=='object' || Array.isArray(value))throw new Error('Format pengaturan tidak valid.');
  fs.mkdirSync(path.dirname(dataFile()),{recursive:true});
  const target=dataFile(),tmp=target+'.tmp';
  fs.writeFileSync(tmp,JSON.stringify(value,null,2),'utf8');
  if(fs.existsSync(target))try{fs.copyFileSync(target,target+'.bak');}catch{}
  fs.renameSync(tmp,target);
  return true;
}
ipcMain.handle('settings:read', () => readSettings());
ipcMain.handle('settings:write', (_e, value) => writeSettings(value));

// Event profiles are stored separately from the general KACA.ID settings.
// Atomic replace protects the previous JSON if Windows closes during a save.
const eventsFile = () => path.join(app.getPath('userData'), 'kaca-events.json');
function readEvents(){
  try {const x=JSON.parse(fs.readFileSync(eventsFile(),'utf8'));
    if(!x || !Array.isArray(x.events)) return {activeEventId:null,events:[]};
    return {activeEventId:typeof x.activeEventId==='string'?x.activeEventId:null,events:x.events};
  }catch{return {activeEventId:null,events:[]};}
}
function writeEvents(data){
  if(!data || !Array.isArray(data.events) || data.events.length>250) throw new Error('Data event tidak valid.');
  const normalized={activeEventId:typeof data.activeEventId==='string'?data.activeEventId:null,events:data.events.map(e=>{
    const id=String(e.id||''); if(!/^[a-f0-9]{16}$/.test(id))throw new Error('ID event tidak valid.');
    return {id,name:String(e.name||'').trim().slice(0,100),date:String(e.date||'').slice(0,10),type:String(e.type||'Event').slice(0,35),config:e.config&&typeof e.config==='object'&&!Array.isArray(e.config)?e.config:{}};
  })};
  if(normalized.activeEventId&&!normalized.events.some(e=>e.id===normalized.activeEventId)) normalized.activeEventId=null;
  fs.mkdirSync(path.dirname(eventsFile()),{recursive:true});
  const tmp=eventsFile()+'.tmp';fs.writeFileSync(tmp,JSON.stringify(normalized,null,2),'utf8');
  fs.renameSync(tmp,eventsFile());
  return normalized;
}
ipcMain.handle('events:read',()=>readEvents());
ipcMain.handle('events:write',(_e,data)=>writeEvents(data));

ipcMain.handle('dashboard:choose-assets', async (_event, kind) => {
  const specs = {
    photos: { title: 'Pilih foto galeri dasbor', filters: [{ name: 'Gambar', extensions: ['jpg','jpeg','png','webp'] }], properties: ['openFile','multiSelections'] },
    logo: { title: 'Pilih logo KACA Studio', filters: [{ name: 'Gambar', extensions: ['png','jpg','jpeg','webp','svg'] }], properties: ['openFile'] },
    video: { title: 'Pilih video latar dasbor', filters: [{ name: 'Video', extensions: ['mp4','webm','mov'] }], properties: ['openFile'] },
    backgroundImage: { title: 'Pilih foto latar dasbor', filters: [{ name: 'Gambar', extensions: ['jpg','jpeg','png','webp'] }], properties: ['openFile'] }
  };
  const spec = specs[kind];
  if (!spec) return [];
  const result = await dialog.showOpenDialog({ ...spec, properties: spec.properties });
  if (result.canceled || !result.filePaths.length) return [];
  const folder = path.join(app.getPath('userData'), 'dashboard-assets');
  fs.mkdirSync(folder, { recursive: true });
  return result.filePaths.map(source => {
    const ext = path.extname(source).toLowerCase();
    const name = `${kind}-${Date.now()}-${Math.random().toString(36).slice(2,8)}${ext}`;
    const target = path.join(folder, name);
    fs.copyFileSync(source, target);
    return { name: path.basename(source), url: pathToFileURL(target).href };
  });
});
ipcMain.handle('storage:choose-folder', async () => { const result=await dialog.showOpenDialog({title:'Pilih folder penyimpanan lokal KACA.ID',properties:['openDirectory','createDirectory']}); return result.canceled||!result.filePaths.length?'':result.filePaths[0]; });
ipcMain.handle('printer:open-properties', async (_event, printerName) => { if(process.platform!=='win32') throw new Error('Dialog properti printer hanya tersedia di Windows.'); const name=String(printerName||'').trim(); if(!name) throw new Error('Pilih printer terlebih dahulu.'); return await new Promise((resolve,reject)=>{ const child=spawn('rundll32.exe',['printui.dll,PrintUIEntry','/e','/n',name],{windowsHide:false,detached:false,stdio:'ignore'}); child.once('error',reject); child.once('exit',(code)=>resolve({ok:code===0,code})); }); });
ipcMain.handle('external:open', async (_event, url) => { const value=String(url||'').trim(); const isAllowedHttps=/^https:\/\/(accounts\.google\.com|drive\.google\.com|wa\.me|web\.whatsapp\.com|api\.whatsapp\.com)\//i.test(value) || /^https:\/\/kacastudio\.id\/paket\/?(?:[?#].*)?$/i.test(value); const isAllowedMailto=/^mailto:[^\r\n<>]+$/i.test(value); if(!isAllowedHttps&&!isAllowedMailto) throw new Error('Alamat berbagi eksternal tidak diizinkan.'); await shell.openExternal(value); return true; });
// DOKU Checkout opens inside a sandboxed KACA.ID payment window, not in WhatsApp/Web.
let dokuCheckoutWindow = null;
function isAllowedDokuUrl(url){
  try{const u=new URL(String(url||''));return u.protocol==='https:'&&(u.hostname==='doku.com'||u.hostname.endsWith('.doku.com'));}
  catch{return false;}
}
ipcMain.handle('payment:open-checkout', async (_event, checkoutUrl) => {
  if(!isAllowedDokuUrl(checkoutUrl)) throw new Error('Alamat DOKU Checkout tidak valid.');
  if(dokuCheckoutWindow && !dokuCheckoutWindow.isDestroyed()) dokuCheckoutWindow.close();
  const win=new BrowserWindow({width:690,height:850,minWidth:500,minHeight:650,modal:true,parent:mainWindow||undefined,
    autoHideMenuBar:true,icon:KACA_APP_ICON,backgroundColor:'#fff',webPreferences:{nodeIntegration:false,contextIsolation:true,sandbox:true,webSecurity:true}});
  dokuCheckoutWindow=win;
  win.webContents.setWindowOpenHandler(()=>({action:'deny'}));
  win.webContents.on('will-navigate', (event, next) => {if(!isAllowedDokuUrl(next))event.preventDefault();});
  win.on('closed',()=>{if(dokuCheckoutWindow===win)dokuCheckoutWindow=null;});
  await win.loadURL(checkoutUrl);
  return {ok:true};
});
ipcMain.handle('payment:close-checkout', () => {
  if(dokuCheckoutWindow&&!dokuCheckoutWindow.isDestroyed())dokuCheckoutWindow.close();
  dokuCheckoutWindow=null;return true;
});
ipcMain.handle('app:version', () => app.getVersion());
ipcMain.handle('window:fullscreen-toggle', () => mainWindow && !mainWindow.isDestroyed() ? setWindowFullscreen(mainWindow, !mainWindow.isFullScreen()) : false);
ipcMain.handle('window:fullscreen-get', () => Boolean(mainWindow && !mainWindow.isDestroyed() && mainWindow.isFullScreen()));
function pythonPath(){
  const root = app.getAppPath();
  const candidates = process.platform === 'win32'
    ? [path.join(process.resourcesPath || root,'python','python.exe'),path.join(root,'runtime','python','python.exe'),path.join(root,'.venv','Scripts','python.exe')]
    : [path.join(root,'.venv','bin','python')];
  const bundled = candidates.find(candidate => fs.existsSync(candidate));
  if (bundled) return bundled;
  // A published Windows installer must be self-contained; never depend on
  // Python being installed globally on the customer's computer.
  if (process.platform === 'win32' && app.isPackaged) return null;
  return process.platform === 'win32' ? 'python' : 'python3';
}
function terminateBackendPid(pid){
  const n=Number(pid); if(!Number.isInteger(n)||n<=0||n===process.pid) return false;
  try {
    if(process.platform==='win32') execFileSync('taskkill.exe',['/PID',String(n),'/T','/F'],{windowsHide:true,stdio:'ignore'});
    else process.kill(n,'SIGTERM');
    writeAppLog('warn',`Stopped stale KACA backend PID=${n} so this application can start the matching backend build.`);
    return true;
  } catch(e) { writeAppLog('error',`Could not stop stale backend PID=${n}: ${e.message}`); return false; }
}
function readBackendHealth(){
  return new Promise(resolve=>{
    const req=http.get(`http://127.0.0.1:${PORT}/health`,res=>{let body='';res.setEncoding('utf8');res.on('data',c=>body+=c);res.on('end',()=>{try{const h=JSON.parse(body||'{}');resolve(res.statusCode===200&&h.ok===true&&h.opencv?h:null);}catch{resolve(null);}});});
    req.on('error',()=>resolve(null)); req.setTimeout(700,()=>{req.destroy();resolve(null);});
  });
}
function isPortInUse(){return new Promise(resolve=>{let settled=false;const done=value=>{if(settled)return;settled=true;try{socket.destroy();}catch{}resolve(value);};const socket=net.createConnection({host:'127.0.0.1',port:PORT});socket.once('connect',()=>done(true));socket.once('error',()=>done(false));socket.setTimeout(500,()=>done(true));});}
async function waitPortFree(timeout=6000){
  const started=Date.now(); while(Date.now()-started<timeout){ if(!(await isPortInUse())) return true; await new Promise(r=>setTimeout(r,200)); } return false;
}
async function startBackend(){
  // A backend left behind by v0.9.52 (or an older build) must not be reused:
  // its routes/camera state may not match the UI currently running.
  const existing=await readBackendHealth();
  if(existing){
    if(existing.app_version===app.getVersion() && existing.backend_protocol===3){
      backend={pid:existing.pid,reused:true,managed:true,killed:false};
      writeAppLog('info',`Reusing matching KACA backend PID=${existing.pid} build=${existing.app_version}.`); return;
    }
    writeAppLog('warn',`Found stale/incompatible KACA backend PID=${existing.pid} version=${existing.app_version||'unknown'} protocol=${existing.backend_protocol||'unknown'}; replacing it.`);
    terminateBackendPid(existing.pid);
    if(!(await waitPortFree())) throw new Error('Backend lama masih menggunakan port 8765. Tutup semua proses KACA.ID lama lalu jalankan kembali aplikasi.');
  }
  if(await isPortInUse()) throw new Error('Port 8765 masih digunakan proses lain dan bukan backend KACA.ID yang cocok. Tutup aplikasi lama atau proses yang memakai port 8765, lalu jalankan ulang KACA.ID.');
  const script=path.join(app.getAppPath(),'backend','camera_server.py');
  const selectedPython=pythonPath();
  if(!selectedPython) throw new Error('Runtime Python portable tidak ditemukan di dalam installer. Jalankan ulang installer KACA.ID atau hubungi pembuat aplikasi; Python global tidak diperlukan dan tidak akan dipanggil.');
  writeAppLog('info',`Starting camera backend: python=${selectedPython} script=${script}`);
  backend=spawn(selectedPython,['-u',script],{cwd:app.getAppPath(),windowsHide:true,env:{...process.env,PYTHONUNBUFFERED:'1',KACA_PREFERRED_CAMERA_INDEX:String(readSettings().cameraDevice??0),KACA_APP_VERSION:app.getVersion(),KACA_BACKEND_PROTOCOL:'3',KACA_DATA_DIR:path.join(app.getPath('userData'),'media'),KACA_LOCAL_ARCHIVE_DIR:readSettings().localStoragePath||path.join(app.getPath('pictures'),'KACA STUDIO'),KACA_DEFAULT_ARCHIVE_DIR:path.join(app.getPath('pictures'),'KACA STUDIO'),KACA_EDSDK_DIR:process.env.KACA_EDSDK_DIR||path.join(app.getAppPath(),'backend','edsdk')},stdio:['ignore','pipe','pipe']});
  const child=backend;
  child.managed=true;
  backendStartedAt=Date.now();
  child.stdout.on('data',d=>{const line=String(d).trim();if(line){writeAppLog('backend',line);console.log('[KACA CAMERA BACKEND]',line);}});
  child.stderr.on('data',d=>{const line=String(d).trim();if(line){writeAppLog('backend-error',line);console.error('[KACA CAMERA BACKEND]',line);}});
  child.on('error',e=>{writeAppLog('fatal',`Backend start error: ${e.stack||e.message}`);console.error('[KACA CAMERA BACKEND START ERROR]',e.message);});
  child.on('exit',(code,signal)=>{
    writeAppLog(code===0?'info':'error',`Backend exit code=${code} signal=${signal}`);
    console.log('[KACA CAMERA BACKEND EXIT]',code,signal);
    if(backend===child){backend=null;if(!appClosing)scheduleBackendRecovery(`code=${code} signal=${signal}`);}
  });
}
function waitBackend(timeout=15000){
  const start=Date.now();
  return new Promise(resolve=>{
    const check=()=>{
      const req=http.get(`http://127.0.0.1:${PORT}/health`,res=>{let body='';res.setEncoding('utf8');res.on('data',c=>body+=c);res.on('end',()=>{
        let health={};try{health=JSON.parse(body||'{}');}catch{}
        if(res.statusCode===200&&health.ok===true&&health.opencv&&health.app_version===app.getVersion()&&health.backend_protocol===3&&backend){
          if(health.pid&&backend.pid&&health.pid!==backend.pid){writeAppLog('error',`Backend PID mismatch: expected ${backend.pid}, received ${health.pid}. Refusing to attach to another process.`);return retry();}
          return resolve(true);
        }
        if(res.statusCode===200&&health.ok===true&&health.app_version!==app.getVersion()) writeAppLog('error',`Incompatible backend still answering health: ${health.app_version||'unknown'}.`);
        if(res.statusCode===503&&health.error)writeAppLog('error',`Backend health check failed: ${health.error}`);retry();
      });});
      req.on('error',retry);req.setTimeout(900,()=>req.destroy());
      function retry(){if(Date.now()-start>timeout)return resolve(false);setTimeout(check,300);}
    };check();
  });
}
async function createWindow(){
  const win = new BrowserWindow({width:1440,height:900,minWidth:1100,minHeight:700,autoHideMenuBar:true,icon:KACA_APP_ICON,backgroundColor:'#0b0b0d',webPreferences:{preload:path.join(__dirname,'preload.js'),contextIsolation:true,nodeIntegration:false}});
  mainWindow = win;
  win.setMenuBarVisibility(false);
  win.setAutoHideMenuBar(true);
  win.on('enter-full-screen', () => win.webContents.send('window:fullscreen-changed', true));
  win.on('leave-full-screen', () => win.webContents.send('window:fullscreen-changed', false));
  win.webContents.on('before-input-event', (event, input) => {
    if (input.type !== 'keyDown') return;
    if (input.control && input.alt && input.key.toLowerCase() === 'r') {event.preventDefault();writeAppLog('warn','Operator requested renderer-only reload using Ctrl+Alt+R');win.webContents.reloadIgnoringCache();return;}
    if (input.key === 'F11') { event.preventDefault(); setWindowFullscreen(win, !win.isFullScreen()); }
    else if (input.key === 'Escape' && win.isFullScreen()) { event.preventDefault(); setWindowFullscreen(win, false); }
  });
  win.webContents.on('render-process-gone', (_event, details) => writeAppLog('fatal',`Renderer process gone: ${JSON.stringify(details)}`));
  win.webContents.on('unresponsive', () => writeAppLog('error','Renderer tidak merespons (unresponsive).'));
  win.webContents.on('responsive', () => writeAppLog('info','Renderer kembali merespons.'));
  win.on('closed', () => { if (mainWindow === win) mainWindow = null; });
  win.loadFile(path.join(__dirname,'src','index.html'));
}
app.whenReady().then(async()=>{
  Menu.setApplicationMenu(null); // Hide native File/Edit/View/Window/Help menu entirely.
  if(!hasSingleInstanceLock) return;
  writeAppLog('info',`KACA.ID start v${app.getVersion()} platform=${process.platform} arch=${process.arch}`);
  // Present the splash screen immediately, while the Python backend starts.
  // The renderer itself waits for /health before revealing the dashboard.
  await createWindow();
  // Cloud is optional for existing offline customers until account migration.
  // Once activated, a locally verified Ed25519 license allows fully offline use.
  cloudAgent=initCloudAgent({app,getMainWindow:()=>mainWindow,readSettings,writeSettings,log:writeAppLog});
  await startBackend();
  const ready=await waitBackend();
  if(!ready) console.error('KACA camera backend tidak sehat. Periksa [BACKEND_DIAGNOSTIC] pada log; pastikan .venv\Scripts\python.exe dan opencv-python tersedia, lalu jalankan setup.bat.');
});
app.on('before-quit',()=>{ app.isQuittingCloud=true;cloudAgent?.stop();appClosing=true;if(backendRestartTimer){clearTimeout(backendRestartTimer);backendRestartTimer=null;} if(!backend||backend.killed)return; backend.killed=true; if(backend.reused||backend.managed){ if(backend.pid)terminateBackendPid(backend.pid); } else if(typeof backend.kill==='function')backend.kill(); });
app.on('window-all-closed',()=>{if(process.platform!=='darwin') app.quit();});
app.on('activate',()=>{if(BrowserWindow.getAllWindows().length===0) createWindow();});
