KACA.ID v0.9.50 — FIX FRAME FLOW, VOUCHER, QRIS, DAN PREVIEW LAG

PERBAIKAN
1. Tombol LANJUT setelah pemilihan frame dikunci sampai inisialisasi kamera dan handler mulai sesi siap. Handler memiliki status loading, try/catch, dan pemulihan tombol bila sesi gagal dibuat.
2. Preview frame dibatasi agar selalu proporsional dan tidak melewati kolom preview. Gambar memakai contain dan batas ukuran 88% dari area preview.
3. Menu Voucher kini menjadi generator dan pengelola voucher. Kode otomatis terdiri dari 5 karakter huruf besar/angka, unik, dapat dibuat massal (1–1000), dengan masa berlaku dan batas penggunaan yang dapat diatur. Admin juga dapat membuat satu kode custom 3–32 karakter.
4. Customer yang memilih Voucher diminta memasukkan kode. Backend memvalidasi kode, tanggal kedaluwarsa, status aktif, dan kuota. Kuota baru dipotong ketika sesi berhasil dimulai, bukan saat validasi awal.
5. Menu Pembayaran dapat menyimpan gambar QRIS statis merchant, nama merchant, nominal, dan instruksi. Customer melihat QRIS dan harus memasukkan PIN operator setelah pembayaran diverifikasi manual.
6. Preview kamera diturunkan menjadi 15 FPS kamera utama / 10 FPS kamera kedua dan JPEG quality 76 untuk mengurangi beban CPU. Resolusi frame kamera untuk proses capture tetap dipertahankan.

CATATAN QRIS
Versi ini menyediakan QRIS statis dengan pemeriksaan manual oleh operator. QRIS dinamis, status pembayaran otomatis, refund, dan rekonsiliasi memerlukan kredensial serta integrasi API payment gateway (contoh Midtrans/DOKU). Jangan menganggap pembayaran berhasil hanya dari tampilan QR.

PENYIMPANAN DATA
Voucher disimpan pada data/vouchers.json. Gambar QRIS dan konfigurasinya disimpan pada data/qris-static.png dan data/qris-config.json. Data tidak disimpan di source folder pengguna.

PENGUJIAN
Jalankan seluruh skrip pada folder tests. Pengujian fisik kamera, QRIS merchant asli, dan build installer Windows tetap perlu dilakukan pada komputer booth.
