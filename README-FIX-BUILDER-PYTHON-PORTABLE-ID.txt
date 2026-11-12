KACA.ID v0.9.89 — FIX SETUP BUILDER PYTHON 3.12 TANPA INSTALLER EXE
=================================================================
Masalah lama:
  Python installer 3.12.10 dapat kembali dengan exit code 0 atau 3010,
  tetapi python.exe tidak muncul/dapat dijalankan di folder privat
  C:\Users\...\AppData\Local\KACA.ID\BuildTools\Python312.

Perbaikan:
  - Tidak lagi menjalankan Python-3.12.10-amd64.exe untuk komputer builder.
  - Memakai runtime/python/python.exe embeddable x64 dari Python.org yang
    memang sudah menjadi isi paket installer KACA.ID pelanggan.
  - Mengunduh pip 26.1.2 wheel pure Python dari PyPI, memvalidasi SHA256
    pinned, lalu mengekstraknya ke runtime/build-pip (hanya untuk builder).
  - Memasang wheel Windows x64 langsung melalui Python embeddable 3.12
    ke runtime/python/Lib/site-packages.
  - Memulihkan python312._pth ke setelan customer seusai setup atau saat error.
  - Windows pelanggan tetap tidak memerlukan Python, pip, atau Node.js global.

CARA MENERAPKAN PATCH:
  1. Tutup jendela setup.bat yang gagal.
  2. Backup folder source KACA.ID.
  3. Salin build/prepare-windows-runtime.ps1 dari ZIP patch ke lokasi
     <folder source KACA.ID>\build\prepare-windows-runtime.ps1.
  4. Jalankan ulang setup.bat dengan internet aktif dan hak tulis folder.
  5. Setelah Setup selesai, jalankan build-windows-installer.bat.
  6. Hasil yang diharapkan: dist\KACA-ID-Setup-0.9.90-x64.exe.

PENTING:
  - Tidak perlu menghapus folder sesi, pengaturan, data Cloud, atau lisensi.
  - Tidak perlu memasang Python 3.12 ke Windows secara manual.
  - Akses dibutuhkan ke python.org, pypi.org, files.pythonhosted.org,
    dan Microsoft agar wheel dan VC++ dapat diunduh pada komputer BUILDER.
  - Node.js LTS dibutuhkan pada komputer BUILDER saja.
  - Tidak ada perubahan pada kode aplikasi, server Cloud, atau lisensi.
  - Build EXE Windows sungguhan tidak dijalankan dalam lingkungan ini;
    skrip harus diuji pada komputer Windows builder milik Anda.

DIAGNOSTIK JIKA MASIH ADA ERROR:
  Dari folder utama source, jalankan di PowerShell:
    powershell -NoProfile -ExecutionPolicy Bypass -File .\build\prepare-windows-runtime.ps1
  Periksa 10–20 baris terakhir jika gagal; jangan tampilkan token pribadi.
