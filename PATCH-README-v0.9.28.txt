KACA.ID v0.9.28 PATCH — WhatsApp Cloud API Otomatis

CARA MENERAPKAN
1. Tutup aplikasi KACA.ID.
2. Buat salinan cadangan folder proyek v0.9.27.
3. Ekstrak isi ZIP patch ke folder proyek v0.9.27 dan izinkan file yang sama ditimpa.
4. Jalankan verify-kaca-id.bat.
5. Jalankan build-windows-installer.bat untuk membuat installer 0.9.28.

FILE UTAMA YANG BERUBAH
- backend/camera_server.py: antrean WhatsApp persisten, menunggu Google Drive siap, dan endpoint status/kirim/retry.
- backend/whatsapp_cloud.py: konfigurasi dan pengiriman template WhatsApp Cloud API.
- src/app.js dan src/src/app.js: pengaturan API, persetujuan pelanggan, tombol kirim otomatis, polling status.
- src.zip: bundle UI diperbarui.
- package.json/package-lock.json: versi 0.9.28.

Canon EDSDK tidak diubah.

Catatan: kredensial Meta dan template Utility yang disetujui harus disiapkan pemilik booth. Pengiriman nyata tidak dapat diuji tanpa kredensial tersebut.
