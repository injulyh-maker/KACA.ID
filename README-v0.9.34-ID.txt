KACA.ID v0.9.34 — APP LOGS & RAM OPTIMIZATION

FITUR BARU
- Menu App Logs pada Pengaturan Admin > Pengaturan Umum.
- Log Electron, renderer JavaScript, backend Python stdout/stderr, dan status renderer unresponsive/crash dicatat lokal.
- Rotasi log: satu file aktif maksimum sekitar 2 MB dan tiga arsip rotasi.
- Tombol muat ulang, buka folder log, dan bersihkan log.
- Pengiriman file foto, video, QR, GIF, dan ZIP backend menggunakan streaming bertahap (256 KB) agar tidak membaca seluruh file ke RAM sekaligus.

LOKASI LOG
Folder logs berada di direktori data pengguna Electron (app.getPath('userData')/logs).

CATATAN PENGUJIAN
Tes otomatis tidak menggantikan pengujian kamera fisik, Canon EOS, printer, WhatsApp, atau Google Drive akun nyata. Log dapat berisi path lokal, nama perangkat, atau rincian error; periksa sebelum membagikannya.

INSTALASI
Ekstrak source ke folder baru, jalankan setup.bat, verify-kaca-id.bat, lalu build-windows-installer.bat pada Windows.
