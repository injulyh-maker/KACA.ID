'use strict';
const fs=require('node:fs'),assert=require('node:assert/strict');
const app=fs.readFileSync('src/app.js','utf8');
const backend=fs.readFileSync('backend/camera_server.py','utf8');
const drive=fs.readFileSync('backend/google_drive.py','utf8');
const desktop=fs.readFileSync('main.js','utf8');
for(const field of ['paymentBasePrice','paymentDiscountType','paymentDiscountValue','savePaymentPricing','deleteStaticQrisImage','midtransServerKey','midtransEnvironment','midtransQrisChannel','qris_midtrans']){
    assert.ok(app.includes(field),'UI missing '+field);
}
assert.equal(app.split("if(['doku_checkout','midtrans_snap'].includes(q.mode))").length-1,2);
assert.equal(app.split("selectedTransactionMethod=checkout.provider==='midtrans'?'qris_midtrans':'qris_doku'").length-1,2);
assert.equal(app.split("if(checkout.free)").length-1,2);
for(const route of ['/api/qris/pricing','/api/qris/image/delete','/api/qris/checkout/status','/api/qris/checkout/create'])assert.ok(backend.includes(route));
assert.ok(backend.includes('def _verified_payment'));
assert.ok(backend.includes("midtrans_snap.check(invoice)"));
assert.ok(drive.includes("'qr_google_drive.png'"));
assert.ok(drive.includes("'hasil_frame_dengan_qr.jpg'"));
assert.ok(desktop.includes("isAllowedCheckoutUrl"));
assert.ok(desktop.includes("u.hostname.endsWith('.midtrans.com')"));
assert.ok(!backend.includes("enqueue_drive_asset_job(sid, session['drive_qr_archive_path']"));
console.log('Payment mode, pricing, provider gate, and QR local-only source contracts pass');
