KACA.ID v0.9.72 — Hasil sesi Live Photo: WebM utama, tanpa GIF dalam preview.

Perubahan terbatas frontend slide hasil:
- output_live.webm diutamakan untuk autoplay muted loop.
- Jika WebM tidak berhasil diputar/didekode, coba output_live.mp4.
- Jika kedua video gagal, tampilkan JPG statis sebagai placeholder; tidak memuat GIF animasi.
- Elemen GIF animasi dihapus dari slide hasil agar tidak menutupi video.
- Ukuran dua panel mengikuti layout 50:50 v0.9.71; tanpa tombol play/pause.
- QR, filter Sketsa/Kartun, scroll filter, kamera dan backend tidak diubah.

Pemasangan patch: tutup KACA.ID, backup source v0.9.71, lalu salin isi folder patch ke folder utama aplikasi (sejajar package.json). Jalankan ulang dengan run-kaca-id.bat.
Catatan: pengujian nyata pada kamera Windows/Electron Anda masih diperlukan.
