KACA.ID v0.9.53 - PERBAIKAN BACKEND, KAMERA, DAN INSTALLER

Perubahan utama:
- Backend yang tertinggal dari versi lama tidak lagi dianggap cocok hanya karena /health merespons. Health sekarang memuat app_version dan backend_protocol.
- Aplikasi memakai single-instance lock dan membersihkan backend KACA yang dikelola saat aplikasi ditutup.
- Runtime Windows memakai CPython 3.13.17 portable, bukan Python 3.15 dari PATH pengguna.
- Setup build menyiapkan runtime Python, OpenCV, Pillow, qrcode, dan Microsoft Visual C++ Redistributable x64.
- Installer memasukkan runtime Python dan menjalankan pemasangan VC++ Redistributable secara senyap.

Pembuatan installer (komputer developer):
1. Pastikan Node.js LTS dan npm tersedia.
2. Jalankan setup.bat (mengunduh runtime portable dan dependensi).
3. Jalankan npm.cmd run dist:win.
4. File installer ada di dist.

Pengguna akhir cukup menjalankan KACA-ID-Setup-0.9.53-x64.exe. Tidak perlu memasang Python, Node.js, atau menjalankan script.

Catatan: build installer Windows dan uji kamera fisik/Canon/printer harus dilakukan di Windows. Paket runtime disiapkan saat setup-runtime.bat dijalankan; jangan menghapus folder runtime sebelum proses dist:win selesai.
