KACA.ID v0.9.35 — HOTFIX DEPENDENSI QR DAN FILE BATCH

Perbaikan:
- Menambahkan qrcode>=7.4,<9 ke requirements.txt agar setup.bat memasang modul QR Code ke .venv.
- Menghapus UTF-8 BOM dari file .bat/.cmd yang sebelumnya membuat cmd.exe membaca karakter aneh sebelum @echo off.
- Memperbarui metadata versi ke 0.9.35.

PENTING UNTUK PEMAKAI v0.9.34:
1. Ekstrak source v0.9.35 ke folder baru (disarankan D:\KACA\KACA-ID-v0.9.35).
2. Jalankan setup.bat agar qrcode dipasang ke virtual environment.
3. Jalankan verify-kaca-id.bat.
Jangan hanya menimpa requirements.txt lalu melewati setup.bat; paket qrcode harus benar-benar terpasang pada .venv yang dipakai aplikasi.

Catatan: pengujian Google Drive tetap menggunakan mock; login OAuth dan pemindaian QR dengan akun/perangkat nyata perlu diuji di PC pengguna.
