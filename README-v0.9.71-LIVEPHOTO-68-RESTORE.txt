KACA.ID v0.9.71 — Pemulihan Live Photo bekerja seperti v0.9.68

MASALAH
- v0.9.68: Live Photo autoplay dan bergerak tetapi preview lebih kecil.
- v0.9.69–v0.9.70: terjadi regresi pada tampilan/jalur video.

PERBAIKAN
- Memulihkan persis blok pemutaran media (WebM => MP4 => GIF cadangan) dari src/app.js v0.9.68.
- Hanya menormalkan lebar, tinggi, dan rasio dua kolom preview agar video memenuhi bidang yang sama dengan JPG.
- Tidak memprioritaskan GIF; WebM kembali menjadi prioritas utama.
- Tetap menjaga filter Sketsa/Kartun dan scroll filter + tombol Lanjutkan tetap diam dari versi terbaru.
- Backend kamera, Google Drive, QR, print, dan pembayaran tidak diubah.

INSTALASI
Tutup aplikasi. Backup folder sumber. Ekstrak PATCH ke folder akar v0.9.70 (yang berisi package.json), overwrite. Jalankan run-kaca-id.bat, lakukan satu sesi dan periksa gerakan Live Photo serta ukuran frame.
Jika masih memakai v0.9.69, gunakan FULL SOURCE v0.9.71 agar perubahan filter scroll dan pemulihan media ikut terpasang.

PENGUJIAN
Pemeriksaan source/sintaks dapat dilakukan secara lokal; autoplay yang terbukti pada mesin booth tetap memerlukan uji satu sesi foto sungguhan.
