KACA.ID v0.9.64 — PERBAIKAN QR DAN LIVE PHOTO PADA SLIDE HASIL

Berbasis source lengkap v0.9.63. Perubahan dibatasi pada pemulihan aset QR dan Live Photo di slide hasil.

PERBAIKAN:
1. Endpoint video /api/session/<id>/output_live.mp4 dan output_live.webm sekarang mencari file pada:
   - direktori sesi: data/sessions/<id>/
   - arsip lokal: <local_archive_path>/Live_Photos/Live_Photo_Frame.mp4 atau .webm
2. Pemetaan file arsip tetap menggunakan nama endpoint logis output_live.mp4/output_live.webm, sehingga frontend lama tidak perlu mengetahui struktur folder arsip.
3. Dukungan HTTP Range (206 Partial Content) yang sudah ada tetap dipertahankan untuk pemutaran dan seeking HTML5 Chromium/Electron.
4. Endpoint render-status kini memeriksa MP4/WebM pada direktori sesi DAN arsip lokal. Status tidak lagi menyatakan Live Photo tidak tersedia hanya karena salinan preview sesi tidak ada.
5. Prioritas preview tetap WebM, dengan MP4 sebagai fallback.
6. Pemeriksaan QR render-status dibatasi pada path sesi/arsip yang sah dan memeriksa file non-kosong. Endpoint QR tetap mencari manifest path, salinan sesi, dan Final_Results/QR_Google_Drive.png.
7. Seluruh alur kamera, Canon, printer, pembayaran, filter, frame, WhatsApp, dan upload Google Drive tidak diubah.

PENGUJIAN LOKAL:
- python -m py_compile backend/camera_server.py
- node --check src/app.js
- Tes regresi sumber QR, WebM, manifest recovery, render worker, dan live preview v0.9.63
- tests/result_archive_media_fallback_v0964_test.py

CATATAN:
Pengujian kode dilakukan pada lingkungan pengembangan. Pengujian pemutaran video Chromium, kamera Canon, printer, dan akun Google Drive tetap perlu dilakukan di PC booth. Untuk verifikasi QR, URL folder Drive pada manifest harus valid dan dapat diakses sesuai izin berbagi.

INSTALASI:
1. Tutup KACA.ID sepenuhnya.
2. Backup folder aplikasi dan data sesi.
3. Ekstrak paket ini ke folder baru atau folder aplikasi setelah backup.
4. Jalankan setup.bat bila dependensi belum tersedia, lalu run-kaca-id.bat.
5. Buat satu sesi uji baru. Untuk sesi lama, aset yang memang sudah tersimpan di arsip lokal sekarang dapat dicoba dimuat kembali.
