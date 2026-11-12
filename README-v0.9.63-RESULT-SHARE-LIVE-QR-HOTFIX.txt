KACA.ID v0.9.63 – Result Share / Live Preview / QR Diagnostic Hotfix

Perubahan:
1. Membuka tautan WhatsApp sekarang diizinkan melalui Electron shell.openExternal (wa.me, web.whatsapp.com, api.whatsapp.com).
2. Tombol Share via Email memakai bridge Electron yang sama untuk membuka mailto, dan menampilkan pesan error bila tidak ada aplikasi email.
3. Preview Live Photo di slide hasil menampilkan kontrol pemutaran, mencoba WebM terlebih dahulu, lalu fallback ke MP4 bila WebM tidak dapat diputar.
4. Jika QR image gagal dimuat, UI meminta respons endpoint QR dan menampilkan error backend yang sebenarnya, bukan terus menampilkan pesan generik.

Catatan:
- QR Google Drive hanya dapat dibuat setelah Google Drive terhubung dan backend menerima drive_url folder sesi. Jika status menyatakan waiting_auth/error, hubungkan ulang Google Drive atau periksa log backend.
- Share via WhatsApp membuka WhatsApp dengan pesan terisi; operator/pelanggan tetap menekan Kirim. WhatsApp Cloud API memerlukan kredensial API yang valid.
- Tes pada paket ini: node --check main.js, node --check src/app.js, python -m py_compile backend/camera_server.py. Belum diuji pada perangkat Windows/kamera/akun Google Drive pengguna.

Pemasangan patch:
1. Tutup KACA.ID sepenuhnya.
2. Ekstrak ZIP patch.
3. Salin main.js ke folder utama aplikasi (timpa file lama).
4. Salin src/app.js ke folder src (timpa file lama).
5. Jalankan kembali run-kaca-id.bat.
