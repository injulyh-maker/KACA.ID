KACA.ID v0.9.61 — Customer Flow, Frame Navigation, and Backend Compatibility

Perbaikan utama:
1. Panel sesi pemotretan (captureGrid) benar-benar dipindahkan ke DocumentFragment saat slide Transaksi, Voucher, Pilih Frame, Filter, dan Hasil aktif. Panel tidak sekadar ditutup dengan CSS dan tidak ikut berada dalam DOM/layout slide tersebut.
2. Panel capture dipasang kembali hanya saat slide Sesi Pemotretan dibuka. Referensi elemen kamera diambil dari captureGrid yang stabil melalui $cap(), sehingga fungsi update tidak bergantung pada document.querySelector untuk elemen yang sedang dilepas.
3. Kamera dan stream tidak dibuka saat slide Transaksi atau Pilih Frame. Kamera baru dibuka setelah frame dipilih dan pengguna menekan Lanjut.
4. Tombol Lanjut menunggu kamera aktif, lalu memulai sesi. Kegagalan backend ditampilkan pada status yang terlihat di slide Pilih Frame; tidak lagi menelan error dari handler sesi.
5. Keyboard virtual Voucher dipulihkan (angka, QWERTY, hapus, bersihkan) dan mendukung layar sentuh.
6. Backend protocol dinaikkan ke 3. Electron menolak backend lama (termasuk v0.9.58/protocol 2), menghentikan proses backend KACA yang terdeteksi dari endpoint health, lalu menjalankan backend yang cocok dengan versi aplikasi.

Validasi yang dijalankan:
- node --check src/app.js dan main.js
- python -m py_compile backend/camera_server.py
- tes alur customer v0.9.61, navigasi frame, layout UI, voucher/QRIS, backend health/version, dan sinkronisasi file UI.
- tes integritas ZIP dan simulasi penerapan patch ke source v0.9.56.

Build installer Windows dan uji kamera fisik/Canon/printer/Google Drive nyata belum dilakukan pada lingkungan audit ini. Source v0.9.56 yang diberikan tidak menyertakan runtime portable; jalankan setup.bat pada Windows untuk mengunduh runtime dan dependencies sebelum npm.cmd run dist:win.
