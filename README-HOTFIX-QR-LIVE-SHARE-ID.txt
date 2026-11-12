KACA.ID v0.9.63 - HOTFIX QR / WEBM LIVE PREVIEW / SHARE

File yang diperbarui:
- backend/camera_server.py
- src/app.js

Perbaikan:
1. Link folder Google Drive sekarang diprovisikan ulang dari endpoint render-status jika OAuth baru selesai setelah sesi difinalisasi. Sebelumnya callback OAuth hanya memulai folder untuk active_session, sedangkan /api/session/finish mengosongkan active_session. Kondisi ini dapat membuat sesi selesai tetap menunggu folder tanpa proses pembuatan link.
2. Setelah link Drive tersedia, QR PNG disimpan di data sesi lokal dan disalin ke folder arsip pelanggan: Final_Results/QR_Google_Drive.png. QR tidak dimasukkan ke antrean upload Google Drive.
3. Live Photo frame MP4 dan WebM di-encode dari frame komposisi yang sama. WebM diprioritaskan untuk preview Electron/Chromium, MP4 tetap dipertahankan sebagai master hasil.
4. Output dan detail Cetak kini memiliki aksi Share WhatsApp dan Share Email. Aksi menampilkan pesan jika link Drive belum tersedia, menunggu provisioning singkat jika sedang berlangsung, dan membuka WhatsApp/email melalui Electron.

Instalasi patch:
1. Tutup KACA.ID.
2. Backup folder aplikasi.
3. Ekstrak ZIP patch.
4. Timpa backend/camera_server.py dan src/app.js sesuai struktur folder.
5. Jalankan ulang run-kaca-id.bat.
6. Pastikan Google Drive sudah terhubung pada Pengaturan > Google Drive sebelum menguji sesi baru.

Catatan:
- QR Drive tidak dapat berisi tautan valid sebelum folder Drive berhasil dibuat. Jika akun belum terhubung, aplikasi akan tetap menampilkan status menunggu autentikasi.
- Kamera scan warnings DirectShow/MSMF pada indeks yang tidak dapat dibuka bukan penyebab QR/Share. Gunakan kamera yang berhasil dibuka (misalnya index 1 pada konfigurasi sebelumnya).
- Pengujian di lingkungan pengembangan: Python compile dan Node syntax checks lulus; tes terpilih live photo/WebM/WhatsApp lulus (4 passed). Pengujian fisik Windows, kamera, dan akun Google Drive pengguna belum dilakukan.
