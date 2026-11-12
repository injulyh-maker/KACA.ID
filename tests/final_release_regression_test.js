'use strict';
// Offline release regression: no network, real filesystem only in temporary dir.
const assert=require('node:assert/strict');
const crypto=require('node:crypto');
const fs=require('node:fs');
const os=require('node:os');
const path=require('node:path');
const Module=require('node:module');
const {readFileSync}=fs;
const root=path.resolve(__dirname,'..');
const appjs=readFileSync(path.join(root,'src','app.js'),'utf8');
const mainjs=readFileSync(path.join(root,'main.js'),'utf8');

// The old license page expected #save, creating the false warning seen by customer.
assert.match(appjs, /license:\['#licenseStatus','#licenseServer'.*'#licensePackages'\]/);
assert.doesNotMatch(appjs,/license:\['#save'\]/);
assert.match(appjs,/else if\(page==='license'\)\{await renderLicense\(\);return;\}/);
assert.match(appjs,/const s=await window\.kaca\.syncCloudNow\(\)/);
assert.match(appjs,/Sinkronisasi Cloud berhasil/);

// Skip must be visible while waiting: previously parent was hidden until timeout.
const start=appjs.indexOf('const prepareFinalAssetsBeforeOpening');
const end=appjs.indexOf('finish.onclick=',start);
assert.ok(start>=0&&end>start);
const flow=appjs.slice(start,end);
assert.match(flow,/if\(actions\)actions\.hidden=false;/);
assert.match(flow,/skipButton\.onclick=\(\)=>\{skipped=true/);
assert.match(flow,/if\(skipped\)return \{video:null,videoName:'',st:null,skipped:true\};/);

// A user opening official packages should not receive 'external URL denied'.
assert.match(mainjs,/kacastudio\\\.id\\\/paket/);

const mockHandlers=new Map();
const originalLoad=Module._load;
Module._load=function(id,parent,main){
 if(id==='electron')return {BrowserWindow:{},dialog:{},ipcMain:{handle:(n,f)=>{assert.ok(!mockHandlers.has(n),`Duplicate IPC handler ${n}`);mockHandlers.set(n,f)}},nativeImage:{}};
 return originalLoad.call(this,id,parent,main);
};
let agent;
try{agent=require('../cloud_control/agent.js');}finally{Module._load=originalLoad;}
const directory=fs.mkdtempSync(path.join(os.tmpdir(),'kaca-final-'));
const app={getPath:()=>directory,getVersion:()=> '0.9.90'};
const {privateKey,publicKey}=crypto.generateKeyPairSync('ed25519');
const pem=publicKey.export({format:'pem',type:'spki'});
const deviceId=agent.hardwareId(directory);
const digest=crypto.createHash('sha256').update(deviceId).digest('hex');
const now=Math.floor(Date.now()/1000);
const encoded=Buffer.from(JSON.stringify({device_hash:digest,exp:now+3600})).toString('base64url');
const signed=encoded+'.'+crypto.sign(null,Buffer.from(encoded),privateKey).toString('base64url');
const configFile=path.join(directory,'kaca-cloud-agent.json');
fs.writeFileSync(configFile,JSON.stringify({server:'http://127.0.0.1:8086',boothName:'TEST-BOOTH',boothId:'local-test',boothKey:'test',offlineLicense:signed,publicKey:pem,licenseExpires:now+3600,lastObservedAt:now}));
let instance;
try{
 instance=agent.initCloudAgent({app,getMainWindow:()=>null,readSettings:()=>({}),writeSettings:()=>{},log:()=>{}});
 const state=instance.status();
 assert.equal(state.licenseActive,true,'Offline license must work without Cloud');
 assert.equal(state.connected,false,'Offline license must not be mistaken for online sync');
 assert.equal(state.server,'https://kacastudio.id','Legacy localhost should migrate');
 assert.equal(mockHandlers.get('cloud:assert-license')().ok,true);
 assert.equal(agent.verifyLicense(signed,pem,deviceId).exp,now+3600);
 assert.throws(()=>agent.verifyLicense(signed,pem,'OTHER-PC'));
 assert.throws(()=>agent.verifyLicense(encoded+'.x',pem,deviceId));
 const expiredPayload=Buffer.from(JSON.stringify({device_hash:digest,exp:now-60})).toString('base64url');
 const expired=expiredPayload+'.'+crypto.sign(null,Buffer.from(expiredPayload),privateKey).toString('base64url');
 assert.throws(()=>agent.verifyLicense(expired,pem,deviceId),/kadaluarsa/);
 console.log('[PASS] License menu, loading skip, official plans link, offline signed license and real Cloud status');
} finally {
 instance?.stop();
 fs.rmSync(directory,{recursive:true,force:true});
}
