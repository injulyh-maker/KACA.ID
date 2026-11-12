KACA.ID v0.9.62 — PERBAIKAN ALUR HASIL & POSISI TRANSAKSI

Perubahan:
1. Tombol LANJUT KE HASIL tidak lagi menunggu proses render preview sampai 120 detik. Finalisasi sesi langsung dikirim ke backend; render JPG/Live Photo, arsip lokal, dan Google Drive tetap berjalan di latar belakang pada halaman hasil.
2. Jika endpoint finalisasi gagal, error sekarang diteruskan ke UI agar pesan COBA LAGI menampilkan alasan yang sebenarnya dan sesi tidak dianggap selesai palsu.
3. Tombol LANJUT pada pemilihan frame disinkronkan dengan frame terpilih dan status sesi.
4. Posisi pilihan Voucher dan QRIS diturunkan sedikit pada layar transaksi, tetap berada di area tengah.
5. Semua salinan app.js dan style.css dalam source disinkronkan.

Instalasi source:
- Tutup KACA.ID.
- Cadangkan folder proyek lama.
- Ekstrak source v0.9.62 ke folder baru.
- Jalankan setup.bat bila dependensi belum tersedia.
- Jalankan npm.cmd start untuk pengujian.
- Build installer dengan npm.cmd run dist:win setelah pengujian lulus.

Catatan: perubahan ini tidak mengubah driver kamera, OpenCV, Canon EDSDK, kredensial Google Drive, atau mekanisme pembayaran. Pengujian perangkat keras dan Google Drive harus dilakukan di komputer Windows pemilik aplikasi.
