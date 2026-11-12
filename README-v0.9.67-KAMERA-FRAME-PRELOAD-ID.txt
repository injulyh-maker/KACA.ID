KACA.ID v0.9.67 — Perbaikan keamanan pemindaian kamera & preload frame
======================================================================
BASIS: v0.9.66. Perbaikan QR dan fallback Live Photo tetap dipertahankan.

DIAGNOSIS TERKONFIRMASI
- v0.9.66 memakai variabel lokal `state` di Handler.do_GET untuk status
  konversi GIF. Itu membuat /api/status dan /api/cameras melempar
  UnboundLocalError dan browser melihat koneksi gagal. Diganti menjadi
  `animation_status` tanpa mengubah `state` global kamera. Ini penyebab utama.
- Log "Backend terhubung; OpenCV ..." lalu "connection refused" hanya membuktikan
  backend tidak dapat dihubungi setelah scan dimulai. Tanpa log backend fatal,
  akar crash tidak bisa dipastikan. Salah satu risiko adalah driver webcam
  DirectShow/MSMF yang menyebabkan crash native pada proses Python.
- v0.9.66 men-decode video GIF menggunakan OpenCV dalam proses backend utama;
  hal ini sekarang dipindahkan ke proses pekerja terpisah untuk mengurangi
  risiko berbagi native decoder dengan kamera.

PERBAIKAN
1. backend/camera_probe.py: probe DirectShow dan MSMF di proses Python terpisah;
   jika driver bermasalah/timeout, backend utama tetap berjalan.
2. backend/camera_server.py: scan menggunakan probe terisolasi, prioritas indeks
   kamera mengikuti konfigurasi komputer; tidak lagi selalu mendahulukan index 1.
3. backend/live_gif_worker.py: decoding fallback animasi berjalan terisolasi,
   bukan dalam proses yang mengendalikan perangkat kamera.
4. main.js: pemulihan otomatis backend yang berhenti tak terduga; dibatasi sampai
   5 percobaan dengan jeda bertingkat untuk menghindari loop restart.
5. src/app.js & src/style.css: overlay "Tunggu kakak..." dan indikator
   progres jumlah frame; semua frame aktif diload & didekode sebelum layar
   Pilih Frame ditampilkan. Frame gagal memuat akan ditunjukkan dengan tombol
   Coba Muat Frame Lagi; tidak masuk ke halaman dengan gambar setengah kosong.
6. build-windows-installer.bat: memeriksa Python portable, cv2/Pillow/qrcode,
   dan redistributable Microsoft sebelum membuat installer.

PASANG PATCH DARI v0.9.66
- Tutup aplikasi KACA.ID dan proses backend terlebih dahulu.
- Backup folder source sebelumnya; jangan menghapus AppData atau Pictures KACA STUDIO.
- Extract patch pada akar project yang memuat package.json, pilih Replace.
- Jalankan run-kaca-id.bat lagi.
- Coba deteksi kamera, buka preview, dan lakukan 1 sesi; perhatikan overlay
  loading sebelum Pilih Frame, lalu QR dan Live Photo di Hasil Sesi.

CATATAN PERANGKAT WINDOWS LAIN
- Webcam/Canon tetap membutuhkan driver USB/EDSDK yang cocok, izin kamera,
  serta kebebasan akses kamera dari aplikasi lain.
- Installer Windows harus dibangun setelah menjalankan setup-runtime.bat dan
  memasukkan runtime portable. Instalasi tidak mengandalkan Python/Node di PC
  pelanggan; source .bat pengembang berbeda dari installer EXE.
- Pengujian ini dilakukan dengan simulasi dan perangkat lunak, bukan webcam
  pelanggan yang sedang bermasalah. Kegagalan driver saat *membuka kamera*
  (bukan hanya saat scanning) masih memerlukan pengujian pada PC target.
- Log aplikasi: %APPDATA%\\kaca-id-photobooth\\logs\\kaca-app.log

PERINGATAN
- Port 127.0.0.1:8765 harus tersedia, dan hanya 1 instance aplikasi.
- Tidak ada data pengguna yang perlu dihapus untuk pembaruan ini.
