KACA.ID v0.9.63 - Result Save on Entry Hotfix

Perubahan:
- Hasil frame JPG, Live Photo MP4, Live Photo WebM, dan GIF disalin ke folder arsip segera setelah render hasil tersedia (saat masuk slide hasil), tidak menunggu tombol SELESAI.
- QR_Google_Drive.png tidak lagi dihapus saat finalisasi. QR tetap lokal dan disalin ke Final_Results.
- WebM hanya disimpan lokal untuk preview Electron/Chromium dan tidak dimasukkan antrean upload Google Drive.
- MP4, JPG frame, dan GIF tetap dapat diunggah ke Google Drive.
- Countdown slide hasil diinisialisasi dan diperbarui eksplisit.

File patch:
backend/camera_server.py
src/app.js

Instalasi: tutup aplikasi, backup folder, ekstrak patch ke root aplikasi dengan mempertahankan struktur folder, timpa file, lalu jalankan run-kaca-id.bat.

Catatan: tes lokal memeriksa sintaks. Autentikasi Google Drive, kamera, dan printer tetap harus diuji di PC booth.
