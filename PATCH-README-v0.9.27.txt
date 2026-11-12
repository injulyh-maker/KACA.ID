KACA.ID v0.9.27 PATCH

Patch ini ditujukan untuk source KACA.ID v0.9.26. Tutup aplikasi dan backend lama sepenuhnya, ekstrak patch ke folder source v0.9.26, lalu izinkan overwrite. Jalankan verify-kaca-id.bat dan build-windows-installer.bat di Windows.

Isi utama:
- Editor visual menggunakan struktur HTML/CSS komponen layar aktual, bukan mockup generik.
- Integrasi Google Drive OAuth 2.0, folder upload per sesi, resumable upload, tautan berbagi, status dan antrean retry offline.
- Pengaturan Google Drive di Pengaturan Umum dan tautan cloud di Arsip Sesi/Hasil.
- Video standalone juga diunggah otomatis ke Google Drive.
- Canon EDSDK inti tidak diubah.

Baca README-v0.9.27-ID.txt untuk menyiapkan Google Cloud OAuth Client ID dan batas pengujian.
