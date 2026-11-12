KACA.ID v0.9.54 - STABILITAS BACKEND, KAMERA, VOUCHER, DAN RUNTIME WINDOWS

Perubahan utama:
- Menghindari CORS preflight yang tidak perlu dari renderer file:// ke API lokal. GET tidak lagi mengirim Content-Type JSON; permintaan JSON menggunakan text/plain yang tetap dibaca sebagai JSON oleh backend.
- Pesan kegagalan API lebih informatif: membedakan timeout dan backend lokal yang tidak dapat dijangkau.
- Backend lama hanya dipakai ulang bila versi aplikasi dan protokolnya cocok. Backend versi lama dihentikan sebelum backend versi baru dijalankan.
- Runtime Windows menggunakan CPython 3.13.17 portable beserta OpenCV, Pillow, qrcode, dan Microsoft Visual C++ Redistributable x64.
- Installer memasukkan Python portable dan memasang VC++ Runtime secara otomatis. Pengguna akhir tidak perlu memasang Python, Node.js, atau menjalankan script.

Build developer (Windows):
1. Instal Node.js LTS pada komputer pembuat installer saja.
2. Jalankan setup.bat untuk mengunduh runtime Python portable dan dependensi.
3. Jalankan npm.cmd run dist:win.
4. Distribusikan KACA-ID-Setup-0.9.54-x64.exe dari folder dist.

Catatan: proses pembuatan installer dan pengujian kamera fisik/Canon harus dilakukan di Windows. Pastikan folder runtime ikut ada saat build.
