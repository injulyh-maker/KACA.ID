KACA.ID v0.9.63 - FULL SOURCE + QR LOKAL FIX

Isi:
- Source project KACA.ID v0.9.63 yang tersedia pada sesi ini.
- Perubahan terbaru pada backend/camera_server.py untuk menyimpan QR Google Drive sebagai PNG lokal di folder sesi (google_drive_qr.png).
- QR lokal tidak dimasukkan sebagai file upload Google Drive oleh perubahan ini.

Cara menggunakan di Windows:
1. Ekstrak seluruh ZIP ke folder kerja baru.
2. Jalankan setup.bat jika dependency/runtime belum disiapkan.
3. Jalankan run-kaca-id.bat.

Catatan:
- Ini adalah source code, bukan installer Windows.
- Pastikan kredensial/konfigurasi Google Drive milik instalasi Anda tetap tersedia.
- Perubahan QR sudah diperiksa dengan python -m py_compile pada backend/camera_server.py.
- Belum dilakukan pengujian end-to-end pada PC Windows, kamera, printer, atau akun Google Drive Anda.
