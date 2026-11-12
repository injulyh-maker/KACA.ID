KACA.ID v0.9.47 — PEMBARUAN UI BERDASARKAN SCREENSHOT

Pembaruan ini mengganti tampilan customer flow agar mengikuti screenshot referensi:
- Slide 2: metode transaksi pada latar biru navy, judul serif putih, dua tombol besar putih.
- Slide 3: pemilihan frame dengan galeri di kiri dan preview frame besar di kanan.
- Slide 4: preview kamera besar, tombol shutter bulat di tengah bawah, saklar kamera di kiri bawah, mirror di kanan bawah, tray foto horizontal dan retake di kanan.
- Slide 5: preview hasil ber-frame di kiri, daftar foto di tengah, pilihan filter di kanan.
- Slide 6: hasil foto di kiri, QR Google Drive dan tombol berbagi/cetak di kanan.
- Header/eyebrow customer flow dan tulisan merek di kiri atas disembunyikan agar tidak muncul pada slide pelanggan.

Perubahan ini berfokus pada CSS/layout. Handler kamera, retake, frame, filter, render, QR, Live Photo, WhatsApp, email, dan cetak dipertahankan.

Build Windows x64:
  npm.cmd run dist:win
