'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
const root=path.resolve(__dirname,'..');
const ui=fs.readFileSync(path.join(root,'src','app.js'),'utf8');
const be=fs.readFileSync(path.join(root,'backend','camera_server.py'),'utf8');
for(const anchor of ['mountKacaSoundSettings','kacaCountdownTest','kacaShutterTest','kacaSaveSound','kacaSound.countdown(n)','kacaSound.shutter()', 'Reload Tampilan Penuh','Pemuatan menu melewati batas waktu','st.print_qr_ready','output-print-qr.jpg?stamp='])assert.ok(ui.includes(anchor),'Missing '+anchor);
for(const anchor of ["'/output-print-qr.jpg'","'print_qr_ready':bool","Hasil_Frame_Dengan_QR.jpg","size = max(1, int(round(min(w*fit_w, h*fit_h))))"])assert.ok(be.includes(anchor),'Missing '+anchor);
console.log('[PASS] KACA Windows menu, sounds, QR print integration present');
