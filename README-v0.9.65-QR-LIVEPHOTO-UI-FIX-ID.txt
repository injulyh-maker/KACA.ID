KACA.ID v0.9.65 — FIX SLIDE HASIL, QR GOOGLE DRIVE, LIVE PHOTO
===========================================================
Basis: KACA.ID v0.9.64 FULL SOURCE. Kamera, render backend, Google Drive,
printer, WhatsApp, pembayaran, frame, dan data sesi tidak diubah.

PENYEBAB UTAMA YANG DIBUKTIKAN
--------------------------------
1. Pada slide Filter, elemen captureGrid diparkir ke DocumentFragment.
2. Saat /api/session/finish berhasil, hasil HTML dibuat di dalam captureGrid.
3. Kode lama memasang handler melalui document.querySelector sebelum hasil
   dipindahkan ke root DOM. Tombol #printSession/#shareWhatsApp belum ditemukan.
   Pemasangan handler melempar TypeError. Alur masuk ke catch, menampilkan
   hasil JPG tetapi tanpa memulai polling QR/Live Photo.
4. Setelah #finishedResult dipindah ke root, $cap() lama hanya mencari pada
   captureGrid dan tidak lagi bisa menemukan #driveQrImage, #resultLiveVideo,
   #resultRenderStatus dan elemen hasil lainnya.
5. Aturan CSS display !important di slide hasil dapat mengalahkan [hidden]
   pada JPG; video yang telah siap bisa terlihat bersebelahan dengan JPG.

PERBAIKAN
---------
- Pasang slide hasil (setFlowStep(5)) tepat setelah HTML hasil dibuat dan
  SEBELUM memasang tombol cetak/WhatsApp/email.
- $cap() mempunyai fallback ke root sehingga semua kontrol dan status
  hasil tetap ditemukan sesudah panel dipindahkan dari captureGrid.
- Polling tidak berhenti hanya karena Drive/render berstatus ready;
  QR PNG dan Live Photo juga harus benar-benar dimuat sebelum berhenti.
- Retry terbatas untuk playback gagal; WebM tetap prioritas dengan fallback
  MP4 seperti pada v0.9.64; JPG tetap tersedia saat video gagal.
- Saat QR baru muncul, waktu scan di layar diperpanjang minimal selama
  durasi countdown yang dikonfigurasi (sekali per sesi).
- CSS memperlakukan [hidden] pada JPG/video secara eksplisit.
- Berkas app.js dan style.css pada src/ dan salinan source alternatif
  disinkronkan agar konsisten. Entry point aktif Electron: src/index.html.

HASIL PENGUJIAN DI LINGKUNGAN SIMULASI
--------------------------------------
- Sebelum patch, simulasi slide Filter -> Hasil mereproduksi masalah:
  QR dan video tanpa src, status tetap "Menyiapkan", handler belum terpasang.
- Sesudah patch, Chromium memuat QR PNG, memutar WebM, menampilkan video
  sebagai satu-satunya media aktif, dan handler cetak/share aktif.
- Simulasi QR belum tersedia (404 awal) -> retry -> QR muncul: lulus.
- Simulasi WebM 404 -> fallback MP4: lulus.
- Pemeriksaan sintaks JavaScript, Python compile: lulus.
Catatan: perangkat Canon, printer dan Google Drive asli tidak dapat diuji
secara langsung di lingkungan ini. Pengujian booth tetap diperlukan.

CARA MEMASANG FULL SOURCE
-------------------------
1. Tutup aplikasi KACA.ID dan terminal backend sebelum mengganti source.
2. Cadangkan folder sumber lama dan data hasil sesi di:
   %APPDATA%\kaca-id-photobooth\media\sessions
   serta folder arsip foto Anda, misalnya Pictures\KACA STUDIO.
3. Ekstrak FULL SOURCE v0.9.65 ke folder baru (jangan menimpa data sesi).
4. Jika dependensi Electron/Python belum ada, ikuti README-INSTALL.txt dan
   jalankan skrip setup yang sudah disediakan di paket source.
5. Jalankan run-kaca-id.bat dari folder utama paket baru.
6. Selesaikan satu sesi foto; periksa slide hasil menampilkan QR dan
   Live Photo. Beri pelanggan waktu untuk scan sebelum menekan SELESAI.

CARA MEMASANG PATCH
-------------------
1. Tutup KACA.ID; cadangkan folder v0.9.64.
2. Ekstrak PATCH ZIP ke folder UTAMA v0.9.64 (folder berisi package.json),
   gabungkan folder src/ dan pilih replace untuk 3 berkas patch.
3. Jalankan run-kaca-id.bat. Nama folder boleh tetap v0.9.64 tetapi versi
   dari package.json menjadi 0.9.65.
4. Jika aplikasi EXE installer lama terpasang, mengganti source terpisah
   TIDAK otomatis memperbarui installer. Bangun ulang dengan perintah
   dist:win di Windows sesuai dokumentasi instalasi.

DIAGNOSTIK RINGKAS
------------------
Backend pada laporan pengguna untuk sesi 3c81133e0b0d:
QR:  HTTP 200 image/png (signature PNG valid).
WebM: HTTP 200 video/webm (Accept-Ranges: bytes).
render-status: finished/ready, drive_qr_available:true,
live_output_preview_available:true.
Karena itulah tidak perlu mengubah proses render/upload backend.
