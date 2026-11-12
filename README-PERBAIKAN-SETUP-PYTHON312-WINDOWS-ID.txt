KACA.ID v0.9.89 — Perbaikan setup Windows untuk pembuat installer (Python 3.12)
==============================================================================

Error lama:
"Mesin BUILDER memerlukan Python 3.12 untuk menyiapkan wheel Win x64"
terjadi karena skrip hanya mencari Python yang sudah terpasang dan menghentikan setup.

Perbaikan:
- Cari Python 3.12 x64 lewat launcher py, PATH, lokasi instalasi umum dan cache.
- Jika belum tersedia, unduh python-3.12.10-amd64.exe dari python.org secara otomatis.
- Pastikan file ditandatangani oleh Python Software Foundation.
- Instal secara senyap hanya untuk user saat ini di:
  %LOCALAPPDATA%\KACA.ID\BuildTools\Python312
- Tidak mengubah PATH Windows, tidak menimpa Python sistem yang lain.
- Python untuk pelanggan tetap berbeda: runtime/python portable dimasukkan ke
  satu installer EXE dengan OpenCV/NumPy, sehingga pelanggan tidak memasang Python.
- Visual C++ x64 dibundel untuk dipasang oleh installer NSIS saat diperlukan.

CARA PAKAI
1. Tutup PowerShell/terminal setup lama.
2. Backup folder source, ekstrak ZIP PATCH lalu salin ISINYA ke folder utama
   KACA.ID yang memiliki setup.bat dan package.json. Pilih Replace.
3. Di folder source KACA.ID jalankan setup.bat (klik ganda) dengan koneksi internet.
   Skrip menyiapkan Python 3.12 secara otomatis saat pertama dipakai.
4. Setelah setup selesai, jalankan build-windows-installer.bat untuk membuat EXE.
5. Verifikasi file dist\KACA-ID-Setup-0.9.90-x64.exe; uji instalasi pada mesin
   Windows bersih sebelum dibagikan.

Jika installer Python BUILD diblokir kebijakan perusahaan, pilihan manual pada
komputer PEMBUAT installer saja:
  winget install --id Python.Python.3.12 --exact
Lalu jalankan setup.bat lagi. Ini BUKAN syarat di komputer pelanggan.

KOMPONEN LAIN YANG TETAP PERLU ADA DI KOMPUTER BUILDER
- Node.js/npm (untuk membangun Electron).
- Internet saat membuat paket runtime dan installer pertama kali.
- Windows 10/11 x64.

CATATAN
- Ini perbaikan kode build, belum file EXE yang sudah dikompilasi.
- Installer EXE harus dibangun pada komputer Windows atau Windows CI.
- Jangan hapus folder data Cloud Control, lisensi, foto, Event, atau AppData.
