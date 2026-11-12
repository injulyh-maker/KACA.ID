KACA.ID v0.9.86 — PHOTO UI & CLOUD CONTROL MULTI BOOTH (FOUNDATION RELEASE)
================================================================================
Basis: FULL SOURCE v0.9.85.

PHOTO SESSION
- Tombol mikrofon/streaming tidak ditampilkan pada sesi foto.
- Shutter kamera menjadi tombol lingkaran besar di tengah preview.
- Tombol Switch Camera (saklar), Mirror, dan Retake tetap berfungsi.
- Tema PHOTO tetap biru mengikuti gaya KACA.ID.
- File contoh visual ada di design/KACA-ID-v0.9.86-PHOTO-UI-MOCKUP.png.
  Gambar tersebut adalah mockup; UI runtime mengikuti stylesheet/fungsi asli.

CLOUD CONTROL WEB — PENGEMBANGAN TAHAP AWAL
- Login, registrasi akun dan dashboard multi-booth berbasis web.
- Lisensi hanya diterbitkan Super Admin, satu lisensi per booth; satu akun
  pelanggan boleh memiliki beberapa lisensi yang berbeda.
- Lisensi perangkat ditandatangani Ed25519 dan bisa diverifikasi offline.
- Monitoring riwayat sesi, status booth, jumlah sesi/pengunjung, pendapatan
  terverifikasi dan estimasi, serta tautan hasil Google Drive.
- Harga, timer, mode, pengaturan kamera yang didukung driver, dan voucher
  diantrikan dari web dan diterapkan agen saat booth online/idle.
- Remote preview jendela KACA.ID dan klik/ketik terbatas membutuhkan
  persetujuan operator booth selama 15 menit. Ini bukan remote seluruh
  desktop Windows, dan belum diuji secara langsung pada komputer booth.
- File pelanggan disimpan lokal seperti sebelumnya. Upload thumbnail ke
  web tidak diaktifkan secara default dan memerlukan persetujuan.
- Offline-first: antrean sync disimpan lokal; foto/video tidak bergantung
  pada ketersediaan server Cloud.

AKTIVASI
1. Setup server: baca cloud_control/README-ID.md.
2. Super Admin bootstrap melalui terminal, setelah itu login ke web.
3. Pemilik booth membuat akun, Admin menerbitkan lisensi untuk akun tersebut.
4. Di desktop KACA.ID buka menu Cloud Control, tekan Aktivasi Akun / Lisensi,
   lalu masukkan URL server HTTPS, email, password, kode lisensi dan nama booth.
5. Agar instalasi BARU mewajibkan akun & lisensi sejak awal, jalankan Electron
   dengan environment KACA_REQUIRE_CLOUD_ACCOUNT=1. Existing customer tidak
   langsung dikunci saat update demi menjaga operasi offline.
6. Jangan membagikan token API, private key penandatanganan, atau password.

CATATAN PENTING
- Cloud server belum dipublikasikan ke internet atau domain.
- Uji integrasi backend menggunakan DB terisolasi. UI web diuji di Chromium
  menggunakan respons API simulasi. Electron Windows, DSLR, remote input
  fisik, dan multi-booth produksi belum diuji.
- Sebelum produksi publik perlu HTTPS reverse proxy, MFA admin, verifikasi
  email, throttle login, monitoring dan backup DB/keys, serta audit keamanan.
- Analytics menghitung jumlah SESI, bukan manusia unik. Pendapatan
  terverifikasi hanya pada pembayaran yang memiliki bukti berhasil.
- Jangan memasang patch di cabang Cloud Admin lain yang tidak berasal
  langsung dari v0.9.85 tanpa merge source terlebih dahulu.

INSTALL PATCH DESKTOP
1. Tutup KACA.ID, backend, dan buat backup source serta data pelanggan.
2. Ekstrak KACA-ID-v0.9.86-PATCH, lalu salin ISI folder patch ke folder
   utama aplikasi v0.9.85 (sejajar package.json).
3. Timpa file lama (Replace), tetapi jangan hapus AppData atau Pictures.
4. Jalankan kembali run-kaca-id.bat, buka menu Cloud Control.
5. Setup Cloud Server terpisah (FastAPI), lalu aktivasi akun/lisensi.
