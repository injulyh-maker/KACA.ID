KACA.ID v0.9.55 — STABILITAS UI & PREVIEW

Fokus versi ini:
1. Pengaturan Umum tidak lagi menunggu jeda pemindaian kamera tetap 1,8 detik. Status Google Drive dan permintaan pemindaian kamera dimulai secara paralel.
2. Navigasi memiliki generation token. Hasil pemuatan Frame, Pengaturan Umum, dan Pembayaran yang terlambat tidak boleh menimpa halaman yang lebih baru.
3. Preview filter menggunakan thumbnail lokal berukuran maksimum 640x480, bukan mengunduh foto original resolusi penuh.
4. Thumbnail dimuat paralel dan render preview memiliki revision guard agar hasil lama tidak menimpa pilihan filter/foto terbaru.
5. Foto original, file final, dan file cetak tidak diturunkan kualitasnya. Thumbnail hanya dipakai untuk tampilan preview.
6. Memulihkan dan mempertahankan pre-render foto/Live Photo pada slide Filter sebelum pelanggan masuk ke slide Hasil.
7. Menambah endpoint preview thumbnail dengan cache terpisah dari folder sesi dan arsip pelanggan.

PEMBUATAN INSTALLER WINDOWS
- Ekstrak source ke folder baru.
- Jalankan setup.bat sebagai pengguna Windows yang akan membuat installer.
- Pastikan proses setup selesai tanpa error.
- Jalankan npm.cmd run dist:win.
- Installer akan dibuat di folder dist.

PENGGUNA AKHIR
Pengguna cukup menjalankan installer KACA.ID. Python portable dan Visual C++ Runtime tetap mengikuti konfigurasi bundling installer.

CATATAN PENTING
- Belum dilakukan pengujian kamera Canon/webcam fisik, printer fisik, dan sesi photobooth panjang pada Windows.
- Tahap ini belum memindahkan penulisan video dari jalur kamera ke writer worker. Itu memerlukan refactor antrean video tersendiri agar tidak mengorbankan Live Photo dan sinkronisasi frame.
- Tetap simpan backup source v0.9.54.
