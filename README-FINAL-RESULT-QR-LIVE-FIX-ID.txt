KACA.ID v0.9.63 — FINAL RESULT QR / LIVE PREVIEW FIX

Perbaikan ini membandingkan alur slide hasil v0.9.63 dengan implementasi hasil sesi v0.9.44 yang Anda berikan.

File yang diperbarui:
- backend/camera_server.py
- src/app.js

Perubahan:
1. Endpoint QR sekarang membaca QR dari semua lokasi lokal yang sah:
   - path QR pada manifest sesi
   - SESSIONS/<id>/google_drive_qr.png
   - <local_archive>/Final_Results/QR_Google_Drive.png
   Jika QR hanya tersisa di arsip pelanggan, slide hasil tetap dapat memuatnya.
2. Status sesi memeriksa keberadaan file QR, MP4, WebM, JPG, dan GIF di disk, bukan hanya mengandalkan metadata manifest.
3. Slide hasil mencoba memuat endpoint QR lokal secara berulang sampai gambar benar-benar berhasil dimuat, tidak lagi menunggu flag drive_url/drive_qr_available yang mungkin tertinggal.
4. Slide hasil memuat WebM terlebih dahulu untuk Chromium/Electron dan fallback ke MP4 bila WebM tidak tersedia/gagal diputar.
5. Hasil render tetap disalin ke penyimpanan lokal dan diantrekan untuk upload Google Drive pada saat render slide hasil selesai; WebM dan QR tidak diunggah.

Pemasangan:
1. Tutup KACA.ID sepenuhnya.
2. Backup folder aplikasi dan data sesi.
3. Ekstrak patch ke folder utama KACA.ID dengan mempertahankan struktur folder.
4. Timpa backend/camera_server.py dan src/app.js.
5. Jalankan run-kaca-id.bat.
6. Buat sesi baru untuk pengujian. Sesi lama tidak otomatis memperbaiki file render yang belum pernah dibuat.

Penting:
- QR Google Drive memerlukan URL folder Drive yang valid. File QR lokal hanya bisa dipindai bila berisi URL yang benar.
- Upload Drive berjalan per-file saat file lokal tersedia, tetapi memerlukan koneksi dan folder Drive yang berhasil dibuat.
- Pengujian kode lokal tidak menggantikan pengujian kamera, codec Chromium, dan OAuth Google Drive pada PC booth.
