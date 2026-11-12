KACA.ID v0.9.90 - Perbaikan builder Windows lokal (Python 3.14 terdeteksi)

Masalah sebelum patch:
  AssertionError: 3.14.8
  Builder memerlukan Python 3.12 x64

Penyebab: script mengambil python.exe pertama dari PATH, walaupun itu Python 3.14.
Python portable 3.12 yang diunduh untuk pelanggan BUKAN Python builder dengan pip.

Perbaikan:
1. Deteksi otomatis Python 3.12 x64 + pip, termasuk via launcher `py -3.12`.
2. Jika tidak ada, unduh installer resmi Python 3.12.10 x64, verifikasi
   tanda tangan Python Software Foundation, lalu pasang hanya untuk build
   di folder proyek BuildTools\Python312 (tanpa mengubah PATH Python 3.14).
3. Dependensi cp312 dipasang privat ke runtime\python\Lib\site-packages.
4. Periksa import modul sebelum membuat installer; unduh VC++ resmi bersertifikat.
5. Nama file hasil EXE yang diverifikasi sudah benar untuk v0.9.90.

Cara menjalankan:
- Ekstrak arsip patch KE DALAM folder KACA-ID-PUBLISH milik Anda.
  Izinkan overwrite file build/prepare-windows-runtime.ps1 dan
  build-windows-installer.bat. Jangan hapus folder data, runtime, atau lisensi.
- Jalankan build-windows-installer.bat dari folder KACA-ID-PUBLISH.
- Jika instalasi builder otomatis gagal, jalankan GitHub Actions di repo privat,
  atau instal Python 3.12 x64 secara manual dari python.org.
- PC builder membutuhkan Node.js/npm dan koneksi internet untuk mengunduh
  dependensi. Komputer pelanggan nantinya tidak membutuhkan Python global.
- Setelah sukses, cari dist\KACA-ID-Setup-0.9.90-x64.exe.

Catatan: Patch skrip telah diperiksa secara statis tetapi BELUM dijalankan
pada Windows pada lingkungan penyusunan ini. Perlu build dan tes PC Windows.
- Folder BuildTools/ dicantumkan dalam .gitignore. Jangan upload builder Python privat
  ke GitHub; hanya source aplikasi yang perlu masuk repository.
- Gagal sebelum tahap npm? Periksa akses unduh installer Python 3.12 dari
  python.org, akses tulis ke direktori proyek, serta log dalam folder TEMP.
