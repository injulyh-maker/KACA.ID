KACA.ID v0.9.24 — fitur tambahan dan build Windows

FITUR BARU
1. Keyboard numerik virtual muncul saat input PIN dan nomor WhatsApp mendapat fokus. Mendukung angka, hapus, backspace, dan tombol selesai.
2. Lokasi penyimpanan lokal dapat dipilih dari Pengaturan Umum. Perubahan berlaku untuk sesi berikutnya; arsip lama tidak dipindahkan otomatis. Jika drive tujuan tidak tersedia, backend memakai folder Pictures bawaan agar aplikasi tidak gagal start.
3. Slot frame dapat diduplikasi. Slot visual baru mewarisi sumber foto slot sebelumnya; pemetaan sumber foto dapat diubah per slot. Jumlah kesempatan pemotretan mengikuti indeks foto sumber tertinggi + 1, sehingga slot dengan sumber Foto 1 yang diduplikasi tidak menambah jatah foto.
4. Latar dashboard mendukung video atau foto, opsi hapus latar kustom, dan opsi kembali ke latar bawaan.
5. Canon EDSDK active files dan EDSDK.dll dipertahankan identik dari basis v0.9.21/v0.9.23.

BUILD INSTALLER WINDOWS
- Host build harus Windows 10/11 x64 dengan Node.js LTS, npm, dan koneksi internet.
- Jalankan build-windows-installer.bat. Script menjalankan electron-builder NSIS dan menghasilkan dist\KACA-ID-Setup-0.9.24-x64.exe.
- Jika build dari proyek lengkap, Python/OpenCV perlu dipasang pada komputer target. Setelah installer selesai dipasang, jalankan setup-python.bat dari folder instalasi satu kali (Python 3.10-3.12 harus terpasang, centang Add Python to PATH).
- Setelah setup Python selesai, jalankan KACA.ID dari shortcut.
- Canon EDSDK membutuhkan EOS Utility/aplikasi lain tidak mengunci kamera, kabel USB data, driver Canon, dan pengujian fisik pada EOS.

BATAS VALIDASI
- Pemeriksaan sintaks JS/Python, pemetaan slot duplikat JPG/Live Photo, API pemilihan folder lokal, struktur arsip lokal dan ZIP dilakukan otomatis.
- Lingkungan pengembangan ini berjalan di Linux dan tidak dapat menghasilkan atau menguji installer Windows NSIS. Akses npm registry saat ini gagal DNS (EAI_AGAIN), sehingga electron-builder tidak dapat diunduh. File installer .exe belum dihasilkan; build-windows-installer.bat disediakan untuk dijalankan pada Windows yang memiliki akses npm registry.
- Kamera Canon EOS 1300D, printer Windows, dan UI touchscreen perlu diuji pada perangkat booth sesungguhnya.
