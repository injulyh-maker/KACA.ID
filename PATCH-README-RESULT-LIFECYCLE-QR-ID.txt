KACA.ID v0.9.63 - RESULT LIFECYCLE / EARLY DRIVE QR / TRANSIENT WEBM PATCH

Tujuan:
- Memastikan tombol SELESAI dan countdown mengembalikan aplikasi ke Dashboard melalui satu jalur idempoten.
- QR Google Drive dibuat dari URL folder yang diprovisikan sejak POST /api/session/start. QR PNG dirender in-memory melalui /api/session/<id>/qr.png dan tidak ditulis sebagai file lokal maupun diunggah ke Drive.
- Pembuatan folder Drive tetap berjalan asinkron sejak sesi dimulai dan kini mencoba ulang hingga lima kali jika handshake/koneksi sementara gagal.
- File Live Photo MP4 tetap menjadi hasil unduhan/arsip. Preview WebM hanya dipakai sementara selama slide Hasil; tidak disalin ke arsip lokal/Drive dan dihapus saat pelanggan kembali ke Dashboard.
- ZIP arsip lokal dibersihkan dari QR PNG dan WebM lama sebelum dibangun ulang.

Pemasangan patch:
1. Tutup KACA.ID sepenuhnya.
2. Cadangkan folder src dan backend.
3. Ekstrak isi ZIP patch ke folder utama KACA-ID-v0.9.63-WINDOWS-BUILD-SOURCE.
4. Izinkan penggantian file.
5. Jalankan run-kaca-id.bat.
6. Uji dengan sesi BARU. QR hanya dapat muncul setelah folder Google Drive selesai dibuat; upload file ke folder boleh masih berlangsung.

Pemeriksaan yang dilakukan di lingkungan pengembangan:
- node --check src/app.js
- python -m py_compile backend/camera_server.py
- tests/result_slide_reliability_v0963_test.py
- tests/result_originals_unfiltered_v0963_test.py
- tests/session_qr_test.py (mock Google Drive, tidak memakai akun pengguna)
- tests/session_render_worker_v0963_test.py

Belum diuji pada komputer Windows/kamera/printer pengguna.
