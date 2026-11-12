KACA.ID v0.9.41 — PATCH NOTES

Perbaikan utama:
1. Konversi MP4 Live Photo ke WebM sekarang berjalan di background setelah file MP4 selesai ditutup. Proses konversi tidak lagi menahan endpoint pemotretan berikutnya. MP4 asli tetap menjadi master arsip.
2. Halaman “Atur Nuansa Foto” menampilkan Live Photo sebagai komposisi di dalam frame: setiap klip diputar pada slot foto masing-masing, filter aktif diterapkan, dan overlay frame tetap berada di lapisan teratas. Tidak lagi memutar satu video mentah di atas kanvas.
3. Preview Live Photo memakai kanvas yang sama dengan preview hasil cetak; tombol FOTO DALAM FRAME dan LIVE PHOTO mengubah mode pratinjau.

Catatan pengujian: pemeriksaan sintaks dan tes otomatis sumber dijalankan. Uji kecepatan kamera, pemutaran WebM, dan tampilan frame tetap perlu dikonfirmasi pada perangkat Windows/KACA.ID pengguna. Jalur Canon EDSDK tidak diubah.

Build Windows: npm.cmd run dist:win
