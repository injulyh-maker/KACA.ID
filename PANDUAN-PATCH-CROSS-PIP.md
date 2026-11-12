# KACA.ID v0.9.90 — Patch Windows Builder (tanpa NuGet)

## Mengapa patch ini diperlukan
Skrip lama gagal mengunduh `python.3.12.10.nupkg` dari NuGet dengan HTTP 404. Patch ini **menghapus kebutuhan NuGet sepenuhnya**. Dengan `pip` dari Python yang sudah terpasang di PC builder (termasuk Python 3.14), skrip meminta paket wheel binary untuk target `cp312` + `win_amd64` secara eksplisit. Python embeddable 3.12.10 tetap disiapkan sebagai runtime yang ikut di-installer dan digunakan untuk memeriksa impor modul saat proses build.

## Cara pakai
1. Ekstrak ZIP patch. Salin `build/prepare-windows-runtime.ps1` ke `KACA-ID-PUBLISH/build/` (timpa file lama). **Jangan hapus** database, AppData, lisensi, ataupun folder hasil sesi.
2. Buka PowerShell, jalankan `python -m pip --version`. Jika berhasil menampilkan versi pip, lanjutkan.
3. Jalankan ulang `build-windows-installer.bat` di root `KACA-ID-PUBLISH`. Script batch menggunakan `-Force` sehingga folder runtime lama direkonstruksi.
4. Pastikan log berisi `pip host dipilih`, `Mengambil paket khusus CPython 3.12 Windows x64`, lalu `[OK]` dari `runtime_preflight.py`.

## Jika Python sudah ada tetapi pip tidak ada
Jalankan `python -m ensurepip --upgrade` untuk menambahkan pip di mesin builder. Jika ada beberapa Python, set `$env:KACA_PIP_PYTHON='C:\lokasi\python.exe'` sebelum menjalankan skrip PowerShell, atau pastikan Python dengan pip muncul di PATH.

## Keamanan dan batasan
- Tidak menggunakan/menjalankan installer Python NuGet atau file EXE pihak ketiga.
- Tidak mengganti PATH atau Python global.
- Python 3.14 hanya menjalankan pip. Seluruh modul native dipilih khusus untuk Python 3.12 Windows x64.
- Installer belum dikompilasi dalam lingkungan ini; perlu diuji pada Windows. Pastikan lulus `runtime_preflight.py` dan verifikasi installer sebelum didistribusikan.
- Jika suatu dependensi tidak menyediakan wheel `win_amd64` yang kompatibel dengan Python 3.12, pip akan gagal dengan pesan eksplisit. Jangan memaksa menginstal wheel Python 3.14.
- Jika berhasil build tetapi aplikasi tidak berjalan pada PC baru, uji di mesin Windows bersih dengan tanpa Python global.

## Log jika masih gagal
Kirim mulai dari baris `pip host dipilih` sampai pesan error terakhir (hapus token/rahasia bila ada). Jika `python -m pip --version` gagal, kirim hasil `where.exe python` dan `py -0p`.
