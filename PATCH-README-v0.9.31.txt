KACA.ID v0.9.31 PATCH

Patch hotfix untuk source v0.9.30.
Salin isi ZIP ke folder source v0.9.30 dan izinkan file yang sama ditimpa.
File yang diubah:
- backend/camera_server.py
- tests/session_qr_test.py
- package.json
- package-lock.json
- build-windows-installer.bat
- README-v0.9.31-ID.txt

Perbaikan utama: QR PNG sekarang ditulis tanpa Pillow agar pembuatan QR tidak gagal saat DLL PIL._imaging tidak dapat dimuat di Windows.
Setelah patch, jalankan verify-kaca-id.bat dan build-windows-installer.bat.
