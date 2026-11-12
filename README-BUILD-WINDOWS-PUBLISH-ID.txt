KACA.ID v0.9.88 — WINDOWS INSTALLER OFFLINE / FULL RUNTIME
===========================================================

TUJUAN
Satu installer Windows (.exe) yang dapat dipakai pelanggan tanpa memasang:
- Python, pip, maupun paket Python secara manual.
- Microsoft Visual C++ Redistributable secara manual.
- Node.js, Electron, Git, atau tool pemrograman.

Apa yang dibundel otomatis dalam installer:
- Electron runtime (Chromium + Node) dari electron-builder.
- Python 3.12.10 EMBEDDABLE x64 disimpan di resources/python.
  Alasan: Canon SDK Python binding yang ada dalam source mendukung CPython 3.12.
- OpenCV, NumPy, Pillow, QRCode serta dependensi Cloud Control.
- Microsoft Visual C++ v14 Redistributable x64 (dari Microsoft resmi),
  disimpan di resources/vc_redist.x64.exe, dipasang otomatis dengan izin admin
  ketika belum tersedia; tidak perlu terhubung internet ketika instalasi.
- Aset aplikasi, backend, modul Cloud Control, dan kode launcher Electron.

INSTALER TIDAK MENJALANKAN pip ATAU mengunduh file apa pun di komputer pelanggan.
Pengunduhan Python, modul, Electron, VC++ dilakukan HANYA di komputer BUILD / GitHub Actions.

METODE 1 — OTOMATIS DENGAN GITHUB ACTIONS (DIREKOMENDASIKAN)
1. Buat repository GitHub privat untuk aplikasi KACA.ID.
2. Upload SEMUA isi folder source ini ke root repository, termasuk folder
   tersembunyi .github/workflows/ (jangan hanya menaruh ZIP di repo).
3. Buka repository -> Actions -> "KACA.ID - Windows Installer (Python + VC++ included)".
4. Klik "Run workflow" pada branch main.
5. Setelah build hijau, buka job selesai -> Artifacts -> KACA-ID-Setup-0.9.90-x64.
6. Download artifact, ekstrak, dan temukan KACA-ID-Setup-0.9.90-x64.exe.
7. PUBLISH file .exe setelah diuji pada Windows 10/11 x64 yang bersih.

Metode ini tidak membutuhkan Node/Python terpasang di laptop developer. GitHub
Actions otomatis menggunakan Windows build runner untuk membuat EXE.

METODE 2 — BUILD DI WINDOWS SENDIRI
Prasyarat MESIN PEMBUAT (BUKAN pelanggan):
- Windows 10/11 x64, internet pada saat BUILD.
- Node.js 22 + npm.
- Python 3.12 x64 + pip.
- Jalankan build-windows-installer.bat dari folder source.
- Installer selesai di dist/KACA-ID-Setup-0.9.90-x64.exe.

PERILAKU PEMASANGAN DI KOMPUTER PELANGGAN
1. Double-click KACA-ID-Setup-0.9.90-x64.exe.
2. Windows meminta izin administrator (UAC) untuk instalasi per-machine dan
   Microsoft Visual C++ Redistributable; klik Yes.
3. Installer memasang aplikasi, Python privat dan VC++ tanpa internet.
4. Jika Windows meminta restart setelah VC++, lakukan restart sebelum membuka.
5. Buka "KACA.ID Photobooth" dari Desktop/Start Menu.
6. Aplikasi memakai Python sendiri tanpa mengubah Python global atau PATH.

PENTING
- Kamera Canon masih memerlukan driver / SDK Canon yang sesuai model kamera.
  Bundling Python+VC++ TIDAK menggantikan driver hardware Canon.
- Printer memerlukan driver printer dari pembuat printer.
- Cloud Control WEB masih memerlukan server/domain sendiri apabila ingin diakses
  dari internet; installer desktop ini tidak otomatis membuat hosting cloud.
- Lisensi Cloud Control, Google Drive, dan Fonnte tetap harus dikonfigurasi.
- Installer ini untuk Windows 10/11 x64.
- Windows SmartScreen dapat memperingatkan jika aplikasi belum ditandatangani
  dengan sertifikat code-signing tepercaya; kode sumber bukan malware,
  namun untuk publish komersial sebaiknya lakukan code signing.
- Vendor harus mematuhi lisensi distribusi Visual C++, Python dan Canon EDSDK.

BUKTI PEMERIKSAAN BUILD
- Script verify-windows-installer.ps1 memeriksa EXE, Python privat,
  VC++ bertanda tangan Microsoft, manifest runtime, modul import Python,
  source backend, dan membuat file SHA-256.
- Jika ada dependensi yang hilang atau gagal, build gagal, tidak mengunggah EXE.
- Pengujian kamera fisik, pembayaran/Drive nyata, dan instalasi pertama pada PC
  Windows baru harus dilakukan oleh operator/publisher sebelum publikasi umum.

STATUS FILE
- ZIP yang diberikan merupakan SOURCE + SISTEM BUILD. File installer Windows
  baru muncul SETELAH menjalankan build di Windows runner/GitHub Actions.
- Jangan mengganti ekstensi ZIP menjadi EXE atau mempublikasikan EXE yang belum lolos verifikasi.

SUMBER RESMI
Python: https://www.python.org/ftp/python/3.12.10/
VC++: https://aka.ms/vc14/vc_redist.x64.exe
Electron NSIS: https://www.electron.build/nsis
