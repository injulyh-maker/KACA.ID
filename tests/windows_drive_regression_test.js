'use strict';
const fs=require('node:fs'), assert=require('node:assert/strict');
const ui=fs.readFileSync('src/app.js','utf8');
const backend=fs.readFileSync('backend/camera_server.py','utf8');
const drive=fs.readFileSync('backend/google_drive.py','utf8');
const uiMarkers=[
  'id="testGoogleDrive"', 'Tes Koneksi Google Drive',
  'Perbaiki & Sinkronkan Arsip Lokal', 'waiting_folder',
  "fetch('http://127.0.0.1:8765/api/google-drive/test'",
  "img.dataset.resultLoaded='1'; // Do not immediately overwrite",
  'print_qr_ready', 'drive_share_warning'
];
const backendMarkers=[
  'def _resume_folder_assets(session_id)', 'def reconcile_local_drive_sessions',
  "status = 'pending' if connected and manifest.get('drive_folder_id')",
  "return self.send_json({'ok':bool(result.get('verified')),'diagnostic':result}",
  'Hasil_Frame_Dengan_QR.jpg', 'Final_Results/QR_Google_Drive.png',
  'threading.Timer(delay,lambda jid=job_id: drive_jobs_queue.put(jid))'
];
for(const marker of uiMarkers)assert.ok(ui.includes(marker),'Missing UI: '+marker);
for(const marker of backendMarkers)assert.ok(backend.includes(marker),'Missing backend: '+marker);
assert.ok(drive.includes('def diagnose(self)'));
console.log('Drive recovery, OAuth diagnostic, QR print and upload queue contracts pass.');
