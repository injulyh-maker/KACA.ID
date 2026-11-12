KACA.ID v0.9.80 — STARTUP LOADING MENU DASBOR + TANPA PILIH FRAME
==============================================================
Basis: KACA.ID v0.9.79 VIDEO FLOW (basis v0.9.78 Event/Drive/QR).

PERUBAHAN
1. Ketika aplikasi baru dibuka, KACA.ID langsung memperlihatkan loading layar penuh,
   bukan sidebar atau menu Pengaturan. Window Electron ditampilkan sebelum backend
   Python selesai dijalankan. Loading menunggu pengaturan aplikasi, profil Event,
   backend kamera /health, lalu kesiapan latar Dashboard secara terbatas.
2. Dashboard utama baru diperlihatkan setelah startup berhasil. Jika backend belum
   tersedia dalam 26 detik, tampilkan pesan dan tombol Coba Lagi atau Buka Dashboard
   Tanpa Kamera; tidak memindahkan pengguna secara otomatis ke menu Pengaturan.
3. Hapus tahap pelanggan Pilih Frame di PHOTO dan VIDEO (tidak lagi ditampilkan).
   Preset frame menggunakan Frame & Layout / Manajemen Event. Jika ID preset tidak
   cocok, PHOTO memilih frame aktif pertama pada profil yang sama; VIDEO dapat
   merekam tanpa frame bila belum ada yang ditentukan.
4. PHOTO: Dashboard -> (transaksi jika aktif) -> loading kamera/frame preset ->
   sesi foto -> pilih filter -> hasil dengan QR/Live Photo/WhatsApp.
5. VIDEO: Dashboard -> (transaksi jika aktif) -> loading kamera/frame preset ->
   rekam video -> review -> hasil dengan QR/WhatsApp.
6. Ketika kamera belum siap, loading tetap memberi pesan dan retry. Setelah
   transaksi tervalidasi, percobaan kamera ulang tidak mengulangi pembayaran.
7. Kontrol administratif Frame & Layout serta frame khusus Event tetap tersedia;
   QR, Google Drive, Live Photo WebM, DOKU dan Fonnte dari v0.9.79 tidak diubah.

INSTALASI PATCH
- Patch dibuat dari v0.9.79 VIDEO FLOW, BUKAN v0.9.79 Cloud Admin.
- Tutup aplikasi KACA.ID dan proses backend, lalu backup folder source dan data.
- Ekstrak PATCH dan salin ISI folder KACA-ID-v0.9.80-PATCH ke folder source utama
  yang mengandung package.json. Pilih Replace untuk file yang sudah ada.
- Jalankan run-kaca-id.bat. Saat membuka, loading tampil dan lalu Dashboard.
- Atur frame default lewat Frame & Layout atau Manajemen Event sebelum sesi foto.

BATASAN UJI
- Chromium: startup belum sehat -> loading tetap di depan; backend sehat -> Dashboard.
- Chromium: PHOTO/VIDEO tanpa transaksi langsung langkah kamera dan frame dari preset.
- Chromium: dengan voucher -> langsung langkah kamera, tanpa layar Pilih Frame.
- JavaScript syntax, Python syntax, QR sesi foto, Drive dan arsip Event: PASS.
- PC Windows, Electron installer, kamera dan gateway riil belum diuji langsung.
- Jika Anda menggunakan cabang v0.9.79 Cloud Admin, jangan overwrite file ini
  sebelum merge agar tidak menghilangkan fitur monitoring Cloud Admin.
