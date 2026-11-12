# KACA.ID v0.9.90 — Perbaikan builder Windows Python 3.12 (NuGet)

## Kenapa gagal sebelumnya

Skrip lama menjalankan installer Python 3.12 `.exe` secara senyap. Instalasinya dapat selesai tanpa menghasilkan `BuildTools\Python312\python.exe` pada path yang diharapkan, misalnya bila sudah ada instalasi Python lain. Error ini **bukan** masalah Windows Cloud atau lisensi.

## Yang diperbaiki

Skrip `build\prepare-windows-runtime.ps1` kini:

1. mencari Python 3.12 x64 dengan pip yang sudah tersedia, tanpa memilih Python 3.14;
2. bila tidak ditemukan, mengunduh paket Python 3.12.10 x64 dari NuGet resmi ke folder builder privat (tanpa menjalankan installer EXE/MSI);
3. memverifikasi paket dengan SHA-512 dari feed NuGet;
4. mengekstrak `BuildTools\Python312\tools\python.exe`;
5. menyiapkan `pip` di builder privat dengan `ensurepip` (atau bootstrap resmi PyPA jika diperlukan);
6. memasang dependensi ke **runtime Python embeddable** yang terpisah, yang nantinya disertakan dalam installer pelanggan.

Python 3.14 pengguna, PATH Windows, data pelanggan, lisensi, dan file foto tidak diubah oleh skrip ini.

## Cara pakai patch

1. Tutup proses build lama.
2. Ekstrak ZIP **Patch Builder NuGet** dan salin `build\prepare-windows-runtime.ps1` ke folder `KACA-ID-PUBLISH\build\`, pilih **Replace**.
3. Jalankan `build-windows-installer.bat` dari folder `KACA-ID-PUBLISH`.
4. Jika build berhasil dan lolos verifikasi, file keluaran yang diharapkan ialah `dist\KACA-ID-Setup-0.9.90-x64.exe`.

Alternatif: gunakan paket lengkap **KACA-ID-v0.9.90-PUBLISH-SOURCE-NUGET-BUILDER-FIX.zip** tanpa memasang patch terpisah.

## Jika unduhan NuGet terblokir

Pastikan Windows builder dapat mengakses `https://api.nuget.org` dan `https://bootstrap.pypa.io` (hanya jika pip perlu bootstrap). Pada jaringan yang memblokir feed ini, gunakan workflow GitHub Actions yang telah menyiapkan Python 3.12 x64 melalui `actions/setup-python`.

Tidak perlu menghapus folder data AppData, database, dan lisensi. Folder `BuildTools` dan `runtime` hanyalah berkas build.

**Status:** Perubahan kode dan struktur ZIP sudah diperiksa, tetapi build EXE sesungguhnya harus diuji di Windows / GitHub Actions. Jangan distribusikan EXE sebelum proses build dan pengujian installer selesai.
