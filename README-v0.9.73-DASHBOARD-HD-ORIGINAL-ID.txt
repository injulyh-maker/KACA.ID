KACA.ID v0.9.73 — Dashboard Video & Foto Original Full HD

PERUBAHAN
1. Video animasi yang diberikan operator menjadi latar DEFAULT dashboard:
   src/assets/dashboard-background.mp4 (1920x1080 H.264, loop, muted).
   Tidak mengubah penempatan tombol, logo, atau pengaturan dashboard.
   Jika pengguna pernah memilih video/foto latar custom, pengaturan custom
   masih diutamakan. Klik "Gunakan Latar Bawaan" di menu Tampilan & Tema
   untuk menampilkan video baru.

2. Semua Foto_##_Original.jpg yang diekspor ke folder lokal
   Pictures/KACA STUDIO/Sesi_*/Photos/ berukuran tepat 1920x1080.
   Diunggah ke Google Drive melalui pipeline asset yang sama menggunakan
   salinan hasil ekspor, sehingga resolusi lokal dan Drive konsisten.
   JPEG quality 98 dan resize Lanczos4 untuk kamera resolusi lebih rendah.
   Source original session (internal app data) tidak ditimpa.
   Rasio sumber dipertahankan; gambar 4:3 atau portrait akan mempunyai
   ruang hitam letterbox agar tidak terpotong/distorsi.
   Tidak ada penambahan detail optik nyata bila resolusi kamera < 1920x1080.
   Fitur berlaku untuk sesi baru setelah patch, bukan upload lama.

3. Pemutaran Live Photo WebM-prioritas dari v0.9.72 tetap dipertahankan.
   Tidak mengubah filter, frame, QR, printer, alur kamera, dan WhatsApp.

CARA PASANG PATCH
- Tutup KACA.ID dan proses backend terlebih dahulu.
- Backup folder aplikasi v0.9.72.
- Ekstrak patch ke folder utama aplikasi v0.9.72 (sejajar dengan package.json).
- Ganti file yang diminta. Jalankan run-kaca-id.bat.
- Bila latar dashboard berbeda, buka Tampilan & Tema > Gunakan Latar Bawaan
  > Simpan Tampilan; pengaturan custom yang tersimpan memang diprioritaskan.

PERHATIAN
- Installer EXE harus dibangun ulang agar video ini ikut dibundel.
- Pemasangan patch tidak memperbarui data sesi atau file upload yang lama.
- Pengujian fisik pada kamera dan Google Drive pelanggan tetap dibutuhkan.
